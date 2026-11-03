"""Session catalog governance, fake Key/transport only; never supplier or SQL calls."""
import asyncio
from uuid import uuid4
import httpx,pytest
from fastapi.testclient import TestClient
from test_model_connections import app_for,payload,H,KEY,chat_result
from data_workspace.main import create_app
from data_workspace.config import Settings

BASE='http://127.0.0.1:8000'
def ctx(app,**changes):
 return {'execution_generation':app.state.model_tests.generation,'config_version':app.state.model_provider.configuration.version,**changes}
def setup(c,app):
 assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==200
 app.state.model_provider.transport=httpx.MockTransport(lambda r:httpx.Response(200,json=chat_result()))
def run(c,app):
 return c.post('/api/v1/model-service/test',json=ctx(app,request_id=str(uuid4()),accept_estimated_cost=True),headers=H)
def enable(c,app,**changes):
 return c.post('/api/v1/model-service/connection/enabled',json=ctx(app,**{'enabled':True,**changes}),headers=H)

def test_catalog_test_enable_refresh_disable_retest_and_key_clear(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  assert c.get('/api/v1/model-service/catalog').json()['models']==[]
  setup(c,app); budget=app.state.model_provider.budget
  assert enable(c,app).status_code==409
  assert run(c,app).json()['status']=='succeeded'
  catalog=c.get('/api/v1/model-service/catalog').json();entry=catalog['models'][0]
  assert not entry['available'] and entry['generation_verified'] and not entry['query_available']
  assert not entry['stream_verified'] and not entry['tools_verified']
  assert enable(c,app).status_code==200
  entry=c.get('/api/v1/model-service/catalog').json()['models'][0]
  assert entry['available'] and entry['enabled'] and KEY not in str(entry)
  assert c.get('/api/v1/model-service/catalog').json()['models'][0]==entry
  oldctx=ctx(app,enabled=True); oldkey=app.state.model_provider.key
  assert enable(c,app,enabled=False).status_code==200
  assert app.state.model_provider.key==oldkey and not app.state.model_provider._verified
  assert c.post('/api/v1/model-service/connection/enabled',json=oldctx,headers=H).status_code==409
  assert enable(c,app).status_code==409 and budget.summary().reserved_requests==1
  assert run(c,app).json()['status']=='succeeded';assert enable(c,app).status_code==200
  assert c.post('/api/v1/model-service/connection/clear',json={'execution_generation':app.state.model_tests.generation},headers=H).status_code==200
  assert c.get('/api/v1/model-service/catalog').json()['models']==[] and not app.state.model_enabled
  assert budget.summary().reserved_requests==2

@pytest.mark.parametrize('change',[{'config_version':'forged'},{'execution_generation':'forged'},{'enabled':'true'},{'scope':'admin'}])
def test_forged_lifecycle_rejected_without_fee_or_secret_echo(tmp_path,change):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app);r=enable(c,app,**change)
  assert r.status_code in (409,422) and KEY not in r.text
  assert not app.state.model_enabled and app.state.model_provider.budget.summary().reserved_requests==0

def test_catalog_auth_origin_and_no_restart_persistence(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app)
  assert c.post('/api/v1/model-service/connection/enabled',json=ctx(app,enabled=False)).status_code==403
  assert c.get('/api/v1/model-service/catalog',headers={'Origin':'http://evil.example'}).status_code==403
  app.state.model_provider.key=app.state.model_provider.configuration.model_id
  assert c.get('/api/v1/model-service/catalog').json()['models']==[]
 with TestClient(create_app(Settings()),base_url=BASE) as c:
  assert c.get('/api/v1/model-service/catalog').status_code==401
 with TestClient(app_for(tmp_path/'new'),base_url=BASE,client=('127.0.0.1',1)) as c:
  assert c.get('/api/v1/model-service/catalog').json()['models']==[]

def test_failure_or_key_edit_revokes_enabled_catalog(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app);run(c,app);enable(c,app)
  app.state.model_provider.transport=httpx.MockTransport(lambda r:httpx.Response(403,json={'secret':KEY}))
  assert run(c,app).json()['status']=='failed_or_unknown'
  assert not c.get('/api/v1/model-service/catalog').json()['models'][0]['available']
  assert enable(c,app).status_code==409
  setup(c,app);run(c,app);enable(c,app)
  old=c.get('/api/v1/model-service/catalog').json()['models'][0]['id']
  assert c.post('/api/v1/model-service/connection',json=payload(app),headers=H).status_code==200
  entry=c.get('/api/v1/model-service/catalog').json()['models'][0]
  assert entry['id']!=old and not entry['available'] and not entry['generation_verified']

def test_busy_lifecycle_refused_and_catalog_unavailable(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app);run(c,app);enable(c,app)
  app.state.model_provider._busy=True
  assert not c.get('/api/v1/model-service/catalog').json()['models'][0]['available']
  assert enable(c,app,enabled=False).status_code==409
  app.state.model_provider._busy=False
  assert c.get('/api/v1/model-service/catalog').json()['models'][0]['available']



def test_downstream_selection_revalidated_not_trusted_from_browser(tmp_path):
 from data_workspace.model_routes import resolve_catalog_model
 from data_workspace.auth import PublicError
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app);run(c,app);enable(c,app)
  ref=c.get('/api/v1/model-service/catalog').json()['models'][0]['id']
  assert resolve_catalog_model(app,ref) is app.state.model_provider
  with pytest.raises(PublicError):resolve_catalog_model(app,'forged')
  enable(c,app,enabled=False)
  with pytest.raises(PublicError):resolve_catalog_model(app,ref)


def test_exhausted_budget_does_not_offer_or_enable_model(tmp_path):
 app=app_for(tmp_path)
 with TestClient(app,base_url=BASE,client=('127.0.0.1',1)) as c:
  setup(c,app);run(c,app);enable(c,app)
  async def exhaust():
   for _ in range(59):await app.state.model_provider.budget.reserve(request_bytes=100,max_output_tokens=128)
  asyncio.run(exhaust())
  assert not c.get('/api/v1/model-service/catalog').json()['models'][0]['available']
  assert enable(c,app).status_code==409


def test_cancelled_retest_revokes_previously_enabled_selection(tmp_path):
 async def scenario():
  from data_workspace.model_routes import ModelTests
  app=app_for(tmp_path)
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url=BASE) as c:
   assert (await c.post('/api/v1/model-service/connection',json=payload(app),headers=H)).status_code==200
   app.state.model_provider.transport=httpx.MockTransport(lambda r:httpx.Response(200,json=chat_result()))
   r=await c.post('/api/v1/model-service/test',json=ctx(app,request_id=str(uuid4()),accept_estimated_cost=True),headers=H)
   assert r.json()['status']=='succeeded'
   assert (await c.post('/api/v1/model-service/connection/enabled',json=ctx(app,enabled=True),headers=H)).status_code==200
   ready=asyncio.Event()
   async def blocked(req):ready.set();await asyncio.Event().wait()
   app.state.model_provider.transport=httpx.MockTransport(blocked)
   task=asyncio.create_task(c.post('/api/v1/model-service/test',json=ctx(app,request_id=str(uuid4()),accept_estimated_cost=True),headers=H))
   await asyncio.wait_for(ready.wait(),5)
   assert (await c.post('/api/v1/model-service/connection/enabled',json=ctx(app,enabled=False),headers=H)).status_code==409
   task.cancel()
   with pytest.raises(asyncio.CancelledError):await task
   assert not app.state.model_provider._verified and not app.state.model_enabled
   assert app.state.model_provider.budget.summary().reserved_requests==2
 asyncio.run(scenario())
