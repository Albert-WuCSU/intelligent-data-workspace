"""Real isolated preflight plus explicitly read-only storage planning tests."""
import asyncio
import hashlib,json,os,sqlite3,time
from pathlib import Path
from threading import Event,Thread
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.contracts import AuthContext
from data_workspace.main import create_app
from data_workspace.source_profiles import SourceStore,ProfileDraft,SaveProfile,ToggleProfile
from data_workspace.storage_inventory import storage_summary
from data_workspace.upload_preflight import inspect_upload
from data_workspace.worker_runtime import WorkerFailure,run_worker
from xlsx_fixture import workbook_bytes

AUTH=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
HEADERS={'X-Workspace-Request':'1'}

@pytest.fixture
def store(tmp_path):return SourceStore(tmp_path/'connections',tmp_path/'allowed')

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def test_actual_preflight_runs_in_worker_not_api_and_promotes_only_valid_upload(store,monkeypatch):
    # If the API tried XML validation, this monkeypatch would fail it; actual child
    # imports its own parser after the Job gate and checks the real package.
    def no_api_parser(content):raise AssertionError('XML parser ran in API')
    monkeypatch.setattr('data_workspace.excel_import.validate_package',no_api_parser)
    receipt=store.upload(AUTH,'中文原件.xlsx',workbook_bytes())
    target=store.root/'uploads'/receipt.file_id
    assert (target/'source.xlsx').exists() and not (store.root/'staging'/receipt.file_id).exists()
    record=json.loads((target/'upload.receipt.json').read_text())
    assert record['owner']==store.owner(AUTH) and record['size_bytes']==len(workbook_bytes())
    assert record['sha256']==hashlib.sha256((target/'source.xlsx').read_bytes()).hexdigest()
    assert '中文原件' not in str(record)
    assert not store.uploads_in_flight

@pytest.mark.parametrize('name,content,code',[('bad.xlsx',b'not-a-package','INVALID_XLSX'),('external.xlsx',workbook_bytes(external=True),'INVALID_XLSX'),('text.csv',b'\xff','INVALID_FILE'),('fake.parquet',b'wrong','INVALID_FILE'),('fake.duckdb',b'wrong','INVALID_FILE')])
def test_failed_preflight_removes_only_this_new_staging_and_keeps_previous_upload(store,name,content,code):
    previous=store.upload(AUTH,'valid.csv',b'code,created_on\na,2025-01-01\n')
    before=hashes(store.root/'uploads')
    with pytest.raises(PublicError) as caught:store.upload(AUTH,name,content)
    assert caught.value.code==code
    assert hashes(store.root/'uploads')==before and (store.root/'uploads'/previous.file_id).exists()
    assert list((store.root/'staging').iterdir())==[] and not store.uploads_in_flight

@pytest.mark.parametrize('code',['WORKER_TIMEOUT','WORKER_ISOLATION_UNAVAILABLE','WORKER_BUSY'])
def test_preflight_fault_no_receipt_no_fallback_and_slot_retry(store,monkeypatch,code):
    called=[]
    def fail(operation,payload,**kwargs):
        called.append(operation)
        assert (store.root/'staging'/payload['upload_id']/'source.csv').is_file()
        assert kwargs['limits'].wall_seconds==10
        raise WorkerFailure(code)
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.worker_runtime.run_worker',fail)
        with pytest.raises(PublicError) as caught:store.upload(AUTH,'valid.csv',b'id\n1\n')
        assert caught.value.code==code and called==['upload_preflight']
    assert list((store.root/'staging').iterdir())==[] and not store.uploads_in_flight
    assert store.upload(AUTH,'retry.csv',b'id\n1\n').file_id


def test_invalid_digest_and_runtime_link_fail_before_parsing(store,tmp_path):
    id=str(uuid4());folder=store.root/'staging'/id;folder.mkdir(parents=True);(folder/'source.xlsx').write_bytes(b'invalid')
    with pytest.raises(ValueError):inspect_upload({'root':str(store.root),'upload_id':id,'suffix':'.xlsx','sha256':'0'*64})
    # Link status is simulated in this unit test; not native symlink evidence.
    # The path checker must reject before opening or parsing any file.
    with pytest.MonkeyPatch.context() as patch:
        original=Path.is_symlink
        patch.setattr(Path,'is_symlink',lambda p:p==folder or original(p))
        with pytest.raises(ValueError):inspect_upload({'root':str(store.root),'upload_id':id,'suffix':'.xlsx','sha256':hashlib.sha256(b'invalid').hexdigest()})


def test_http_health_responsive_during_upload_preflight_offloaded_from_event_loop(store,monkeypatch):
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    entered=Event();release=Event();result=[];original=store.upload
    def wait(*args):entered.set();assert release.wait(4);return original(*args)
    monkeypatch.setattr(store,'upload',wait)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        thread=Thread(target=lambda:result.append(client.post('/api/v1/source-profiles/upload',files={'file':('safe.csv',b'id\n1\n')},headers=HEADERS)))
        thread.start()
        try:
            assert entered.wait(3)
            start=time.monotonic();assert client.get('/health/live').status_code==200
            assert time.monotonic()-start<2
        finally:release.set();thread.join(5)
        assert not thread.is_alive() and result[0].status_code==200


def test_storage_read_only_protects_saved_disabled_and_live_drafts_not_delete_candidates(store):
    upload=store.upload(AUTH,'safe.csv',b'id,created_on\n1,2025-01-01\n')
    tested=asyncio.run(store.test(AUTH,ProfileDraft(name='saved',file_id=upload.file_id,usage_authorized=True)))
    profile=store.save(AUTH,SaveProfile(test_id=tested.test_id));store.toggle(AUTH,profile.id,ToggleProfile(enabled=False,expected_version=1))
    second=store.upload(AUTH,'unsaved.csv',b'id\n2\n')
    draft=asyncio.run(store.test(AUTH,ProfileDraft(name='draft',file_id=second.file_id,usage_authorized=True)))
    before=hashes(store.root)
    value=storage_summary(store,AUTH)
    assert value.scan_state=='COMPLETE' and value.automatic_cleanup is False
    assert value.saved_profiles==1 and value.unsaved_tests==1
    assert value.snapshots.referenced_folders==2 and value.uploads.referenced_folders==2
    assert hashes(store.root)==before and 'safe.csv' not in value.model_dump_json()
    store.tests.clear()
    after=storage_summary(store,AUTH)
    assert after.snapshots.referenced_folders==1 and after.snapshots.review_only_folders==1
    assert after.uploads.referenced_folders==1 and after.uploads.review_only_folders==1
    assert hashes(store.root)==before  # inventory is NOT a TTL sweep


def test_legacy_upload_is_unknown_and_inventory_does_not_initialize_database(store):
    folder=store.root/'uploads'/str(uuid4());folder.mkdir(parents=True);(folder/'source.csv').write_bytes(b'id\n1\n')
    before=hashes(store.root);value=storage_summary(store,AUTH)
    assert value.uploads.unknown_folders==1 and value.uploads.review_only_folders==0
    assert not (store.root/'profiles.sqlite3').exists() and hashes(store.root)==before


def test_storage_scan_busy_and_denied_fail_before_mutation(store):
    store.uploads_in_flight.add('operation')
    with pytest.raises(PublicError) as caught:storage_summary(store,AUTH)
    assert caught.value.code=='STORAGE_BUSY'
    store.uploads_in_flight.clear();store.active=True
    with pytest.raises(PublicError):storage_summary(store,AUTH)
    with pytest.raises(PublicError) as caught:storage_summary(store,AuthContext(mode='development',principal_id='other',tenant_id='local-workspace'))
    assert caught.value.code=='CONNECTOR_DENIED' and not store.root.exists()


def test_storage_scan_bounded_and_unexpected_nested_objects_are_unknown(store,monkeypatch):
    parent=store.root/'uploads';parent.mkdir(parents=True)
    folder=parent/str(uuid4());folder.mkdir();(folder/'nested').mkdir()
    monkeypatch.setattr('data_workspace.storage_inventory.LIMIT',1)
    other=parent/str(uuid4());other.mkdir();(other/'source.csv').write_bytes(b'abc')
    before=hashes(store.root);value=storage_summary(store,AUTH)
    assert value.scan_state=='PARTIAL' and value.uploads.folders==1 and value.automatic_cleanup is False
    assert hashes(store.root)==before


def test_preflight_receipt_mismatch_fails_closed_and_cleans_own_staging(store,monkeypatch):
    def wrong(*args,**kwargs):return {'ok':True,'data':{'size_bytes':99,'sha256':'0'*64,'suffix':'.csv'}}
    monkeypatch.setattr('data_workspace.worker_runtime.run_worker',wrong)
    with pytest.raises(PublicError) as caught:store.upload(AUTH,'safe.csv',b'id\n1\n')
    assert caught.value.code=='UPLOAD_PREFLIGHT_INVALID'
    assert list((store.root/'staging').iterdir())==[] and not store.uploads_in_flight


def test_upload_admission_rejects_before_any_body_read_and_failure_releases_slot(store):
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        app.state.upload_admission.acquire();app.state.upload_admission.acquire()
        try:
            response=client.post('/api/v1/source-profiles/upload',content=b'',headers={**HEADERS,'Content-Length':str(30*1024*1024)})
            assert response.status_code==429 and response.json()['code']=='UPLOAD_BUSY' and not store.root.exists()
            assert client.get('/health/live').status_code==200
        finally:app.state.upload_admission.release();app.state.upload_admission.release()
        invalid=client.post('/api/v1/source-profiles/upload',files={'file':('bad.xlsx',b'not-xlsx')},headers=HEADERS)
        assert invalid.status_code==422
        assert app.state.upload_admission.acquire(blocking=False) and app.state.upload_admission.acquire(blocking=False)
        app.state.upload_admission.release();app.state.upload_admission.release()


def test_storage_api_returns_only_nonsecret_readonly_summary_and_rejects_other_identity(store):
    app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
    store.upload(AUTH,'never-expose-filename.csv',b'id\n1\n');before=hashes(store.root)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        response=client.get('/api/v1/source-profiles/storage')
        assert response.status_code==200 and response.json()['automatic_cleanup'] is False
        assert 'never-expose' not in response.text and str(store.root) not in response.text
        assert hashes(store.root)==before and response.headers['cache-control']=='no-store'
        class Other:
            def resolve(self,request):return AuthContext(mode='development',principal_id='other',tenant_id='local-workspace')
        app.state.identity_provider=Other()
        assert client.get('/api/v1/source-profiles/storage').status_code==403 and hashes(store.root)==before
