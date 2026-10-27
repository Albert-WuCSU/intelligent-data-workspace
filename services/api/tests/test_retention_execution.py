"""Real native deletion ONLY of isolated newly-created UUID test artifacts.

Never run a sweep of project/default runtime storage. Crash fixtures terminate
only their own subprocess. Fault seams are not exposed by the product API.
"""
import asyncio
import json
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
from uuid import uuid4
from datetime import timedelta
import pytest
from data_workspace.auth import PublicError
from data_workspace.source_profiles import SourceStore,SaveProfile,ProfileDraft
from data_workspace.retention import (MARKER,TTL,write_marker,write_test_reference,storage_lease)
from data_workspace.retention_executor import cleanup_one,prune_expired_references
from data_workspace.retention_native import PinnedObject
from data_workspace.worker_runtime import worker_environment
from test_retention import AUTH,NOW,artifact,hashes,store


def test_actual_native_handle_deletes_only_marked_expired_copy_and_idempotent(store,tmp_path):
    outside=tmp_path/'original.csv';outside.write_bytes(b'original must remain')
    old=artifact(store);fresh=artifact(store,age=timedelta(hours=1))
    unknown=store.root/'uploads'/str(uuid4());unknown.mkdir();(unknown/'source.csv').write_bytes(b'unknown history')
    evidence=tmp_path/'project-control';evidence.mkdir();(evidence/'evidence.json').write_text('{}')
    before=outside.read_bytes();saved_evidence=hashes(evidence);other=hashes(fresh);legacy=hashes(unknown)
    result=cleanup_one(store,AUTH,'uploads',old.name)
    assert result=={'state':'DONE','deleted_files':3,'already_done':False}
    assert not old.exists() and outside.read_bytes()==before and hashes(evidence)==saved_evidence
    assert hashes(fresh)==other and hashes(unknown)==legacy
    assert cleanup_one(SourceStore(store.root,clock=lambda:NOW),AUTH,'uploads',old.name)['already_done'] is True


@pytest.mark.parametrize('kind',['staging','snapshots'])
def test_interrupted_new_marker_can_reclaim_only_known_unreferenced_children(store,kind):
    id=str(uuid4());folder=store.root/kind/id;folder.mkdir(parents=True)
    write_marker(store.root,folder,kind='snapshot' if kind=='snapshots' else 'upload',owner=store.owner(AUTH),created_at=(NOW-TTL-timedelta(seconds=1)).isoformat())
    (folder/('source.duckdb.wal' if kind=='snapshots' else 'source.csv')).write_bytes(b'partial isolated worker bytes')
    assert cleanup_one(store,AUTH,kind,id)['state']=='DONE' and not folder.exists()


@pytest.mark.parametrize('fault',['fresh','unknown','nested','hardlink','changed','future','wrong_root'])
def test_reclaim_refuses_unverifiable_legacy_or_changed_descendants(store,tmp_path,fault):
    folder=artifact(store,age=timedelta(hours=1) if fault=='fresh' else TTL+timedelta(hours=1))
    if fault=='unknown':(folder/MARKER).rename(folder/'legacy.json')
    if fault=='nested':(folder/'nested').mkdir()
    if fault=='hardlink':os.link(folder/'source.csv',tmp_path/'original-hardlink.csv')
    if fault=='changed':(folder/'source.csv').write_bytes(b'changed')
    if fault in {'future','wrong_root'}:
        path=folder/MARKER;value=json.loads(path.read_text())
        value['created_at' if fault=='future' else 'root_key']=(NOW+TTL).isoformat() if fault=='future' else '0'*64
        path.write_text(json.dumps(value))
    before=hashes(folder)
    with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,'uploads',folder.name)
    assert caught.value.code=='CLEANUP_STOPPED' and hashes(folder)==before


def test_saved_disabled_and_valid_durable_test_refs_block_execution(store):
    upload=artifact(store);snapshot=artifact(store,'snapshots',upload_id=upload.name)
    with store.db() as db:
        db.execute('INSERT INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES (?,?,?,?,?,?,?,?)',
                   [str(uuid4()),store.owner(AUTH),'saved',1,0,str(snapshot/'source.duckdb'),'local',NOW.isoformat()])
    for area,folder in [('uploads',upload),('snapshots',snapshot)]:
        with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,area,folder.name)
        assert caught.value.code=='STORAGE_REFERENCED' and folder.exists()
    other=artifact(store)
    write_test_reference(store.root,str(uuid4()),owner=store.owner(AUTH),at=NOW.isoformat(),snapshot_id=None,upload_id=other.name)
    with pytest.raises(PublicError) as caught:cleanup_one(SourceStore(store.root,clock=lambda:NOW),AUTH,'uploads',other.name)
    assert caught.value.code=='STORAGE_REFERENCED' and other.exists()


def test_revalidate_reference_after_plan_and_no_reuse_of_old_preview(store,monkeypatch):
    folder=artifact(store)
    def race(stage):
        if stage=='validated':write_test_reference(store.root,str(uuid4()),owner=store.owner(AUTH),at=NOW.isoformat(),snapshot_id=None,upload_id=folder.name)
    monkeypatch.setattr('data_workspace.retention_executor.observe',race)
    before=hashes(folder)
    with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,'uploads',folder.name)
    assert caught.value.code=='STORAGE_REFERENCED' and hashes(folder)==before


def test_native_handles_reject_write_replace_and_directory_race_before_delete(store,monkeypatch):
    folder=artifact(store);attempts=[]
    def race(stage):
        if stage=='validated':
            for operation in (lambda:(folder/'source.csv').write_bytes(b'other writer'),lambda:folder.rename(folder.with_name(str(uuid4())))):
                with pytest.raises(OSError):operation()
                attempts.append(True)
    monkeypatch.setattr('data_workspace.retention_executor.observe',race)
    assert cleanup_one(store,AUTH,'uploads',folder.name)['state']=='DONE' and attempts==[True,True]


@pytest.mark.parametrize('stage',['validated','deleting','file_deleted','directory_deleted'])
def test_actual_process_crash_then_restart_reconciles_same_ids_without_redelete(store,stage):
    folder=artifact(store)
    code='''import os,sys
from datetime import datetime
from pathlib import Path
from data_workspace.source_profiles import SourceStore
from data_workspace.contracts import AuthContext
import data_workspace.retention_executor as e
root,id,stage,now=sys.argv[1:]
def crash(point):
 if point==stage:os._exit(23)
e.observe=crash
s=SourceStore(Path(root),clock=lambda:datetime.fromisoformat(now))
e.cleanup_one(s,AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer'),'uploads',id)
'''
    child=subprocess.run([sys.executable,'-c',code,str(store.root),folder.name,stage,NOW.isoformat()],capture_output=True,timeout=15,env=worker_environment())
    assert child.returncode==23,child.stderr.decode(errors='replace')
    restarted=SourceStore(store.root,clock=lambda:NOW)
    assert cleanup_one(restarted,AUTH,'uploads',folder.name)['state']=='DONE'
    assert not folder.exists() and cleanup_one(restarted,AUTH,'uploads',folder.name)['already_done']


def test_partial_failure_then_changed_or_new_descendant_stops_before_further_delete(store,monkeypatch):
    folder=artifact(store)
    def fault(stage):
        if stage=='file_deleted':raise OSError('injected crash')
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention_executor.observe',fault)
        with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    assert folder.exists()
    (folder/'new-unknown.txt').write_bytes(b'protect unknown content')
    before=hashes(folder)
    with pytest.raises(PublicError):cleanup_one(SourceStore(store.root,clock=lambda:NOW),AUTH,'uploads',folder.name)
    assert hashes(folder)==before


def test_complete_uuid_recreated_never_reclaimed_with_old_done_receipt(store):
    folder=artifact(store);cleanup_one(store,AUTH,'uploads',folder.name)
    folder.mkdir();(folder/'original-new-file.csv').write_bytes(b'not the same object')
    with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    assert (folder/'original-new-file.csv').read_bytes()==b'not the same object'


def test_valid_atomic_journal_temp_is_reconciled_but_corrupt_temp_stops(store,monkeypatch):
    folder=artifact(store)
    original=Path.replace;interrupted=[]
    def fault(path,target):
        if path.suffix=='.tmp' and path.parent.name=='cleanup-journal' and not interrupted:
            interrupted.append(True);raise OSError('isolated atomic replace failure')
        return original(path,target)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'replace',fault)
        with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    assert hashes(folder)
    assert cleanup_one(SourceStore(store.root,clock=lambda:NOW),AUTH,'uploads',folder.name)['state']=='DONE'
    other=artifact(store);parent=store.root/'cleanup-journal';(parent/(other.name+'.tmp')).write_text('broken')
    before=hashes(other)
    with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',other.name)
    assert hashes(other)==before


def test_expired_reference_maintenance_preserves_active_invalid_future_and_unknown(store):
    id=str(uuid4())
    for at in [NOW-TTL-timedelta(seconds=1),NOW-TTL,NOW,NOW+TTL]:
        write_test_reference(store.root,str(uuid4()),owner=store.owner(AUTH),at=at.isoformat(),snapshot_id=None,upload_id=id)
    (store.root/'test-references'/'unknown.tmp').write_bytes(b'unknown')
    assert prune_expired_references(store,AUTH)=={'removed':1,'retained':2,'unknown':2}
    assert prune_expired_references(store,AUTH)=={'removed':0,'retained':2,'unknown':2}


def test_no_mutation_if_database_lock_or_active_operation_cannot_be_frozen(store):
    folder=artifact(store);before=hashes(folder)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,'uploads',folder.name)
        assert caught.value.code=='STORAGE_REFERENCES_BUSY'
    store.active=True
    with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,'uploads',folder.name)
    assert caught.value.code=='STORAGE_BUSY' and hashes(folder)==before


def test_permission_and_absolute_target_validation_before_native_mutation(store):
    folder=artifact(store);before=hashes(folder)
    for area,id in [('project-control',folder.name),('uploads','..'),('uploads',str(store.root))]:
        with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,area,id)
        assert caught.value.code=='CLEANUP_TARGET_INVALID'
    other=AUTH.model_copy(update={'principal_id':'other'})
    with pytest.raises(PublicError) as caught:cleanup_one(store,other,'uploads',folder.name)
    assert caught.value.code=='CONNECTOR_DENIED' and hashes(folder)==before

def test_retention_view_is_read_only_and_real_api_reports_actual_journal_counts(store):
    from fastapi.testclient import TestClient
    from data_workspace.main import create_app
    from data_workspace.config import Settings
    from data_workspace.storage_inventory import storage_summary
    folder=artifact(store);cleanup_one(store,AUTH,'uploads',folder.name)
    before=hashes(store.root)
    summary=storage_summary(store,AUTH)
    assert summary.retention.completed_cleanup_folders==1 and summary.retention.last_state=='DONE'
    assert summary.retention.automatic_cleanup is False and summary.retention.last_run_at==NOW.isoformat()
    assert hashes(store.root)==before
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        result=client.get('/api/v1/source-profiles/storage')
        assert result.status_code==200 and result.json()['retention']['completed_cleanup_folders']==1
        assert str(store.root) not in result.text and 'sha256' not in result.text
        assert client.post('/api/v1/source-profiles/storage/cleanup',headers={'X-Workspace-Request':'1'}).status_code==404
        assert client.post('/fixture-only/retention-example',headers={'X-Workspace-Request':'1'}).status_code==404
    assert hashes(store.root)==before


def test_retention_view_preserves_corrupt_receipt_and_shows_unverified_state(store):
    from data_workspace.retention_status import retention_status
    with storage_lease(store.root):pass
    parent=store.root/'cleanup-journal';parent.mkdir();(parent/(str(uuid4())+'.json')).write_text('{}')
    before=hashes(store.root);value=retention_status(store,AUTH)
    assert value.unverified_receipts==1 and value.last_state=='UNKNOWN'
    assert value.completed_cleanup_folders==0 and hashes(store.root)==before


def test_empty_retention_view_never_creates_database_or_lock(store):
    from data_workspace.retention_status import retention_status
    value=retention_status(store,AUTH)
    assert value.scan_state=='NOT_SCANNED' and value.last_state=='NOT_RUN' and not store.root.exists()


def test_partial_pending_directory_identity_replacement_is_not_deleted(store,monkeypatch):
    folder=artifact(store)
    def fault(stage):
        if stage=='deleting':raise OSError('isolated fault before first delete')
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.retention_executor.observe',fault)
        with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    moved=folder.with_name(str(uuid4()))
    assert folder.resolve().is_relative_to(store.root.resolve()) and moved.resolve().is_relative_to(store.root.resolve())
    folder.rename(moved)
    folder.mkdir();(folder/'new-original.csv').write_bytes(b'protect recreated UUID')
    before=hashes(folder);preserved=hashes(moved)
    with pytest.raises(PublicError):cleanup_one(store,AUTH,'uploads',folder.name)
    assert hashes(folder)==before and hashes(moved)==preserved

def test_standalone_status_import_has_no_main_app_import_order_dependency():
    command=[sys.executable,'-c','from data_workspace.retention_status import retention_status; print("ready")']
    result=subprocess.run(command,capture_output=True,text=True,timeout=10,env=worker_environment())
    assert result.returncode==0 and result.stdout.strip()=='ready',result.stderr


def test_native_database_identity_and_sqlite_writers_frozen_until_cleanup_finishes(store,monkeypatch):
    store.profiles(AUTH);folder=artifact(store);attempted=[]
    def race(stage):
        if stage=='validated':
            dbpath=store.root/'profiles.sqlite3'
            with pytest.raises(OSError):dbpath.rename(store.root/'profiles-replaced.sqlite3')
            with sqlite3.connect(dbpath,timeout=0) as writer:
                with pytest.raises(sqlite3.OperationalError):writer.execute('UPDATE profiles SET enabled=0')
            attempted.append(True)
    monkeypatch.setattr('data_workspace.retention_executor.observe',race)
    assert cleanup_one(store,AUTH,'uploads',folder.name)['state']=='DONE' and attempted==[True]
    assert (store.root/'profiles.sqlite3').is_file() and not (store.root/'profiles-replaced.sqlite3').exists()


def test_linked_target_classified_as_safe_stop_not_raw_exception(store,monkeypatch):
    folder=artifact(store);before=hashes(folder);original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda p:p==folder or original(p))
    with pytest.raises(PublicError) as caught:cleanup_one(store,AUTH,'uploads',folder.name)
    assert caught.value.code=='CLEANUP_STOPPED' and hashes(folder)==before

def test_real_test_receipt_expiration_is_server_derived_and_optional_legacy_schema(store,monkeypatch):
    from data_workspace.remote_access import HTTPMCPDraft
    from data_workspace.source_profiles import TestedDraft
    draft=HTTPMCPDraft(kind='http_mcp',name='expiry',url='http://127.0.0.1:9000/mcp',auth_mode='none',usage_authorized=True)
    async def metadata(*args):return {'tables':[]}
    monkeypatch.setattr('data_workspace.remote_sources.remote_navigation',metadata)
    result=asyncio.run(store.test(AUTH,draft))
    assert result.expires_at==(NOW+TTL).isoformat()
    legacy=result.model_dump();legacy.pop('expires_at')
    assert TestedDraft.model_validate(legacy).expires_at is None
