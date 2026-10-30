"""One application-owned bounded retention task. No HTTP execution controls.

Every cycle lives in a fixed Windows Job worker; shutdown signals only that job.
A restart rechecks references/native identities, never replays a SQL request.
"""
import asyncio
from datetime import timedelta
import json
import os
from threading import Event
from .auth import PublicError
from .retention import root_key,OWNER,timestamp,storage_lease
from .upload_preflight import checked_runtime_path
from .worker_runtime import run_worker,WorkerFailure,WorkerLimits

INTERVAL_SECONDS=600
START_DELAY_SECONDS=5
CYCLE_SCHEMA='workspace-retention-cycle-v1'
COUNT_KEYS={'scanned','reclaimed','recovered','protected','unknown','fresh','deferred','references_removed'}
STATES={'RUNNING','SUCCEEDED','PARTIAL','SKIPPED_BUSY','FAILED','STOPPED','INTERRUPTED'}


def validate_cycle(root,value):
    if (not isinstance(value,dict) or set(value)!={'schema','owner','root_key','at','state','counts','error_code'}
            or value['schema']!=CYCLE_SCHEMA or value['owner']!=OWNER or value['root_key']!=root_key(root)
            or value['state'] not in STATES or not isinstance(value['counts'],dict)
            or set(value['counts'])!=COUNT_KEYS):raise ValueError('invalid cycle receipt')
    timestamp(value['at'])
    if any(type(v) is not int or not 0<=v<=20000 for v in value['counts'].values()):raise ValueError('invalid cycle counts')
    if value['error_code'] is not None and (not isinstance(value['error_code'],str) or not value['error_code'].replace('_','').isalnum() or len(value['error_code'])>60):raise ValueError('invalid cycle category')
    return value


def read_cycle(root):
    from .storage_inventory import read_object
    path=checked_runtime_path(root,root/'cleanup-cycle.json')
    if not path.exists():return None
    if path.stat().st_nlink!=1:raise ValueError('linked receipt')
    return validate_cycle(root,read_object(path))


def save_cycle(root,record):
    validate_cycle(root,record)
    checked_runtime_path(root,root)
    root.mkdir(parents=True,exist_ok=True)
    path=checked_runtime_path(root,root/'cleanup-cycle.json')
    temp=checked_runtime_path(root,root/'cleanup-cycle.tmp')
    if path.exists():
        if not path.is_file() or path.stat().st_nlink!=1:raise ValueError('invalid receipt target')
        read_cycle(root)  # Corrupt existing metadata is not silently replaced to enable cleanup.
    # Never overwrite/delete an ambiguous leftover temp merely to make cleanup run.
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(record,stream);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)


class RetentionRunner:
    def __init__(self,store,*,interval=INTERVAL_SECONDS,start_delay=START_DELAY_SECONDS):
        if not .05<=interval<=3600 or not 0<=start_delay<=600:raise ValueError('invalid internal cadence')
        self.store=store;self.interval=interval;self.start_delay=start_delay
        self.leader=None;self.task=None;self.enabled=False;self.running=False;self.next_run_at=None
        self.last=None;self.stop_event=Event();self._wake=asyncio.Event()

    async def start(self):
        if self.task is not None:raise RuntimeError('runner already started')
        try:
            self.leader=storage_lease(self.store.root,_name='.retention-leader.lock')
            self.leader.__enter__()
        except PublicError as error:
            self.leader=None;self.last=self.record('SKIPPED_BUSY',error.code)
            return
        self.enabled=True
        try:
            self.last=read_cycle(self.store.root)
            if self.last and self.last['state']=='RUNNING':
                self.last={**self.last,'state':'INTERRUPTED','error_code':'OUTCOME_UNKNOWN'}
        except (ValueError,OSError):
            self.last=self.record('FAILED','CYCLE_RECEIPT_INVALID')
        self.task=asyncio.create_task(self.loop(),name='bounded-retention-cycle')

    def record(self,state,error=None,counts=None):
        return {'schema':CYCLE_SCHEMA,'owner':OWNER,'root_key':root_key(self.store.root),
                'at':self.store.clock().isoformat(),'state':state,
                'counts':counts or dict.fromkeys(COUNT_KEYS,0),'error_code':error}

    def snapshot(self):
        return {'enabled':self.enabled,'running':self.running,'interval_seconds':int(self.interval),
                'next_run_at':self.next_run_at,'last':self.last}

    async def wait(self,seconds):
        self.next_run_at=(self.store.clock()+timedelta(seconds=seconds)).isoformat()
        try:await asyncio.wait_for(self._wake.wait(),timeout=seconds)
        except TimeoutError:pass
        self.next_run_at=None

    async def loop(self):
        try:
            await self.wait(self.start_delay)
            while not self.stop_event.is_set():
                await self.tick()
                # Fixed delay AFTER completion; never concurrent cycles or catchup bursts.
                await self.wait(self.interval)
        finally:
            self.running=False;self.enabled=False;self.next_run_at=None
            if self.leader is not None:
                self.leader.__exit__(None,None,None);self.leader=None

    async def tick(self):
        import anyio
        self.running=True
        try:
            # Safe receipt persistence precedes every cycle. Failure stops execution.
            self.last=self.record('RUNNING')
            await anyio.to_thread.run_sync(lambda:save_cycle(self.store.root,self.last))
            try:
                value=await anyio.to_thread.run_sync(lambda:run_worker('retention_cycle',{'root':str(self.store.root)},limits=WorkerLimits(wall_seconds=15),cancel_event=self.stop_event))
                if value.get('ok') is not True:
                    code=value.get('code')
                    state='SKIPPED_BUSY' if code in {'STORAGE_BUSY','STORAGE_REFERENCES_BUSY','WORKER_BUSY'} else 'FAILED'
                    final=self.record(state,code if isinstance(code,str) else 'CYCLE_FAILED')
                else:
                    data=value.get('data')
                    if not isinstance(data,dict) or set(data)!=COUNT_KEYS|{'state','error_code'} or data['state'] not in {'SUCCEEDED','PARTIAL'}:raise ValueError('invalid cycle response')
                    final=self.record(data['state'],data['error_code'],{k:data[k] for k in COUNT_KEYS})
                    validate_cycle(self.store.root,final)
            except WorkerFailure as error:
                state='STOPPED' if error.code=='WORKER_CANCELLED' else 'SKIPPED_BUSY' if error.code=='WORKER_BUSY' else 'INTERRUPTED'
                final=self.record(state,error.code)
            await anyio.to_thread.run_sync(lambda:save_cycle(self.store.root,final))
            self.last=final  # Publish completion only after the durable receipt exists.
        except Exception:
            # Includes partial receipt-write failure: not success, no secret/raw text log.
            self.last=self.record('FAILED','CYCLE_RECEIPT_OR_RESPONSE_INVALID')
        finally:self.running=False

    async def stop(self):
        self.stop_event.set();self._wake.set()
        if self.task is not None:
            # Worker monitor stops its own Job, release handles before lifespan exit.
            await self.task
        self.enabled=False;self.next_run_at=None
