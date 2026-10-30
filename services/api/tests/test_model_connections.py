"""Generic BYOK tests use fake keys and isolated transports. No supplier calls."""
import asyncio,json
from uuid import uuid4
import httpx,pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.model_provider import ModelConfiguration,MessagesProvider
from data_workspace.model_egress import public_endpoint_valid,PublicModelTransport
from data_workspace.model_budget import EstimatedBudget
from data_workspace.chat_model_provider import ChatCompletionsProvider
from test_model_provider import KEY

def payload(app,**change):
 return {'preset':'custom','protocol':'openai_chat_completions','endpoint':'https://api.example.com/v1/chat/completions','model_id':'fixture-model','authentication':'bearer','api_key':KEY,'execution_generation':app.state.model_tests.generation,'accept_fixed_test_egress':True,'accept_estimated_cost':True,**change}
H={'X-Workspace-Request':'1'}
def app_for(tmp_path):
 app=create_app(Settings(mode='development',dev_identity=True));app.state.model_provider.budget=EstimatedBudget(tmp_path/'budget');return app

def test_web_save_clear_no_key_echo_or_fee_and_version_invalidation(tmp_path):
 app=app_for(tmp_path);budget=app.state.model_provider.budget
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  old=app.state.model_tests.generation
  r=c.post('/api/v1/model-service/connection',json=payload(app),headers=H);assert r.status_code==200,r.text
  assert KEY not in r.text and isinstance(app.state.model_provider,ChatCompletionsProvider)
  assert app.state.model_provider.key==KEY and app.state.model_tests.generation!=old
  assert budget.summary().reserved_requests==0
  status=c.get('/api/v1/model-service/status');assert KEY not in status.text and status.json()['test_available']
  assert not status.json()['generation_verified']
  r=c.post('/api/v1/model-service/connection/clear',json={'execution_generation':app.state.model_tests.generation},headers=H)
  assert r.status_code==200 and KEY not in r.text and app.state.model_provider.key==''
  assert budget.summary().reserved_requests==0

@pytest.mark.parametrize('endpoint',['http://api.example.com/v1/messages','https://127.0.0.1/v1/messages','https://169.254.169.254/v1/messages','https://localhost/v1/messages','https://host.internal/v1/messages','https://user:secret@api.example.com/v1/messages','https://api.example.com/v1/messages?key=x','https://api.example.com/../v1/messages','https://api.example.com:8080/v1/messages'])
def test_custom_ssrf_and_secret_urls_refuse_without_touching_old_key(tmp_path,endpoint):
 app=app_for(tmp_path);app.state.model_provider.key='old-fixture-key'
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/model-service/connection',json=payload(app,protocol='anthropic_messages',endpoint=endpoint),headers=H)
  assert r.status_code==422 and KEY not in r.text and 'secret@' not in r.text
  assert app.state.model_provider.key=='old-fixture-key'

def test_auth_origin_body_and_preset_denials_keep_secret_out_of_errors(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  for headers,body,expected in [({},payload(app),403),({**H,'Origin':'http://evil.example'},payload(app),403),(H,payload(app,api_key='bad'),422),(H,payload(app,extra=KEY),422),(H,payload(app,preset='ai_plan'),403),(H,payload(app,endpoint='https://api.example.com/'+KEY+'/messages'),422)]:
   r=c.post('/api/v1/model-service/connection',json=body,headers=headers);assert r.status_code==expected,r.text;assert KEY not in r.text
  r=c.post('/api/v1/model-service/connection',content=json.dumps(payload(app,api_key='x'*9000)),headers={**H,'Content-Type':'application/json'})
  assert r.status_code==413 and 'x'*100 not in r.text
 with TestClient(create_app(Settings()),base_url='http://127.0.0.1:8000') as c:
  assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==401

def test_busy_and_stale_context_no_key_swap(tmp_path):
 app=app_for(tmp_path);old=app.state.model_provider
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  old._busy=True
  assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==409
  old._busy=False
  assert c.post('/api/v1/model-service/connection',json=payload(app,execution_generation='stale'),headers=H).status_code==409
  assert app.state.model_provider is old

def test_private_preset_only_exact_grant_and_no_fee_on_save(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  r=c.post('/api/v1/model-service/connection',json=payload(app,preset='ai_plan',protocol='anthropic_messages',endpoint='http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',model_id='deepseek-v4.1-flash',authentication='bearer'),headers=H)
  assert r.status_code==200 and KEY not in r.text
  assert app.state.model_provider.configuration.observed_response_alias=='deepseek-v4-1-flash-261017'
  assert app.state.model_provider.budget.summary().reserved_requests==0

def test_public_transport_actual_target_ip_pinned_host_tls_and_no_envproxy():
 seen=[]
 def handler(req):
  seen.append(req);assert req.url.host=='8.8.8.8' and req.headers['host']=='api.example.com'
  assert req.extensions['sni_hostname']=='api.example.com';return httpx.Response(200,json={'safe':True})
 async def scenario():
  t=PublicModelTransport('https://api.example.com/v1/messages',resolver=lambda h:'8.8.8.8',transport=httpx.MockTransport(handler))
  async with httpx.AsyncClient(transport=t,trust_env=False) as c:await c.post('https://api.example.com/v1/messages',json={})
 asyncio.run(scenario());assert len(seen)==1

@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','169.254.169.254','::1'])
def test_dns_rebind_private_denied_before_inner_transport(ip):
 async def scenario():
  t=PublicModelTransport('https://api.example.com/v1/messages',resolver=lambda h:ip,transport=httpx.MockTransport(lambda r:pytest.fail('must not connect')))
  from data_workspace.auth import PublicError
  with pytest.raises(PublicError):await t.handle_async_request(httpx.Request('POST','https://api.example.com/v1/messages',content=b'{}'))
  await t.aclose()
 asyncio.run(scenario())

def chat_result():return {'model':'fixture-model','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'OK'}}],'usage':{'prompt_tokens':4,'completion_tokens':2}}
@pytest.mark.parametrize('mutation',['valid','partial','tool','model','empty','usage','key'])
def test_chat_protocol_strict_text_no_tools_or_aliases(mutation):
 from test_model_provider import Permit
 from data_workspace.auth import PublicError
 data=chat_result()
 if mutation=='partial':data['choices'][0]['finish_reason']='length'
 if mutation=='tool':data['choices'][0]['message']['tool_calls']=[{'name':'execute'}]
 if mutation=='model':data['model']='different'
 if mutation=='empty':data['choices'][0]['message']['content']=''
 if mutation=='usage':data['usage']['completion_tokens']=129
 if mutation=='key':data['choices'][0]['message']['content']=KEY
 def handler(req):assert json.loads(req.content)['stream'] is False;return httpx.Response(200,json=data)
 p=ChatCompletionsProvider(ModelConfiguration('https://api.example.com/v1/chat/completions','fixture-model','openai_chat_completions','bearer','public_https'),KEY,Permit(),httpx.MockTransport(handler))
 if mutation=='valid':assert asyncio.run(p.generate('fixed')).text=='OK'
 else:
  with pytest.raises(PublicError):asyncio.run(p.generate('fixed'))


def test_generic_default_auth_reports_bearer_for_chat_and_existing_budget_not_reset(tmp_path):
 app=app_for(tmp_path);b=app.state.model_provider.budget
 asyncio.run(b.reserve(request_bytes=100,max_output_tokens=128))
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  assert c.post('/api/v1/model-service/connection',json=payload(app,authentication='protocol_default'),headers=H).status_code==200
  s=c.get('/api/v1/model-service/status').json();assert s['authentication']=='bearer' and s['budget']['reserved_requests']==1

def test_connection_update_rejected_while_real_async_test_inflight(tmp_path):
 async def scenario():
  from data_workspace.model_routes import ModelTestRequest
  app=app_for(tmp_path);ready=asyncio.Event()
  async def handler(req):ready.set();await asyncio.Event().wait()
  app.state.model_provider=ChatCompletionsProvider(ModelConfiguration('https://api.example.com/v1/chat/completions','fixture-model','openai_chat_completions','bearer','public_https'),KEY,app.state.model_provider.budget,httpx.MockTransport(handler))
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
   old=app.state.model_provider
   task=asyncio.create_task(c.post('/api/v1/model-service/test',json={'request_id':str(uuid4()),'config_version':old.configuration.version,'execution_generation':app.state.model_tests.generation,'accept_estimated_cost':True},headers=H))
   await ready.wait()
   r=await c.post('/api/v1/model-service/connection',json=payload(app),headers=H);assert r.status_code==409
   r=await c.post('/api/v1/model-service/connection/clear',json={'execution_generation':app.state.model_tests.generation},headers=H);assert r.status_code==409
   assert app.state.model_provider is old and old.key==KEY
   task.cancel()
   with pytest.raises(asyncio.CancelledError):await task
 asyncio.run(scenario())
