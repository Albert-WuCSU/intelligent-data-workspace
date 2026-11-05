"""Public conventional-Agent dialogue: real-event summaries, no thinking/payload."""
from data_workspace.sdk_dialogue import public_dialogue
from data_workspace.agent_contracts import AgentClarificationTurn

def test_public_dialogue_interleaves_tools_question_answer_and_continuation():
    turns=[AgentClarificationTurn(clarification_id='q1',question='Which scope?',answer='All time')]
    events=[{'type':'SKILL_LOADED'}, {'type':'ROUTE_READY','metric_matched':True},
            {'type':'METADATA_READ','table':'main.data'}, {'type':'CLARIFICATION'},
            {'type':'CLARIFICATION_ANSWERED'}, {'type':'PLAN_READY'}, {'type':'AWAITING_CONFIRMATION'},
            {'type':'CONFIRMED'}, {'type':'EXECUTING'}, {'type':'CHECKING'}, {'type':'PUBLISHED'}]
    dialogue=public_dialogue(events,turns)
    assert [d.kind for d in dialogue][3:6]==['clarification','user','update']
    assert dialogue[3].text=='Which scope?' and dialogue[4].text=='All time'
    assert '同一任务' in dialogue[5].text
    assert dialogue[0].tools==['data-query Skill']
    assert dialogue[-1].tools==['receipt-gated publication']
    assert len(set(d.id for d in dialogue))==len(dialogue)
    assert 'main.data' in dialogue[2].text

def test_public_dialogue_does_not_emit_unknown_payload_thought_rows_or_secrets():
    events=[{'type':'thinking','text':'hidden thought'}, {'type':'TOOL_USE','name':'Bash','input':'secret-key'},
            {'type':'METADATA_READ','table':'secret-key'}, {'type':'PUBLISHED','rows':[[9999]],'sql':'secret sql'},
            {'type':'METADATA_READ','table':123}]
    dialogue=public_dialogue(events,[],secret='secret-key')
    assert len(dialogue)==1 and dialogue[0].id=='event-3-PUBLISHED'
    output=' '.join(d.model_dump_json() for d in dialogue)
    for prohibited in ('hidden thought','Bash','secret-key','9999','secret sql'): assert prohibited not in output

def test_unmatched_metric_does_not_claim_l2_l3_rag_already_available():
    dialogue=public_dialogue([{'type':'ROUTE_READY','metric_matched':False}],[])
    assert '尚未匹配' in dialogue[0].text and '不会偷偷转到' in dialogue[0].text
    assert dialogue[0].tools==['search_semantics']

def test_two_clarification_rounds_order_and_bounded_output():
    turns=[AgentClarificationTurn(clarification_id=f'q{i}',question=f'scope{i}',answer=f'answer{i}') for i in range(2)]
    dialogue=public_dialogue([{'type':'CLARIFICATION'},{'type':'CLARIFICATION_ANSWERED'},{'type':'CLARIFICATION'},{'type':'CLARIFICATION_ANSWERED'}],turns)
    assert [d.text for d in dialogue if d.kind=='user']==['answer0','answer1']
    assert len(public_dialogue([{'type':'CHECKING'}]*200,[]))==50


def test_topic_plan_public_tool_label_matches_actual_route():
    dialogue=public_dialogue([{'type':'TOPIC_TEMPLATE_LOADED'},{'type':'PLAN_READY','engine':'topic_sql'}],[])
    assert dialogue[0].tools==['load_topic_sql_template']
    assert dialogue[1].tools==['propose_topic_query'] and '模板' in dialogue[1].text
