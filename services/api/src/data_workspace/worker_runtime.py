"""Windows-only, parent-owned bounded workers. No shell or unbounded fallback.

Bootstrap reads no request before the parent assigns its Job Object. Native job
limits cover the worker and descendants; only this newly-created job is killed.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import BoundedSemaphore, Event, Lock, Thread
import time

ROOT = Path(__file__).resolve().parents[4]
ENTRY = Path(__file__).with_name('worker_entry.py')
OPERATIONS = frozenset({'snapshot', 'http_navigation', 'postgres_navigation', 'upload_preflight'})
SLOTS = BoundedSemaphore(2)

class WorkerFailure(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)  # Never include payload, stdout, credentials or raw exceptions.

@dataclass(frozen=True)
class WorkerLimits:
    memory_bytes: int = 384 * 1024 * 1024
    job_memory_bytes: int = 512 * 1024 * 1024
    cpu_seconds: int = 8
    wall_seconds: float = 25
    processes: int = 2
    output_bytes: int = 250000

    def __post_init__(self):
        if not (32*1024*1024 <= self.memory_bytes <= self.job_memory_bytes <= 512*1024*1024 and 1<=self.cpu_seconds<=8 and .1<=self.wall_seconds<=30 and 1<=self.processes<=2 and 1<=self.output_bytes<=250000):
            raise ValueError('Invalid internal worker limits')

class WindowsJob:
    def __init__(self, limits):
        self.handle = None
        if os.name != 'nt':
            raise WorkerFailure('WORKER_ISOLATION_UNAVAILABLE')
        try:
            import win32api, win32job
            self.api, self.job = win32api, win32job
            self.handle = win32job.CreateJobObject(None, '')
            info = win32job.QueryInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation)
            basic = info['BasicLimitInformation']
            basic.update(LimitFlags=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS | win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY | win32job.JOB_OBJECT_LIMIT_JOB_MEMORY | win32job.JOB_OBJECT_LIMIT_JOB_TIME | win32job.JOB_OBJECT_LIMIT_PROCESS_TIME,
                         ActiveProcessLimit=limits.processes, PerJobUserTimeLimit=limits.cpu_seconds*10000000, PerProcessUserTimeLimit=limits.cpu_seconds*10000000)
            info.update(ProcessMemoryLimit=limits.memory_bytes, JobMemoryLimit=limits.job_memory_bytes)
            win32job.SetInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation, info)
            win32job.SetInformationJobObject(self.handle, win32job.JobObjectEndOfJobTimeInformation, {'EndOfJobTimeAction':win32job.JOB_OBJECT_TERMINATE_AT_END_OF_JOB})
        except Exception:
            if self.handle is not None:
                self.handle.Close(); self.handle=None
            raise WorkerFailure('WORKER_ISOLATION_UNAVAILABLE') from None

    def assign(self, process):
        try:
            import win32con
            handle=self.api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, process.pid)
            try:self.job.AssignProcessToJobObject(self.handle,handle)
            finally:handle.Close()
        except Exception:
            raise WorkerFailure('WORKER_ISOLATION_UNAVAILABLE') from None

    def stop(self):
        if self.handle is not None:
            self.job.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle is not None:
            self.handle.Close(); self.handle=None


def worker_environment():
    # No PATH/HOME/USERPROFILE/PG*/proxy/secret namespace or host tool tokens.
    result={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','TEMP','TMP') if k in os.environ}
    result['PYTHONUTF8']='1'
    return result


def run_worker(operation, payload, *, limits=None):
    if operation not in OPERATIONS:
        raise WorkerFailure('WORKER_OPERATION_DENIED')
    return _run_entry(operation,payload,limits or WorkerLimits())


def _run_entry(operation,payload,limits, *, entry=ENTRY):
    # entry is internal-only for isolated failure test fixtures, never a product API field.
    try:
        encoded=json.dumps({'operation':operation,'payload':payload},ensure_ascii=False,allow_nan=False).encode('utf-8')
    except Exception:
        raise WorkerFailure('WORKER_INPUT_INVALID') from None
    if len(encoded)>65536:raise WorkerFailure('WORKER_INPUT_TOO_LARGE')
    if not SLOTS.acquire(blocking=False):raise WorkerFailure('WORKER_BUSY')
    process=None;job=None;reader=None;writer=None
    chunks=[];failures=[];guard=Lock();finished=Event()
    def failed(code):
        with guard:
            if not failures:failures.append(code)
        finished.set()
    try:
        job=WindowsJob(limits)
        # Base Python -S avoids venv launcher child races and site/custom startup code.
        # Fixed bootstrap explicitly supplies the approved project site-packages after the gate.
        executable=getattr(sys,'_base_executable',sys.executable)
        process=subprocess.Popen([executable,'-S',str(entry.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=ROOT,env=worker_environment(),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        job.assign(process)
        def receive():
            total=0
            try:
                while True:
                    chunk=process.stdout.read(4096)
                    if not chunk:break
                    total+=len(chunk)
                    if total>limits.output_bytes:
                        failed('WORKER_OUTPUT_LIMIT');return
                    chunks.append(chunk)
            except Exception:failed('WORKER_PIPE_FAILED')
            finally:finished.set()
        def send():
            try:
                process.stdin.write(encoded);process.stdin.flush();process.stdin.close()
            except Exception:failed('WORKER_PIPE_FAILED')
        reader=Thread(target=receive,daemon=True);writer=Thread(target=send,daemon=True)
        reader.start();writer.start()
        deadline=time.monotonic()+limits.wall_seconds
        while process.poll() is None or not finished.is_set():
            if failures:raise WorkerFailure(failures[0])
            accounting=job.job.QueryInformationJobObject(job.handle,job.job.JobObjectBasicAccountingInformation)
            if accounting['TotalUserTime']+accounting['TotalKernelTime'] >= limits.cpu_seconds*10000000:
                raise WorkerFailure('WORKER_CPU_LIMIT')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise WorkerFailure('WORKER_TIMEOUT')
            finished.wait(min(.02,remaining))
            if finished.is_set() and process.poll() is None:time.sleep(.01)
        if failures:raise WorkerFailure(failures[0])
        if process.returncode!=0:
            accounting=job.job.QueryInformationJobObject(job.handle,job.job.JobObjectBasicAccountingInformation)
            if accounting['TotalUserTime']+accounting['TotalKernelTime'] >= limits.cpu_seconds*10000000:raise WorkerFailure('WORKER_CPU_LIMIT')
            raise WorkerFailure('WORKER_CRASHED')
        try:
            result=json.loads(b''.join(chunks).decode('utf-8'))
            if not isinstance(result,dict) or type(result.get('ok')) is not bool:raise ValueError()
        except Exception:raise WorkerFailure('WORKER_RESPONSE_INVALID') from None
        return result
    except WorkerFailure as exc:
        if job and job.handle:
            exc.accounting=job.job.QueryInformationJobObject(job.handle,job.job.JobObjectBasicAccountingInformation)
        raise
    except Exception:raise WorkerFailure('WORKER_FAILED') from None
    finally:
        # Stop by owned job HANDLE, not a guessed PID or shell tree command.
        try:
            try:
                if job:job.stop()
            finally:
                if process:
                    if process.poll() is None:process.kill()
                    process.wait(timeout=5)
        finally:
            try:
                if job:job.close()
                for thread in (writer,reader):
                    if thread:thread.join(5)
                if process:
                    for stream in (process.stdin,process.stdout):
                        if stream and not stream.closed:stream.close()
            finally:SLOTS.release()



def public_worker_error(exc):
    from .auth import PublicError
    messages={
        'WORKER_TIMEOUT':(504,'读取超时，已终止本次专属进程并释放名额；原配置保留。远端查询结果可能未知，不会自动重新提交。'),
        'WORKER_BUSY':(409,'受限读取进程已达容量，请等待现有请求结束后手动重试。'),
        'WORKER_ISOLATION_UNAVAILABLE':(503,'本机资源隔离不可用，未执行读取；请检查Windows及项目依赖，不会降级为无限制执行。'),
    }
    status,message=messages.get(exc.code,(422,'本次读取进程异常或超过资源限额，已清理进程；原配置保留，请检查来源后重新连接。不会自动重复远端查询。'))
    return PublicError(status,exc.code,message)
