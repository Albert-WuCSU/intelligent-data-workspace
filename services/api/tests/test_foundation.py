from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from data_workspace.main import create_app, CONTRACTS
from data_workspace.config import Settings
from data_workspace.contracts import QuerySpec, AuthContext, Task, TaskStatus, ErrorEnvelope, DatasetAsset, ConnectorCapability
from data_workspace.repository import MemoryTaskRepository
from data_workspace.auth import PublicError

SPEC={'schema_version':'1.0','target':{'kind':'metric','metric_refs':[{'id':'order_conversion_rate','version':'1.0.0'}]},
      'time_range':{'start':'2026-10-19','end_exclusive':'2026-10-26'},'timezone':'Asia/Shanghai','dimensions':['region'],'filters':[]}
HEADERS={'X-Workspace-Request':'1'}

@pytest.fixture
def app():
    return create_app(Settings(mode='development',dev_identity=True))

@pytest.fixture
def client(app):
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10000)) as c:
        yield c

@pytest.mark.parametrize('mode,dev,host', [('production',True,'127.0.0.1'),('development',True,'0.0.0.0'),('x',False,'127.0.0.1')])
def test_invalid_config(mode,dev,host):
    with pytest.raises(ValueError):Settings(mode=mode,dev_identity=dev,host=host)

@pytest.mark.parametrize('mutation', [
    {'tenant_id':'attacker'}, {'principal_id':'attacker'}, {'policy_context':{}}, {'schema_version':'9.0'},
    {'timezone':'Not/A_Timezone'}, {'time_range':{'start':'2026-10-26','end_exclusive':'2026-10-19'}},
    {'dimensions':['region','region']}, {'target':{'kind':'metric','metric_refs':[]}},
    {'filters':[{'field':'region','operator':'eq','values':['a','b']}]}
])
def test_query_contract_rejects_invalid_input(client,mutation):
    data=deepcopy(SPEC);data.update(mutation)
    response=client.post('/api/v1/query-spec/validate',json=data,headers=HEADERS)
    assert response.status_code==422
    assert response.json()['code']=='INVALID_REQUEST'
    assert 'input' not in response.text

def test_table_target_is_explicit_contract(client):
    data=deepcopy(SPEC);data['target']={'kind':'table','datasource_id':'hive','full_table_name':'sales.orders','columns':['region','amount']}
    result=client.post('/api/v1/query-spec/validate',json=data,headers=HEADERS)
    assert result.status_code==200 and result.json()['execution_available'] is False

def test_metric_validation_is_not_business_certification(client):
    r=client.post('/api/v1/query-spec/validate',json=SPEC,headers=HEADERS)
    assert r.status_code==200 and r.json()['execution_available'] is False
    assert '尚未验证' in r.json()['note']

def test_bad_json_does_not_reflect_secret(client):
    r=client.post('/api/v1/tasks',content='{"secret":"do-not-show',headers={**HEADERS,'Content-Type':'application/json'})
    assert r.status_code==422
    assert 'do-not-show' not in r.text

def test_default_production_auth_is_closed():
    with TestClient(create_app(Settings()),base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
        assert c.get('/health/live').status_code==200
        assert c.get('/api/v1/session',headers={'X-Tenant-ID':'admin','Authorization':'Bearer made-up'}).status_code==401
        assert c.post('/api/v1/tasks',json=SPEC,headers=HEADERS).status_code==401

def test_dev_identity_requires_explicit_flag():
    with TestClient(create_app(Settings(mode='development')),base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
        assert c.get('/api/v1/session').status_code==401

def test_dev_identity_rejects_remote_address(app):
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('192.168.1.2',1)) as c:
        assert c.get('/api/v1/session',headers={'X-Forwarded-For':'127.0.0.1'}).status_code==401

def test_untrusted_host_rejected(app):
    with TestClient(app,base_url='http://evil.example',client=('127.0.0.1',1)) as c:
        assert c.get('/api/v1/session').status_code==400

@pytest.mark.parametrize('method,path', [('get','/api/v1/session'),('post','/api/v1/tasks')])
def test_cross_origin_requests_rejected(client,method,path):
    args={'headers':{**HEADERS,'Origin':'https://evil.example'}}
    if method=='post':args['json']=SPEC
    assert getattr(client,method)(path,**args).status_code==403

def test_missing_csrf_header_rejected(client):
    assert client.post('/api/v1/tasks',json=SPEC).status_code==403

def test_unknown_capabilities_are_not_supported():
    c=ConnectorCapability(connector_id='hive',configured=False)
    assert c.cancel=='unknown' and c.query_cost=='unknown'

def test_capabilities_no_fake_connectors(client):
    c=client.get('/api/v1/capabilities').json()
    assert c['connectors']==[] and not any(m['available'] for m in c['modules'])

def test_session_is_server_owned(client):
    s=client.get('/api/v1/session',headers={'X-Tenant-ID':'other','X-User-ID':'other'}).json()
    assert s['identity']['tenant_id']=='local-workspace'
    assert s['identity']['principal_id']=='local-developer'
    assert s['storage']=='memory_development'

def test_register_task_never_claims_sql_succeeded(client):
    r=client.post('/api/v1/tasks',json=SPEC,headers=HEADERS)
    assert r.status_code==201
    task=r.json()
    assert task['status']=='FAILED' and task['error']['code']=='EXECUTOR_NOT_CONFIGURED'
    again=client.get('/api/v1/tasks/'+task['task_id'])
    assert again.json()==task
    assert again.headers['cache-control']=='no-store'
    assert again.headers['x-trace-id']
    assert client.post('/api/v1/tasks/'+task['task_id']+'/cancel',headers=HEADERS,json={}).status_code==409

def test_other_tenant_and_user_cannot_read_task(client,app):
    task=client.post('/api/v1/tasks',json=SPEC,headers=HEADERS).json()
    class Other:
        def resolve(self,request):return AuthContext(principal_id='local-developer',tenant_id='other',mode='development')
    app.state.identity_provider=Other()
    r=client.get('/api/v1/tasks/'+task['task_id'])
    missing=client.get('/api/v1/tasks/unknown')
    assert r.status_code==missing.status_code==404
    assert r.json()['safe_message']==missing.json()['safe_message']
    class SameTenantOtherUser:
        def resolve(self,request):return AuthContext(principal_id='another-user',tenant_id='local-workspace',mode='development')
    app.state.identity_provider=SameTenantOtherUser()
    assert client.get('/api/v1/tasks/'+task['task_id']).status_code==404

def task_fixture():
    now=datetime.now(timezone.utc)
    return Task(task_id='task1',tenant_id='tenant1',principal_id='user1',query_spec=QuerySpec.model_validate(SPEC),status=TaskStatus.CREATED,created_at=now,updated_at=now,trace_id='trace1')

@pytest.mark.parametrize('terminal',[TaskStatus.SUCCEEDED,TaskStatus.FAILED,TaskStatus.CANCELLED])
def test_terminal_transitions_rejected(terminal):
    t=task_fixture();t.status=terminal
    with pytest.raises(ValueError):t.transition(TaskStatus.RUNNING)

def test_task_transitions_require_error_on_failure():
    t=task_fixture()
    with pytest.raises(ValueError):t.transition(TaskStatus.FAILED)
    t.transition(TaskStatus.RUNNING);t.transition(TaskStatus.SUCCEEDED)
    assert t.status==TaskStatus.SUCCEEDED

def test_repository_returns_copies_and_is_bounded():
    repo=MemoryTaskRepository(capacity=1);t=task_fixture();repo.add(t);t.tenant_id='bad'
    auth=AuthContext(principal_id='user1',tenant_id='tenant1',mode='development')
    x=repo.get('task1',auth);x.tenant_id='changed'
    assert repo.get('task1',auth).tenant_id=='tenant1'
    with pytest.raises(PublicError):repo.add(task_fixture())
    assert MemoryTaskRepository()._tasks=={}

def test_unexpected_errors_hide_raw_exception(client,app,caplog):
    class Broken:
        def resolve(self,request):raise RuntimeError('password=secret-should-not-leak')
    app.state.identity_provider=Broken()
    r=client.get('/api/v1/session')
    assert r.status_code==500 and r.json()['code']=='INTERNAL_ERROR'
    assert 'secret-should-not-leak' not in r.text and 'secret-should-not-leak' not in caplog.text
    assert r.json()['trace_id'] in caplog.text

def test_contract_endpoint_matches_model(client):
    for name,model in CONTRACTS.items():
        assert client.get('/api/v1/contracts/'+name).json()==model.model_json_schema()
    assert client.get('/api/v1/contracts/Unknown').status_code==404

@pytest.mark.parametrize('data_ref', ['https://public.example/result','protected://other/a.parquet','protected://tenant1/../other/a'])
def test_asset_rejects_public_or_cross_tenant_refs(data_ref):
    with pytest.raises(ValidationError):
        DatasetAsset(asset_id='a1',asset_version='v1',tenant_id='tenant1',data_ref=data_ref,
            fields=[{'name':'region','type':'string'}],row_count=1,grain='region',
            provenance={'source_class':'COMPUTED'},quality={'status':'PASS'},policy_ref='p1')

def test_generated_contract_files_are_current():
    root=Path(__file__).resolve().parents[3]
    for name,model in CONTRACTS.items():
        assert json.loads((root/'contracts'/f'{name}.schema.json').read_text(encoding='utf-8'))==model.model_json_schema()
    assert json.loads((root/'contracts/openapi.json').read_text(encoding='utf-8'))==create_app(Settings()).openapi()
