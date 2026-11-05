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
from data_workspace.model_routes import resolve_catalog_model
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

@pytest.mark.parametrize('model',['claude-sonnet-user-choice','deepseek-custom-choice','gateway/model-v2'])
def test_aiplan_user_model_name_not_locked_but_endpoint_auth_still_governed(tmp_path,model):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  body=payload(app,preset='ai_plan',protocol='anthropic_messages',endpoint='http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',model_id=model,authentication='bearer')
  r=c.post('/api/v1/model-service/connection',json=body,headers=H)
  # Governed private model IDs permit valid standard characters, not slash aliases.
  if '/' in model:
   assert r.status_code==422
  else:
   assert r.status_code==200 and KEY not in r.text
   assert app.state.model_provider.configuration.model_id==model
   assert app.state.model_provider.configuration.observed_response_alias is None
   status=c.get('/api/v1/model-service/status').json()
   assert status['model_id']==model and not status['generation_verified']
   assert status['endpoint']==body['endpoint'] and KEY not in str(status)
  assert app.state.model_provider.budget.summary().reserved_requests==0

@pytest.mark.parametrize('change',[{'endpoint':'http://10.0.0.1/v1/messages'},{'protocol':'openai_responses'},{'authentication':'x_api_key'}])
def test_user_selected_aiplan_model_does_not_widen_network_auth_grant(tmp_path,change):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  body=payload(app,preset='ai_plan',protocol='anthropic_messages',endpoint='http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',model_id='my-chosen-model',authentication='bearer')
  body.update(change);r=c.post('/api/v1/model-service/connection',json=body,headers=H)
  assert r.status_code==403 and KEY not in r.text
  assert not app.state.model_provider.key and app.state.model_provider.budget.summary().reserved_requests==0

def test_private_user_model_response_still_exact_not_fuzzy(tmp_path):
 from data_workspace.auth import PublicError
 from test_model_provider import Permit
 data={'type':'message','role':'assistant','model':'other-version','stop_reason':'end_turn','content':[{'type':'text','text':'OK'}],'usage':{'input_tokens':4,'output_tokens':2}}
 provider=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','my-user-model','anthropic_messages','bearer'),KEY,Permit(),httpx.MockTransport(lambda r:httpx.Response(200,json=data)))
 with pytest.raises(PublicError):asyncio.run(provider.generate('fixed'))
 assert not provider._verified


def test_multi_model_catalog_add_test_enable_select_remove(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==200
  generation=app.state.model_tests.generation
  primary_version=app.state.model_provider.configuration.version
  added=c.post('/api/v1/model-service/connection/models',json={'execution_generation':generation,'config_version':primary_version,'model_id':'second-model'},headers=H)
  assert added.status_code==200,added.text
  entry=app.state.model_registry.entries['second-model']
  entry.provider.transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'model':'second-model','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'OK'}}],'usage':{'prompt_tokens':4,'completion_tokens':2}}))
  catalog=c.get('/api/v1/model-service/catalog').json()
  assert len(catalog['models'])==2 and catalog['default_model_id']=='fixture-model'
  second=next(model for model in catalog['models'] if model['model_id']=='second-model')
  assert second['available'] is False and second['enabled'] is False
  tested=c.post('/api/v1/model-service/models/test',json={'model_id':'second-model','request_id':str(uuid4()),'execution_generation':generation,'config_version':entry.provider.configuration.version,'accept_estimated_cost':True},headers=H)
  assert tested.status_code==200 and tested.json()['status']=='succeeded'
  enabled=c.post('/api/v1/model-service/models/enabled',json={'model_id':'second-model','execution_generation':generation,'config_version':entry.provider.configuration.version,'enabled':True},headers=H)
  assert enabled.status_code==200,enabled.text
  catalog=c.get('/api/v1/model-service/catalog').json()
  second=next(model for model in catalog['models'] if model['model_id']=='second-model')
  assert second['enabled'] is True and second['available'] is True and second['source']=='personal_api'
  assert resolve_catalog_model(app,second['id']) is entry.provider
  removed=c.post('/api/v1/model-service/connection/models/remove',json={'execution_generation':generation,'config_version':primary_version,'model_id':'second-model'},headers=H)
  assert removed.status_code==200,removed.text
  assert len(c.get('/api/v1/model-service/catalog').json()['models'])==1
  assert entry.provider.key==''


def test_multi_model_rejects_primary_duplicate_and_unverified_enable(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',1)) as c:
  assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==200
  generation=app.state.model_tests.generation
  primary_version=app.state.model_provider.configuration.version
  duplicate=c.post('/api/v1/model-service/connection/models',json={'execution_generation':generation,'config_version':primary_version,'model_id':'fixture-model'},headers=H)
  assert duplicate.status_code==409 and duplicate.json()['code']=='MODEL_ALREADY_PRIMARY'
  added=c.post('/api/v1/model-service/connection/models',json={'execution_generation':generation,'config_version':primary_version,'model_id':'second-model'},headers=H)
  assert added.status_code==200
  entry=app.state.model_registry.entries['second-model']
  enable=c.post('/api/v1/model-service/models/enabled',json={'model_id':'second-model','execution_generation':generation,'config_version':entry.provider.configuration.version,'enabled':True},headers=H)
  assert enable.status_code==409 and enable.json()['code']=='MODEL_NOT_VERIFIED'
  stale=c.post('/api/v1/model-service/connection/models',json={'execution_generation':generation,'config_version':'stale','model_id':'third-model'},headers=H)
  assert stale.status_code==409
