"""Fixed workspace_aggregate_v1 server; old navigation MCP stays unchanged."""
import hashlib,json
from typing import Any
from copy import deepcopy
from datetime import datetime,timezone
from threading import Lock
from uuid import uuid4
import anyio
from mcp.server.fastmcp import FastMCP
from .aggregate_contract import AggregateRequest,schema_hash
from .aggregate_engine import execute_aggregate

class AggregateExecution:
    def __init__(self,warehouse):self.warehouse=warehouse;self.lock=Lock();self.keys={};self.tasks={};self.busy=False
    def submit(self,request,key):
        b=AggregateRequest.model_validate(request)
        from uuid import UUID
        if str(UUID(key))!=key:raise ValueError('UUID required')
        digest=hashlib.sha256(b.model_dump_json().encode()).hexdigest()
        with self.lock:
            if key in self.keys:
                task=self.tasks[self.keys[key]]
                if task['fingerprint']!=digest:raise ValueError('idempotency conflict')
                return self.status(task['id'])
            if self.busy or len(self.tasks)>=100:raise ValueError('capacity')
            self.busy=True;id=str(uuid4());self.keys[key]=id;self.tasks[id]={'id':id,'status':'RUNNING','fingerprint':digest,'result':None,'error':None,'submitted_at':datetime.now(timezone.utc).isoformat()}
        try:result=execute_aggregate(self.warehouse,b);error=None
        except Exception:result=None;error={'code':'AGGREGATE_FAILED','safe_message':'Aggregate denied, interrupted or failed validation; no complete result.'}
        with self.lock:
            self.tasks[id].update(status='SUCCEEDED' if error is None else 'FAILED',result=result.model_dump() if result else None,error=error);self.busy=False
            return self.status(id)
    def status(self,id):return {'ok':True,'task':deepcopy({k:v for k,v in self.tasks[id].items() if k not in ('fingerprint','result')})}
    def result(self,id):
        with self.lock:
            t=self.tasks[id]
            return {'ok':True,'result':deepcopy(t['result'])} if t['status']=='SUCCEEDED' else {'ok':False,'error':t['error']}

def create_aggregate_server(directory,database=None):
    from .local_file import LocalFileWarehouse
    from .engine import OwnedWarehouse
    warehouse=LocalFileWarehouse(database) if database else OwnedWarehouse(directory)
    service=AggregateExecution(warehouse);server=FastMCP('workspace_aggregate_v1',log_level='ERROR')
    def safe(call):
        try:return call()
        except Exception:return {'ok':False,'error':{'code':'AGGREGATE_DENIED','safe_message':'Aggregate contract or resource denied.'}}
    @server.tool(structured_output=True)
    def aggregate_metadata(table:str)->dict[str,Any]:
        def read():
            desc=warehouse.describe(table)
            return {'ok':True,'capability':'workspace_aggregate_v1','metadata':{'table':desc['table'],'fields':[{'name':c['name'],'type':c['type']} for c in desc['fields']],'source':desc['source'],'schema_hash':schema_hash(desc)}}
        return safe(read)
    @server.tool(structured_output=True)
    async def submit_aggregate(request:dict,idempotency_key:str)->dict[str,Any]:
        return await anyio.to_thread.run_sync(lambda:safe(lambda:service.submit(request,idempotency_key)))
    @server.tool(structured_output=True)
    def aggregate_status(task_id:str)->dict[str,Any]:return safe(lambda:service.status(task_id))
    @server.tool(structured_output=True)
    def aggregate_result(task_id:str)->dict[str,Any]:return safe(lambda:service.result(task_id))
    return server
