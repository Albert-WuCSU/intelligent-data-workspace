"""Bounded stdio streams for MCP SDK ClientSession; parent-owned Windows Job.

No SDK patches, shell, executable profile or environment inheritance. Lifetime
CPU budget is deliberately finite; exhaustion requires a fresh confirmed session.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import json
import subprocess
import sys
from threading import BoundedSemaphore
import anyio
from mcp import types
from mcp.shared.message import SessionMessage
from data_workspace.worker_runtime import WindowsJob,WorkerLimits,WorkerFailure,worker_environment,ROOT

SLOTS=BoundedSemaphore(4)
MAX_LINE=512*1024  # SDK can duplicate bounded structured results in text content.
ENTRY=Path(__file__).with_name('stdio_entry.py')

class StdioState:
    def __init__(self):
        self.process=None;self.job=None;self.failure=None;self.closing=False
    @property
    def healthy(self):return self.process is not None and self.failure is None and self.process.returncode is None
    def abort(self):
        if self.job and self.job.handle:self.job.stop()

@asynccontextmanager
async def governed_stdio(warehouse,database=None,*,limits=None,entry=ENTRY):
    limits=limits or WorkerLimits()
    if not SLOTS.acquire(blocking=False):raise WorkerFailure('WORKER_BUSY')
    state=StdioState();read_tx,read_rx=anyio.create_memory_object_stream(8);write_tx,write_rx=anyio.create_memory_object_stream(8)
    async def fault(code):
        if not state.closing and state.failure is None:
            if code=='WORKER_CRASHED' and state.job and state.job.handle:
                info=state.job.job.QueryInformationJobObject(state.job.handle,state.job.job.JobObjectBasicAccountingInformation)
                if info['TotalUserTime']+info['TotalKernelTime']>=limits.cpu_seconds*10000000:code='WORKER_CPU_LIMIT'
            state.failure=code;state.abort()
            try:await read_tx.send(WorkerFailure(code))
            except (anyio.BrokenResourceError,anyio.ClosedResourceError):pass
    try:
        state.job=WindowsJob(limits)
        state.process=await anyio.open_process([getattr(sys,'_base_executable',sys.executable),'-S',str(entry.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=ROOT,env=worker_environment(),creationflags=subprocess.CREATE_NO_WINDOW)
        state.job.assign(state.process)
        initial=json.dumps({'warehouse':str(warehouse),'database':str(database) if database else None}).encode()+b'\n'
        if len(initial)>65536:raise WorkerFailure('WORKER_INPUT_TOO_LARGE')
        await state.process.stdin.send(initial)
        async def reader():
            buffer=b''
            try:
                while True:
                    chunk=await state.process.stdout.receive(4096)
                    buffer+=chunk
                    while b'\n' in buffer:
                        line,buffer=buffer.split(b'\n',1)
                        if len(line)>MAX_LINE:await fault('WORKER_OUTPUT_LIMIT');return
                        try:message=types.JSONRPCMessage.model_validate_json(line)
                        except Exception:await fault('WORKER_RESPONSE_INVALID');return
                        await read_tx.send(SessionMessage(message))
                    if len(buffer)>MAX_LINE:await fault('WORKER_OUTPUT_LIMIT');return
            except anyio.EndOfStream:await fault('WORKER_CRASHED')
            except (anyio.BrokenResourceError,anyio.ClosedResourceError):pass
            except Exception:await fault('WORKER_PIPE_FAILED')
        async def writer():
            try:
                async for message in write_rx:
                    line=message.message.model_dump_json(by_alias=True,exclude_none=True).encode()+b'\n'
                    if len(line)>65536:await fault('WORKER_INPUT_TOO_LARGE');return
                    await state.process.stdin.send(line)
            except (anyio.BrokenResourceError,anyio.ClosedResourceError):await fault('WORKER_PIPE_FAILED')
            except Exception:await fault('WORKER_PIPE_FAILED')
        async def monitor():
            while not state.closing and state.failure is None:
                info=state.job.job.QueryInformationJobObject(state.job.handle,state.job.job.JobObjectBasicAccountingInformation)
                if info['TotalUserTime']+info['TotalKernelTime']>=limits.cpu_seconds*10000000:
                    await fault('WORKER_CPU_LIMIT');return
                if state.process.returncode is not None:await fault('WORKER_CRASHED');return
                await anyio.sleep(.05)
        async with anyio.create_task_group() as group:
            group.start_soon(reader);group.start_soon(writer);group.start_soon(monitor)
            try:yield read_rx,write_tx,state
            finally:
                state.closing=True
                with anyio.CancelScope(shield=True):
                    state.abort()
                    with anyio.move_on_after(5):await state.process.wait()
                group.cancel_scope.cancel()
    finally:
        with anyio.CancelScope(shield=True):
            try:
                state.closing=True;state.abort()
                if state.process:
                    with anyio.move_on_after(5):await state.process.wait()
                    await state.process.aclose()
            finally:
                if state.job:state.job.close()
                await read_tx.aclose();await read_rx.aclose();await write_tx.aclose();await write_rx.aclose()
                SLOTS.release()
