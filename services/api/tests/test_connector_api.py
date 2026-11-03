from copy import deepcopy
from fastapi.testclient import TestClient
import pytest
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.contracts import AuthContext

HEADERS={'X-Workspace-Request':'1'}
BODY={'request':{'table':'fact_order','columns':['order_id','paid_amount_cents'],'limit':5},'idempotency_key':'api-preview','confirmed':True}

@pytest.fixture(scope='module')
def app():
    return create_app(Settings(mode='development',dev_identity=True,owned_warehouse=True))

@pytest.fixture(scope='module')
def client(app):
    BODY['execution_generation']=app.state.connector.generation
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10000)) as c:yield c


def test_real_api_mcp_metadata_preview_and_idempotency(client):
    summary=client.get('/api/v1/connectors/owned-synthetic').json()
    assert summary['state']=='READY' and summary['verified'] is True
    assert 'connectors' in [m['id'] for m in client.get('/api/v1/capabilities').json()['modules'] if m['available']]
    verified=client.post('/api/v1/connectors/owned-synthetic/verify',headers=HEADERS,json={})
    assert verified.status_code==200 and len(verified.json()['metadata']['tables'])==5
    schema=client.get('/api/v1/connectors/owned-synthetic/tables/fact_order/schema').json()
    assert schema['metadata']['fields'][0]['name']=='order_id'
    first=client.post('/api/v1/execution-previews',headers=HEADERS,json=BODY)
    assert first.status_code==200 and first.json()['status']=='SUCCEEDED'
    task=first.json();task_id=task['task_id']
    assert client.get('/api/v1/execution-previews/'+task_id).json()==task
    result=client.get('/api/v1/execution-previews/'+task_id+'/result').json()['result']
    assert result['returned_row_count']==5 and result['truncated'] is True and result['reported_total_rows'] is None
    assert result['source']=='independently_generated_synthetic' and result['quality']['status']=='WARN'
    again=client.post('/api/v1/execution-previews',headers=HEADERS,json=BODY).json()
    assert again['task_id']==task_id
    changed=deepcopy(BODY);changed['request']['limit']=4
    assert client.post('/api/v1/execution-previews',headers=HEADERS,json=changed).status_code==409


@pytest.mark.parametrize('mutation',[{'confirmed':False},{'tenant_id':'attacker'},{'request':{**BODY['request'],'table':'secret_data'}},{'request':{**BODY['request'],'columns':['password-secret-sentinel']}},{'request':{**BODY['request'],'sql':'DROP TABLE x'}}])
def test_preview_rejects_unconfirmed_scope_injection_without_reflection(client,mutation):
    body=deepcopy(BODY);body.update(mutation)
    result=client.post('/api/v1/execution-previews',headers=HEADERS,json=body)
    assert result.status_code==422
    assert 'password-secret-sentinel' not in result.text


def test_preview_csrf_and_unknown_task(client):
    assert client.post('/api/v1/execution-previews',json=BODY).status_code==403
    assert client.get('/api/v1/execution-previews/missing/result').status_code==404


def test_connector_identity_scope_not_client_controlled(app,client):
    old=app.state.identity_provider
    class Other:
        def resolve(self,request):return AuthContext(principal_id='other',tenant_id='local-workspace',mode='development')
    app.state.identity_provider=Other()
    try:
        assert client.get('/api/v1/connectors/owned-synthetic').status_code==403
        assert client.post('/api/v1/execution-previews',headers=HEADERS,json=BODY).status_code==403
        assert client.get('/api/v1/execution-previews/unknown/result').status_code==403
        assert client.get('/api/v1/capabilities').json()['connectors']==[]
    finally:app.state.identity_provider=old


def test_disabled_connector_fails_closed():
    with TestClient(create_app(Settings(mode='development',dev_identity=True)),base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
        assert c.get('/api/v1/connectors/owned-synthetic').json()['state']=='NOT_CONFIGURED'
        assert c.post('/api/v1/execution-previews',json=BODY,headers=HEADERS).status_code==503


def test_production_cannot_enable_local_warehouse():
    with pytest.raises(ValueError):Settings(owned_warehouse=True)

def test_expired_execution_generation_never_resubmits(client):
    body=deepcopy(BODY);body['execution_generation']='00000000-0000-0000-0000-000000000000';body['idempotency_key']='expired-generation'
    response=client.post('/api/v1/execution-previews',json=body,headers=HEADERS)
    assert response.status_code==409 and response.json()['code']=='EXECUTION_CONTEXT_EXPIRED'


def test_outcome_unknown_preserves_receipt_and_does_not_retry(app,client):
    manager=app.state.connector;old=manager.call;calls=[]
    async def lost(*args,**kwargs):
        calls.append(1)
        raise RuntimeError('sentinel-private-communication-error')
    manager.call=lost
    body=deepcopy(BODY);body['idempotency_key']='unknown-outcome'
    try:
        first=client.post('/api/v1/execution-previews',json=body,headers=HEADERS).json()
        second=client.post('/api/v1/execution-previews',json=body,headers=HEADERS).json()
        assert first['status']=='OUTCOME_UNKNOWN' and first==second and calls==[1]
        assert 'sentinel-private' not in str(first)
        assert client.get('/api/v1/execution-previews/'+first['task_id']+'/result').status_code==409
    finally:manager.call=old


def test_disabled_api_loads_without_optional_engine_packages():
    import subprocess,sys
    code='''import sys,importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'duckdb','sqlglot','mcp','langgraph','langsmith','langchain_core'}:raise ImportError('blocked optional dependency')
sys.meta_path.insert(0,Block())
from data_workspace.main import create_app
from data_workspace.config import Settings
assert create_app(Settings()).state.connector.enabled is False
'''
    run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
