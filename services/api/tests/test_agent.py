"""Real full-row aggregate and graph flow on owned fixtures; model only fake HTTP responses."""
import asyncio,json
from pathlib import Path
from uuid import uuid4
from datetime import date
import pytest,httpx
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.semantic_store import SemanticStore
from data_workspace.semantic_contracts import SemanticDraftInput,PublishInput
from data_workspace.semantic_metadata import read_schema
from data_workspace.contracts import AuthContext
from data_workspace.model_provider import ModelConfiguration,MessagesProvider
from data_workspace.model_budget import EstimatedBudget
from data_workspace.warehouse.local_file import LocalFileWarehouse
from data_workspace.warehouse.aggregate_contract import AggregateRequest,AggregateTime,schema_hash,compile_aggregate,validate_aggregate
from data_workspace.warehouse.aggregate_engine import execute_aggregate
from data_workspace.warehouse.aggregate_client import AggregateMCPClient
from data_workspace.warehouse.aggregate_server import AggregateExecution
from data_workspace.auth import PublicError
from data_workspace.warehouse.policy import QueryDenied
AUTH=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer');H={'X-Workspace-Request':'1'};BASE='http://127.0.0.1:8000'
KEY='fake-agent-only-key'
def fixture(tmp_path,duplicates=False):
 source=tmp_path/'allowed'/'rows.csv';source.parent.mkdir(parents=True)
 source.write_text('id,region,amount,cost,created_at\n'+''.join(f'{i//2 if duplicates else i},{"A" if i%2 else "B"},{i},1,2026-10-{(i%20)+1:02}\n' for i in range(1,151)),encoding='utf-8')
 store=SourceStore(tmp_path/'connections',source.parent);database,_=store.snapshot(ProfileDraft(name='aggregate fixture',path=str(source),usage_authorized=True));return store,database

def metric(operator='sum'):
 from data_workspace.semantic_contracts import SemanticMetric
 return SemanticMetric(id='total',name='Total',operator=operator,column='amount' if operator=='sum' else None,numerator='cost' if operator=='ratio' else None,denominator='amount' if operator=='ratio' else None,unit='declared units',additive=operator!='ratio')

@pytest.mark.parametrize('operator,expected',[('count_rows',150),('sum',11325),('ratio',150/11325)])
def test_complete_input_aggregate_not_100_preview(tmp_path,operator,expected):
 store,database=fixture(tmp_path);warehouse=LocalFileWarehouse(database);desc=warehouse.describe('t0')
 request=AggregateRequest(table='t0',schema_hash=schema_hash(desc),metric=metric(operator),grain=['id'])
 result=execute_aggregate(warehouse,request);assert result.input_rows==result.matched_rows==150
 assert float(result.rows[0][0])==pytest.approx(expected) and result.full_input_aggregate and not result.truncated
 assert result.duplicate_grain_rows==0 and result.unit=='declared units'


def test_group_time_and_duplicate_grain_quality_real_engine(tmp_path):
 store,database=fixture(tmp_path,duplicates=True);w=LocalFileWarehouse(database);d=w.describe('t0')
 req=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'],dimensions=['region'],time_filter=AggregateTime(column='created_at',start=date(2026,10,1),end_exclusive=date(2026,10,11)))
 result=execute_aggregate(w,req);assert len(result.rows)==2 and result.matched_rows<150 and result.quality=='WARN'
 assert result.duplicate_grain_rows>0
 sql,params,*_=compile_aggregate(req,d);assert sql.count('?')==2 and params==['2026-10-01','2026-10-11'] and 'LIMIT 101' in sql
 for unsafe in [sql+'; DROP TABLE source',sql.replace('SUM("amount")','read_csv(\'x\')'),sql+' -- hack',sql.replace('FROM ','FROM "foreign".')]:
  with pytest.raises(QueryDenied):validate_aggregate(unsafe,sql,d,req)


def test_actual_aggregate_mcp_distinct_contract_idempotent_single_submit(tmp_path):
 async def scenario():
  store,database=fixture(tmp_path);w=LocalFileWarehouse(database);d=w.describe('t0');req=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'])
  async with AggregateMCPClient(AUTH,database=database).connected() as client:
   metadata=await client.call('aggregate_metadata',{'table':'t0'});assert metadata['capability']=='workspace_aggregate_v1'
   key=str(uuid4());first=await client.call('submit_aggregate',{'request':req.model_dump(mode='json'),'idempotency_key':key});assert first['task']['status']=='SUCCEEDED'
   second=await client.call('submit_aggregate',{'request':req.model_dump(mode='json'),'idempotency_key':key});assert first==second
   result=await client.call('aggregate_result',{'task_id':first['task']['id']});assert result['result']['rows']==[[11325]]
   with pytest.raises(PublicError):await client.call('submit_query',{})
 asyncio.run(scenario())

def setup_app(tmp_path,model_plan=None):
 app=create_app(Settings(mode='development',dev_identity=True,sdk_web_agent=False));store,database=fixture(tmp_path);app.state.sources=store;app.state.semantics=SemanticStore(tmp_path/'semantics')
 source=str(uuid4())
 with store.db() as db:db.execute('INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES(?,?,?,?,?,?,?,?)',[source,store.owner(AUTH),'actual fixture',1,1,str(database),'independent fixture','2026-11-02'])
 body=SemanticDraftInput(domain='orders',name='Totals',owner_note='fixture only',source_id=source,table_id='t0',grain=['id'],grain_note='per record',metrics=[metric()])
 draft=app.state.semantics.draft(AUTH,body);schema=asyncio.run(read_schema(store,AUTH,source,'t0'));published=app.state.semantics.publish(AUTH,PublishInput(draft_id=draft.draft_id,validation_id=str(uuid4()),request_id=str(uuid4()),approve_definition=True),draft,schema)
 calls=[]
 def handler(req):
  calls.append(json.loads(req.content));assert KEY not in req.content.decode();assert 'rows' not in calls[-1]['messages'][0]['content']
  return httpx.Response(200,json={'type':'message','role':'assistant','model':'fixture-model','stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(model_plan or {'metric_id':'total','dimensions':[],'time_range':None,'needs_clarification':'none'})}],'usage':{'input_tokens':50,'output_tokens':30}})
 app.state.model_provider=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','fixture-model','anthropic_messages','bearer'),KEY,EstimatedBudget(tmp_path/'budget'),httpx.MockTransport(handler));app.state.model_provider._verified=True;app.state.model_enabled=True
 return app,source,published,calls

def request_body(app,source,version,**changes):return {'request_id':str(uuid4()),'question':'What is total amount?','model_ref':app.state.model_tests.generation+':'+app.state.model_provider.configuration.version,'semantic_version_id':version.id,'selected_source_refs':[source],'accept_model_egress':True,**changes}

def wait(c,id,phase=None):
 import time
 for _ in range(250):
  t=c.get('/api/v1/agent/tasks/'+id).json()
  if phase is not None and t['phase']==phase:return t
  if t['phase'] not in ('PLANNING','VALIDATING','EXECUTING','CHECKING'):return t
  time.sleep(.04)
 raise AssertionError('bounded task did not finish')

def test_real_graph_model_plan_human_interrupt_aggregate_result_replay(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  body=request_body(app,source,v);r=c.post('/api/v1/agent/tasks',json=body,headers=H);assert r.status_code==200,r.text
  t=wait(c,r.json()['id']);assert t['phase']=='AWAITING_CONFIRMATION',t
  assert not t['sql_executed'] and len(calls)==1
  assert c.post('/api/v1/agent/tasks',json=body,headers=H).json()['id']==t['id']
  assert c.post('/api/v1/agent/tasks',json={**body,'question':'different'},headers=H).status_code==409
  confirm={'plan_hash':t['plan_hash'],'execution_generation':t['execution_generation'],'confirm_execute':True}
  r=c.post('/api/v1/agent/tasks/'+t['id']+'/confirm',json=confirm,headers=H);assert r.status_code==200
  result=wait(c,t['id']);assert result['phase']=='SUCCEEDED',result
  assert result['result']['rows']==[[11325]] and result['result']['input_rows']==150 and result['sql_executed']
  old=result['execution_receipt'];c.post('/api/v1/agent/tasks/'+t['id']+'/confirm',json=confirm,headers=H)
  assert c.get('/api/v1/agent/tasks/'+t['id']).json()['execution_receipt']==old and len(calls)==1
  assert app.state.model_provider.budget.summary().reserved_requests==1
  assert KEY not in json.dumps(result) and not result['result']['truncated']

@pytest.mark.parametrize('model_plan,phase,code',[({'metric_id':'forbidden'},'FAILED','AGENT_METRIC_DENIED'),({'metric_id':'total','dimensions':['foreign']},'FAILED','AGENT_FIELD_DENIED'),({'needs_clarification':'metric'},'NEEDS_CLARIFICATION',None),({'sql':'DROP TABLE anything'},'FAILED','AGENT_MODEL_PLAN_INVALID')])
def test_model_invalid_or_ambiguous_plan_never_executes(tmp_path,model_plan,phase,code):
 app,source,v,calls=setup_app(tmp_path,model_plan)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);t=wait(c,r.json()['id'])
  assert t['phase']==phase and t['error_code']==code and not t['sql_executed'] and not t['execution_receipt']
  assert len(calls)==1


def test_expired_model_or_semantic_confirmation_no_sql_and_no_second_model_call(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);t=wait(c,r.json()['id'])
  app.state.model_enabled=False
  c.post('/api/v1/agent/tasks/'+t['id']+'/confirm',json={'plan_hash':t['plan_hash'],'execution_generation':t['execution_generation'],'confirm_execute':True},headers=H)
  result=wait(c,t['id']);assert result['phase']=='EXPIRED' and not result['sql_executed'] and not app.state.agent.records[t['id']]['submitted']
  assert len(calls)==1


def test_agent_refuses_privilege_or_egress_missing_before_model(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  body=request_body(app,source,v)
  for changes,status in [({'accept_model_egress':False},422),({'tenant_id':'evil'},422),({'model_ref':'forged'},409),({'selected_source_refs':[str(uuid4())]},403),({'question':KEY},422)]:
   assert c.post('/api/v1/agent/tasks',json={**body,**changes},headers=H).status_code==status
  assert not calls and not app.state.agent.tasks
  assert c.post('/api/v1/agent/tasks',json=body).status_code==403

@pytest.mark.parametrize('fault',['time_without_definition','context_overflow','source_changed','schema_changed','pack_disabled'])
def test_governed_plan_context_conditions_fail_before_sql(tmp_path,fault):
 model_plan={'metric_id':'total','time_range':{'start':'2026-10-01','end_exclusive':'2026-10-11'}} if fault=='time_without_definition' else None
 app,source,v,calls=setup_app(tmp_path,model_plan)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  b=request_body(app,source,v,question='q'*1590 if fault=='context_overflow' else 'sum all')
  r=c.post('/api/v1/agent/tasks',json=b,headers=H);task=wait(c,r.json()['id'])
  if fault=='time_without_definition':assert task['phase']=='NEEDS_CLARIFICATION' and not task['sql_executed'];return
  if fault=='context_overflow':assert task['error_code']=='AGENT_CONTEXT_LIMIT' and not calls;return
  if fault=='source_changed':
   with app.state.sources.db() as db:db.execute('UPDATE profiles SET version=2 WHERE id=?',[source])
  if fault=='schema_changed':
   original=app.state.sources.call
   async def changed(*args,**kwargs):
    result=await original(*args,**kwargs);result['metadata']['fields'][2]['type']='VARCHAR';return result
   app.state.sources.call=changed
  if fault=='pack_disabled':
   from data_workspace.semantic_contracts import SemanticStateInput
   app.state.semantics.toggle(AUTH,v.pack_id,SemanticStateInput(expected_version=1,expected_state_revision=0,enabled=False))
  c.post('/api/v1/agent/tasks/'+task['id']+'/confirm',json={'plan_hash':task['plan_hash'],'execution_generation':task['execution_generation'],'confirm_execute':True},headers=H)
  t=wait(c,task['id']);assert t['phase']=='EXPIRED' and not t['sql_executed'] and not app.state.agent.records[t['id']]['submitted']
  assert len(calls)==1


def test_graph_replays_one_confirm_under_concurrency_and_unknown_submit_not_retried(tmp_path,monkeypatch):
 app,source,v,calls=setup_app(tmp_path)
 from data_workspace.warehouse.aggregate_client import AggregateMCPClient
 original=AggregateMCPClient.call;submits=[]
 async def drop_result(self,name,args=None):
  if name=='submit_aggregate':submits.append(args);await original(self,name,args);raise RuntimeError('lost acknowledgement, must not resubmit')
  return await original(self,name,args)
 monkeypatch.setattr(AggregateMCPClient,'call',drop_result)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);task=wait(c,r.json()['id']);body={'plan_hash':task['plan_hash'],'execution_generation':task['execution_generation'],'confirm_execute':True}
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(2) as executor:responses=list(executor.map(lambda _:c.post('/api/v1/agent/tasks/'+task['id']+'/confirm',json=body,headers=H),range(2)))
  assert all(r.status_code==200 for r in responses)
  t=wait(c,task['id']);assert t['phase']=='UNKNOWN' and len(submits)==1 and t['result'] is None
  c.post('/api/v1/agent/tasks/'+task['id']+'/confirm',json=body,headers=H);assert len(submits)==1 and len(calls)==1


def test_cancel_waiting_human_never_calls_mcp_or_replays_model(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);task=wait(c,r.json()['id'])
  cancelled=c.post('/api/v1/agent/tasks/'+task['id']+'/cancel',json={},headers=H).json();assert cancelled['phase']=='CANCELLED'
  c.post('/api/v1/agent/tasks/'+task['id']+'/confirm',json={'plan_hash':task['plan_hash'],'execution_generation':task['execution_generation'],'confirm_execute':True},headers=H)
  assert not app.state.agent.records[task['id']]['submitted'] and len(calls)==1


def test_graph_respects_disabled_tracing_even_with_host_trace_enabled(tmp_path,monkeypatch):
 # No real secret; confirms environment cannot make LangSmith acquire network access.
 monkeypatch.setenv('LANGSMITH_TRACING','true');monkeypatch.setenv('LANGCHAIN_TRACING_V2','true');monkeypatch.setenv('LANGSMITH_API_KEY','fake-host-do-not-use')
 from typing import TypedDict
 from langgraph.graph import StateGraph,START,END
 from langgraph.types import interrupt,Command
 from langgraph.checkpoint.memory import InMemorySaver
 from data_workspace.graph_runtime import no_external_tracing
 async def scenario():
  import socket
  def forbidden(*a,**k):pytest.fail('graph tracing must not use network')
  monkeypatch.setattr(socket.socket,'connect',forbidden)
  class State(TypedDict):value:int
  g=StateGraph(State);g.add_node('approve',lambda s:{'value':2} if interrupt({'value':s['value']}) is True else {'value':0});g.add_edge(START,'approve');g.add_edge('approve',END);compiled=g.compile(checkpointer=InMemorySaver());cfg={'configurable':{'thread_id':'isolated'},'callbacks':[]}
  with no_external_tracing():
   first=await compiled.ainvoke({'value':1},cfg);assert '__interrupt__' in first
   done=await compiled.ainvoke(Command(resume=True),cfg);assert done['value']==2
 asyncio.run(scenario())


def test_zero_denominator_empty_and_group_limits_not_fake_success(tmp_path):
 store,database=fixture(tmp_path);w=LocalFileWarehouse(database);desc=w.describe('t0')
 request=AggregateRequest(table='t0',schema_hash=schema_hash(desc),metric=metric(),grain=['id'],dimensions=['id'])
 with pytest.raises(QueryDenied):execute_aggregate(w,request)
 request=request.model_copy(update={'dimensions':[],'time_filter':AggregateTime(column='created_at',start=date(2020,1,1),end_exclusive=date(2020,1,2))})
 result=execute_aggregate(w,request);assert result.rows==[[None]] and result.matched_rows==0 and result.quality=='WARN'
 # Create distinct actual snapshot for zero denominator; original copied snapshot never edited.
 file=tmp_path/'allowed'/'zeros.csv';file.write_text('id,amount,cost\n1,0,4\n2,0,5\n',encoding='utf-8');zero_db,_=store.snapshot(ProfileDraft(name='zeros',path=str(file),usage_authorized=True));z=LocalFileWarehouse(zero_db);d=z.describe('t0')
 r=execute_aggregate(z,AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric('ratio'),grain=['id']))
 assert r.rows==[[None]] and r.zero_denominator_groups==1 and r.quality=='WARN'


def test_compile_rejects_forged_metadata_or_function_extra_fields(tmp_path):
 store,database=fixture(tmp_path);w=LocalFileWarehouse(database);d=w.describe('t0');body=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id']).model_dump(mode='json')
 for mutation in [{'schema_hash':'a'*64},{'grain':['missing']},{'dimensions':['missing']},{'sql':'SELECT *'}]:
  from pydantic import ValidationError
  with pytest.raises((QueryDenied,ValidationError)):compile_aggregate({**body,**mutation},d)

def test_input_row_budget_actual_source_and_invalid_output_bytebudget(tmp_path):
 store,database=fixture(tmp_path)
 # Current importer deliberately caps snapshots at20000 rows. Do not widen it for this test.
 # Build an independent actual DuckDB boundary fixture to exercise the engine's extra hard cap.
 import duckdb,hashlib
 from data_workspace.warehouse.engine import ENGINE_CONFIG
 db=tmp_path/'boundary.duckdb'
 with duckdb.connect(str(db),config=ENGINE_CONFIG) as con:con.execute('CREATE TABLE main.data AS SELECT range AS id, 1::BIGINT AS amount FROM range(200001)')
 db.with_suffix('.manifest.json').write_text(json.dumps({'database_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'version':'isolated-row-limit-fixture','tables':{'t0':{'schema':'main','name':'data','columns':[{'name':'id','type':'BIGINT'},{'name':'amount','type':'BIGINT'}]}}}),encoding='utf-8')
 w=LocalFileWarehouse(db);d=w.describe('t0');req=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'])
 with pytest.raises(QueryDenied,match='input row budget'):execute_aggregate(w,req)
 # A result can exceed the output byte cap without exceeding 100 groups.
 file=tmp_path/'allowed'/'large-text.csv';file.write_text('id,region,amount\n'+''.join(f'{i},{"x"*4000}{i},1\n' for i in range(60)),encoding='utf-8')
 db,_=store.snapshot(ProfileDraft(name='bigtext',path=str(file),usage_authorized=True));w=LocalFileWarehouse(db);d=w.describe('t0')
 with pytest.raises(QueryDenied,match='result byte budget'):execute_aggregate(w,AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'],dimensions=['region']))


def test_known_key_in_semantic_unit_refused_without_browser_echo(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 # Independent test-only definition may contain accidental Key in a non-prompt field.
 from data_workspace.semantic_contracts import SemanticDraftInput,PublishInput
 value=v.contract.model_copy(deep=True);value.pack_id=v.pack_id;value.expected_version=1;value.metrics[0].unit=KEY
 draft=app.state.semantics.draft(AUTH,value);new=app.state.semantics.publish(AUTH,PublishInput(draft_id=draft.draft_id,validation_id=str(uuid4()),request_id=str(uuid4()),approve_definition=True),draft,v.schema_snapshot)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,new),headers=H)
  assert r.status_code==422 and KEY not in r.text and not calls and not app.state.agent.tasks

@pytest.mark.parametrize('status',[401,403,429,500])
def test_model_access_error_no_sql_no_fallback_budget_retained(tmp_path,status):
 app,source,v,calls=setup_app(tmp_path)
 def rejected(req):calls.append(req);return httpx.Response(status,text='forbidden upstream '+KEY)
 app.state.model_provider.transport=httpx.MockTransport(rejected)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);t=wait(c,r.json()['id'])
  assert t['phase']=='FAILED' and not t['sql_executed'] and KEY not in json.dumps(t)
  assert len(calls)==1 and app.state.model_provider.budget.summary().reserved_requests==1

@pytest.mark.parametrize('data_type',['DATE','TIMESTAMP','TIMESTAMP WITH TIME ZONE'])
def test_explicit_date_or_utc_timestamptz_boundaries_ignore_locked_display_zone(tmp_path,data_type):
 import duckdb,hashlib
 from data_workspace.warehouse.engine import ENGINE_CONFIG
 db=tmp_path/'time-fixture.duckdb'
 with duckdb.connect(str(db),config=ENGINE_CONFIG) as c:
  c.execute(f'CREATE TABLE main.data(id BIGINT, amount BIGINT, created_at {data_type})')
  literals=['2026-09-30 23:59:59+00:00','2026-10-01 00:00:00+00:00'] if data_type=='TIMESTAMP WITH TIME ZONE' else ['2026-09-30','2026-10-01']
  c.executemany('INSERT INTO main.data VALUES(?,?,?)',[(1,5,literals[0]),(2,9,literals[1])])
 db.with_suffix('.manifest.json').write_text(json.dumps({'database_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'version':'timezone-fixture','tables':{'t0':{'schema':'main','name':'data','columns':[{'name':'id','type':'BIGINT'},{'name':'amount','type':'BIGINT'},{'name':'created_at','type':data_type}]}}}),encoding='utf-8')
 class ShanghaiLocked(LocalFileWarehouse):
  def connect(self):
   c=duckdb.connect(str(self.database),read_only=True,config=ENGINE_CONFIG)
   c.execute("SET TimeZone='Asia/Shanghai'");c.execute('SET lock_configuration=true');return c
 w=ShanghaiLocked(db);d=w.describe('t0');r=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'],time_filter=AggregateTime(column='created_at',start=date(2026,10,1),end_exclusive=date(2026,10,2)))
 sql,params,*_=compile_aggregate(r,d)
 assert params==(['2026-10-01T00:00:00+00:00','2026-10-02T00:00:00+00:00'] if data_type=='TIMESTAMP WITH TIME ZONE' else ['2026-10-01','2026-10-02'])
 out=execute_aggregate(w,r);assert out.rows==[[9]] and out.matched_rows==1


def test_time_of_day_cannot_be_date_range(tmp_path):
 store,db=fixture(tmp_path);w=LocalFileWarehouse(db);d=w.describe('t0');d['fields'][-1]['type']='TIME'
 r=AggregateRequest(table='t0',schema_hash=schema_hash(d),metric=metric(),grain=['id'],time_filter=AggregateTime(column='created_at',start=date(2026,1,1),end_exclusive=date(2026,1,2)))
 with pytest.raises(QueryDenied):compile_aggregate(r,d)


def test_plan_model_safe_diagnostics_readonly_no_costly_retry(tmp_path):
 app,source,v,calls=setup_app(tmp_path)
 def truncated(req):
  calls.append(req);return httpx.Response(200,json={'type':'message','role':'assistant','model':'fixture-model','stop_reason':'max_tokens','content':[{'type':'text','text':'truncated '+KEY}],'usage':{'input_tokens':15,'output_tokens':128}})
 app.state.model_provider.transport=httpx.MockTransport(truncated)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/agent/tasks',json=request_body(app,source,v),headers=H);t=wait(c,r.json()['id'])
  assert t['phase']=='FAILED' and t['model_diagnostics']['reason']=='incomplete_output'
  assert KEY not in json.dumps(t) and not t['sql_executed']
  assert c.get('/api/v1/agent/tasks/'+t['id']).json()['model_diagnostics']==t['model_diagnostics']
  assert len(calls)==1 and app.state.model_provider.budget.summary().reserved_requests==1
