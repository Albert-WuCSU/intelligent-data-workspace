"""Opt-in local MCP API. Identity and task ownership are never client supplied."""
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone
import hashlib
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, Request
from pydantic import Field
from .auth import identity, PublicError
from .contracts import Contract, AuthContext, ErrorEnvelope
from .warehouse.request import PreviewRequest

CONNECTOR = "owned-synthetic"

class ConnectorSummary(Contract):
    connector_id: Literal["owned-synthetic"] = CONNECTOR
    label: str = "专属合成测试数仓"
    configured: bool
    verified: bool
    state: Literal["NOT_CONFIGURED", "READY", "FAILED"]
    source: Literal["independently_generated_synthetic"] = "independently_generated_synthetic"
    sql_dialect: Literal["duckdb"] = "duckdb"
    note: str
    execution_generation: str | None = None

class ConnectorMetadata(Contract):
    connector: ConnectorSummary
    metadata: dict

class PreviewSubmit(Contract):
    request: PreviewRequest
    idempotency_key: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9_-]+$")
    confirmed: Literal[True]
    execution_generation: str = Field(min_length=36,max_length=36)

class PreviewReceipt(Contract):
    execution_generation: str | None = None
    task_id: str
    status: Literal["SUBMITTING", "RUNNING", "SUCCEEDED", "FAILED", "OUTCOME_UNKNOWN", "RESULT_EXPIRED"]
    created_at: datetime
    trace_id: str
    error: ErrorEnvelope | None = None

class PreviewColumn(Contract):
    name: str
    type: str

class PreviewQuality(Contract):
    status: Literal["WARN", "FAIL"]
    limitations: list[str]

class QueryPreview(Contract):
    source: Literal["independently_generated_synthetic"]
    dataset_version: str
    sql_dialect: Literal["duckdb"]
    columns: list[PreviewColumn] = Field(max_length=100)
    rows: list[list[str | int | float | bool | None]] = Field(max_length=100)
    returned_row_count: int = Field(ge=0,le=100)
    reported_total_rows: int | None
    truncated: bool
    retrieved_at: datetime
    currency: Literal["TEST"]
    quality: PreviewQuality

class PreviewResult(Contract):
    task_id: str
    result: QueryPreview

class ConnectorManager:
    def __init__(self, enabled):
        self.generation=str(uuid4())
        self.enabled=enabled;self.client=None;self.verified=False;self.failed=False
        self.tasks={};self.keys={};self.active=False

    def authorize(self, auth):
        if (auth.mode,auth.tenant_id,auth.principal_id)!=("development","local-workspace","local-developer"):
            raise PublicError(403,"CONNECTOR_DENIED","此数据源仅授权给本机开发身份。")

    def invalidate(self):
        # Transition once per fault episode, retaining receipts/keys as tombstones.
        if self.failed:return
        self.generation=str(uuid4());self.verified=False;self.failed=True
        for record in self.tasks.values():
            record['invalidated']=True
            receipt=record['receipt']
            if receipt.status=='SUCCEEDED':
                receipt.status='RESULT_EXPIRED'
                receipt.error=ErrorEnvelope(code='RESULT_CONTEXT_EXPIRED',safe_message='SQL曾完成，但所属MCP结果上下文已失效；旧结果不再可读，请重新验证并确认新预览。',trace_id=receipt.trace_id)

    def summary(self):
        return ConnectorSummary(execution_generation=self.generation if self.enabled else None,configured=self.enabled,verified=self.verified,state="READY" if self.verified else "FAILED" if self.failed else "NOT_CONFIGURED",note="真实MCP已验证；仅合成数据只读预览，尚无自然语言取数、取消或正式持久化。" if self.verified else "连接已失效；点击验证数据源连接重建受限MCP。旧结果可能过期，不会自动重新提交查询。" if self.failed else "尚未启用；使用本地启动器启用专属测试仓，不需要填写令牌。")

    async def call(self, auth, name, arguments=None):
        self.authorize(auth)
        if not self.client:
            raise PublicError(503,"CONNECTOR_NOT_READY","本机MCP未就绪；请检查项目依赖和数仓后重启本地服务。")
        try:
            value=await self.client.call(name,arguments)
        except PublicError as exc:
            if exc.code=='CAPACITY_EXCEEDED':raise
            self.invalidate()
            raise PublicError(502,"CONNECTOR_UNAVAILABLE","MCP通信未完成；不要重新提交不明任务，可读取原任务状态。") from None
        except Exception:
            self.invalidate()
            raise PublicError(502,"CONNECTOR_UNAVAILABLE","MCP通信未完成；不要重新提交不明任务，可读取原任务状态。") from None
        if value.get("ok") is False:
            code=value.get("error",{}).get("code")
            status=404 if code=="TASK_NOT_FOUND" else 409 if code in {"IDEMPOTENCY_CONFLICT","CAPACITY_EXCEEDED","NOT_READY"} else 422
            raise PublicError(status,code if code in {"TASK_NOT_FOUND","IDEMPOTENCY_CONFLICT","CAPACITY_EXCEEDED","NOT_READY"} else "QUERY_DENIED","请求未完成；请检查授权表/字段或读取已有任务。")
        return value

    def owned(self, auth, task_id):
        self.authorize(auth)
        record=self.tasks.get(task_id)
        if record is None or record['scope']!=(auth.tenant_id,auth.principal_id):
            raise PublicError(404,"TASK_NOT_FOUND","任务不存在或不可访问。")
        return record

    async def submit(self, auth, body, trace):
        self.authorize(auth)
        if not self.enabled:raise PublicError(503,"CONNECTOR_NOT_READY","本机连接器尚未启用。")
        if body.execution_generation!=self.generation:raise PublicError(409,"EXECUTION_CONTEXT_EXPIRED","服务已重启或执行上下文已过期；请重新验证连接并确认查询，不自动重试。")
        from .warehouse.catalog import COLUMNS
        names={name for name,_ in COLUMNS.get(body.request.table,[])}
        if not names or not set(body.request.columns)<=names:raise PublicError(422,"QUERY_DENIED","表或字段未获授权。")
        scope=(auth.tenant_id,auth.principal_id)
        key=(scope,body.idempotency_key)
        fingerprint=hashlib.sha256(body.request.model_dump_json().encode()).hexdigest()
        if key in self.keys:
            record=self.owned(auth,self.keys[key])
            if record['fingerprint']!=fingerprint:raise PublicError(409,"IDEMPOTENCY_CONFLICT","同一提交键不能用于不同查询范围。")
            return record['receipt']
        if not self.verified:raise PublicError(503,"CONNECTOR_NOT_READY","请先验证数据源连接。")
        if self.active or len(self.tasks)>=100:raise PublicError(503,"CAPACITY_EXCEEDED","已有查询运行或已达本机100条任务上限，请先处理已有任务。")
        task_id=str(uuid4());receipt=PreviewReceipt(execution_generation=self.generation,task_id=task_id,status="SUBMITTING",created_at=datetime.now(timezone.utc),trace_id=trace)
        record={'scope':scope,'fingerprint':fingerprint,'receipt':receipt,'upstream':None,'generation':self.generation,'invalidated':False}
        self.tasks[task_id]=record;self.keys[key]=task_id;self.active=True
        try:
            output=await self.call(auth,"submit_query",{"request":body.request.model_dump(mode='json'),"idempotency_key":body.idempotency_key})
            upstream=output['task'];record['upstream']=upstream['task_id']
            if upstream['status'] not in {'RUNNING','SUCCEEDED','FAILED'}:raise ValueError('unsupported status')
            if record['invalidated'] or record['generation']!=self.generation:raise ValueError('expired submission')
            receipt.status=upstream['status']
            if upstream.get('error'):
                receipt.error=ErrorEnvelope(code="QUERY_FAILED",safe_message="本机SQL未完成；可调整授权范围后以新任务重试。",trace_id=trace)
        except BaseException as exc:
            # Submission may have occurred. A repeated key never auto-submits.
            receipt.status="OUTCOME_UNKNOWN"
            receipt.error=ErrorEnvelope(code="OUTCOME_UNKNOWN",safe_message="提交结果不明；已保留原任务，不会自动重复执行。请检查连接器状态。",trace_id=trace)
            if isinstance(exc,asyncio.CancelledError):raise
        finally:self.active=False
        return receipt

@asynccontextmanager
async def connector_lifespan(app):
    manager=app.state.connector
    service=None
    if manager.enabled:
        from .warehouse.persistent import PersistentMCP
        auth=AuthContext(principal_id='local-developer',tenant_id='local-workspace',mode='development')
        service=PersistentMCP(auth,manager.invalidate);service.start();manager.client=service
        try:
            value=await manager.call(auth,'list_tables')
            manager.verified=len(value['metadata']['tables'])==5
            manager.failed=not manager.verified
        except Exception:manager.invalidate()
    try:yield
    finally:
        manager.client=None;manager.verified=False
        if service:await service.stop()

router=APIRouter(prefix='/api/v1')

@router.get('/connectors/owned-synthetic',response_model=ConnectorSummary)
def connector_summary(request:Request,auth:AuthContext=Depends(identity)):
    manager=request.app.state.connector;manager.authorize(auth);return manager.summary()

@router.post('/connectors/owned-synthetic/verify',response_model=ConnectorMetadata)
async def verify_connector(request:Request,auth:AuthContext=Depends(identity)):
    manager=request.app.state.connector
    value=await manager.call(auth,'list_tables')
    if len(value.get('metadata',{}).get('tables',[]))!=5:
        manager.invalidate();raise PublicError(502,'CATALOG_MISMATCH','目录与本机合成仓不一致，请检查完整性。')
    manager.verified=True;manager.failed=False
    return ConnectorMetadata(connector=manager.summary(),metadata=value['metadata'])

@router.get('/connectors/owned-synthetic/tables/{table}/schema',response_model=ConnectorMetadata)
async def table_schema(table:str,request:Request,auth:AuthContext=Depends(identity)):
    manager=request.app.state.connector;value=await manager.call(auth,'describe_table',{'table':table})
    return ConnectorMetadata(connector=manager.summary(),metadata=value['metadata'])

@router.post('/execution-previews',response_model=PreviewReceipt)
async def preview_submit(body:PreviewSubmit,request:Request,auth:AuthContext=Depends(identity)):
    return await request.app.state.connector.submit(auth,body,request.state.trace_id)

@router.get('/execution-previews/{task_id}',response_model=PreviewReceipt)
def preview_status(task_id:str,request:Request,auth:AuthContext=Depends(identity)):
    return request.app.state.connector.owned(auth,task_id)['receipt']

@router.get('/execution-previews/{task_id}/result',response_model=PreviewResult)
async def preview_result(task_id:str,request:Request,auth:AuthContext=Depends(identity)):
    manager=request.app.state.connector;record=manager.owned(auth,task_id)
    if record.get('invalidated') or record.get('generation')!=manager.generation:
        raise PublicError(409,'RESULT_CONTEXT_EXPIRED','结果所属MCP上下文已失效；请重新验证连接并确认新的预览，不会恢复或重提旧查询。')
    if record['receipt'].status!='SUCCEEDED':raise PublicError(409,'RESULT_NOT_READY','任务未成功，尚无可读取结果。')
    output=await manager.call(auth,'get_query_result',{'task_id':record['upstream']})
    if record.get('invalidated') or record.get('generation')!=manager.generation:
        raise PublicError(409,'RESULT_CONTEXT_EXPIRED','读取中MCP上下文失效，已丢弃旧结果。')
    return PreviewResult(task_id=task_id,result=output['result'])
