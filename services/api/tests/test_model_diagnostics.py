"""Safe diagnostics are categories, never remote body/Key/model strings. No gateway calls."""
import asyncio,json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.model_provider import MessagesProvider
from data_workspace.auth import PublicError
from test_claude_preset import CONFIG
from test_model_provider import KEY,Permit,response

@pytest.mark.parametrize('change,reason',[
 ({'model':'upstream-private-alias'},'model_mismatch'),
 ({'stop_reason':'max_tokens'},'incomplete_output'),
 ({'content':[{'type':'thinking','thinking':KEY},{'type':'text','text':'OK'}]},'unsupported_content'),
 ({'type':'other'},'envelope_mismatch'),
 ({'content':[]},'content_shape'),
 ({'content':[{'type':'text','text':''}]},'empty_or_oversized_text'),
 ({'usage':{'output_tokens':129}},'output_budget_exceeded'),
 ({'content':[{'type':'text','text':KEY}]},'secret_echo'),
 ({'usage':{'output_tokens':True}},'usage_invalid')])
def test_categories_preserve_strict_checks_and_no_upstream_strings(change,reason):
 data=response(model=CONFIG.model_id,**change) if 'model' not in change else response(**change)
 p=MessagesProvider(CONFIG,KEY,Permit(),httpx.MockTransport(lambda req:httpx.Response(200,json=data)))
 with pytest.raises(PublicError) as caught:asyncio.run(p.generate('fixed'))
 d=caught.value.response_diagnostics
 assert caught.value.code=='MODEL_RESPONSE_INVALID' and d.reason==reason
 assert KEY not in d.model_dump_json() and 'upstream-private-alias' not in d.model_dump_json()
 assert len(p.budget.reservations)==1 and not p._busy

def test_arbitrary_content_and_stop_values_only_fixed_categories():
 data=response(model=CONFIG.model_id,stop_reason=KEY,content=[{'type':KEY,'text':KEY}])
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(json.dumps(data).encode())
 d=caught.value.response_diagnostics
 assert d.stop_reason=='other' and d.content_types==['other'] and KEY not in d.model_dump_json()

@pytest.mark.parametrize('raw',[b'{broken',b'[]'])
def test_malformed_json_or_envelope_no_raw_echo(raw):
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(raw)
 assert caught.value.response_diagnostics.reason in ('invalid_json','envelope_mismatch')

def test_actual_route_stores_diagnostics_and_same_uuid_no_second_network():
 calls=[]
 def handler(req):calls.append(req);return httpx.Response(200,json=response(model=CONFIG.model_id,stop_reason='max_tokens',usage={'input_tokens':10,'output_tokens':128}))
 app=create_app(Settings(mode='development',dev_identity=True));p=MessagesProvider(CONFIG,KEY,Permit(),httpx.MockTransport(handler));app.state.model_provider=p
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
  body={'request_id':str(uuid4()),'execution_generation':app.state.model_tests.generation,'config_version':CONFIG.version,'accept_estimated_cost':True}
  r=c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'})
  assert r.status_code==200 and r.json()['diagnostics']['reason']=='incomplete_output'
  assert r.json()['diagnostics']['output_tokens']==128 and KEY not in r.text
  assert c.post('/api/v1/model-service/test',json=body,headers={'X-Workspace-Request':'1'}).json()==r.json()
  assert len(calls)==1 and not p._verified


@pytest.mark.parametrize('model,reported',[('claude-deepseek-v4.1-flash','claude-deepseek-v4.1-flash'),('private-model-secret','other_or_unreported'),(KEY,'other_or_unreported')])
def test_only_known_public_returned_model_identifiers_disclosed_still_reject_mismatch(model,reported):
 p=MessagesProvider(CONFIG,KEY)
 with pytest.raises(PublicError) as caught:p.parse_response(json.dumps(response(model=model)).encode())
 d=caught.value.response_diagnostics
 assert d.reason=='model_mismatch' and d.returned_model==reported
 assert KEY not in d.model_dump_json() and 'private-model-secret' not in d.model_dump_json()
