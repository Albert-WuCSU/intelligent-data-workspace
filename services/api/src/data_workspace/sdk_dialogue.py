"""Public execution summaries derived from allowlisted facts, never model thinking."""
from .agent_contracts import AgentDialogueEntry

FACTS = {
    'TABLES_DISCOVERED': ('已列出本次授权绑定的表；这里只包含当前单表，不代表整个数仓目录已接入。', ['list_authorized_tables']),
    'FIELDS_DISCOVERED': ('已检索实际授权字段；没有读取结果行，也不推断分区或关联键。', ['search_authorized_fields']),
    'TOPIC_TEMPLATE_LOADED': ('L1未匹配，已加载由批准口径派生的单表主题SQL模板。口径和字段仍受治理，执行前需另确认。', ['load_topic_sql_template']),
    'SKILL_LOADED': ('已加载受治理取数技能。我会先核对已发布指标，再在授权范围内确认需要的字段。', ['data-query Skill']),
    'PLAN_READY': ('查询计划已通过字段、指标与粒度检查；我会请你核对口径，确认前不会取数。', ['propose_metric_query']),
    'AWAITING_CONFIRMATION': ('请确认本次指标、范围和单位。只有你明确确认后，才会提交查询。', ['request_confirmation']),
    'CONFIRMED': ('已收到你的执行确认，继续核验当前计划和权限。', []),
    'EXECUTING': ('正在通过受治理MCP读取完整匹配数据并执行聚合，不用预览行推算总体。', ['execute_approved_query']),
    'CHECKING': ('已收到执行回执，正在检查结果结构、单位和数据质量；质检未通过不会发布为成功。', ['automatic QA']),
    'PUBLISHED': ('执行与质量回执已核验，结果已发布。下面整理口径、结果和限制供你核对。', ['receipt-gated publication']),
    'CLARIFICATION_TIMED_OUT': ('等待补充口径已超时，本次未执行。请整理口径后重新提问。', []),
    'CLARIFICATION_LIMIT': ('澄清次数已到上限，本次未执行。请整理完整范围后再提问。', []),
}

def public_dialogue(events, turns, secret=''):
    result=[]
    asked=answered=0
    for index, event in enumerate(events[-100:]):
        if not isinstance(event,dict): continue
        kind=event.get('type')
        text=None;tools=[];role='update';origin='governed_event'
        if kind=='PLAN_READY' and event.get('engine')=='topic_sql':
            text='单表主题模板的参数计划已通过字段、指标和粒度检查；请核对口径，确认前不会取数。'
            tools=['propose_topic_query']
        elif kind in FACTS: text,tools=FACTS[kind]
        elif kind=='ROUTE_READY':
            matched=event.get('metric_matched') is True
            text=('已匹配到已发布指标，优先采用指标口径；接下来核对字段和范围。' if matched else
                  '尚未匹配到已发布指标，需要进一步确认口径。可检查本任务已批准口径派生的单表模板；不会偷偷转到未授权自由SQL或尚未接入的RAG路径。')
            tools=['search_semantics']
        elif kind=='METADATA_READ':
            table=event.get('table')
            if not isinstance(table,str) or len(table)>200: continue
            text=f'已读取授权表 {table} 的字段元数据。我会基于这些真实字段检查分组和筛选，不猜测列名或读取样例行作为总体。'
            tools=['read_authorized_metadata']
        elif kind=='CLARIFICATION':
            if asked>=len(turns): continue
            text=turns[asked].question;asked+=1;role='clarification'
        elif kind=='CLARIFICATION_ANSWERED':
            if answered>=len(turns) or not turns[answered].answer: continue
            turn=turns[answered];answered+=1
            if not secret or secret not in turn.answer:
                result.append(AgentDialogueEntry(id=f'answer-{turn.clarification_id}',kind='user',text=turn.answer,origin='user_answer'))
            text='已收到你的补充，继续同一任务。旧计划和确认已失效，我会按补充口径重新规划，再请你确认执行。'
        if text and (not secret or secret not in text):
            result.append(AgentDialogueEntry(id=f'event-{index}-{kind}',kind=role,text=text[:1600],tools=tools,origin=origin))
    return result[-50:]
