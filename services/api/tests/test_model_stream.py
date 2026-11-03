"""Messages live stream fixture tests: fake Key, no external model or business data."""
import asyncio,json
from uuid import uuid4
import httpx,pytest
from data_workspace.model_provider import MessagesProvider,ModelConfiguration
from data_workspace.auth import PublicError
from data_workspace.model_budget import EstimatedBudget
from test_model_connections import app_for,H,payload

KEY='stream-fixture-secret'
TEXT='Safe fixed test response. '*4

def frames(text=TEXT,model='fixture-model',stop='end_turn',thinking=True):
    values=[{'type':'message_start','message':{'type':'message','role':'assistant','model':model,'content':[],'stop_reason':None,'usage':{'input_tokens':8,'output_tokens':0}}}]
    index=0
    if thinking:
        values += [{'type':'content_block_start','index':0,'content_block':{'type':'thinking','thinking':'fixture thinking secret','signature':'opaque'}},{'type':'content_block_delta','index':0,'delta':{'type':'thinking_delta','thinking':'private reasoning'}},{'type':'content_block_stop','index':0}];index=1
    values += [{'type':'content_block_start','index':index,'content_block':{'type':'text','text':''}}]
    values += [{'type':'content_block_delta','index':index,'delta':{'type':'text_delta','text':part}} for part in [text[:20],text[20:]]]
    values += [{'type':'content_block_stop','index':index},{'type':'message_delta','delta':{'stop_reason':stop},'usage':{'output_tokens':20}},{'type':'message_stop'}]
    return values

def encoded(values):return b''.join(('event: '+v['type']+'\ndata: '+json.dumps(v)+'\n\n').encode() for v in values)
class Bytes(httpx.AsyncByteStream):
    def __init__(self,data,fragment=11,gate=None):self.data=data;self.fragment=fragment;self.gate=gate
    async def __aiter__(self):
        for i in range(0,len(self.data),self.fragment):
            yield self.data[i:i+self.fragment]
            await asyncio.sleep(0)
        if self.gate:await self.gate.wait()

def provider(tmp_path,values=None,status=200,fragment=11):
    calls=[]
    def handler(req):
        calls.append(req)
        body=json.loads(req.content);assert body['stream'] is True and body['max_tokens']==128
        assert body['messages'][0]['content']=='fixed'
        return httpx.Response(status,headers={'content-type':'text/event-stream'},stream=Bytes(encoded(values or frames()),fragment))
    p=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','fixture-model','anthropic_messages','bearer'),KEY,EstimatedBudget(tmp_path/'budget'),httpx.MockTransport(handler))
    return p,calls

@pytest.mark.parametrize('fragment',[1,11,8192])
def test_live_provider_split_unicode_crlf_safety_and_completion(tmp_path,fragment):
    p,calls=provider(tmp_path,frames(text=TEXT+'中文'),fragment=fragment)
    async def collect():return [e async for e in p.stream('fixed')]
    result=asyncio.run(collect());assert result[-1].kind=='completed'
    assert ''.join(e.text for e in result)==TEXT+'中文'
    assert 'reasoning' not in str(result) and 'thinking' not in str(result) and KEY not in str(result)
    assert result[-1].generation.output_tokens==20 and len(calls)==1 and not p._busy
    assert p.budget.summary().reserved_requests==1

@pytest.mark.parametrize('fault',['model','stop','missing_end','tool','secret','usage','out_of_order','post_stop','invalidjson'])
def test_bad_or_partial_stream_never_completes_or_leaks_key(tmp_path,fault):
    values=frames()
    if fault=='model':values[0]['message']['model']='another-model'
    if fault=='stop':values[-2]['delta']['stop_reason']='max_tokens'
    if fault=='missing_end':values=values[:-2]
    if fault=='tool':values[4]['content_block']={'type':'tool_use','name':'sql'}
    if fault=='secret':values=frames(text='safe '+KEY+' suffix')
    if fault=='usage':values[-2]['usage']['output_tokens']=129
    if fault=='out_of_order':values[5]['index']=99
    if fault=='post_stop':values += [{'type':'message_stop'}]
    p,calls=provider(tmp_path,values)
    if fault=='invalidjson':p.transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Bytes(b'data: no json\n\n')))
    async def scenario():
        results=[]
        with pytest.raises(PublicError):
            async for e in p.stream('fixed'):results.append(e)
        assert all(e.kind!='completed' for e in results)
        assert KEY not in ''.join(e.text for e in results)
        assert not p._busy
    asyncio.run(scenario());assert p.budget.summary().reserved_requests==1

@pytest.mark.parametrize('status,code',[(401,'MODEL_ACCESS_DENIED'),(403,'MODEL_ACCESS_DENIED'),(429,'MODEL_RATE_LIMITED'),(500,'MODEL_SERVICE_FAILED')])
def test_stream_refusal_no_retry_and_reserved(tmp_path,status,code):
    p,calls=provider(tmp_path,status=status)
    async def scenario():
        with pytest.raises(PublicError) as e:
            async for _ in p.stream('fixed'):pass
        assert e.value.code==code
    asyncio.run(scenario());assert len(calls)==1 and p.budget.summary().reserved_requests==1

def body(app,id=None):return {'request_id':id or str(uuid4()),'execution_generation':app.state.model_tests.generation,'config_version':app.state.model_provider.configuration.version,'accept_estimated_cost':True}

def stream_app(tmp_path,missing=False,gate=None):
    app=app_for(tmp_path)
    values=frames()
    if missing:values=values[:-2]
    calls=[]
    def handler(req):
        calls.append(req);return httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Bytes(encoded(values),11,gate))
    app.state.model_provider=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','fixture-model','anthropic_messages','bearer'),KEY,app.state.model_provider.budget,httpx.MockTransport(handler))
    return app,calls

def test_async_product_api_events_poll_idempotent_budget_and_capability(tmp_path):
    async def scenario():
        app,calls=stream_app(tmp_path)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);r=await c.post('/api/v1/model-service/stream-test',json=b,headers=H);assert r.status_code==200
            await app.state.model_stream_tests.tasks[b['request_id']]
            receipt=(await c.get('/api/v1/model-service/stream-tests/'+b['request_id'])).json();assert receipt['status']=='succeeded' and not receipt['sql_executed']
            assert KEY not in str(receipt) and 'reasoning' not in str(receipt)
            assert (await c.post('/api/v1/model-service/stream-test',json=b,headers=H)).json()==receipt
            assert (await c.post('/api/v1/model-service/test',json=b,headers=H)).status_code==409
            status=(await c.get('/api/v1/model-service/status')).json();assert status['stream_verified'] and status['generation_verified']
            assert len(calls)==1 and status['budget']['reserved_requests']==1
            assert (await c.get('/api/v1/model-service/stream-tests/'+b['request_id'],headers={'Origin':'http://evil.example'})).status_code==403
            assert (await c.post('/api/v1/model-service/stream-test',json=body(app))).status_code==403
    asyncio.run(scenario())

def test_incomplete_live_stream_partial_and_busy_cancel_preserve_budget(tmp_path):
    async def scenario():
        gate=asyncio.Event();app,calls=stream_app(tmp_path,missing=True,gate=gate);app.state.model_enabled=True;app.state.model_provider._verified=True
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);r=await c.post('/api/v1/model-service/stream-test',json=b,headers=H);assert r.status_code==200
            for _ in range(100):
                if app.state.model_stream_tests.receipts[b['request_id']].events:break
                await asyncio.sleep(.01)
            assert (await c.post('/api/v1/model-service/connection',json=payload(app),headers=H)).status_code==409
            assert (await c.post('/api/v1/model-service/connection/clear',json={'execution_generation':b['execution_generation']},headers=H)).status_code==409
            receipt=(await c.post('/api/v1/model-service/stream-tests/'+b['request_id']+'/cancel',headers=H)).json()
            assert receipt['status']=='partial' and receipt['error_code']=='MODEL_STREAM_CANCELLED'
            assert not app.state.model_provider._verified and not app.state.model_enabled and not app.state.model_configuration_lock.locked()
            assert app.state.model_provider.budget.summary().reserved_requests==1 and len(calls)==1
            assert (await c.post('/api/v1/model-service/stream-test',json=b,headers=H)).json()==receipt
    asyncio.run(scenario())

def test_unsupported_protocol_and_invalid_id_no_network_or_budget(tmp_path):
    from data_workspace.responses_provider import ResponsesProvider
    async def scenario():
        app,calls=stream_app(tmp_path)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            assert (await c.post('/api/v1/model-service/stream-test',json=body(app,'bad'),headers=H)).status_code==422
            b=body(app);b['config_version']='forged';assert (await c.post('/api/v1/model-service/stream-test',json=b,headers=H)).status_code==409
            old=app.state.model_provider
            app.state.model_provider=ResponsesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/responses','fixture-model','openai_responses'),KEY,old.budget,old.transport)
            assert (await c.post('/api/v1/model-service/stream-test',json=body(app),headers=H)).status_code==409
            assert not calls and old.budget.summary().reserved_requests==0
    asyncio.run(scenario())

@pytest.mark.parametrize('fault',['rawlimit','eventlimit','wrong_encoding','wrong_content_type','timeout','transport'])
def test_stream_network_envelope_resource_limits(tmp_path,fault):
    p,calls=provider(tmp_path)
    def handler(req):
        if fault=='timeout':raise httpx.ReadTimeout('do not expose '+KEY)
        if fault=='transport':raise httpx.ConnectError('do not expose '+KEY)
        data=encoded(frames())
        headers={'content-type':'text/event-stream'}
        if fault=='rawlimit':data=b':' + b'x'*70000+b'\n\n'
        if fault=='eventlimit':data=b'event: ping\ndata: {"type":"ping"}\n\n'*300
        if fault=='wrong_encoding':headers['content-encoding']='gzip'
        if fault=='wrong_content_type':headers['content-type']='application/json'
        return httpx.Response(200,headers=headers,stream=Bytes(data,11))
    p.transport=httpx.MockTransport(handler)
    async def scenario():
        with pytest.raises(PublicError) as e:
            async for _ in p.stream('fixed'):pass
        assert KEY not in e.value.message and not p._busy
    asyncio.run(scenario());assert p.budget.summary().reserved_requests==1

def test_crlf_sse_chunks_and_secret_prefix_held_until_safe(tmp_path):
    p,calls=provider(tmp_path,frames(text=KEY[:10]+'-not-a-secret'),fragment=1)
    original=p.transport
    raw=encoded(frames(text=KEY[:10]+'-not-a-secret')).replace(b'\n',b'\r\n')
    p.transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Bytes(raw,1)))
    async def scenario():return [e async for e in p.stream('fixed')]
    result=asyncio.run(scenario());assert result[-1].kind=='completed' and KEY not in str(result)

def test_shutdown_or_immediate_cancel_releases_admission_and_old_context_receipts(tmp_path):
    async def scenario():
        app,calls=stream_app(tmp_path,missing=True,gate=asyncio.Event())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);assert (await c.post('/api/v1/model-service/stream-test',json=b,headers=H)).status_code==200
            r=await c.post('/api/v1/model-service/stream-tests/'+b['request_id']+'/cancel',headers=H)
            assert r.json()['status'] in ('partial','failed_or_unknown')
            assert not app.state.model_configuration_lock.locked()
            assert (await c.post('/api/v1/model-service/connection',json=payload(app),headers=H)).status_code==200
            assert (await c.get('/api/v1/model-service/stream-tests/'+b['request_id'])).status_code==404
            assert not app.state.model_stream_tests.receipts
            await app.state.model_stream_tests.close()
    asyncio.run(scenario())

def test_stream_unconfigured_and_unsupported_before_fee(tmp_path):
    p,calls=provider(tmp_path);p.key=''
    async def scenario():
        with pytest.raises(PublicError):
            async for _ in p.stream('fixed'):pass
    asyncio.run(scenario());assert not calls and p.budget.summary().reserved_requests==0

def test_busy_stream_refuses_fresh_nonstream_request_without_queue_or_fee(tmp_path):
    async def scenario():
        app,calls=stream_app(tmp_path,missing=True,gate=asyncio.Event())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);assert (await c.post('/api/v1/model-service/stream-test',json=b,headers=H)).status_code==200
            for _ in range(100):
                if calls:break
                await asyncio.sleep(.01)
            response=await asyncio.wait_for(c.post('/api/v1/model-service/test',json=body(app),headers=H),2)
            assert response.status_code==409 and response.json()['code']=='MODEL_CONNECTION_BUSY'
            assert app.state.model_provider.budget.summary().reserved_requests==1
            assert not app.state.model_tests.receipts and len(calls)==1
            await c.post('/api/v1/model-service/stream-tests/'+b['request_id']+'/cancel',headers=H)
            assert app.state.model_provider.budget.summary().reserved_requests==1
    asyncio.run(scenario())

@pytest.mark.parametrize('fault,reason',[('model','model_mismatch'),('stop','incomplete_output'),('tool','unsupported_content'),('usage','usage_invalid'),('secret','secret_echo'),('sequence','sequence')])
def test_failed_snapshot_diagnostics_fixed_safe_not_upstream_body(tmp_path,fault,reason):
    async def scenario():
        app,calls=stream_app(tmp_path)
        values=frames()
        if fault=='model':values[0]['message']['model']='upstream-private-secret-model-'+KEY
        if fault=='stop':values[-2]['delta']['stop_reason']='max_tokens'
        if fault=='tool':values[4]['content_block']={'type':'tool_use','name':KEY}
        if fault=='usage':values[-2]['usage']['output_tokens']=129
        if fault=='secret':values=frames(text='safe '+KEY+' forbidden')
        if fault=='sequence':values[5]['index']=50
        app.state.model_provider.transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Bytes(encoded(values),11)))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);await c.post('/api/v1/model-service/stream-test',json=b,headers=H)
            await app.state.model_stream_tests.tasks[b['request_id']]
            r=await c.get('/api/v1/model-service/stream-tests/'+b['request_id']);value=r.json()
            assert value['diagnostics']['reason']==reason
            assert value['status'] in ('partial','failed_or_unknown') and KEY not in r.text and 'upstream-private' not in r.text
            assert all(e['kind']!='completed' for e in value['events'])
            count=app.state.model_provider.budget.summary().reserved_requests
            assert (await c.get('/api/v1/model-service/stream-tests/'+b['request_id'])).json()==value
            assert app.state.model_provider.budget.summary().reserved_requests==count==1
    asyncio.run(scenario())

def test_busy_nonstream_same_uuid_reads_cached_receipt_no_second_reservation(tmp_path):
    async def scenario():
        from data_workspace.model_routes import ModelTestReceipt
        app,calls=stream_app(tmp_path,missing=True,gate=asyncio.Event())
        cached_body=body(app)
        app.state.model_tests.receipts[cached_body['request_id']]=ModelTestReceipt(request_id=cached_body['request_id'],execution_generation=cached_body['execution_generation'],config_version=cached_body['config_version'],status='failed_or_unknown',error_code='MODEL_RESULT_UNKNOWN')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1:8000') as c:
            b=body(app);await c.post('/api/v1/model-service/stream-test',json=b,headers=H)
            r=await asyncio.wait_for(c.post('/api/v1/model-service/test',json=cached_body,headers=H),2)
            assert r.status_code==200 and r.json()['error_code']=='MODEL_RESULT_UNKNOWN'
            await c.post('/api/v1/model-service/stream-tests/'+b['request_id']+'/cancel',headers=H)
            assert len(calls)<=1
    asyncio.run(scenario())
