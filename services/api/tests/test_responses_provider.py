"""Responses wire contract fixtures, never real gateway/host credentials."""
import asyncio
import json
from copy import deepcopy
import httpx
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.model_provider import ModelConfiguration, MessagesProvider
from data_workspace.responses_provider import ResponsesProvider
from test_model_provider import Permit, KEY, CONFIG as MESSAGES_CONFIG

CONFIG=ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/responses','gpt-6.1-sol[1M]','openai_responses')
def result():
    return {'object':'response','id':'fixture-response','model':CONFIG.model_id,'status':'completed',
        'error':None,'incomplete_details':None,'output':[{'type':'message','role':'assistant','status':'completed',
        'content':[{'type':'output_text','text':'fixture response','annotations':[]}]}],
        'usage':{'input_tokens':9,'output_tokens':4,'total_tokens':13}}
def provider(handler,budget=True):return ResponsesProvider(CONFIG,KEY,Permit() if budget else None,httpx.MockTransport(handler))
def run(p):return asyncio.run(p.generate('fixed non-sensitive question'))

def test_explicit_responses_request_bearer_minimal_store_false_no_host_env(monkeypatch):
    monkeypatch.setenv('HTTP_PROXY','http://should-not-use');seen=[]
    def handler(req):
        seen.append(req)
        assert req.url==CONFIG.endpoint and req.headers['authorization']=='Bearer '+KEY
        assert 'x-api-key' not in req.headers and 'anthropic-version' not in req.headers
        assert req.headers['accept-encoding']=='identity'
        assert json.loads(req.content)=={'model':CONFIG.model_id,'input':'fixed non-sensitive question','max_output_tokens':128,'store':False,'stream':False}
        assert len(p.budget.reservations)==1
        return httpx.Response(200,json=result())
    p=provider(handler);r=run(p)
    assert len(seen)==1 and r.text=='fixture response' and r.input_tokens==9 and r.output_tokens==4
    assert r.config_version==CONFIG.version and not r.sql_executed and r.cost_status=='unknown'
    assert not p.status().generation_verified and p.status().models==[] and KEY not in repr(p)

def test_env_factory_selects_responses_only_from_dedicated_project_fields(monkeypatch):
    monkeypatch.setenv('WORKSPACE_MODEL_ENDPOINT',CONFIG.endpoint);monkeypatch.setenv('WORKSPACE_MODEL_PROTOCOL',CONFIG.protocol)
    monkeypatch.setenv('WORKSPACE_MODEL_ID',CONFIG.model_id);monkeypatch.setenv('WORKSPACE_MODEL_KEY',KEY)
    monkeypatch.setenv('OPENAI_API_KEY','fixture-host-never-copy')
    p=MessagesProvider.from_env();assert isinstance(p,ResponsesProvider) and p.key==KEY
    assert p.status().protocol=='openai_responses' and p.status().state=='budget_unverified'
    assert 'WORKSPACE_MODEL_KEY' not in __import__('os').environ

@pytest.mark.parametrize('wrong', ['provider','suffix','unknown','host','userinfo','query','port'])
def test_mismatch_target_rejected_before_network_and_reservation(wrong):
    p=provider(lambda req:pytest.fail('invalid target'))
    config={'endpoint':CONFIG.endpoint,'model_id':CONFIG.model_id,'protocol':CONFIG.protocol}
    if wrong=='provider':p=MessagesProvider(CONFIG,KEY,Permit(),p.transport)
    elif wrong=='suffix':config['endpoint']=MESSAGES_CONFIG.endpoint
    elif wrong=='unknown':config['protocol']='openai_chat_completions'
    elif wrong=='host':config['endpoint']='http://evil.example/coding-plan/v1/responses'
    elif wrong=='userinfo':config['endpoint']='http://secret@ada-cli-golang.ctripcorp.com/coding-plan/v1/responses'
    elif wrong=='query':config['endpoint']+='?key=value'
    elif wrong=='port':config['endpoint']='http://ada-cli-golang.ctripcorp.com:999/coding-plan/v1/responses'
    p.configuration=ModelConfiguration(**config)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_CONFIGURATION_INVALID' and not p.budget.reservations

@pytest.mark.parametrize('mutation', ['failed','incomplete','queued','model','error','details','empty','tool','partial-message','refusal','role','missing-output','non-dict','secret','usage-bool','negative-usage','output-budget'])
def test_invalid_responses_partial_tools_alias_and_key_echo_rejected(mutation):
    data=result()
    if mutation in ('failed','incomplete','queued'):data['status']=mutation
    elif mutation=='model':data['model']='unauthorized-alias'
    elif mutation=='error':data['error']={'message':KEY}
    elif mutation=='details':data['incomplete_details']={'reason':'max_output_tokens'}
    elif mutation=='empty':data['output']=[]
    elif mutation=='tool':data['output']=[{'type':'function_call','name':'arbitrary','arguments':'{}'}]
    elif mutation=='partial-message':data['output'][0]['status']='in_progress'
    elif mutation=='refusal':data['output'][0]['content']=[{'type':'refusal','refusal':KEY}]
    elif mutation=='role':data['output'][0]['role']='user'
    elif mutation=='missing-output':data.pop('output')
    elif mutation=='non-dict':data=['bad']
    elif mutation=='secret':data['output'][0]['content'][0]['text']=KEY
    elif mutation=='usage-bool':data['usage']['input_tokens']=True
    elif mutation=='negative-usage':data['usage']['input_tokens']=-1
    elif mutation=='output-budget':data['usage']['output_tokens']=129
    p=provider(lambda req:httpx.Response(200,json=data))
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_RESPONSE_INVALID' and KEY not in caught.value.message and not p._busy

@pytest.mark.parametrize('status,code',[(401,'MODEL_ACCESS_DENIED'),(403,'MODEL_ACCESS_DENIED'),(429,'MODEL_RATE_LIMITED'),(302,'MODEL_SERVICE_FAILED'),(500,'MODEL_SERVICE_FAILED')])
def test_shared_error_limits_no_raw_secret_redirect_or_retries(status,code):
    seen=[]
    def handler(req):seen.append(req);return httpx.Response(status,text=KEY,headers={'Location':'http://evil.example'})
    p=provider(handler)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code==code and KEY not in caught.value.message and len(seen)==1

def test_budget_missing_blocks_responses_even_with_candidate_configuration():
    p=provider(lambda req:pytest.fail('no verifiedfeepermit'),False)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_BUDGET_UNVERIFIED' and p.status().state=='budget_unverified'

def test_reasoning_not_disclosed_and_null_usage_not_zero():
    data=result();data['output'].insert(0,{'type':'reasoning','summary':[{'text':'fixture-private-reasoning'}]});data['usage']=None
    r=run(provider(lambda req:httpx.Response(200,json=data)))
    assert r.text=='fixture response' and 'private-reasoning' not in r.model_dump_json()
    assert r.input_tokens is None and r.output_tokens is None

def test_reasoning_only_is_not_a_successful_text_response():
    data=result();data['output']=[{'type':'reasoning','summary':[]}]
    with pytest.raises(PublicError):run(provider(lambda req:httpx.Response(200,json=data)))

def test_multiple_output_texts_preserved_not_sdk_output_text_shortcut():
    data=result();data['output'][0]['content'].append({'type':'output_text','text':' part2'})
    assert run(provider(lambda req:httpx.Response(200,json=data))).text=='fixture response part2'

def test_timeout_unknown_cancellation_and_slot_reuse():
    def handler(req):raise httpx.ReadTimeout(KEY)
    p=provider(handler)
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_RESULT_UNKNOWN' and len(p.budget.reservations)==1 and not p._busy
    async def scenario():
        started=asyncio.Event()
        async def wait(req):started.set();await asyncio.Event().wait()
        p=provider(wait);task=asyncio.create_task(p.generate('fixed'));await started.wait()
        with pytest.raises(PublicError) as caught:await p.generate('fixed')
        assert caught.value.code=='MODEL_BUSY';task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert not p._busy and len(p.budget.reservations)==1
    asyncio.run(scenario())

@pytest.mark.parametrize('body',[b'{broken',b'x'*65537],ids=['badjson','oversize'])
def test_shared_response_size_and_invalid_json_limits(body):
    with pytest.raises(PublicError) as caught:run(provider(lambda req:httpx.Response(200,content=body)))
    assert caught.value.code in ('MODEL_RESPONSE_LIMIT','MODEL_RESPONSE_INVALID')

def test_actual_api_status_dedicated_responses_configuration_safe_and_unverified(monkeypatch):
    for k,v in {'WORKSPACE_MODEL_ENDPOINT':CONFIG.endpoint,'WORKSPACE_MODEL_ID':CONFIG.model_id,'WORKSPACE_MODEL_PROTOCOL':CONFIG.protocol,'WORKSPACE_MODEL_KEY':KEY}.items():monkeypatch.setenv(k,v)
    app=create_app(Settings(mode='development',dev_identity=True))
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        r=client.get('/api/v1/model-service/status');assert r.status_code==200 and KEY not in r.text
        s=r.json();assert s['protocol']=='openai_responses' and s['model_id']==CONFIG.model_id
        assert s['state']=='budget_unverified' and not s['generation_verified'] and s['models']==[]


def test_launcher_static_nonsecret_candidate_and_explicit_configuration_priority():
    from dev import model_candidate_environment, frontend_environment, backend_environment
    source={'PATH':'safe','WORKSPACE_MODEL_KEY':KEY,'OPENAI_API_KEY':'fixture-host'}
    candidate=model_candidate_environment(source)
    assert candidate['WORKSPACE_MODEL_PROTOCOL']=='openai_responses' and candidate['WORKSPACE_MODEL_ENDPOINT']==CONFIG.endpoint
    assert candidate['WORKSPACE_MODEL_ID']==CONFIG.model_id and source.get('WORKSPACE_MODEL_ENDPOINT') is None
    assert 'WORKSPACE_MODEL_KEY' not in backend_environment(candidate) and 'OPENAI_API_KEY' not in backend_environment(candidate)
    assert not any(k.startswith('WORKSPACE_MODEL_') for k in frontend_environment(candidate))
    explicit=model_candidate_environment({'WORKSPACE_MODEL_ENDPOINT':MESSAGES_CONFIG.endpoint,'WORKSPACE_MODEL_ID':'fixture-model','WORKSPACE_MODEL_PROTOCOL':'anthropic_messages'})
    assert explicit['WORKSPACE_MODEL_ENDPOINT']==MESSAGES_CONFIG.endpoint and explicit['WORKSPACE_MODEL_PROTOCOL']=='anthropic_messages'

def test_responses_secret_in_config_never_reflected_or_sent():
    p=provider(lambda req:pytest.fail('invalid reflectedkey'))
    p.configuration=ModelConfiguration(CONFIG.endpoint,KEY,CONFIG.protocol)
    assert KEY not in p.status().model_dump_json()
    with pytest.raises(PublicError) as caught:run(p)
    assert caught.value.code=='MODEL_CONFIGURATION_INVALID' and not p.budget.reservations


@pytest.mark.parametrize('http_status,expected',[(200,None),(403,'MODEL_ACCESS_DENIED')])
def test_real_loopback_http_transport_without_company_gateway(http_status,expected):
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from threading import Thread
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            raw=self.rfile.read(int(self.headers['Content-Length']));requests.append((self.path,dict(self.headers),json.loads(raw)))
            payload=json.dumps(result()).encode()
            self.send_response(http_status);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    class LoopbackTransport(httpx.AsyncBaseTransport):
        # Test-only address route, payload/auth/real wire preserved; never production selectable.
        async def handle_async_request(self,request):
            self.inner=httpx.AsyncHTTPTransport()
            target=httpx.URL(f'http://127.0.0.1:{server.server_port}'+request.url.path)
            forwarded=httpx.Request(request.method,target,headers=request.headers,content=request.content)
            return await self.inner.handle_async_request(forwarded)
        async def aclose(self):
            if hasattr(self,'inner'):await self.inner.aclose()
    p=ResponsesProvider(CONFIG,KEY,Permit(),LoopbackTransport())
    try:
        if expected:
            with pytest.raises(PublicError) as caught:run(p)
            assert caught.value.code==expected
        else:assert run(p).text=='fixture response'
        assert len(requests)==1 and requests[0][0]=='/coding-plan/v1/responses'
        assert requests[0][2]['store'] is False and requests[0][2]['stream'] is False
        assert len(p.budget.reservations)==1
    finally:server.shutdown();server.server_close();thread.join(3)
