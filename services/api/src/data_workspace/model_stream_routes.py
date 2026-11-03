"""Explicit stream test receipts: bounded async task, read-only snapshots, no replay calls."""
import asyncio
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,Request
from pydantic import BaseModel,Field
from .auth import identity,PublicError
from .contracts import AuthContext
from .model_routes import authorize,ModelTestRequest,FIXED_TEST
from .model_stream import ProviderStreamEvent,StreamDiagnostics

router=APIRouter(prefix='/api/v1/model-service',tags=['model-service'])
class StreamTestReceipt(BaseModel):
    request_id: str
    execution_generation: str
    config_version: str
    status: Literal['running','succeeded','partial','failed_or_unknown'] = 'running'
    events: list[ProviderStreamEvent] = Field(default_factory=list)
    error_code: str | None = None
    diagnostics: StreamDiagnostics | None = None
    kind: Literal['fixed_model_stream_test'] = 'fixed_model_stream_test'
    sql_executed: Literal[False] = False
    cost_mode: Literal['estimated_not_actual'] = 'estimated_not_actual'
    per_request_estimate_usd: str = '0.25'

class StreamTests:
    def __init__(self):self.receipts={};self.tasks={}
    async def close(self):
        tasks=list(self.tasks.values())
        for t in tasks:t.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
    async def run(self,app,receipt):
        provider=app.state.model_provider;complete=False
        try:
            async for event in provider.stream(FIXED_TEST):
                if len(receipt.events)>=256:raise PublicError(502,'MODEL_RESPONSE_LIMIT','流式事件超限。')
                receipt.events.append(event)
                if event.kind=='completed':complete=True
            if not complete:raise PublicError(502,'MODEL_STREAM_INVALID','流式结束回执缺失。')
            receipt.status='succeeded';provider._verified=True;provider._stream_verified=True
        except asyncio.CancelledError:
            receipt.error_code='MODEL_STREAM_CANCELLED';receipt.diagnostics=StreamDiagnostics(reason='cancelled')
        except PublicError as exc:
            receipt.error_code=exc.code
            inferred={'MODEL_RESPONSE_LIMIT':'resource_limit','MODEL_RESULT_UNKNOWN':'timeout',
                      'MODEL_TRANSPORT_FAILED':'transport','MODEL_SERVICE_FAILED':'upstream_refused'}
            fallback=inferred.get(exc.code,'unknown')
            normal=getattr(exc,'response_diagnostics',None)
            if normal is not None:
                fallback={'model_mismatch':'model_mismatch','empty_or_oversized_text':'incomplete_output',
                          'usage_invalid':'usage_invalid','output_budget_exceeded':'usage_invalid',
                          'secret_echo':'secret_echo','unsupported_content':'unsupported_content'}.get(normal.reason,'unknown')
            receipt.diagnostics=getattr(exc,'stream_diagnostics',None) or StreamDiagnostics(reason=fallback)
        except Exception:
            receipt.error_code='MODEL_RESULT_UNKNOWN';receipt.diagnostics=StreamDiagnostics(reason='unknown')
        finally:
            if receipt.status!='succeeded':
                receipt.status='partial' if any(e.kind=='text_delta' for e in receipt.events) else 'failed_or_unknown'
                # Unconfirmed suffix/text is never returned as a completed generation.
                receipt.events=[e for e in receipt.events if e.kind!='completed']
                provider._verified=False;provider._stream_verified=False;app.state.model_enabled=False
            app.state.model_configuration_lock.release()

@router.post('/stream-test',response_model=StreamTestReceipt)
async def start_stream(request:Request,body:ModelTestRequest,auth:AuthContext=Depends(identity)):
    authorize(auth);app=request.app;provider=app.state.model_provider;tests=app.state.model_stream_tests
    if body.execution_generation!=app.state.model_tests.generation or body.config_version!=provider.configuration.version:
        raise PublicError(409,'MODEL_TEST_CONTEXT_EXPIRED','模型连接已变化，请刷新。')
    try:
        if str(UUID(body.request_id))!=body.request_id:raise ValueError()
    except (ValueError,TypeError):raise PublicError(422,'MODEL_TEST_ID_INVALID','请求编号无效。') from None
    # One namespace shared with normal fixed tests; no same UUID second provider invocation.
    if body.request_id in app.state.model_tests.receipts:raise PublicError(409,'MODEL_TEST_ID_REUSED','编号已用于普通测试，不重新调用。')
    if body.request_id in tests.receipts:return tests.receipts[body.request_id]
    if provider.supported_protocol!='anthropic_messages':raise PublicError(409,'MODEL_STREAM_UNSUPPORTED','此协议流式尚未实现，不自动切换。')
    if not provider.status().test_available:raise PublicError(409,'MODEL_NOT_VERIFIED','模型未配置或预算不可用。')
    if app.state.model_configuration_lock.locked() or provider._busy:raise PublicError(409,'MODEL_CONNECTION_BUSY','已有测试/配置操作进行中。')
    if len(tests.receipts)>=60:raise PublicError(409,'MODEL_TEST_LIMIT','本轮流式测试已到上限。')
    await app.state.model_configuration_lock.acquire()
    try:
        receipt=StreamTestReceipt(request_id=body.request_id,execution_generation=body.execution_generation,config_version=body.config_version)
        tests.receipts[body.request_id]=receipt
        task=asyncio.create_task(tests.run(app,receipt))
        tests.tasks[body.request_id]=task
        def early_cancel(done):
            if receipt.status=='running' and done.cancelled():
                receipt.status='failed_or_unknown';receipt.error_code='MODEL_STREAM_CANCELLED';receipt.diagnostics=StreamDiagnostics(reason='cancelled')
                provider._verified=False;provider._stream_verified=False;app.state.model_enabled=False
                if app.state.model_configuration_lock.locked():app.state.model_configuration_lock.release()
        task.add_done_callback(early_cancel)
        return receipt
    except BaseException:
        app.state.model_configuration_lock.release();raise

@router.get('/stream-tests/{request_id}',response_model=StreamTestReceipt)
def snapshot(request_id:str,request:Request,auth:AuthContext=Depends(identity)):
    authorize(auth)
    receipt=request.app.state.model_stream_tests.receipts.get(request_id)
    if receipt is None or receipt.execution_generation!=request.app.state.model_tests.generation:raise PublicError(404,'MODEL_TEST_NOT_FOUND','流式测试不在当前上下文；不会重新调用。')
    return receipt

@router.post('/stream-tests/{request_id}/cancel',response_model=StreamTestReceipt)
async def cancel(request_id:str,request:Request,auth:AuthContext=Depends(identity)):
    authorize(auth);receipt=snapshot(request_id,request,auth);task=request.app.state.model_stream_tests.tasks.get(request_id)
    if task is not None and not task.done():
        task.cancel();await asyncio.gather(task,return_exceptions=True)
    return receipt
