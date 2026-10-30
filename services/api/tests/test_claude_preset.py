"""Explicit user-selected Claude-style Messages/Bearer package. No host token access."""
import asyncio,json
import httpx
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.model_provider import MessagesProvider,ModelConfiguration
from test_model_provider import KEY,Permit,response
from dev import model_candidate_environment,backend_environment,frontend_environment

CONFIG=ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','deepseek-v4.1-flash','anthropic_messages','bearer')

def test_claude_preset_explicitly_binds_all_fields_no_host_auth_or_auto_fallback():
    env={'WORKSPACE_MODEL_PROTOCOL':'openai_responses','WORKSPACE_MODEL_ENDPOINT':'http://bad.example','WORKSPACE_MODEL_ID':'old','WORKSPACE_MODEL_AUTH_MODE':'x_api_key','ANTHROPIC_AUTH_TOKEN':'host-fixture-only','WORKSPACE_MODEL_KEY':KEY}
    v=model_candidate_environment(env,'claude-code');assert env['WORKSPACE_MODEL_ID']=='old'
    assert v['WORKSPACE_MODEL_ENDPOINT']==CONFIG.endpoint and v['WORKSPACE_MODEL_ID']=='deepseek-v4.1-flash'
    assert v['WORKSPACE_MODEL_PROTOCOL']=='anthropic_messages' and v['WORKSPACE_MODEL_AUTH_MODE']=='bearer'
    assert v['WORKSPACE_MODEL_ESTIMATED_BUDGET']=='1'
    back=backend_environment(v);front=frontend_environment(v)
    assert 'ANTHROPIC_AUTH_TOKEN' not in back and 'WORKSPACE_MODEL_KEY' not in back
    assert back['WORKSPACE_MODEL_AUTH_MODE']=='bearer' and not any(k.startswith('WORKSPACE_MODEL_') for k in front)
    with pytest.raises(ValueError):model_candidate_environment({},'unknown')

@pytest.mark.parametrize('auth,header', [('bearer','authorization'),('x_api_key','x-api-key'),('protocol_default','x-api-key')])
def test_messages_explicit_auth_one_header_only_and_fixed_contract(auth,header):
    endpoint=CONFIG.endpoint if auth!='bearer' else 'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages'
    config=ModelConfiguration(endpoint,CONFIG.model_id,CONFIG.protocol,auth);seen=[]
    def handler(req):
        seen.append(req);assert req.headers[header]==('Bearer '+KEY if header=='authorization' else KEY)
        assert ('x-api-key' not in req.headers if header=='authorization' else 'authorization' not in req.headers)
        assert req.headers['anthropic-version']=='2023-06-01'
        assert json.loads(req.content)=={'model':'deepseek-v4.1-flash','max_tokens':128,'messages':[{'role':'user','content':'fixed test'}]}
        return httpx.Response(200,json=response(model='deepseek-v4.1-flash'))
    p=MessagesProvider(config,KEY,Permit(),httpx.MockTransport(handler));r=asyncio.run(p.generate('fixed test'))
    assert len(seen)==1 and r.model_id=='deepseek-v4.1-flash' and not r.sql_executed
    assert p.status().authentication==('x_api_key' if auth=='protocol_default' else auth)
    assert not p.status().generation_verified

@pytest.mark.parametrize('status',[401,403])
def test_safe_upstream_status_distinguishes_refusal_no_retry_no_raw_error(status,tmp_path):
    from data_workspace.model_budget import EstimatedBudget
    from uuid import uuid4
    calls=[]
    def handler(req):calls.append(req);return httpx.Response(status,text=KEY)
    p=MessagesProvider(CONFIG,KEY,EstimatedBudget(tmp_path/'budget'),httpx.MockTransport(handler))
    app=create_app(Settings(mode='development',dev_identity=True));app.state.model_provider=p
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
        s=c.get('/api/v1/model-service/status').json()
        assert s['authentication']=='bearer' and s['model_id']=='deepseek-v4.1-flash' and KEY not in json.dumps(s)
        body={'request_id':str(uuid4()),'config_version':CONFIG.version,'execution_generation':s['execution_generation'],'accept_estimated_cost':True}
        result=c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'})
        assert result.json()['error_code']=='MODEL_ACCESS_DENIED' and result.json()['upstream_status']==status
        assert KEY not in result.text
        assert c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'}).json()==result.json()
        assert len(calls)==1 and p.budget.summary().reserved_requests==1

def test_auth_change_invalidates_configuration_and_rejects_unknown_before_request():
    assert CONFIG.version!=ModelConfiguration(CONFIG.endpoint,CONFIG.model_id,CONFIG.protocol,'x_api_key').version
    config=ModelConfiguration(CONFIG.endpoint,CONFIG.model_id,CONFIG.protocol,'unknown')
    p=MessagesProvider(config,KEY,Permit(),httpx.MockTransport(lambda req:pytest.fail('unknownauth denied')))
    with pytest.raises(PublicError):asyncio.run(p.generate('fixed'))
    assert not p.budget.reservations

def test_env_factory_claude_style_consumes_dedicated_key_only(monkeypatch):
    for k,v in model_candidate_environment({},'claude-code').items():monkeypatch.setenv(k,v)
    # Avoid enabling real runtime ledger during fixture test.
    monkeypatch.setenv('WORKSPACE_MODEL_ESTIMATED_BUDGET','0')
    monkeypatch.setenv('WORKSPACE_MODEL_KEY',KEY);monkeypatch.setenv('ANTHROPIC_AUTH_TOKEN','host-fixture-only')
    p=MessagesProvider.from_env();assert type(p) is MessagesProvider
    assert p.configuration==CONFIG and p.key==KEY and p.status().authentication=='bearer'
    assert 'WORKSPACE_MODEL_KEY' not in __import__('os').environ


def test_supplied_sdk_contract_root_path_and_x_api_key_no_authorization():
    seen=[]
    def handler(req):
        seen.append(req)
        assert req.url.path=='/v1/messages' and req.url.host=='ada-cli-golang.ctripcorp.com'
        assert req.headers['x-api-key']==KEY and 'authorization' not in req.headers
        return httpx.Response(200,json=response(model=CONFIG.model_id))
    sdk_config=ModelConfiguration('http://ada-cli-golang.ctripcorp.com/v1/messages',CONFIG.model_id,'anthropic_messages','x_api_key')
    p=MessagesProvider(sdk_config,KEY,Permit(),httpx.MockTransport(handler))
    assert asyncio.run(p.generate('fixed')).model_id=='deepseek-v4.1-flash'
    assert len(seen)==1

@pytest.mark.parametrize('endpoint,protocol,auth',[
 ('http://ada-cli-golang.ctripcorp.com/v1/messages','anthropic_messages','bearer'),
 ('http://ada-cli-golang.ctripcorp.com/v1/responses','openai_responses','bearer'),
 ('http://evil.example/v1/messages','anthropic_messages','x_api_key'),
 ('http://ada-cli-golang.ctripcorp.com/admin/v1/messages','anthropic_messages','x_api_key')])
def test_root_exception_is_exact_not_general_network_expansion(endpoint,protocol,auth):
    assert not ModelConfiguration(endpoint,CONFIG.model_id,protocol,auth).valid()


def test_ai_plan_cli_connection_contract_used_without_embedding_cli_runtime():
    v=model_candidate_environment({},'claude-code')
    assert v['WORKSPACE_MODEL_ENDPOINT']=='http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages'
    assert v['WORKSPACE_MODEL_AUTH_MODE']=='bearer' and v['WORKSPACE_MODEL_ID']=='deepseek-v4.1-flash'
    assert not any(k in v for k in ('ANTHROPIC_AUTH_TOKEN','hooks','API_TIMEOUT_MS','CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY'))
    seen=[]
    def handler(req):
        seen.append(req)
        assert req.headers['authorization']=='Bearer '+KEY and 'x-api-key' not in req.headers
        assert req.url.path=='/coding-plan/v1/messages'
        return httpx.Response(200,json=response(model=CONFIG.model_id))
    p=MessagesProvider(CONFIG,KEY,Permit(),httpx.MockTransport(handler))
    assert asyncio.run(p.generate('fixed')).model_id==CONFIG.model_id and len(seen)==1
