"""Actual bounded stdio/long-lived owner recovery, not production persistence."""
import asyncio
from copy import deepcopy
from pathlib import Path
import time
import anyio
import pytest
from fastapi.testclient import TestClient
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.contracts import AuthContext
from data_workspace.worker_runtime import WorkerLimits,WorkerFailure,WindowsJob
from data_workspace.warehouse.stdio_transport import governed_stdio
from data_workspace.warehouse.client import OwnedMCPClient
from test_worker_runtime import alive

PROBE=Path(__file__).with_name('stdio_probe.py')
HEADERS={'X-Workspace-Request':'1'}

@pytest.mark.parametrize('mode,code',[('cpu','WORKER_CPU_LIMIT'),('output','WORKER_OUTPUT_LIMIT'),('crash','WORKER_CRASHED')])
def test_actual_stdio_fault_limits_release_job_and_slot(mode,code,tmp_path):
    pidfile=tmp_path/'pid'
    async def exercise():
        with anyio.fail_after(10):
            async with governed_stdio(mode,pidfile,limits=WorkerLimits(cpu_seconds=1),entry=PROBE) as (read,write,state):
                value=await read.receive()
                assert isinstance(value,WorkerFailure) and value.code==code
                assert not state.healthy
                pid=state.process.pid
            assert not alive(pid)
            async with governed_stdio('ready',None,entry=PROBE) as (read,write,state):
                assert (await read.receive()).message.root.method=='notifications/ready'
                pid=state.process.pid
            assert not alive(pid)
    asyncio.run(exercise())


def test_stdio_memory_hard_limit_actually_refuses_allocation():
    async def exercise():
        with anyio.fail_after(5):
            async with governed_stdio('memory',None,limits=WorkerLimits(memory_bytes=32*1024*1024,job_memory_bytes=64*1024*1024),entry=PROBE) as (read,write,state):
                value=await read.receive()
                assert value.message.root.params['refused'] is True
                pid=state.process.pid
            assert not alive(pid)
    asyncio.run(exercise())


def test_stdio_assignment_failure_cannot_read_bootstrap_and_does_not_fallback(tmp_path,monkeypatch):
    marker=tmp_path/'must-not-exist'
    async def exercise():
        with monkeypatch.context() as patch:
            def failed(self,process):raise WorkerFailure('WORKER_ISOLATION_UNAVAILABLE')
            patch.setattr(WindowsJob,'assign',failed)
            with pytest.raises(WorkerFailure) as caught:
                async with governed_stdio('ready',marker,entry=PROBE):pytest.fail('isolation bypass')
            assert caught.value.code=='WORKER_ISOLATION_UNAVAILABLE' and not marker.exists()
        async with governed_stdio('ready',None,entry=PROBE) as (read,write,state):
            assert (await read.receive()).message.root.method=='notifications/ready'
    asyncio.run(exercise())


def wait_failed(client):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        summary=client.get('/api/v1/connectors/owned-synthetic').json()
        if summary['state']=='FAILED':return summary
        time.sleep(.03)
    pytest.fail('actual MCP death did not become FAILED')

def query(generation,key='new'):
    return {'request':{'table':'fact_order','limit':5},'idempotency_key':key,'confirmed':True,'execution_generation':generation}

def test_actual_long_lived_process_death_rotates_generation_expires_results_and_manually_recovers():
    app=create_app(Settings(mode='development',dev_identity=True,owned_warehouse=True))
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        manager=app.state.connector
        generation=client.get('/api/v1/connectors/owned-synthetic').json()['execution_generation']
        first=client.post('/api/v1/execution-previews',json=query(generation,'first'),headers=HEADERS);assert first.status_code==200,first.text
        task=first.json()['task_id'];assert first.json()['status']=='SUCCEEDED'
        assert client.get(f'/api/v1/execution-previews/{task}/result').status_code==200
        old=manager.client.current.transport.process.pid
        # Abort only this test app's parent-owned job; no guessed production PID.
        manager.client.current.transport.abort()
        failed=wait_failed(client);assert failed['execution_generation']!=generation
        assert not alive(old) and manager.client.current is None
        assert client.get(f'/api/v1/execution-previews/{task}').json()['status']=='RESULT_EXPIRED'
        rejected=client.get(f'/api/v1/execution-previews/{task}/result');assert rejected.status_code==409 and rejected.json()['code']=='RESULT_CONTEXT_EXPIRED'
        stale=client.post('/api/v1/execution-previews',json=query(generation,'never-replay'),headers=HEADERS);assert stale.status_code==409
        assert client.get('/api/v1/connectors/owned-synthetic/tables/fact_order/schema').status_code==502
        verified=client.post('/api/v1/connectors/owned-synthetic/verify',json={},headers=HEADERS);assert verified.status_code==200,verified.text
        current=verified.json()['connector']['execution_generation'];assert current!=generation and verified.json()['connector']['verified']
        assert manager.client.current.transport.process.pid!=old
        tombstone=client.post('/api/v1/execution-previews',json=query(current,'first'),headers=HEADERS).json();assert tombstone['task_id']==task and tombstone['status']=='RESULT_EXPIRED'
        success=client.post('/api/v1/execution-previews',json=query(current,'fresh'),headers=HEADERS);assert success.json()['status']=='SUCCEEDED'
        assert client.get(f'/api/v1/execution-previews/{task}/result').status_code==409
        new_pid=manager.client.current.transport.process.pid
    assert not alive(new_pid)


def test_actual_submit_then_lost_reply_is_never_replayed_after_reconnect(monkeypatch):
    app=create_app(Settings(mode='development',dev_identity=True,owned_warehouse=True))
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        manager=app.state.connector;generation=manager.generation;calls=[]
        original=manager.client.current.call
        async def drop_reply(name,args=None):
            value=await original(name,args)
            if name=='submit_query':calls.append(value['task']['task_id']);raise RuntimeError('test-only dropped reply')
            return value
        monkeypatch.setattr(manager.client.current,'call',drop_reply)
        result=client.post('/api/v1/execution-previews',json=query(generation,'lost'),headers=HEADERS)
        assert result.status_code==200 and result.json()['status']=='OUTCOME_UNKNOWN'
        task=result.json()['task_id'];assert len(calls)==1
        assert manager.generation!=generation and manager.failed
        recovered=client.post('/api/v1/connectors/owned-synthetic/verify',json={},headers=HEADERS);assert recovered.status_code==200
        again=client.post('/api/v1/execution-previews',json=query(manager.generation,'lost'),headers=HEADERS)
        assert again.json()['task_id']==task and again.json()['status']=='OUTCOME_UNKNOWN' and len(calls)==1
        assert client.get(f'/api/v1/execution-previews/{task}/result').status_code==409


def test_repeated_long_lived_recovery_stays_same_owner_task_and_leaks_no_processes():
    app=create_app(Settings(mode='development',dev_identity=True,owned_warehouse=True))
    pids=[]
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        owner=app.state.connector.client.task
        for _ in range(3):
            service=app.state.connector.client;pids.append(service.current.transport.process.pid)
            service.current.transport.abort();wait_failed(client)
            assert client.post('/api/v1/connectors/owned-synthetic/verify',json={},headers=HEADERS).status_code==200
            assert app.state.connector.client.task is owner
        pids.append(app.state.connector.client.current.transport.process.pid)
    assert all(not alive(pid) for pid in pids)


def test_cancelled_request_keeps_unknown_receipt_and_never_replays_same_key():
    from data_workspace.connector_routes import ConnectorManager,PreviewSubmit
    async def exercise():
        manager=ConnectorManager(True);manager.verified=True
        entered=asyncio.Event();release=asyncio.Event();calls=[]
        async def waiting(*args):
            calls.append(1);entered.set();await release.wait()
            return {'task':{'task_id':'unused','status':'SUCCEEDED'}}
        manager.call=waiting
        body=PreviewSubmit.model_validate(query(manager.generation,'disconnected'))
        task=asyncio.create_task(manager.submit(AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer'),body,'test-trace'))
        await entered.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        record=next(iter(manager.tasks.values()))
        assert record['receipt'].status=='OUTCOME_UNKNOWN' and not manager.active
        receipt=await manager.submit(AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer'),body,'test-trace')
        assert receipt.status=='OUTCOME_UNKNOWN' and calls==[1]
    asyncio.run(exercise())


def test_capacity_rejection_is_not_a_worker_fault_or_generation_change():
    from data_workspace.connector_routes import ConnectorManager
    from data_workspace.auth import PublicError
    async def exercise():
        manager=ConnectorManager(True);manager.verified=True;generation=manager.generation
        class Busy:
            async def call(self,*args):raise PublicError(409,'CAPACITY_EXCEEDED','safe capacity error')
        manager.client=Busy()
        with pytest.raises(PublicError) as caught:await manager.call(AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer'),'list_tables')
        assert caught.value.code=='CAPACITY_EXCEEDED' and manager.generation==generation and manager.verified and not manager.failed
    asyncio.run(exercise())
