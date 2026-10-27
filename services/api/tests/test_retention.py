"""Retention foundation: actual Windows leases + isolated provenance/clock faults.

No TTL deletion runs, no project runtime artifacts are removed by these tests.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.contracts import AuthContext
from data_workspace.main import create_app
from data_workspace.source_profiles import SourceStore, ProfileDraft, SaveProfile, ToggleProfile
from data_workspace.retention import (MARKER, TTL, storage_lease, write_marker, retention_preview,
                                      write_test_reference)

AUTH = AuthContext(mode='development', tenant_id='local-workspace', principal_id='local-developer')
NOW = datetime(2026, 10, 27, 6, 0, tzinfo=timezone.utc)

@pytest.fixture
def store(tmp_path):
    return SourceStore(tmp_path/'connections', tmp_path/'allowed', clock=lambda: NOW)


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def artifact(store, area='uploads', age=TTL+timedelta(seconds=1), upload_id=None):
    id=str(uuid4()); kind='snapshot' if area=='snapshots' else 'upload'
    folder=store.root/('snapshots' if kind=='snapshot' else 'staging')/id
    folder.mkdir(parents=True)
    if kind=='snapshot':
        (folder/'source.duckdb').write_bytes(b'isolated unit fixture, not a query result')
        (folder/'source.manifest.json').write_text(json.dumps({'version':id,'upload_file_id':upload_id}))
    else:
        (folder/'source.csv').write_bytes(b'id,created_at\n1,2025-01-01\n')
        (folder/'upload.receipt.json').write_text(json.dumps({'schema_version':'1.0','owner':store.owner(AUTH)}))
    write_marker(store.root,folder,kind=kind,owner=store.owner(AUTH),created_at=(NOW-age).isoformat(),upload_id=upload_id,complete=True)
    if area=='uploads':
        dest=store.root/area/id;dest.parent.mkdir(exist_ok=True);folder.rename(dest);folder=dest
    return folder


def test_strict_24h_boundary_and_no_file_deletion_or_mtime_guess(store):
    at=artifact(store,age=TTL);old=artifact(store);fresh=artifact(store,age=timedelta(hours=1))
    with storage_lease(store.root): pass
    before=hashes(store.root)
    value=retention_preview(store,AUTH)
    assert value['areas']['uploads']=={'eligible':1,'fresh':2,'protected':0,'unknown':0}
    assert value['execution']=='not_run' and value['automatic_cleanup'] is False
    assert hashes(store.root)==before and all(p.exists() for p in (at,old,fresh))
    os.utime(fresh,(0,0))
    assert retention_preview(store,AUTH)['areas']['uploads']['fresh']==2


@pytest.mark.parametrize('fault',['missing','owner','root','time','naive','incomplete','changed','extra','nested','link'])
def test_unknown_corrupt_foreign_and_linked_artifacts_protected(store,monkeypatch,fault):
    folder=artifact(store);path=folder/MARKER;record=json.loads(path.read_text())
    if fault=='missing': path.rename(folder/'legacy.receipt.json')
    elif fault=='changed': (folder/'source.csv').write_bytes(b'changed')
    elif fault=='extra': (folder/'secret.txt').write_bytes(b'unit-sentinel')
    elif fault=='nested': (folder/'nested').mkdir()
    elif fault=='link':
        original=Path.is_symlink
        monkeypatch.setattr(Path,'is_symlink',lambda p:p==folder/'source.csv' or original(p))
    else:
        field,value={'owner':('owner','unknown'), 'root':('root_key','0'*64),
                     'time':('created_at',(NOW+TTL).isoformat()), 'naive':('created_at','2026-10-25T00:00:00'),
                     'incomplete':('complete',False)}[fault]
        record[field]=value;path.write_text(json.dumps(record))
    value=retention_preview(store,AUTH)['areas']['uploads']
    assert value['unknown']==1 and value['eligible']==0 and folder.exists()


def test_saved_disabled_and_restart_protect_snapshot_and_original_upload(store):
    upload=artifact(store);snapshot=artifact(store,'snapshots',upload_id=upload.name)
    with store.db() as db:
        db.execute('INSERT INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES (?,?,?,?,?,?,?,?)',
                   [str(uuid4()),store.owner(AUTH),'saved',2,0,str(snapshot/'source.duckdb'),'local',NOW.isoformat()])
    restarted=SourceStore(store.root,store.allowed_root,clock=lambda:NOW+timedelta(days=100))
    value=retention_preview(restarted,AUTH)
    assert value['areas']['uploads']['protected']==1 and value['areas']['snapshots']['protected']==1
    assert upload.exists() and snapshot.exists()


def test_durable_test_reference_survives_restart_but_draft_not_resumed(store):
    upload=artifact(store);snapshot=artifact(store,'snapshots',upload_id=upload.name)
    id=str(uuid4())
    write_test_reference(store.root,id,owner=store.owner(AUTH),at=NOW.isoformat(),snapshot_id=snapshot.name,upload_id=upload.name)
    restarted=SourceStore(store.root,store.allowed_root,clock=lambda:NOW+timedelta(hours=1))
    value=retention_preview(restarted,AUTH)
    assert value['areas']['uploads']['protected']==1 and value['areas']['snapshots']['protected']==1
    with pytest.raises(PublicError) as caught: restarted.save(AUTH,SaveProfile(test_id=id))
    assert caught.value.code=='TEST_EXPIRED' and not restarted.tests
    restarted.clock=lambda:NOW+TTL
    assert retention_preview(restarted,AUTH)['areas']['uploads']['eligible']==1


def test_corrupt_durable_reference_fails_closed_not_ignored(store):
    artifact(store)
    refs=store.root/'test-references';refs.mkdir();(refs/(str(uuid4())+'.json')).write_text('{}')
    with pytest.raises(PublicError) as caught:retention_preview(store,AUTH)
    assert caught.value.code=='STORAGE_REFERENCES_INVALID'


def test_save_exact_expiry_rejected_without_database_or_disk_mutation(store):
    id=str(uuid4());store.tests[id]={'owner':store.owner(AUTH),'at':(NOW-TTL).isoformat(),'draft':ProfileDraft(name='expired',path='data/unit.csv',usage_authorized=True)}
    with pytest.raises(PublicError) as caught:store.save(AUTH,SaveProfile(test_id=id))
    assert caught.value.code=='TEST_EXPIRED' and not store.tests and not (store.root/'profiles.sqlite3').exists()


def test_expired_50_slots_released_before_new_test_and_reference_write_fault(store,monkeypatch):
    from data_workspace.remote_access import HTTPMCPDraft
    draft=HTTPMCPDraft(kind='http_mcp',name='unit remote',url='http://127.0.0.1:9000/mcp',auth_mode='none',usage_authorized=True)
    for _ in range(50):store.tests[str(uuid4())]={'at':(NOW-TTL).isoformat(),'owner':store.owner(AUTH)}
    async def metadata(*args):return {'tables':[]}
    monkeypatch.setattr('data_workspace.remote_sources.remote_navigation',metadata)
    result=asyncio.run(store.test(AUTH,draft))
    assert len(store.tests)==1 and result.test_id in store.tests
    def failed(*args,**kwargs):raise OSError('isolated receipt disk fault')
    monkeypatch.setattr('data_workspace.source_profiles.write_test_reference',failed)
    with pytest.raises(PublicError) as caught:asyncio.run(store.test(AUTH,draft))
    assert caught.value.code=='TEST_REFERENCE_FAILED' and len(store.tests)==1 and not store.active
    with storage_lease(store.root):pass


def test_actual_crossprocess_lock_refuses_racing_operations_then_crash_releases(store):
    code='''import os,sys
from pathlib import Path
from data_workspace.retention import storage_lease
with storage_lease(Path(sys.argv[1])):
 print("locked",flush=True)
 sys.stdin.readline()
 os._exit(17)
'''
    child=subprocess.Popen([sys.executable,'-c',code,str(store.root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='locked'
        second=SourceStore(store.root,store.allowed_root)
        for action in (lambda:retention_preview(second,AUTH),lambda:second.upload(AUTH,'x.csv',b'id\n1\n'),
                       lambda:second.save(AUTH,SaveProfile(test_id=str(uuid4()))),
                       lambda:asyncio.run(second.test(AUTH,ProfileDraft(name='x',path='data/x.csv',usage_authorized=True)))):
            with pytest.raises(PublicError) as caught:action()
            assert caught.value.code=='STORAGE_BUSY'
        child.stdin.write('crash\n');child.stdin.flush();assert child.wait(timeout=5)==17
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=5)
        for stream in (child.stdin,child.stdout,child.stderr):stream.close()
    with storage_lease(store.root):pass
    assert not list((store.root/'staging').glob('*'))


def test_lease_unavailable_denies_before_upload_and_can_retry(store,monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention.os.name','unverified')
        with pytest.raises(PublicError) as caught:store.upload(AUTH,'unit.csv',b'id\n1\n')
        assert caught.value.code=='STORAGE_LOCK_UNAVAILABLE' and not store.root.exists()
    assert store.upload(AUTH,'unit.csv',b'id,created_on\n1,2025-01-01\n').file_id


def test_http_expired_save_clear_error_and_no_execution_endpoint(store):
    id=str(uuid4());store.tests[id]={'owner':store.owner(AUTH),'at':(NOW-TTL).isoformat()}
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        response=client.post('/api/v1/source-profiles/save',json={'test_id':id},headers={'X-Workspace-Request':'1'})
        assert response.status_code==409 and response.json()['code']=='TEST_EXPIRED'
        assert '重新测试' in response.json()['safe_message']
        assert client.post('/api/v1/source-profiles/storage/cleanup',headers={'X-Workspace-Request':'1'}).status_code==404
        assert client.get('/api/v1/source-profiles/storage').json()['automatic_cleanup'] is False


def test_scan_budget_and_bad_database_fail_closed(store,monkeypatch):
    artifact(store)
    monkeypatch.setattr('data_workspace.retention.MAX_HASH_BYTES',1)
    with pytest.raises(PublicError) as caught:retention_preview(store,AUTH)
    assert caught.value.code=='STORAGE_SCAN_INCOMPLETE'
    (store.root/'profiles.sqlite3').write_bytes(b'invalid isolated database')
    with pytest.raises(PublicError) as caught:retention_preview(store,AUTH)
    assert caught.value.code=='STORAGE_REFERENCES_INVALID'


def test_actual_hardlinked_artifact_is_never_eligible(store,tmp_path):
    folder=artifact(store)
    os.link(folder/'source.csv',tmp_path/'external-unit-copy.csv')
    value=retention_preview(store,AUTH)
    assert value['areas']['uploads']['unknown']==1 and value['areas']['uploads']['eligible']==0


def test_async_request_lease_held_until_completion_and_exception(store,monkeypatch):
    from threading import Thread,Event
    from data_workspace.remote_access import HTTPMCPDraft
    entered=Event();released=Event();errors=[]
    async def paused(*args):
        entered.set()
        while not released.is_set():await asyncio.sleep(.01)
        raise PublicError(422,'UNIT_FAULT','isolated failure')
    monkeypatch.setattr('data_workspace.remote_sources.remote_navigation',paused)
    draft=HTTPMCPDraft(kind='http_mcp',name='unit',url='http://127.0.0.1:9000/mcp',auth_mode='none',usage_authorized=True)
    def run():
        try:asyncio.run(store.test(AUTH,draft))
        except PublicError as error:errors.append(error.code)
    thread=Thread(target=run);thread.start()
    try:
        assert entered.wait(3)
        with pytest.raises(PublicError) as caught:retention_preview(SourceStore(store.root),AUTH)
        assert caught.value.code=='STORAGE_BUSY'
    finally:released.set();thread.join(5)
    assert not thread.is_alive() and errors==['UNIT_FAULT'] and not store.active
    with storage_lease(store.root):pass


def test_marker_write_failure_never_promotes_upload_preserves_original(store,monkeypatch):
    content=b'id,created_at\n1,2025-01-01\n'
    def fail(*args,**kwargs):raise OSError('isolated fsync fault')
    monkeypatch.setattr('data_workspace.retention.os.fsync',fail)
    with pytest.raises(PublicError) as caught:store.upload(AUTH,'original.csv',content)
    assert caught.value.code=='UPLOAD_FAILED'
    assert not (store.root/'uploads').exists() and not list((store.root/'staging').iterdir())
    assert not store.uploads_in_flight and content==b'id,created_at\n1,2025-01-01\n'
    with storage_lease(store.root):pass


def test_only_known_children_with_bounded_iteration_are_eligible(store):
    folder=artifact(store)
    for i in range(20):(folder/('extra'+str(i))).write_bytes(b'unit fixture')
    assert retention_preview(store,AUTH)['areas']['uploads']['unknown']==1
