import asyncio,json
from uuid import uuid4
import httpx,pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.model_provider import MessagesProvider
from data_workspace.auth import PublicError
from test_claude_preset import CONFIG
from test_model_provider import KEY,Permit,response

@pytest.mark.parametrize('name',['deepseek-v4.1-flash-202610','DeepSeek-V4.1-Flash','vendor/deepseek-v4.1-flash'])
def test_safe_diagnostic_identifier_is_not_a_model_mapping(name):
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(json.dumps(response(model=name)).encode())
 d=caught.value.response_diagnostics
 assert d.returned_model_identifier==name and d.reason=='model_mismatch'
 assert not p._verified

@pytest.mark.parametrize('name',[KEY,'ada_claude_secret','gpt-token-value','deepseek\nrawtext','deepseek<unsafe>','x'*200])
def test_unsafe_identifier_not_reflected(name):
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(json.dumps(response(model=name)).encode())
 assert caught.value.response_diagnostics.returned_model_identifier is None
 assert KEY not in caught.value.response_diagnostics.model_dump_json()

def test_valid_thinking_and_redacted_blocks_ignored_text_only():
 p=MessagesProvider(CONFIG,KEY)
 data=response(model=CONFIG.model_id,content=[{'type':'thinking','thinking':KEY,'signature':'private-signature'},{'type':'redacted_thinking','data':'private-opaque'},{'type':'text','text':'OK'}])
 value=p.parse_response(json.dumps(data).encode())
 assert value.text=='OK' and KEY not in value.model_dump_json()
 assert 'private' not in value.model_dump_json()
 # No text or arbitrary tools must never become success.
 for content in ([{'type':'thinking','thinking':'internal','signature':'sig'}],[{'type':'tool_use','name':'sql','input':{}}]):
  with pytest.raises(PublicError):p.parse_response(json.dumps(response(model=CONFIG.model_id,content=content)).encode())

def test_readonly_diagnostics_returns_no_body_and_never_reinvokes():
 calls=[]
 def handler(req):calls.append(req);return httpx.Response(200,json=response(model='vendor/deepseek-v4.1-flash',content=[{'type':'thinking','thinking':KEY,'signature':'sig'},{'type':'text','text':'private-result'}]))
 app=create_app(Settings(mode='development',dev_identity=True));p=MessagesProvider(CONFIG,KEY,Permit(),httpx.MockTransport(handler));app.state.model_provider=p
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
  rid=str(uuid4());payload={'request_id':rid,'execution_generation':app.state.model_tests.generation,'config_version':CONFIG.version,'accept_estimated_cost':True}
  assert c.post('/api/v1/model-service/test',json=payload,headers={'X-Workspace-Request':'1'}).status_code==200
  for _ in range(3):
   r=c.get('/api/v1/model-service/tests/'+rid+'/diagnostics');assert r.status_code==200
   assert r.json()['diagnostics']['returned_model_identifier']=='vendor/deepseek-v4.1-flash'
   assert KEY not in r.text and 'private-result' not in r.text and 'generation' not in r.json()
  assert len(calls)==1 and len(p.budget.reservations)==1
  assert c.get('/api/v1/model-service/tests/missing/diagnostics').status_code==404
 with TestClient(create_app(Settings()),base_url='http://127.0.0.1:8000') as c:
  assert c.get('/api/v1/model-service/tests/'+rid+'/diagnostics').status_code==401
