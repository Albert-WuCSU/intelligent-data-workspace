"""Policy A automatic lifecycle tests; real deletion ONLY in fresh isolated roots."""
import asyncio
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json
import os
from threading import Event
import time
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.source_profiles import SourceStore
from data_workspace.retention import TTL,MARKER,storage_lease,write_marker,write_test_reference
from data_workspace.retention_cycle import execute_cycle,worker_cycle
from data_workspace.retention_runner import RetentionRunner,read_cycle,save_cycle
from data_workspace.worker_runtime import run_worker,_run_entry,WorkerLimits,WorkerFailure,SLOTS
from test_retention import AUTH,NOW,artifact,hashes,store


def test_cycle_bounded_targets_then_next_cycle_only_remaining(store):
    folders=[artifact(store) for _ in range(10)]
    unknown=store.root/'uploads'/str(uuid4());unknown.mkdir();(unknown/'original.csv').write_bytes(b'unknown')
    value=execute_cycle(store,AUTH)
    assert value['reclaimed']==8 and value['deferred']==2 and value['state']=='PARTIAL'
    assert sum(p.exists() for p in folders)==2 and unknown.exists()
    second=execute_cycle(store,AUTH)
    assert second['reclaimed']==2 and second['state']=='SUCCEEDED' and unknown.exists()
    assert execute_cycle(store,AUTH)['reclaimed']==0


def test_cycle_saved_disabled_active_durable_refs_and_unknown_legacy_protected(store):
    upload=artifact(store);snapshot=artifact(store,'snapshots',upload_id=upload.name)
    with store.db() as db:
        db.execute('INSERT INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES (?,?,?,?,?,?,?,?)',
                   [str(uuid4()),store.owner(AUTH),'saved',1,0,str(snapshot/'source.duckdb'),'saved',NOW.isoformat()])
    tested=artifact(store)
    write_test_reference(store.root,str(uuid4()),owner=store.owner(AUTH),at=NOW.isoformat(),snapshot_id=None,upload_id=tested.name)
    disposable=artifact(store)
    result=execute_cycle(store,AUTH)
    assert result['reclaimed']==1 and not disposable.exists()
    assert all(p.exists() for p in (upload,snapshot,tested)) and result['protected']>=3


def test_full_scan_failure_or_corrupt_refs_never_starts_deleting(store,monkeypatch):
    folder=artifact(store);other=artifact(store);before=hashes(folder)
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention_cycle.MAX_FOLDERS',1)
        with pytest.raises(PublicError) as caught:execute_cycle(store,AUTH)
        assert caught.value.code=='STORAGE_SCAN_INCOMPLETE'
    assert hashes(folder)==before and other.exists()
    refs=store.root/'test-references';refs.mkdir();(refs/(str(uuid4())+'.json')).write_text('{}')
    with pytest.raises(PublicError) as caught:execute_cycle(store,AUTH)
    assert caught.value.code=='STORAGE_REFERENCES_INVALID' and hashes(folder)==before


def test_cycle_metadata_and_actual_hash_budget_no_unbounded_deletion(store,monkeypatch):
    folder=artifact(store);before=hashes(folder)
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention_cycle.METADATA_BYTES',1)
        with pytest.raises(PublicError):execute_cycle(store,AUTH)
    assert hashes(folder)==before
    monkeypatch.setattr('data_workspace.retention_cycle.MAX_HASH_BYTES',1)
    value=execute_cycle(store,AUTH)
    assert value['deferred']==1 and value['reclaimed']==0 and folder.exists()


def test_marked_interrupted_staging_reclaimed_unknown_children_never_deleted(store):
    id=str(uuid4());folder=store.root/'staging'/id;folder.mkdir(parents=True)
    write_marker(store.root,folder,kind='upload',owner=store.owner(AUTH),created_at=(NOW-TTL-timedelta(seconds=1)).isoformat())
    (folder/'source.csv').write_bytes(b'isolated partial')
    unknown=artifact(store);(unknown/'unknown.txt').write_bytes(b'protect')
    result=execute_cycle(store,AUTH)
    assert not folder.exists() and unknown.exists() and result['reclaimed']==1 and result['state']=='PARTIAL'


def test_actual_worker_cycle_uses_fixed_entry_no_host_secrets(tmp_path,monkeypatch):
    root=tmp_path/'connections';store=SourceStore(root,clock=lambda:datetime.now(timezone.utc)-timedelta(hours=25))
    receipt=store.upload(AUTH,'isolated.csv',b'id,created_on\n1,2025-01-01\n')
    monkeypatch.setenv('WORKSPACE_CONNECTOR_SECRET_TEST','unit-not-real-secret');monkeypatch.setenv('PGPASSWORD','unit-not-real-secret')
    value=run_worker('retention_cycle',{'root':str(root)},limits=WorkerLimits(wall_seconds=15))
    assert value['ok'] and value['data']['reclaimed']==1 and not (root/'uploads'/receipt.file_id).exists()
    assert run_worker('retention_cycle',{'root':str(root),'command':'powershell'})['ok'] is False
    assert run_worker('retention_cycle',{'root':'relative-root'})['ok'] is False


def test_real_runner_periodic_lifespan_no_overlap_or_catchup_and_stop(tmp_path):
    async def scenario():
        store=SourceStore(tmp_path/'connections',clock=lambda:datetime.now(timezone.utc)-timedelta(hours=25))
        receipt=store.upload(AUTH,'temp.csv',b'id\n1\n');store.clock=lambda:datetime.now(timezone.utc)
        runner=RetentionRunner(store,interval=.1,start_delay=0);store.retention_runner=runner
        await runner.start()
        deadline=time.monotonic()+8
        while (runner.last is None or runner.last['state'] not in {'SUCCEEDED','PARTIAL'}) and time.monotonic()<deadline:await asyncio.sleep(.01)
        assert runner.last['state']=='SUCCEEDED' and not (store.root/'uploads'/receipt.file_id).exists()
        assert runner.snapshot()['enabled'] and read_cycle(store.root)['state']=='SUCCEEDED'
        await runner.stop()
        assert runner.task.done() and not runner.enabled and not runner.running
        assert read_cycle(store.root)['state'] in {'SUCCEEDED','STOPPED'}
    asyncio.run(scenario())


def test_runner_busy_skips_then_later_cycle_revalidates_without_overlap(store):
    async def scenario():
        folder=artifact(store);runner=RetentionRunner(store,interval=3600,start_delay=600)
        await runner.start()
        try:
            with storage_lease(store.root):await runner.tick()
            assert runner.last['state']=='SKIPPED_BUSY' and folder.exists()
            await runner.tick()
            assert runner.last['state']=='SUCCEEDED' and not folder.exists()
        finally:await runner.stop()
    asyncio.run(scenario())


def test_two_application_runners_have_one_native_leader_then_release(store):
    async def scenario():
        first=RetentionRunner(store,start_delay=600);await first.start()
        second=RetentionRunner(SourceStore(store.root),start_delay=600);await second.start()
        assert first.enabled and not second.enabled and second.last['state']=='SKIPPED_BUSY'
        await first.stop();await second.stop()
        third=RetentionRunner(store,start_delay=600);await third.start();assert third.enabled;await third.stop()
    asyncio.run(scenario())


def test_stop_actual_owned_job_cancels_and_releases_worker_slot(store,monkeypatch):
    from test_worker_runtime import PROBE,alive
    marker=store.root/'owned-worker.pid';store.root.mkdir(parents=True)
    def blocked(operation,payload,*,limits,cancel_event):
        return _run_entry('test_probe',{'mode':'timeout','pid_file':str(marker)},limits,entry=PROBE,cancel_event=cancel_event)
    monkeypatch.setattr('data_workspace.retention_runner.run_worker',blocked)
    async def scenario():
        runner=RetentionRunner(store,start_delay=0);await runner.start()
        try:
            deadline=time.monotonic()+5;raw=''
            # File creation precedes write completion. Wait for the actual owned PID, not only existence.
            while time.monotonic()<deadline:
                try:raw=marker.read_text().strip()
                except (FileNotFoundError,PermissionError):raw=''
                if raw:break
                await asyncio.sleep(.01)
            assert raw.isdigit();pid=int(raw);assert pid>0 and alive(pid)
            before=time.monotonic();await runner.stop()
            assert time.monotonic()-before<6 and runner.last['state']=='STOPPED'
            assert not alive(pid) and read_cycle(store.root)['state']=='STOPPED'
            acquired=[]
            try:
                for _ in range(2):acquired.append(SLOTS.acquire(blocking=False))
                assert all(acquired)
            finally:
                for value in acquired:
                    if value:SLOTS.release()
        finally:
            await runner.stop()
    asyncio.run(scenario())


def test_runner_corrupt_or_unpersistable_receipt_refuses_execution(store,monkeypatch):
    store.root.mkdir(parents=True);file=store.root/'cleanup-cycle.json';file.write_bytes(b'broken receipt')
    called=[]
    def forbidden(*args,**kwargs):called.append(True);raise AssertionError('must not execute')
    monkeypatch.setattr('data_workspace.retention_runner.run_worker',forbidden)
    async def scenario():
        runner=RetentionRunner(store,start_delay=600);await runner.start()
        try:await runner.tick();assert runner.last['state']=='FAILED'
        finally:await runner.stop()
    asyncio.run(scenario())
    assert not called and file.read_bytes()==b'broken receipt'


def test_restart_reports_interrupted_receipt_and_only_resumes_same_native_object(store,monkeypatch):
    from data_workspace.retention_executor import cleanup_one
    folder=artifact(store)
    def crash(stage):
        if stage=='file_deleted':raise OSError('isolated partial deletion')
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention_executor.observe',crash)
        with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    saved=RetentionRunner(store).record('RUNNING');save_cycle(store.root,saved)
    async def scenario():
        restarted=SourceStore(store.root,clock=lambda:datetime.now(timezone.utc));runner=RetentionRunner(restarted,start_delay=600)
        await runner.start();assert runner.last['state']=='INTERRUPTED'
        try:
            await runner.tick();assert runner.last['state']=='SUCCEEDED' and not folder.exists()
        finally:await runner.stop()
    asyncio.run(scenario())


def test_disabled_default_production_guard_and_readonly_status_endpoint(store):
    assert not Settings().retention_cleanup
    with pytest.raises(ValueError):Settings(retention_cleanup=True)
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        value=client.get('/api/v1/source-profiles/retention');assert value.status_code==200
        assert value.json()['automatic_cleanup'] is False and value.json()['cycle_state']=='NOT_RUN'
        assert client.post('/api/v1/source-profiles/retention',headers={'X-Workspace-Request':'1'}).status_code==405
        assert client.post('/api/v1/source-profiles/storage/cleanup',headers={'X-Workspace-Request':'1'}).status_code==404
    assert not store.root.exists()


def test_real_app_lifespan_starts_and_joins_retention_runner(store):
    app=create_app(Settings(mode='development',dev_identity=True,retention_cleanup=True));app.state.sources=store
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        runner=store.retention_runner;assert runner.enabled and runner.task is not None
        value=client.get('/api/v1/source-profiles/retention').json()
        assert value['automatic_cleanup'] and value['interval_seconds']==600 and value['next_run_at']
    assert runner.task.done() and not runner.enabled

def test_cancel_mid_delete_then_real_new_worker_finishes_verified_remaining_objects(store,monkeypatch):
    signal=store.root/'paused-cycle.pid';folder=artifact(store)
    probe=Path(__file__).with_name('retention_cycle_probe.py')
    def pause(operation,payload,*,limits,cancel_event):
        return _run_entry(operation,{'root':payload['root'],'signal':str(signal)},limits,entry=probe,cancel_event=cancel_event)
    async def scenario():
        with monkeypatch.context() as patch:
            patch.setattr('data_workspace.retention_runner.run_worker',pause)
            runner=RetentionRunner(store,start_delay=0);await runner.start()
            deadline=time.monotonic()+5
            while not signal.exists() and time.monotonic()<deadline:await asyncio.sleep(.01)
            try:
                assert signal.exists()
                assert folder.exists() and (store.root/'cleanup-journal'/(folder.name+'.json')).is_file()
            finally:await runner.stop()
            assert runner.last['state']=='STOPPED'
        restarted=RetentionRunner(SourceStore(store.root),start_delay=600)
        await restarted.start()
        try:
            await restarted.tick()
            assert restarted.last['state']=='SUCCEEDED' and not folder.exists()
        finally:await restarted.stop()
    asyncio.run(scenario())


def test_runner_completion_not_published_until_receipt_written(store,monkeypatch):
    from data_workspace.retention_runner import save_cycle as actual_save
    entered=Event();release=Event()
    def hold(root,value):
        if value['state']=='SUCCEEDED':entered.set();assert release.wait(4)
        return actual_save(root,value)
    monkeypatch.setattr('data_workspace.retention_runner.save_cycle',hold)
    async def scenario():
        runner=RetentionRunner(store,start_delay=600);await runner.start()
        task=asyncio.create_task(runner.tick())
        try:
            deadline=time.monotonic()+5
            while not entered.is_set() and time.monotonic()<deadline:await asyncio.sleep(.01)
            assert entered.is_set() and runner.last['state']=='RUNNING'
            assert read_cycle(store.root)['state']=='RUNNING'
        finally:release.set();await task;await runner.stop()
        assert runner.last['state']=='SUCCEEDED' and read_cycle(store.root)['state']=='SUCCEEDED'
    asyncio.run(scenario())


def test_retention_flag_not_forwarded_to_frontend_or_worker(monkeypatch):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
    from dev import frontend_environment,backend_environment
    values={'WORKSPACE_RETENTION_CLEANUP':'1','WORKSPACE_CONNECTOR_SECRET_SENTINEL':'not-real'}
    assert backend_environment(values)['WORKSPACE_RETENTION_CLEANUP']=='1'
    assert 'WORKSPACE_RETENTION_CLEANUP' not in frontend_environment(values)
    monkeypatch.setenv('WORKSPACE_RETENTION_CLEANUP','1')
    from data_workspace.worker_runtime import worker_environment
    assert 'WORKSPACE_RETENTION_CLEANUP' not in worker_environment()

def test_reference_metadata_budget_includes_rechecks_and_never_reclaims_on_overrun(store):
    snapshot=artifact(store,'snapshots')
    manifest=snapshot/'source.manifest.json'
    manifest.write_text(json.dumps({'version':snapshot.name,'upload_file_id':None,'padding':'x'*60000}))
    with store.db() as db:
        for _ in range(48):
            db.execute('INSERT INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES (?,?,?,?,?,?,?,?)',
                       [str(uuid4()),store.owner(AUTH),'metadata budget',1,0,str(snapshot/'source.duckdb'),'fixture',NOW.isoformat()])
    disposable=artifact(store)
    result=execute_cycle(store,AUTH)
    assert result['state']=='PARTIAL' and result['error_code']=='STORAGE_SCAN_INCOMPLETE'
    assert result['reclaimed']==0 and disposable.exists() and snapshot.exists()


def test_invalid_retention_flag_and_nonloopback_enablement_denied(monkeypatch):
    monkeypatch.setenv('WORKSPACE_RETENTION_CLEANUP','yes')
    with pytest.raises(ValueError):Settings.from_env()
    with pytest.raises(ValueError):Settings(mode='development',dev_identity=False,retention_cleanup=True)
    with pytest.raises(ValueError):Settings(mode='development',dev_identity=True,host='0.0.0.0',retention_cleanup=True)

def test_repeated_reference_reads_close_sqlite_without_relying_on_garbage_collection(store):
    import gc
    from data_workspace.retention import retention_references
    from data_workspace.retention_native import PinnedObject
    snapshot=artifact(store,'snapshots')
    with store.db() as db:
        db.execute('INSERT INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES (?,?,?,?,?,?,?,?)',
                   [str(uuid4()),store.owner(AUTH),'read-close',1,0,str(snapshot/'source.duckdb'),'fixture',NOW.isoformat()])
    enabled=gc.isenabled();gc.disable()
    try:
        for _ in range(20):assert snapshot.name in retention_references(store)[0]
        # Open no-delete-share native handle requiring DELETE access: a leaked SQLite
        # reader would deny this immediately. Do not actually dispose/delete the DB.
        with PinnedObject(store.root,store.root/'profiles.sqlite3',delete=True) as pinned:
            assert pinned.size>0
    finally:
        if enabled:gc.enable()
