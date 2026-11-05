"""Bounded L2 templates and L3 metadata on owned synthetic snapshots only."""
import asyncio
from uuid import uuid4
import pytest
from data_workspace.auth import PublicError
from data_workspace.sdk_agent_backend import SdkBudget
from data_workspace.warehouse.aggregate_contract import AggregateRequest,schema_hash
from data_workspace.warehouse.local_file import LocalFileWarehouse
from test_sdk_agent import backend,metric


def ready(tmp_path):
    subject=backend(tmp_path)
    subject.record_skill("governed:data-query","a"*64)
    return subject

def test_discovery_is_actual_bound_metadata_without_rows_or_partitions(tmp_path):
    subject=ready(tmp_path)
    tables=subject.list_authorized_tables()
    assert len(tables['tables'])==1 and tables['tables'][0]['id']=='t0'
    assert tables['rows_read'] is False and tables['partitions'] is None
    assert tables['approved_topic_metrics']==[{'id':'total','name':'Total amount'}]
    fields=subject.search_authorized_fields('t0','REG')
    assert fields['fields']==[{'name':'region','type':'VARCHAR'}] and fields['rows_read'] is False
    assert subject.search_authorized_fields('t0','notthere')['fields']==[]
    with pytest.raises(PublicError): subject.search_authorized_fields('other','')
    with pytest.raises(PublicError): subject.search_authorized_fields('t0','x'*201)
    assert not subject.submitted and subject.publication is None

def test_template_l1_priority_metric_auth_and_route_invalidation(tmp_path):
    subject=ready(tmp_path)
    route=subject.search_semantics('total amount')
    with pytest.raises(PublicError) as exc: subject.load_topic_sql_template(route['route_receipt'],'total')
    assert exc.value.code=='SDK_METRIC_ROUTE_REQUIRED'
    route=subject.search_semantics('unmapped custom request')
    with pytest.raises(PublicError): subject.load_topic_sql_template(route['route_receipt'],'invented')
    template=subject.load_topic_sql_template(route['route_receipt'],'total')
    assert template['metric']==metric().model_dump(mode='json')
    assert template['readonly'] and not template['join_available'] and 'binding' not in template
    proposal=subject.propose_topic_query(route['route_receipt'],template['template_receipt'],['region'],filters=[{'column':'amount','operator':'gte','values':[100]}])
    assert proposal['engine']=='topic_sql' and subject.query_path=='L2' and not subject.submitted
    assert '?' in subject.plan_sql and '100' not in subject.plan_sql
    changed=subject.search_semantics('another unmapped intent')
    with pytest.raises(PublicError) as exc: subject.propose_topic_query(changed['route_receipt'],template['template_receipt'],[])
    assert exc.value.code=='SDK_TOPIC_TEMPLATE_EXPIRED'

def test_topic_receipt_bound_to_task_and_clarification_round(tmp_path):
    subject=ready(tmp_path)
    subject.binding_hash='task-a'
    route=subject.search_semantics('unmapped custom request')
    template=subject.load_topic_sql_template(route['route_receipt'],'total')
    subject.binding_hash='task-b'
    second=subject.load_topic_sql_template(route['route_receipt'],'total')
    assert template['template_receipt']!=second['template_receipt']
    with pytest.raises(PublicError):subject.propose_topic_query(route['route_receipt'],template['template_receipt'],[])
    subject.clarification_turns.append({'question':'scope','answer':'all'})
    with pytest.raises(PublicError):subject.propose_topic_query(route['route_receipt'],second['template_receipt'],[])

def test_same_id_forged_metric_definition_never_executes(tmp_path):
    subject=ready(tmp_path);route=subject.search_semantics('unmapped custom request')
    description=LocalFileWarehouse(subject.database).describe('t0')
    base=AggregateRequest(table='t0',schema_hash=schema_hash(description),metric=metric(),grain=['id']).model_dump(mode='json')
    for changed in ({'column':'cost'},{'unit':'forged currency'},{'name':'fake title'},{'additive':False}):
        spec={**base,'metric':{**base['metric'],**changed}}
        with pytest.raises(PublicError) as exc: subject.propose_sql_query(route['route_receipt'],spec)
        assert exc.value.code=='SDK_METRIC_DENIED'
    assert not subject.submitted and subject.publication is None

def test_template_real_mcp_qa_and_publication_and_no_replanning_after_submit(tmp_path):
    subject=ready(tmp_path);route=subject.search_semantics('unmapped custom request')
    template=subject.load_topic_sql_template(route['route_receipt'],'total')
    proposal=subject.propose_topic_query(route['route_receipt'],template['template_receipt'],['region'],filters=[{'column':'amount','operator':'gte','values':[100]}])
    async def scenario():
        async def explicit_user(name,value): subject.approve_confirmation(value)
        subject.event_handler=explicit_user
        confirmed=await subject.request_confirmation(proposal['plan_hash'])
        result=await subject.execute_approved_query(proposal['plan_hash'],confirmed['confirmation_id'],str(uuid4()))
        assert result['publication_status']=='PUBLISHED'
        assert subject.publication['query_path']=='L2' and subject.publication['quality_receipt']['status']=='PASS'
        data=subject.publication['result']
        assert data['input_rows']==150 and data['matched_rows']==51 and len(data['rows'])==2
        assert sum(row[-1] for row in data['rows'])==6375
        with pytest.raises(PublicError):subject.propose_topic_query(route['route_receipt'],template['template_receipt'],[])
        assert subject.publication['result']==data
    asyncio.run(scenario())

def test_discovery_and_template_reads_share_metadata_budget():
    budget=SdkBudget(max_metadata_calls=2)
    budget.tool('list_authorized_tables');budget.tool('search_authorized_fields')
    with pytest.raises(PublicError) as exc:budget.tool('load_topic_sql_template')
    assert exc.value.code=='SDK_METADATA_BUDGET_EXCEEDED' and budget.metadata_calls==3


def test_unloaded_skill_cannot_discover_or_load_templates(tmp_path):
    subject=backend(tmp_path)
    for action in (lambda:subject.list_authorized_tables(),lambda:subject.search_authorized_fields('t0',''),
                   lambda:subject.load_topic_sql_template('invented','total')):
        with pytest.raises(PublicError):action()
    assert not subject.submitted


def test_template_schema_change_invalidates_before_confirmation(tmp_path,monkeypatch):
    subject=ready(tmp_path);route=subject.search_semantics('unmapped custom request')
    template=subject.load_topic_sql_template(route['route_receipt'],'total')
    original=LocalFileWarehouse.describe
    def changed(self,table):
        description=original(self,table)
        description={**description,'fields':[*description['fields'],{'name':'changed','type':'VARCHAR'}]}
        return description
    monkeypatch.setattr(LocalFileWarehouse,'describe',changed)
    with pytest.raises(PublicError) as exc:subject.propose_topic_query(route['route_receipt'],template['template_receipt'],[])
    assert exc.value.code=='SDK_SCHEMA_CHANGED' and not subject.submitted


def test_web_free_sql_stays_disabled_even_with_template(tmp_path):
    subject=ready(tmp_path);subject.allow_sql_path=False
    route=subject.search_semantics('unmapped custom request')
    template=subject.load_topic_sql_template(route['route_receipt'],'total')
    desc=LocalFileWarehouse(subject.database).describe('t0')
    spec=AggregateRequest(table='t0',schema_hash=schema_hash(desc),metric=metric(),grain=['id'])
    with pytest.raises(PublicError) as exc:subject.propose_sql_query(route['route_receipt'],spec.model_dump(mode='json'))
    assert exc.value.code=='SDK_SQL_PATH_UNSUPPORTED'
    proposal=subject.propose_topic_query(route['route_receipt'],template['template_receipt'],[])
    assert proposal['engine']=='topic_sql' and subject.query_path=='L2'
