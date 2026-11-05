"""Complete public intent text only; keys/thinking/results/values never escape."""
import pytest
from data_workspace.sdk_public_notes import safe_public_note
from data_workspace.sdk_dialogue import public_dialogue
from test_sdk_agent import backend

@pytest.mark.parametrize('text',[
    '我会先核对授权字段，再请你确认范围。',
    '接下来核对时间口径，暂不执行。',
    'Please confirm the scope before any query.',
    'I will check the authorized fields before requesting your approval.',
])
def test_generic_future_intent_allowed(text):
    assert safe_public_note(text)==text

@pytest.mark.parametrize('text',[
    '已经执行查询并通过质检。','我会报告结果是100万元。','我会检查 0 行数据。',
    '我会查询三个月销售额。','I will report results are complete.',
    '我会读取 D:\\Users\\person\\secret','我会打开 https://outside.invalid',
    '我会执行 SELECT amount FROM data','我会使用 api_key=secret',
    '我会输出 <script>data</script>','我会展示思考过程。','隐藏分析内容',
    '我会先核对 token 内容','我会输出 `code`','我会核查 '+('x'*501),
])
def test_unsafe_or_unverified_note_omitted(text):
    assert safe_public_note(text) is None


def test_exact_secret_suppressed_without_raw_diagnostic(tmp_path):
    subject=backend(tmp_path)
    assert not subject.record_public_intent('m1','我会核对 fixture-only-not-a-credential','fixture-only-not-a-credential')
    assert subject.events==[] and not subject.public_note_ids


def test_public_intent_bounded_deduplicated_and_cannot_change_plan(tmp_path):
    subject=backend(tmp_path)
    before=(subject.plan_hash,subject.confirmed,subject.submitted,subject.publication)
    for i in range(4): assert subject.record_public_intent(f'm{i}','我会先核对授权字段。')
    assert not subject.record_public_intent('m0','我会更改任务。')
    assert not subject.record_public_intent('m5','我会继续说明。')
    assert (subject.plan_hash,subject.confirmed,subject.submitted,subject.publication)==before
    dialogue=public_dialogue(subject.events,[])
    assert len(dialogue)==4 and all(d.origin=='model_public_intent' and not d.tools for d in dialogue)


def test_notes_not_allowed_after_submit_or_publication(tmp_path):
    subject=backend(tmp_path);subject.submitted=True
    assert not subject.record_public_intent('m','我会先核对字段。')
    subject.submitted=False;subject.publication={'published':True}
    assert not subject.record_public_intent('m','我会先核对字段。')
    assert not subject.events


def test_api_mirror_rechecks_note_and_preserves_fact_order():
    events=[{'type':'MODEL_PUBLIC_INTENT','text':'我会先核对字段。'},
            {'type':'METADATA_READ','table':'main.data'},
            {'type':'MODEL_PUBLIC_INTENT','text':'我会报告总计100。'},
            {'type':'MODEL_PUBLIC_INTENT','text':'我会核对 fixture-key'},
            {'type':'CHECKING'}]
    dialogue=public_dialogue(events,[],secret='fixture-key')
    assert [d.origin for d in dialogue]==['model_public_intent','governed_event','governed_event']
    assert all('100' not in d.text and 'fixture-key' not in d.text for d in dialogue)


def test_complete_text_blocks_join_same_id_only_when_tool_arrives():
    from data_workspace.sdk_public_notes import PublicIntentMessageBuffer
    buffer=PublicIntentMessageBuffer()
    buffer.add_text('m1','我会核对授权字段。')
    buffer.add_text('m1','接下来请确认范围。')
    assert buffer.for_tool('other')==''
    assert buffer.for_tool('m1')=='我会核对授权字段。\n接下来请确认范围。'
    assert buffer.for_tool('m1')==''


def test_bad_later_block_poisoned_whole_message_no_prefix_leak():
    from data_workspace.sdk_public_notes import PublicIntentMessageBuffer
    buffer=PublicIntentMessageBuffer(secret='fixture-secret')
    buffer.add_text('m1','我会核对授权字段。')
    buffer.add_text('m1','我会报告100万元。')
    buffer.add_text('m1','我会核对范围。')
    assert buffer.for_tool('m1')=='' and not buffer.notes
    assert '100万元' not in repr(buffer.__dict__)


def test_message_buffer_is_bounded_and_never_retains_unsafe_content():
    from data_workspace.sdk_public_notes import PublicIntentMessageBuffer
    buffer=PublicIntentMessageBuffer(max_messages=2)
    buffer.add_text('m1','我会核对字段。');buffer.add_text('m2','already published private details')
    buffer.add_text('m3','我会核对范围。')
    assert len(buffer.seen)==2 and buffer.for_tool('m3')==''
    assert 'private details' not in repr(buffer.__dict__)
