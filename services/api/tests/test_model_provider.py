"""Isolated Messages fixtures: no company gateway requests or real credentials."""
import asyncio
import getpass
import json
from pathlib import Path
import sys
import warnings

import httpx
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.model_provider import MessagesProvider, ModelConfiguration

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'scripts'))
from dev import backend_environment, frontend_environment
from model_key_input import read_model_key
KEY='fixture-only-dedicated-key'
CONFIG=ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages', 'fixture-model', 'anthropic_messages')
class Permit:
    def __init__(self):self.reservations=[]
    async def reserve(self, **kwargs):self.reservations.append(kwargs)

def response(**updates):
    return {'type':'message','role':'assistant','model':'fixture-model','stop_reason':'end_turn',
            'content':[{'type':'text','text':'isolated test response'}], 'usage':{'input_tokens':8,'output_tokens':4},**updates}

def provider(handler, *, budget=True):
    return MessagesProvider(CONFIG,KEY,Permit() if budget else None,httpx.MockTransport(handler))

def run(p):return asyncio.run(p.generate('fixed non-sensitive test'))

@pytest.mark.parametrize('endpoint', ['https://example.com/messages','http://ada-cli-golang.ctripcorp.com.evil/coding-plan/v1/messages','http://user:password@ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','http://ada-cli-golang.ctripcorp.com/coding-plan/../v1/messages','http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages?token=value','http://ada-cli-golang.ctripcorp.com:999/coding-plan/v1/messages','http://ada-cli-golang.ctripcorp.com/coding-plan//v1/messages'])
def test_target_policy_rejects_egress_before_reservation(endpoint):
    p=provider(lambda req:pytest.fail('network forbidden'));p.configuration=ModelConfiguration(endpoint,CONFIG.model_id,CONFIG.protocol)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_CONFIGURATION_INVALID' and not p.budget.reservations

def test_dedicated_key_consumed_only_by_backend_and_not_returned(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_AUTH_TOKEN','fixture-host-token');monkeypatch.setenv('OPENAI_API_KEY','fixture-host-key')
    p=MessagesProvider.from_env();assert not p.key
    monkeypatch.setenv('WORKSPACE_MODEL_KEY',KEY)
    p=MessagesProvider.from_env();assert p.key==KEY
    assert 'WORKSPACE_MODEL_KEY' not in __import__('os').environ
    assert KEY not in repr(p) and KEY not in p.status().model_dump_json()
    assert 'fixture-host-token' not in repr(p)

def test_environment_whitelist_never_inherits_model_or_host_secret():
    env={'PATH':'safe','WORKSPACE_MODEL_KEY':KEY,'ANTHROPIC_AUTH_TOKEN':'fixture-host','WORKSPACE_MODEL_ENDPOINT':CONFIG.endpoint,'WORKSPACE_MODEL_ID':'fixture-model','WORKSPACE_MODEL_PROTOCOL':'anthropic_messages','WORKSPACE_CONNECTOR_SECRET_TEST':'fixture-source'}
    front=frontend_environment(env);back=backend_environment(env)
    assert front=={'PATH':'safe'} and 'WORKSPACE_MODEL_KEY' not in back and 'ANTHROPIC_AUTH_TOKEN' not in back
    assert back['WORKSPACE_MODEL_ENDPOINT']==CONFIG.endpoint

def test_budget_missing_refuses_before_http_and_does_not_claim_verified():
    p=provider(lambda req:pytest.fail('no fee evidence'),budget=False)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_BUDGET_UNVERIFIED'
    status=p.status();assert status.state=='budget_unverified' and status.models==[] and not status.generation_verified and status.cost_status=='unknown'

def test_valid_contract_request_is_minimal_no_rows_history_tools_and_reserves_first():
    seen=[]
    p=None
    def handler(request):
        assert len(p.budget.reservations)==1
        seen.append(request);assert request.headers['x-api-key']==KEY
        body=json.loads(request.content);assert set(body)=={'model','max_tokens','messages'}
        assert body['max_tokens']==128 and body['messages']==[{'role':'user','content':'fixed non-sensitive test'}]
        return httpx.Response(200,json=response())
    p=provider(handler);result=run(p)
    assert len(seen)==1 and not result.sql_executed and result.cost_status=='unknown'
    assert result.model_id=='fixture-model' and result.config_version==CONFIG.version
    assert result.input_tokens==8 and result.output_tokens==4
    assert not p._busy and not p.status().generation_verified  # fixture is not production verification

@pytest.mark.parametrize('status,code',[(401,'MODEL_ACCESS_DENIED'),(403,'MODEL_ACCESS_DENIED'),(429,'MODEL_RATE_LIMITED'),(302,'MODEL_SERVICE_FAILED'),(500,'MODEL_SERVICE_FAILED')])
def test_errors_no_secret_raw_body_or_retry(status,code):
    calls=[]
    def handler(req):calls.append(req);return httpx.Response(status,text=KEY,headers={'Location':'http://example.com'})
    p=provider(handler)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code==code and KEY not in caught.value.message and len(calls)==1 and not p._busy

@pytest.mark.parametrize('data',[response(model='different'),response(stop_reason='max_tokens'),response(content=[]),response(content=[{'type':'tool_use','text':'not allowed'}]),response(content=[{'type':'text','text':KEY}]),response(usage={'input_tokens':True}),response(usage={'output_tokens':129}),response(role='user'),['bad']])
def test_invalid_partial_tool_alias_or_secret_echo_rejected(data):
    p=provider(lambda req:httpx.Response(200,json=data))
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_RESPONSE_INVALID' and KEY not in caught.value.message

@pytest.mark.parametrize('body',[b'{broken',b'x'*(64*1024+1)],ids=['malformed-json','oversize-response'])
def test_malformed_and_oversize_bounded(body):
    p=provider(lambda req:httpx.Response(200,content=body))
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code in {'MODEL_RESPONSE_INVALID','MODEL_RESPONSE_LIMIT'}

def test_timeout_unknown_no_refund_no_retry_and_release():
    def handler(req):raise httpx.ReadTimeout(KEY)
    p=provider(handler)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_RESULT_UNKNOWN' and KEY not in caught.value.message
    assert len(p.budget.reservations)==1 and not p._busy

def test_cancellation_and_concurrency_release_without_refund():
    async def scenario():
        started=asyncio.Event()
        async def handler(req):started.set();await asyncio.Event().wait()
        p=provider(handler);task=asyncio.create_task(p.generate('fixed'));await started.wait()
        with pytest.raises(PublicError) as caught:await p.generate('fixed')
        assert caught.value.code=='MODEL_BUSY'
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert not p._busy and len(p.budget.reservations)==1
    asyncio.run(scenario())

class Terminal:
    def __init__(self,tty):self.tty=tty
    def isatty(self):return self.tty

def test_hidden_prompt_rejects_pipe_and_warning_no_echo_fallback():
    with pytest.raises(ValueError):read_model_key(stream=Terminal(False),prompt=lambda _:pytest.fail('must not read'))
    def warning(_):warnings.warn('fixture hidden input unavailable',getpass.GetPassWarning);pytest.fail('fallback must never run')
    with pytest.raises(ValueError):read_model_key(stream=Terminal(True),prompt=warning)
    assert read_model_key(stream=Terminal(True),prompt=lambda _:KEY)==KEY
    for value in ('bad','secret\nline','含中文key'):
        with pytest.raises(ValueError):read_model_key(stream=Terminal(True),prompt=lambda _:value)

def test_status_authorization_no_key_input_or_paid_endpoint(tmp_path,monkeypatch):
    monkeypatch.setenv('WORKSPACE_MODEL_KEY',KEY)
    app=create_app(Settings(mode='development',dev_identity=True))
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        result=client.get('/api/v1/model-service/status');assert result.status_code==200
        assert result.json()['credential_configured'] and KEY not in result.text
        assert result.json()['models']==[] and not result.json()['generation_verified']
        denied=client.post('/api/v1/model-service/status',json={'key':KEY},headers={'X-Workspace-Request':'1'})
        assert denied.status_code==405 and KEY not in denied.text
    with TestClient(create_app(Settings()),base_url='http://127.0.0.1:8000') as client:
        assert client.get('/api/v1/model-service/status').status_code==401


def test_request_input_invalid_does_not_reserve_or_call():
    for value in ('', 'x'*2001, {'rows':[[1,2]]}):
        p=provider(lambda req:pytest.fail('input denied'))
        with pytest.raises(PublicError):asyncio.run(p.generate(value))
        assert not p.budget.reservations

def test_worker_whitelist_excludes_model_key_and_configuration(monkeypatch):
    from data_workspace.worker_runtime import worker_environment
    monkeypatch.setenv('WORKSPACE_MODEL_KEY',KEY);monkeypatch.setenv('WORKSPACE_MODEL_ID','fixture-model')
    assert not any(k.startswith('WORKSPACE_MODEL_') for k in worker_environment())

def test_compressed_response_refuses_before_decoding():
    import gzip
    p=provider(lambda req:httpx.Response(200,content=gzip.compress(b'x'*65537),headers={'Content-Encoding':'gzip'}))
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_RESPONSE_INVALID'

def test_missing_token_usage_is_unknown_not_zero():
    data=response();data.pop('usage')
    result=run(provider(lambda req:httpx.Response(200,json=data)))
    assert result.input_tokens is None and result.output_tokens is None


def test_accidental_secret_in_nonsecret_configuration_never_returns_or_sends_key():
    p=provider(lambda req:pytest.fail('invalid nonsecret config must not send'))
    p.configuration=ModelConfiguration(CONFIG.endpoint,KEY,CONFIG.protocol)
    assert KEY not in p.status().model_dump_json() and p.status().state=='configuration_missing'
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_CONFIGURATION_INVALID' and not p.budget.reservations
