"""Exact gateway mapping observed through an authorized read-only receipt, not guessed aliases."""
import json,asyncio
from uuid import uuid4
import httpx,pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.model_provider import ModelConfiguration,MessagesProvider
from data_workspace.auth import PublicError
from test_claude_preset import CONFIG
from test_model_provider import KEY,Permit,response
ALIAS='deepseek-v4-1-flash-261017'

def data(**changes):return response(model=ALIAS,content=[{'type':'thinking','thinking':KEY,'signature':'never-return-signature'},{'type':'text','text':'OK'}],**changes)

def test_observed_alias_only_preserves_returned_and_requested_identity():
 p=MessagesProvider(CONFIG,KEY)
 result=p.parse_response(json.dumps(data()).encode())
 assert result.model_id=='deepseek-v4.1-flash' and result.returned_model_id==ALIAS
 assert result.model_binding=='observed_gateway_alias' and result.text=='OK'
 assert KEY not in result.model_dump_json() and 'signature' not in result.model_dump_json()
 assert not p._verified

@pytest.mark.parametrize('name',['deepseek-v4-1-flash-261018','claude-deepseek-v4.1-flash','deepseek-v4-1-flash','other-model'])
def test_unobserved_versions_prefixes_or_names_still_denied(name):
 with pytest.raises(PublicError) as caught:MessagesProvider(CONFIG,KEY).parse_response(json.dumps(response(model=name)).encode())
 assert caught.value.response_diagnostics.reason=='model_mismatch'

@pytest.mark.parametrize('config',[
 ModelConfiguration(CONFIG.endpoint,CONFIG.model_id,CONFIG.protocol,'x_api_key'),
 ModelConfiguration('http://ada-cli-golang.ctripcorp.com/v1/messages',CONFIG.model_id,CONFIG.protocol,'x_api_key'),
 ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/other/messages',CONFIG.model_id,CONFIG.protocol,'bearer'),
 ModelConfiguration(CONFIG.endpoint,'claude-haiku-4-5',CONFIG.protocol,'bearer')])
def test_mapping_not_shared_across_provider_account_contract_or_model(config):
 assert config.observed_response_alias is None
 with pytest.raises(PublicError):MessagesProvider(config,KEY).parse_response(json.dumps(response(model=ALIAS)).encode())

@pytest.mark.parametrize('stop',['max_tokens','tool_use',None])
def test_known_alias_does_not_bypass_complete_output(stop):
 with pytest.raises(PublicError) as caught:MessagesProvider(CONFIG,KEY).parse_response(json.dumps(data(stop_reason=stop)).encode())
 assert caught.value.response_diagnostics.reason=='incomplete_output'

def test_alias_still_rejects_tool_blocks_or_secret_text():
 p=MessagesProvider(CONFIG,KEY)
 for blocks in ([{'type':'tool_use','name':'arbitrary','input':{}}],[{'type':'text','text':KEY}]):
  with pytest.raises(PublicError):p.parse_response(json.dumps(response(model=ALIAS,content=blocks)).encode())

def test_alias_version_and_receipt_tracking_readonly_no_extra_call():
 assert CONFIG.observed_response_alias==ALIAS
 assert CONFIG.version!=ModelConfiguration(CONFIG.endpoint,CONFIG.model_id,CONFIG.protocol,'x_api_key').version
 calls=[]
 def handler(req):calls.append(req);return httpx.Response(200,json=data())
 app=create_app(Settings(mode='development',dev_identity=True));p=MessagesProvider(CONFIG,KEY,Permit(),httpx.MockTransport(handler));app.state.model_provider=p
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
  rid=str(uuid4());body={'request_id':rid,'execution_generation':app.state.model_tests.generation,'config_version':CONFIG.version,'accept_estimated_cost':True}
  r=c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'})
  assert r.json()['status']=='succeeded' and r.json()['generation']['returned_model_id']==ALIAS
  assert c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'}).json()==r.json()
  read=c.get('/api/v1/model-service/tests/'+rid+'/diagnostics');assert read.json()['status']=='succeeded' and 'generation' not in read.json()
  assert len(calls)==1 and len(p.budget.reservations)==1


@pytest.mark.parametrize('block',[
 {'type':'thinking','thinking':'fixture reasoning without signature'},
 {'type':'thinking','text':'fixture translated reasoning'},
 {'type':'thinking'},
 {'type':'redacted_thinking','data':{'opaque':'fixture'}},
 {'type':'thinking','signature':None,'private_value':'fixture'}])
def test_observed_gateway_opaque_reasoning_not_interpreted_or_disclosed(block):
 p=MessagesProvider(CONFIG,KEY)
 value=p.parse_response(json.dumps(response(model=ALIAS,content=[block,{'type':'text','text':'OK'}])).encode())
 assert value.text=='OK' and value.returned_model_id==ALIAS
 assert 'fixture' not in value.model_dump_json() and value.model_binding=='observed_gateway_alias'
 # The gateway envelope cannot turn reasoning-only output or tool calls into valid text.
 with pytest.raises(PublicError):p.parse_response(json.dumps(response(model=ALIAS,content=[block])).encode())

def test_opaque_gateway_exception_does_not_allow_tools_bad_text_or_other_models():
 p=MessagesProvider(CONFIG,KEY)
 for content in ([{'type':'thinking'},{'type':'text','text':None}],
                 [{'type':'thinking'},{'type':'tool_use','name':'execute_sql','input':{}}],
                 [{'type':'thinking'},{'type':'text','text':KEY}]):
  with pytest.raises(PublicError):p.parse_response(json.dumps(response(model=ALIAS,content=content)).encode())
 with pytest.raises(PublicError):p.parse_response(json.dumps(response(model='unapproved-model',content=[{'type':'thinking'},{'type':'text','text':'OK'}])).encode())

def test_binding_diagnostic_distinguishes_exact_name_from_allowed_alias():
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(json.dumps(response(model=ALIAS,content=[{'type':'tool_use'}])).encode())
 d=caught.value.response_diagnostics
 assert d.model_matches is False and d.model_binding=='observed_gateway_alias'
 assert d.reason=='unsupported_content'
