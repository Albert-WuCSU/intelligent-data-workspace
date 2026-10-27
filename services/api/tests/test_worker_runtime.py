"""Real Windows JobObject faults plus scoped service recovery tests."""
import asyncio
import os
from pathlib import Path
import time
from threading import Thread
import pytest
import win32api,win32con,win32process
from data_workspace.worker_runtime import _run_entry,run_worker,WorkerLimits,WorkerFailure,WindowsJob,SLOTS
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.contracts import AuthContext
from data_workspace.auth import PublicError

PROBE=Path(__file__).with_name('worker_probe.py')
AUTH=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')

def alive(pid):
    try:
        handle=win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
    except Exception:return False
    try:return win32process.GetExitCodeProcess(handle)==259
    finally:handle.Close()

def probe(mode,**kwargs):
    return _run_entry('test_probe',{'mode':mode,**kwargs},WorkerLimits(wall_seconds=2),entry=PROBE)

def test_job_declares_native_cpu_memory_process_and_kill_on_close_limits():
    import win32job
    limits=WorkerLimits();job=WindowsJob(limits)
    try:
        value=win32job.QueryInformationJobObject(job.handle,win32job.JobObjectExtendedLimitInformation)
        basic=value['BasicLimitInformation']
        assert value['ProcessMemoryLimit']==384*1024*1024 and value['JobMemoryLimit']==512*1024*1024
        assert basic['PerJobUserTimeLimit']==80000000 and basic['ActiveProcessLimit']==2
        assert basic['LimitFlags'] & win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        assert basic['LimitFlags'] & win32job.JOB_OBJECT_LIMIT_JOB_TIME
    finally:job.close()


def test_worker_success_and_no_host_secret_environment(monkeypatch):
    monkeypatch.setenv('WORKSPACE_CONNECTOR_SECRET_TEST','never-real');monkeypatch.setenv('PGPASSWORD','never-real')
    value=probe('ok');assert value['ok'] and value['data']['secret_env_absent']
    assert not alive(value['data']['pid'])

@pytest.mark.parametrize('mode,expected',[('timeout','WORKER_TIMEOUT'),('crash','WORKER_CRASHED'),('output','WORKER_OUTPUT_LIMIT'),('cpu','WORKER_CPU_LIMIT')])
def test_real_worker_fault_bounded_and_slot_reusable(mode,expected,tmp_path):
    marker=tmp_path/'pid.txt';start=time.monotonic()
    limits=WorkerLimits(cpu_seconds=1,wall_seconds=6 if mode=='cpu' else .7,output_bytes=4096)
    with pytest.raises(WorkerFailure) as caught:_run_entry('test_probe',{'mode':mode,'pid_file':str(marker)},limits,entry=PROBE)
    assert caught.value.code==expected, (getattr(caught.value,'accounting',{}), __import__('sys')._base_executable)
    assert time.monotonic()-start<9
    if marker.exists():assert not alive(int(marker.read_text()))
    assert probe('ok')['ok']  # failure cannot leak the global slot


def test_os_memory_limit_actually_refuses_allocation():
    value=_run_entry('test_probe',{'mode':'memory'},WorkerLimits(memory_bytes=32*1024*1024,job_memory_bytes=64*1024*1024,wall_seconds=2),entry=PROBE)
    assert value=={'ok':True,'data':{'allocation_refused':True}}

@pytest.mark.parametrize('mode',['child_timeout','child_crash'])
def test_owned_job_cleans_descendants_without_killing_unrelated_processes(mode,tmp_path):
    pid_file=tmp_path/'parent';child_file=tmp_path/'child'
    with pytest.raises(WorkerFailure):
        _run_entry('test_probe',{'mode':mode,'pid_file':str(pid_file),'child_file':str(child_file)},WorkerLimits(wall_seconds=.8),entry=PROBE)
    assert child_file.exists()
    assert not alive(int(pid_file.read_text())) and not alive(int(child_file.read_text()))
    assert alive(os.getpid())


def test_assignment_failure_denies_before_request_and_releases_slot(monkeypatch,tmp_path):
    marker=tmp_path/'no-execution'
    with monkeypatch.context() as patch:
        def deny(self,process):raise WorkerFailure('WORKER_ISOLATION_UNAVAILABLE')
        patch.setattr(WindowsJob,'assign',deny)
        with pytest.raises(WorkerFailure) as caught:_run_entry('test_probe',{'mode':'ok','pid_file':str(marker)},WorkerLimits(),entry=PROBE)
        assert caught.value.code=='WORKER_ISOLATION_UNAVAILABLE' and not marker.exists()
    assert probe('ok')['ok']


def test_operation_and_payload_budget_refuse_before_process_creation():
    with pytest.raises(WorkerFailure) as caught:run_worker('shell',{'command':'anything'})
    assert caught.value.code=='WORKER_OPERATION_DENIED'
    with pytest.raises(WorkerFailure) as caught:run_worker('snapshot',{'huge':'x'*65537})
    assert caught.value.code=='WORKER_INPUT_TOO_LARGE'
    SLOTS.acquire();SLOTS.acquire()
    try:
        with pytest.raises(WorkerFailure) as caught:run_worker('snapshot',{})
        assert caught.value.code=='WORKER_BUSY'
    finally:SLOTS.release();SLOTS.release()


def test_source_worker_failure_cleans_only_new_staging_and_manual_retry_works(tmp_path,monkeypatch):
    allowed=tmp_path/'allowed';allowed.mkdir();source=allowed/'original.csv';source.write_bytes(b'id,created_on\n1,2025-01-01\n')
    original=source.read_bytes();store=SourceStore(tmp_path/'connections',allowed)
    draft=ProfileDraft(name='Local recovery',path=str(source),usage_authorized=True)
    def fails(operation,payload,**kwargs):
        staging=store.root/'snapshots'/payload['snapshot_id']
        # Parent now creates and marks the UUID before the Worker may write.
        assert (staging/'temporary.receipt.json').is_file()
        (staging/'partial').write_bytes(b'partial')
        raise WorkerFailure('WORKER_TIMEOUT')
    with monkeypatch.context() as patch:
        patch.setattr('data_workspace.worker_runtime.run_worker',fails)
        with pytest.raises(PublicError) as caught:asyncio.run(store.test(AUTH,draft))
        assert caught.value.code=='WORKER_TIMEOUT'
    assert not store.active and not store.tests and list((store.root/'snapshots').iterdir())==[]
    assert source.read_bytes()==original
    tested=asyncio.run(store.test(AUTH,draft));assert len(tested.tables)==1 and not store.active


def test_saved_profile_recovery_does_not_replay_unknown_query(tmp_path,monkeypatch):
    allowed=tmp_path/'allowed';allowed.mkdir();source=allowed/'original.csv';source.write_bytes(b'id,created_on\n1,2025-01-01\n')
    store=SourceStore(tmp_path/'connections',allowed)
    from data_workspace.source_profiles import SaveProfile
    tested=asyncio.run(store.test(AUTH,ProfileDraft(name='saved',path=str(source),usage_authorized=True)))
    profile=store.save(AUTH,SaveProfile(test_id=tested.test_id))
    calls=[]
    async def unavailable(*args):calls.append(args);raise PublicError(422,'SOURCE_CONNECTION_FAILED','test-only safe error')
    with monkeypatch.context() as patch:
        patch.setattr(store,'call',unavailable)
        with pytest.raises(PublicError):asyncio.run(store.navigation(AUTH,profile.id))
    assert len(calls)==1 and not store.active and store.profiles(AUTH).profiles[0].state=='NEEDS_RETEST'
    assert asyncio.run(store.navigation(AUTH,profile.id))['tables']
    assert store.profiles(AUTH).profiles[0].state=='SAVED' and store.get(AUTH,profile.id)['version']==1


def test_native_process_count_limit_rejects_extra_process():
    value=_run_entry('test_probe',{'mode':'process_limit'},WorkerLimits(processes=1,wall_seconds=3),entry=PROBE)
    assert value=={'ok':True,'data':{'process_refused':True}}
