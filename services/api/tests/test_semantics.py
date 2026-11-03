"""M03 finite semantic lifecycle with actual metadata, no model or row query."""
import json,asyncio
from uuid import uuid4
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.semantic_store import SemanticStore
from data_workspace.semantic_contracts import SemanticDraftInput,check_contract
from data_workspace.contracts import AuthContext

AUTH=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
H={'X-Workspace-Request':'1'}
BASE='http://127.0.0.1:8000'

def configured(tmp_path,real=False):
    app=create_app(Settings(mode='development',dev_identity=True));app.state.semantics=SemanticStore(tmp_path/'semantics')
    app.state.sources=SourceStore(tmp_path/'connections',tmp_path/'allowed');app.state.sources.allowed_root.mkdir(parents=True)
    path=app.state.sources.allowed_root/'source.csv';path.write_text('id,amount,cost,created_at\n1,10,3,2025-01-01\n2,20,4,2025-01-02\n',encoding='utf-8')
    if real:database,_=app.state.sources.snapshot(ProfileDraft(name='fixture',path=str(path),usage_authorized=True))
    else:database=path
    source=str(uuid4())
    with app.state.sources.db() as db:db.execute('INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES(?,?,?,?,?,?,?,?)',[source,app.state.sources.owner(AUTH),'Semantic source',1,1,str(database),'independent fixture','2026-11-02'])
    calls=[]
    if not real:
        async def call(auth,database,tool,args=None):
            assert tool=='describe_table','must never submit query or preview for semantics'
            assert args=={'table':'t0'};calls.append(tool)
            return {'ok':True,'metadata':{'table':'main.source','fields':[{'name':'id','type':'BIGINT'},{'name':'amount','type':'BIGINT'},{'name':'cost','type':'BIGINT'},{'name':'created_at','type':'DATE'}],'source':'user_provided'}}
        app.state.sources.call=call
    return app,source,calls

def payload(source,**change):
 return {'domain':'sales','name':'Sales definitions','owner_note':'Analyst confirms local fixture only','source_id':source,'table_id':'t0','grain':['id'],'grain_note':'one row per declared id; uniqueness not statistically certified','metrics':[{'id':'amount_sum','name':'Amount','operator':'sum','column':'amount','unit':'declared units','additive':True,'aliases':['total amount']}],**change}
def pipeline(c,source,**change):
 r=c.post('/api/v1/semantics/drafts',json=payload(source,**change),headers=H);assert r.status_code==200,r.text;draft=r.json()
 r=c.post('/api/v1/semantics/drafts/'+draft['draft_id']+'/check',json={},headers=H);assert r.status_code==200,r.text
 return draft,r.json()
def publish_body(draft,check):return {'draft_id':draft['draft_id'],'validation_id':check['validation_id'],'request_id':str(uuid4()),'approve_definition':True}

def test_actual_local_mcp_metadata_only_publish_restart_idempotent_no_rows(tmp_path,monkeypatch):
 app,source,_=configured(tmp_path,real=True)
 from data_workspace.warehouse.local_file import LocalFileWarehouse
 monkeypatch.setattr(LocalFileWarehouse,'preview',lambda *a,**k:pytest.fail('semantics must never read rows'))
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  schema=c.get(f'/api/v1/semantics/sources/{source}/tables/t0/schema');assert schema.status_code==200,schema.text
  assert schema.json()['rows_read'] is False and [f['name'] for f in schema.json()['columns']]==['id','amount','cost','created_at']
  assert not c.get('/api/v1/semantics').json()['versions']
  draft,check=pipeline(c,source);assert check['result']['valid']
  body=publish_body(draft,check);r=c.post('/api/v1/semantics/publish',json=body,headers=H);assert r.status_code==200,r.text
  version=r.json();assert version['version']==1 and version['execution_available'] is False and version['approved_by']=='local-developer'
  assert c.post('/api/v1/semantics/publish',json=body,headers=H).json()==version
  assert c.post(f"/api/v1/semantics/versions/{version['id']}/resolve",json={},headers=H).json()['mapping_verified']
  assert len(c.get('/api/v1/semantics').json()['versions'])==1
  root=app.state.semantics.root;app.state.semantics=SemanticStore(root)
  assert c.get(f"/api/v1/semantics/versions/{version['id']}").json()==version
  assert c.post('/api/v1/semantics/publish',json=body,headers=H).json()==version
  assert c.post(f"/api/v1/semantics/drafts/{draft['draft_id']}/check",json={},headers=H).status_code==404

@pytest.mark.parametrize('change,code',[({'grain':['missing']},'FIELD_MISSING'),({'grain':['id','id']},'GRAIN_DUPLICATE'),({'metrics':[{'id':'m','name':'A','operator':'sum','column':'created_at','unit':'x','additive':True}]},'TYPE_MISMATCH'),({'metrics':[{'id':'m','name':'A','aliases':[' a '],'operator':'count_rows','unit':'rows','additive':True}]},'ALIAS_CONFLICT'),({'time':{'column':'cost','meaning':'not a date','timezone':'UTC'}},'TYPE_MISMATCH')])
def test_conflicts_refuse_publication_and_rows_not_read(tmp_path,change,code):
 app,source,calls=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source,**change);assert not r['result']['valid'] and code in [i['code'] for i in r['result']['issues']]
  assert c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).status_code==409
  assert c.get('/api/v1/semantics').json()['versions']==[] and calls==['describe_table']

@pytest.mark.parametrize('change',[{'tenant_id':'evil'},{'metrics':[{'id':'m','name':'X','operator':'python','unit':'x','additive':True}]},{'metrics':[{'id':'m','name':'X','operator':'ratio','numerator':'amount','denominator':'cost','unit':'ratio','additive':True}]},{'sql':'SELECT *'},{'time':{'column':'created_at','meaning':'created','timezone':'invalid-zone'}},{'grain':[]}])
def test_untrusted_formula_privilege_or_missing_grain_rejected_before_io(tmp_path,change):
 app,source,calls=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/semantics/drafts',json=payload(source,**change),headers=H);assert r.status_code==422 and not calls and not app.state.semantics.drafts

def test_ratio_no_uniform_date_nonadditive_and_zero_null(tmp_path):
 app,source,calls=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source,metrics=[{'id':'cost_ratio','name':'Cost ratio','operator':'ratio','numerator':'cost','denominator':'amount','unit':'ratio','additive':False}])
  assert r['result']['valid'] and d['contract']['time'] is None and d['contract']['metrics'][0]['denominator_zero']=='null'
  assert c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).status_code==200

def test_schema_change_disable_rechecks_and_cross_version_immutable(tmp_path):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);b=publish_body(d,r)
  with app.state.sources.db() as db:db.execute('UPDATE profiles SET version=2 WHERE id=?',[source])
  assert c.post('/api/v1/semantics/publish',json=b,headers=H).json()['code']=='SEMANTIC_MAPPING_STALE'
  d,r=pipeline(c,source);v=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json()
  d2,r2=pipeline(c,source,pack_id=v['pack_id'],expected_version=1,name='New definition')
  v2=c.post('/api/v1/semantics/publish',json=publish_body(d2,r2),headers=H).json();assert v2['version']==2
  assert c.get('/api/v1/semantics/versions/'+v['id']).json()['contract']['name']=='Sales definitions'
  assert c.post('/api/v1/semantics/drafts',json=payload(source,pack_id=v['pack_id'],expected_version=1),headers=H).status_code==409
  with app.state.sources.db() as db:db.execute('UPDATE profiles SET enabled=0,version=3 WHERE id=?',[source])
  assert c.post('/api/v1/semantics/versions/'+v2['id']+'/resolve',json={},headers=H).status_code==409
  assert c.get('/api/v1/semantics/versions/'+v['id']).status_code==200

def test_publish_mismatch_alias_collision_replay_conflict_and_approval(tmp_path):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);body=publish_body(d,r)
  assert c.post('/api/v1/semantics/publish',json={**body,'approve_definition':False},headers=H).status_code==422
  v=c.post('/api/v1/semantics/publish',json=body,headers=H);assert v.status_code==200
  d2,r2=pipeline(c,source)
  assert c.post('/api/v1/semantics/publish',json={**publish_body(d2,r2),'request_id':body['request_id']},headers=H).json()['code']=='SEMANTIC_REQUEST_CONFLICT'
  assert c.post('/api/v1/semantics/publish',json=publish_body(d2,r2),headers=H).json()['code']=='SEMANTIC_ALIAS_CONFLICT'
  assert c.post('/api/v1/semantics/publish',json={**publish_body(d2,r2),'validation_id':r['validation_id']},headers=H).status_code==409
  assert len(c.get('/api/v1/semantics').json()['versions'])==1

def test_auth_origin_body_budget_no_secret_echo_and_no_unknown_source(tmp_path):
 app,source,calls=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  assert c.post('/api/v1/semantics/drafts',json=payload(source)).status_code==403
  assert c.get('/api/v1/semantics',headers={'Origin':'https://evil.example'}).status_code==403
  assert c.post('/api/v1/semantics/drafts',content='x'*40000,headers={**H,'Content-Type':'application/json'}).status_code==413
  assert c.post('/api/v1/semantics/drafts',json=payload(str(uuid4())),headers=H).status_code==404
 with TestClient(create_app(Settings()),base_url=BASE) as c:assert c.get('/api/v1/semantics').status_code==401
 other=AUTH.model_copy(update={'principal_id':'other'})
 from data_workspace.auth import PublicError
 with pytest.raises(PublicError):app.state.semantics.versions(other)
 assert not calls

def test_metadata_malformed_or_schema_drift_rejects_publish_and_resolve(tmp_path):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);b=publish_body(d,r)
  original=app.state.sources.call
  async def changed(*args,**kwargs):
   v=await original(*args,**kwargs);v['metadata']['fields'][1]['type']='VARCHAR';return v
  app.state.sources.call=changed
  assert c.post('/api/v1/semantics/publish',json=b,headers=H).status_code==409
  async def malformed(*args,**kwargs):return {'ok':True,'metadata':{'table':'x','fields':[{'name':'a','type':'INT'},{'name':'a','type':'INT'}]}}
  app.state.sources.call=malformed
  assert c.get(f'/api/v1/semantics/sources/{source}/tables/t0/schema').json()['code']=='SEMANTIC_SCHEMA_INVALID'
  assert not app.state.sources.active

def test_version_transactions_concurrent_replay_and_conflict_are_atomic(tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 from data_workspace.semantic_contracts import PublishInput
 from data_workspace.semantic_metadata import read_schema
 app,source,_=configured(tmp_path);store=app.state.semantics
 body=SemanticDraftInput.model_validate(payload(source));d=store.draft(AUTH,body);schema=asyncio.run(read_schema(app.state.sources,AUTH,source,'t0'));b=PublishInput(draft_id=d.draft_id,validation_id=str(uuid4()),request_id=str(uuid4()),approve_definition=True)
 other=SemanticStore(store.root)
 def publish(s):return s.publish(AUTH,b,d,schema)
 with ThreadPoolExecutor(2) as pool:versions=list(pool.map(publish,[store,other]))
 assert versions[0].id==versions[1].id and len(store.versions(AUTH))==1
 # Same expected version with a different publish ID cannot overwrite the immutable version.
 from data_workspace.auth import PublicError
 with pytest.raises(PublicError):store.publish(AUTH,b.model_copy(update={'request_id':str(uuid4())}),d,schema)
 assert len(store.versions(AUTH))==1

def test_store_link_refusal_and_limits_no_auto_delete(tmp_path):
 from data_workspace.auth import PublicError
 app,source,_=configured(tmp_path);store=app.state.semantics
 for _ in range(100):store.draft(AUTH,SemanticDraftInput.model_validate(payload(source)))
 with pytest.raises(PublicError):store.draft(AUTH,SemanticDraftInput.model_validate(payload(source)))
 assert len(store.drafts)==100
 # Simulated junction branch, not claiming native filesystem corruption/production verification.
 from unittest.mock import patch
 with patch.object(Path,'is_junction',return_value=True):
  with pytest.raises(PublicError):store.versions(AUTH)

# Actual governed HTTP MCP describes only metadata; no submit_query even with a valid table grant.
from test_remote_sources import http_fixture

def test_actual_http_metadata_only_authorization_and_no_preview(tmp_path,http_fixture,monkeypatch):
 from data_workspace.remote_access import RemoteAccessPolicy,HTTPGrant,SECRET_PREFIX
 from test_remote_sources import TOKEN
 from data_workspace.warehouse.local_file import LocalFileWarehouse
 url,requests=http_fixture;monkeypatch.setenv(SECRET_PREFIX+'HTTP_TEST',TOKEN)
 app,source,_=configured(tmp_path/'app-fixture')
 app.state.sources=SourceStore(tmp_path/'remote-profiles',tmp_path/'allowed-remote',RemoteAccessPolicy(http_mcp=[HTTPGrant(url=url,secret_ref='HTTP_TEST',table_ids=['t0'])]))
 connection={'kind':'http_mcp','name':'fixture','url':url,'auth_mode':'bearer','secret_ref':'HTTP_TEST','usage_authorized':True}
 with app.state.sources.db() as db:db.execute('INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at,kind,config_json) VALUES(?,?,?,?,?,?,?,?,?,?)',[source,app.state.sources.owner(AUTH),'HTTP semantic',1,1,'','independent fixture','2026-11-02','http_mcp',json.dumps(connection)])
 monkeypatch.setattr(LocalFileWarehouse,'preview',lambda *a,**k:pytest.fail('semantics must not preview in MCP'))
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  r=c.get(f'/api/v1/semantics/sources/{source}/tables/t0/schema');assert r.status_code==200,r.text
  assert r.json()['rows_read'] is False and [col['name'] for col in r.json()['columns']]==['id','created_at','shipped_on']
  assert TOKEN not in r.text
  assert c.get(f'/api/v1/semantics/sources/{source}/tables/forbidden/schema').status_code==403


def test_postgres_metadata_contract_has_no_row_select(tmp_path):
 from data_workspace.warehouse.postgres_worker import navigate,table_id
 class Cursor:
  def __init__(self,value):self.value=value
  def fetchall(self):return self.value
 class Connection:
  def __init__(self):self.sql=[]
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def execute(self,sql,parameters=None):
   self.sql.append(str(sql));assert 'SELECT *' not in str(sql)
   if 'FROM pg_catalog.pg_class' in str(sql):return Cursor([('public','orders')])
   if 'FROM pg_catalog.pg_attribute' in str(sql):return Cursor([('id','integer'),('amount','numeric')])
   return Cursor([])
 con=Connection()
 payload={'draft':{'kind':'postgresql','name':'fixture','host':'127.0.0.1','port':5432,'database':'fixture','username':'reader','secret_ref':'TEST_PG','sslmode':'disable','usage_authorized':True},'schemas':['public'],'operation':'describe','table':table_id('public','orders'),'password':'fake-only'}
 result=navigate(payload,connect=lambda **kw:con)
 assert result['fields']==[{'name':'id','type':'integer'},{'name':'amount','type':'numeric'}]
 assert all('LIMIT 101' not in str(sql) or 'pg_attribute' in str(sql) for sql in con.sql)
 # Contract with fake PG connect only; actual PG instance remains deferred/not_run.

@pytest.mark.parametrize('kind',['INTERVAL','INTEGER-looking-text','FLOAT-injected'])
def test_numeric_types_exact_not_prefix_guess(tmp_path,kind):
 app,source,_=configured(tmp_path);original=app.state.sources.call
 async def changed(*args,**kwargs):
  v=await original(*args,**kwargs);v['metadata']['fields'][1]['type']=kind;return v
 app.state.sources.call=changed
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);assert not r['result']['valid'] and r['result']['issues'][0]['code']=='TYPE_MISMATCH'
  assert c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).status_code==409

@pytest.mark.parametrize('approval',[1,'true',False])
def test_approval_must_be_actual_true_boolean(tmp_path,approval):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);b=publish_body(d,r);b['approve_definition']=approval
  assert c.post('/api/v1/semantics/publish',json=b,headers=H).status_code==422
  assert not c.get('/api/v1/semantics').json()['versions']

def test_pack_disable_preserves_raw_versions_restart_and_enable_revalidates(tmp_path):
 app,source,calls=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);v=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json()
  with app.state.semantics.db() as db:original=db.execute('SELECT body FROM versions WHERE id=?',[v['id']]).fetchone()[0]
  body={'expected_version':1,'expected_state_revision':0,'enabled':False};url='/api/v1/semantics/packs/'+v['pack_id']+'/state'
  before=len(calls);response=c.post(url,json=body,headers=H);assert response.status_code==200,response.text
  assert response.json()['state']=='disabled' and response.json()['state_revision']==1 and len(calls)==before
  assert c.post('/api/v1/semantics/versions/'+v['id']+'/resolve',json={},headers=H).json()['code']=='SEMANTIC_DISABLED'
  assert c.post(url,json=body,headers=H).status_code==409
  with app.state.semantics.db() as db:assert db.execute('SELECT body FROM versions WHERE id=?',[v['id']]).fetchone()[0]==original
  root=app.state.semantics.root;app.state.semantics=SemanticStore(root)
  assert c.get('/api/v1/semantics/versions/'+v['id']).json()['state']=='disabled'
  enabled=c.post(url,json={'expected_version':1,'expected_state_revision':1,'enabled':True},headers=H)
  assert enabled.status_code==200 and enabled.json()['state_revision']==2
  assert c.post('/api/v1/semantics/versions/'+v['id']+'/resolve',json={},headers=H).status_code==200
  assert len(c.get('/api/v1/semantics').json()['versions'])==1

def test_old_version_readonly_disabled_pack_new_publication_stays_disabled(tmp_path):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);v=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json()
  url='/api/v1/semantics/packs/'+v['pack_id']+'/state'
  assert c.post(url,json={'expected_version':1,'expected_state_revision':0,'enabled':False},headers=H).status_code==200
  d,r=pipeline(c,source,pack_id=v['pack_id'],expected_version=1,name='revision');v2=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json()
  assert v2['version']==2 and v2['state']=='disabled'
  assert c.post(url,json={'expected_version':2,'expected_state_revision':1,'enabled':True},headers=H).status_code==200
  assert c.get('/api/v1/semantics/versions/'+v['id']).json()['state']=='superseded'
  assert c.post('/api/v1/semantics/versions/'+v['id']+'/resolve',json={},headers=H).json()['code']=='SEMANTIC_VERSION_STALE'
  assert c.post('/api/v1/semantics/versions/'+v2['id']+'/resolve',json={},headers=H).status_code==200

def test_cannot_enable_stale_or_disabled_source_and_state_privilege_denied(tmp_path):
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);v=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json();url='/api/v1/semantics/packs/'+v['pack_id']+'/state'
  b={'expected_version':1,'expected_state_revision':0,'enabled':False}
  assert c.post(url,json=b).status_code==403
  assert c.post(url,json={**b,'enabled':'false'},headers=H).status_code==422
  assert c.post(url,json=b,headers=H).status_code==200
  with app.state.sources.db() as db:db.execute('UPDATE profiles SET version=2 WHERE id=?',[source])
  assert c.post(url,json={**b,'expected_state_revision':1,'enabled':True},headers=H).json()['code']=='SEMANTIC_MAPPING_STALE'
  with app.state.sources.db() as db:db.execute('UPDATE profiles SET enabled=0 WHERE id=?',[source])
  assert c.post(url,json={**b,'expected_state_revision':1,'enabled':True},headers=H).json()['code']=='SOURCE_DISABLED'
  assert c.get('/api/v1/semantics/versions/'+v['id']).json()['state']=='disabled'

def test_state_cas_and_disable_during_resolve_never_returns_verified(tmp_path):
 from data_workspace.semantic_contracts import SemanticStateInput
 app,source,_=configured(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source);v=c.post('/api/v1/semantics/publish',json=publish_body(d,r),headers=H).json()
  original=app.state.sources.call;once=[False]
  async def disable_then_return(*args,**kwargs):
   result=await original(*args,**kwargs)
   if not once[0]:
    once[0]=True;app.state.semantics.toggle(AUTH,v['pack_id'],SemanticStateInput(expected_version=1,expected_state_revision=0,enabled=False))
   return result
  app.state.sources.call=disable_then_return
  response=c.post('/api/v1/semantics/versions/'+v['id']+'/resolve',json={},headers=H)
  assert response.status_code==409 and response.json()['code']=='SEMANTIC_VERSION_STALE'
  url='/api/v1/semantics/packs/'+v['pack_id']+'/state'
  assert c.post(url,json={'expected_version':1,'expected_state_revision':0,'enabled':True},headers=H).json()['code']=='SEMANTIC_VERSION_CONFLICT'
  assert c.get('/api/v1/semantics/versions/'+v['id']).json()['state']=='disabled'

@pytest.mark.parametrize('field',['unit','name'])
def test_blank_metric_labels_cannot_be_approved(tmp_path,field):
 app,source,calls=configured(tmp_path);value=payload(source);value['metrics'][0][field]='   '
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  assert c.post('/api/v1/semantics/drafts',json=value,headers=H).status_code==422
  assert not calls and not app.state.semantics.drafts

@pytest.mark.parametrize('kind',['VARCHAR_TIME','TEXT_DATE'])
def test_temporal_types_not_guessed_from_name_substring(tmp_path,kind):
 app,source,_=configured(tmp_path);original=app.state.sources.call
 async def changed(*args,**kwargs):
  v=await original(*args,**kwargs);v['metadata']['fields'][-1]['type']=kind;return v
 app.state.sources.call=changed
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  d,r=pipeline(c,source,time={'column':'created_at','meaning':'creation date','timezone':'UTC'})
  assert not r['result']['valid'] and r['result']['issues'][0]['code']=='TYPE_MISMATCH'
