"""Estimated campaign and model test endpoint. Fake keys/HTTP only, no company API."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.model_budget import EstimatedBudget
from data_workspace.model_routes import ModelTests,ModelTestRequest,FIXED_TEST
from data_workspace.responses_provider import ResponsesProvider
from test_model_provider import KEY
from test_responses_provider import CONFIG,result


def reserve(b):return asyncio.run(b.reserve(request_bytes=500,max_output_tokens=128))

def test_budget_empty_decimal_exact_cap_and_cross_restart(tmp_path):
    budget=EstimatedBudget(tmp_path/'ledger')
    assert budget.summary().estimated_reserved_usd=='0.00'
    for _ in range(60):reserve(budget)
    summary=EstimatedBudget(tmp_path/'ledger').summary()
    assert summary.estimated_reserved_usd=='15.00' and summary.estimated_remaining_usd=='0.00'
    assert not summary.hard_cost_guarantee and summary.reserved_requests==60
    with pytest.raises(PublicError) as caught:reserve(EstimatedBudget(tmp_path/'ledger'))
    assert caught.value.code=='MODEL_ESTIMATED_BUDGET_EXHAUSTED'

def test_concurrent_process_like_stores_cannot_overspend_reservations(tmp_path):
    root=tmp_path/'ledger';budget=EstimatedBudget(root);budget.summary()
    for _ in range(57):reserve(budget)
    def attempt(_):
        try:reserve(EstimatedBudget(root));return 'ok'
        except PublicError:return 'denied'
    with ThreadPoolExecutor(max_workers=8) as pool:values=list(pool.map(attempt,range(8)))
    assert values.count('ok')==3 and budget.summary().reserved_requests==60

@pytest.mark.parametrize('value',[-1,0,16385,True])
def test_invalid_request_size_denies_before_reservation(tmp_path,value):
    b=EstimatedBudget(tmp_path/'ledger')
    with pytest.raises(PublicError):asyncio.run(b.reserve(request_bytes=value,max_output_tokens=128))
    assert not b.root.exists()

def test_wrong_output_regime_denies(tmp_path):
    with pytest.raises(PublicError):asyncio.run(EstimatedBudget(tmp_path/'ledger').reserve(request_bytes=100,max_output_tokens=129))

def test_unknown_outcome_reserved_across_restart_no_refund(tmp_path):
    b=EstimatedBudget(tmp_path/'ledger');id=reserve(b);assert b.receipt_outcome(id)=='reserved_unknown'
    b.finish(id);b.finish(id)
    again=EstimatedBudget(tmp_path/'ledger');assert again.receipt_outcome(id)=='failed_or_unknown'
    assert again.summary().estimated_reserved_usd=='0.25'

def test_unknown_corrupt_or_empty_existing_ledger_not_reinitialized(tmp_path):
    root=tmp_path/'ledger';root.mkdir();file=root/'estimated-budget.sqlite3';file.write_bytes(b'unknownfixture')
    with pytest.raises(PublicError):reserve(EstimatedBudget(root))
    assert file.read_bytes()==b'unknownfixture'

def test_modified_campaign_denies(tmp_path):
    b=EstimatedBudget(tmp_path/'ledger');b.summary()
    with sqlite3.connect(b.root/'estimated-budget.sqlite3') as db:db.execute('UPDATE campaign SET max_requests=999')
    with pytest.raises(PublicError):reserve(b)

def test_ledger_hardlink_and_outside_path_refused(tmp_path):
    import os
    root=tmp_path/'ledger';root.mkdir();original=tmp_path/'original';original.write_bytes(b'unchanged')
    os.link(original,root/'estimated-budget.sqlite3')
    with pytest.raises(PublicError):reserve(EstimatedBudget(root))
    assert original.read_bytes()==b'unchanged'

def setup_app(tmp_path,handler):
    app=create_app(Settings(mode='development',dev_identity=True))
    b=EstimatedBudget(tmp_path/'ledger');app.state.model_provider=ResponsesProvider(CONFIG,KEY,b,httpx.MockTransport(handler))
    return app,b

def body(app):return {'request_id':str(uuid4()),'execution_generation':app.state.model_tests.generation,'config_version':CONFIG.version,'accept_estimated_cost':True}
H={'X-Workspace-Request':'1'}

def test_actual_api_fixed_prompt_receipt_idempotency_no_sql_or_browserkey(tmp_path):
    calls=[]
    def handler(req):calls.append(req);assert json.loads(req.content)['input']==FIXED_TEST;return httpx.Response(200,json=result())
    app,b=setup_app(tmp_path,handler)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
        ready=c.get('/api/v1/model-service/status').json();assert ready['test_available'] and ready['budget']['mode']=='estimated_soft_budget'
        payload=body(app)
        receipt=c.post('/api/v1/model-service/test',json=payload,headers=H);assert receipt.status_code==200,receipt.text
        assert receipt.json()['status']=='succeeded' and not receipt.json()['sql_executed'] and KEY not in receipt.text
        assert c.post('/api/v1/model-service/test',json=payload,headers=H).json()==receipt.json()
        assert len(calls)==1 and b.summary().reserved_requests==1
        assert c.get('/api/v1/model-service/status').json()['generation_verified']
        assert c.post('/api/v1/model-service/test',json={**body(app),'key':KEY},headers=H).status_code==422
        assert c.post('/api/v1/model-service/test',json=body(app)).status_code==403
        assert c.post('/api/v1/model-service/test',json=body(app),headers={**H,'Origin':'http://evil.example'}).status_code==403
    # DB contains only usage/outcome/UUID metadata, never the prompt or Key.
    assert KEY.encode() not in (b.root/'estimated-budget.sqlite3').read_bytes()
    assert FIXED_TEST.encode() not in (b.root/'estimated-budget.sqlite3').read_bytes()

def test_failed_unknown_test_does_not_retry_refund_or_echo(tmp_path):
    calls=[]
    def handler(req):calls.append(req);raise httpx.ReadTimeout(KEY)
    app,b=setup_app(tmp_path,handler)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
        payload=body(app);receipt=c.post('/api/v1/model-service/test',json=payload,headers=H)
        assert receipt.json()['error_code']=='MODEL_RESULT_UNKNOWN' and KEY not in receipt.text
        assert c.post('/api/v1/model-service/test',json=payload,headers=H).json()==receipt.json()
        assert len(calls)==1 and b.summary().estimated_reserved_usd=='0.25'

def test_old_context_rejected_after_restart_no_new_network(tmp_path):
    app,b=setup_app(tmp_path,lambda req:pytest.fail('expired'))
    old=body(app);app.state.model_tests=ModelTests()
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
        assert c.post('/api/v1/model-service/test',json=old,headers=H).status_code==409
        assert c.post('/api/v1/model-service/test',json={**body(app),'config_version':'old'},headers=H).status_code==409
        assert c.post('/api/v1/model-service/test',json={**body(app),'accept_estimated_cost':False},headers=H).status_code==422
    assert not b.root.exists()

def test_busy_cancellation_keeps_reservation_and_same_request_unknown(tmp_path):
    async def scenario():
        started=asyncio.Event()
        async def handler(req):started.set();await asyncio.Event().wait()
        app,b=setup_app(tmp_path,handler);manager=app.state.model_tests
        payload=ModelTestRequest(**body(app));task=asyncio.create_task(manager.run(app.state.model_provider,payload));await started.wait()
        with pytest.raises(PublicError) as caught:await manager.run(app.state.model_provider,ModelTestRequest(**body(app)))
        assert caught.value.code=='MODEL_BUSY';task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        again=await manager.run(app.state.model_provider,payload)
        assert again.status=='failed_or_unknown' and b.summary().reserved_requests==1
    asyncio.run(scenario())

def test_budget_admission_failure_does_not_set_verified(tmp_path):
    app,b=setup_app(tmp_path,lambda req:pytest.fail('budgetexhausted'))
    for _ in range(60):reserve(b)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:
        assert not c.get('/api/v1/model-service/status').json()['test_available']
        r=c.post('/api/v1/model-service/test',json=body(app),headers=H).json()
        assert r['error_code']=='MODEL_ESTIMATED_BUDGET_EXHAUSTED' and not app.state.model_provider._verified
