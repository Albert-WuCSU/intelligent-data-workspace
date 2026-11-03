"""User-triggered fixed non-sensitive model tests, never warehouse querying or Key input."""
import asyncio
from uuid import uuid4, UUID
from typing import Literal
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, SecretStr, Field
from .auth import identity, PublicError
from .contracts import AuthContext
from .model_provider import ModelServiceStatus, ModelGeneration, ModelResponseDiagnostics
from .model_budget import EstimatedBudgetSummary

router = APIRouter(prefix='/api/v1/model-service', tags=['model-service'])
FIXED_TEST = 'Reply with only OK. This is a non-sensitive model connection test. Do not call tools.'

class ModelReadiness(ModelServiceStatus):
    execution_generation: str
    connection_management: bool = True
    budget: EstimatedBudgetSummary | None = None
    endpoint: str | None = None
    stream_management: bool = True
    stream_available: bool = False
    model_name_editable: bool = True
    catalog_management: bool = True
    catalog_enabled: bool = False

class ModelTestRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id: str
    execution_generation: str
    config_version: str
    accept_estimated_cost: Literal[True]

class ModelTestReceipt(BaseModel):
    request_id: str
    execution_generation: str
    config_version: str
    status: Literal['succeeded','failed_or_unknown','running']
    kind: Literal['model_connection_test'] = 'model_connection_test'
    generation: ModelGeneration | None = None
    error_code: str | None = None
    upstream_status: Literal[401,403] | None = None
    diagnostics: ModelResponseDiagnostics | None = None
    per_request_estimate_usd: str = '0.25'
    cost_mode: Literal['estimated_not_actual'] = 'estimated_not_actual'
    sql_executed: Literal[False] = False


def authorize(auth):
    if (auth.mode, auth.tenant_id, auth.principal_id) != ('development','local-workspace','local-developer'):
        raise PublicError(403,'MODEL_SERVICE_DENIED','模型服务未获授权。')

class ModelTests:
    def __init__(self):
        self.generation=str(uuid4())
        self.receipts={}
        self.lock=asyncio.Lock()

    async def run(self,provider,body):
        if body.execution_generation!=self.generation or body.config_version!=provider.configuration.version:
            raise PublicError(409,'MODEL_TEST_CONTEXT_EXPIRED','模型执行上下文已变化，请刷新状态；不会重提旧请求。')
        try:
            if str(UUID(body.request_id))!=body.request_id:raise ValueError()
        except (ValueError,TypeError,AttributeError):
            raise PublicError(422,'MODEL_TEST_ID_INVALID','测试请求编号无效。') from None
        async with self.lock:
            if body.request_id in self.receipts:return self.receipts[body.request_id]
            if any(r.status=='running' for r in self.receipts.values()):
                raise PublicError(429,'MODEL_BUSY','已有模型测试进行中，请等待，不重复发起。')
            if len(self.receipts)>=60:raise PublicError(409,'MODEL_TEST_LIMIT','本轮模型测试请求数已到上限。')
            receipt=ModelTestReceipt(request_id=body.request_id,execution_generation=self.generation,
                config_version=body.config_version,status='running')
            self.receipts[body.request_id]=receipt
        try:
            result=await provider.generate(FIXED_TEST)
            receipt.generation=result;receipt.status='succeeded';provider._verified=True
        except PublicError as exc:
            receipt.status='failed_or_unknown';receipt.error_code=exc.code
            receipt.upstream_status=getattr(exc,'upstream_status',None)
            receipt.diagnostics=getattr(exc,'response_diagnostics',None)
        except BaseException:
            receipt.status='failed_or_unknown';receipt.error_code='MODEL_RESULT_UNKNOWN'
            raise
        return receipt

@router.get('/status',response_model=ModelReadiness)
def status(request: Request,auth: AuthContext=Depends(identity)):
    authorize(auth)
    provider=request.app.state.model_provider
    value=provider.status().model_dump()
    value['generation_verified']=provider._verified
    value['stream_verified']=provider._stream_verified
    value['stream_available']=bool(provider.supported_protocol=='anthropic_messages' and provider.status().test_available)
    value['catalog_enabled']=request.app.state.model_enabled
    if value['protocol'] is not None:
        value['endpoint']=provider.configuration.endpoint
    budget=provider.budget.summary() if provider.budget is not None and hasattr(provider.budget,'summary') else None
    if budget is not None and budget.reserved_requests>=budget.max_requests:
        value['test_available']=False;value['stream_available']=False
    return ModelReadiness(**value,execution_generation=request.app.state.model_tests.generation,budget=budget)

@router.post('/test',response_model=ModelTestReceipt)
async def test(request:Request,body:ModelTestRequest,auth:AuthContext=Depends(identity)):
    authorize(auth)
    if body.request_id in request.app.state.model_stream_tests.receipts:
        raise PublicError(409,'MODEL_TEST_ID_REUSED','编号已用于流式测试，不重新调用。')
    if request.app.state.model_configuration_lock.locked():
        # A readonly replay may return its existing receipt, but never queue a fresh paid request.
        cached=request.app.state.model_tests.receipts.get(body.request_id)
        if (cached is not None and body.execution_generation==request.app.state.model_tests.generation
            and body.config_version==request.app.state.model_provider.configuration.version):
            return cached
        raise PublicError(409,'MODEL_CONNECTION_BUSY','已有模型测试或配置操作进行中；本次未排队、未调用，请等待后显式重试。')
    async with request.app.state.model_configuration_lock:
        try:
            receipt=await request.app.state.model_tests.run(request.app.state.model_provider,body)
        except asyncio.CancelledError:
            request.app.state.model_provider._verified=False
            request.app.state.model_provider._stream_verified=False
            request.app.state.model_enabled=False
            raise
        if receipt.status!='succeeded':
            request.app.state.model_provider._verified=False
            request.app.state.model_provider._stream_verified=False
            request.app.state.model_enabled=False
        return receipt


class ModelTestDiagnostics(BaseModel):
    request_id: str
    status: Literal['succeeded','failed_or_unknown','running']
    error_code: str | None = None
    upstream_status: Literal[401,403] | None = None
    diagnostics: ModelResponseDiagnostics | None = None
    sql_executed: Literal[False] = False

@router.get('/tests/{request_id}/diagnostics',response_model=ModelTestDiagnostics)
def read_diagnostics(request_id:str,request:Request,auth:AuthContext=Depends(identity)):
    authorize(auth)
    # Pure read; cannot create a request, reserve budget or invoke a model.
    receipt=request.app.state.model_tests.receipts.get(request_id)
    if receipt is None:raise PublicError(404,'MODEL_TEST_NOT_FOUND','该测试不在当前运行上下文中；未重新调用模型。')
    return ModelTestDiagnostics(**receipt.model_dump(include={'request_id','status','error_code','upstream_status','diagnostics','sql_executed'}))


class ModelConnectionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preset: Literal['ai_plan','custom']
    protocol: Literal['openai_responses','openai_chat_completions','anthropic_messages']
    endpoint: str = Field(max_length=512)
    model_id: str = Field(min_length=1,max_length=120)
    authentication: Literal['bearer','x_api_key','protocol_default'] = 'protocol_default'
    api_key: SecretStr
    execution_generation: str
    accept_fixed_test_egress: Literal[True]
    accept_estimated_cost: Literal[True]

class ModelConnectionAck(BaseModel):
    configured: bool
    execution_generation: str
    config_version: str
    storage: Literal['backend_session_memory'] = 'backend_session_memory'
    note: str

class ModelClearRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    execution_generation: str

def build_connection(body):
    from .model_provider import ModelConfiguration,MessagesProvider
    from .responses_provider import ResponsesProvider
    from .chat_model_provider import ChatCompletionsProvider
    import re
    key=body.api_key.get_secret_value()
    if not re.fullmatch(r'[\x21-\x7e]{8,4096}',key):
        raise PublicError(422,'MODEL_KEY_INVALID','Key格式无效，请重新输入；不会回显。')
    if any(key in v for v in (body.endpoint,body.model_id)):
        raise PublicError(422,'MODEL_CONFIGURATION_INVALID','不能在地址或模型字段中填写Key。')
    if body.preset=='ai_plan':
        expected=('anthropic_messages','http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','bearer')
        if (body.protocol,body.endpoint,body.authentication)!=expected:
            raise PublicError(403,'MODEL_PRESET_MISMATCH','公司AI Plan预设固定地址、协议与认证，请选择自定义公网服务配置其他厂商。')
        config=ModelConfiguration(body.endpoint,body.model_id,body.protocol,body.authentication)
    else:
        config=ModelConfiguration(body.endpoint,body.model_id,body.protocol,body.authentication,'public_https')
    if not config.valid():
        raise PublicError(422,'MODEL_CONFIGURATION_INVALID','请填写受支持协议的完整HTTPS接口地址和模型名；自定义地址不允许本机、私网、认证URL或跳转。')
    cls={'openai_responses':ResponsesProvider,'openai_chat_completions':ChatCompletionsProvider,'anthropic_messages':MessagesProvider}[body.protocol]
    return cls(config,key)

@router.post('/connection',response_model=ModelConnectionAck)
async def save_connection(request:Request,body:ModelConnectionRequest,auth:AuthContext=Depends(identity)):
    authorize(auth)
    app=request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409,'MODEL_CONNECTION_BUSY','正在测试或更新连接，请等待；现有Key未改变。')
    async with app.state.model_configuration_lock:
        if body.execution_generation!=app.state.model_tests.generation:
            raise PublicError(409,'MODEL_TEST_CONTEXT_EXPIRED','连接已变化，请刷新后再保存。')
        old=app.state.model_provider
        if old._busy:raise PublicError(409,'MODEL_CONNECTION_BUSY','模型请求进行中，不能更换Key。')
        provider=build_connection(body)
        from .model_budget import EstimatedBudget
        from pathlib import Path
        # Reuse the existing campaign, never reset costs on profile/key/vendor changes.
        provider.budget=old.budget if old.budget is not None and hasattr(old.budget,'summary') else EstimatedBudget(Path(__file__).resolve().parents[4]/'data/model-runtime')
        app.state.model_provider=provider
        app.state.model_tests=ModelTests()
        from .model_stream_routes import StreamTests
        app.state.model_stream_tests=StreamTests()
        app.state.model_enabled=False
        old.key='';old._verified=False;old._stream_verified=False
        return ModelConnectionAck(configured=True,execution_generation=app.state.model_tests.generation,
            config_version=provider.configuration.version,note='Key仅保存在本次后端内存，尚未调用模型；请显式测试，重启后重新输入。')

@router.post('/connection/clear',response_model=ModelConnectionAck)
async def clear_connection(request:Request,body:ModelClearRequest,auth:AuthContext=Depends(identity)):
    authorize(auth)
    app=request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409,'MODEL_CONNECTION_BUSY','请求进行中，请结束后清除。')
    async with app.state.model_configuration_lock:
        if body.execution_generation!=app.state.model_tests.generation:
            raise PublicError(409,'MODEL_TEST_CONTEXT_EXPIRED','连接已变化，请刷新。')
        old=app.state.model_provider
        if old._busy:raise PublicError(409,'MODEL_CONNECTION_BUSY','模型请求进行中，不能清除。')
        old.key='';old._verified=False;old._stream_verified=False
        app.state.model_tests=ModelTests()
        from .model_stream_routes import StreamTests
        app.state.model_stream_tests=StreamTests()
        app.state.model_enabled=False
        return ModelConnectionAck(configured=False,execution_generation=app.state.model_tests.generation,
            config_version=old.configuration.version,note='已清除本次会话Key，预算账本保留；旧测试失效。')


class ModelCatalogEntry(BaseModel):
    id: str
    model_id: str
    protocol: str
    config_version: str
    execution_generation: str
    enabled: bool
    available: bool
    generation_verified: bool
    stream_verified: bool = False
    tools_verified: Literal[False] = False
    structured_output_verified: Literal[False] = False
    query_available: Literal[False] = False

class ModelCatalog(BaseModel):
    models: list[ModelCatalogEntry]
    storage: Literal['backend_session_memory'] = 'backend_session_memory'
    query_available: Literal[False] = False


def budget_available(provider):
    if provider.budget is None:return False
    if hasattr(provider.budget,'summary'):
        summary=provider.budget.summary()
        return summary.reserved_requests<summary.max_requests
    return True


def current_catalog(app):
    provider=app.state.model_provider
    ready=provider.status()
    # Only this authenticated runtime's configured model; never enumerate upstream models.
    if not ready.credential_configured or ready.model_id is None:
        return ModelCatalog(models=[])
    free=not app.state.model_configuration_lock.locked() and not provider._busy
    available=bool(app.state.model_enabled and provider._verified and free and ready.test_available and budget_available(provider))
    return ModelCatalog(models=[ModelCatalogEntry(
        id=f'{app.state.model_tests.generation}:{ready.config_version}',
        model_id=ready.model_id,protocol=ready.protocol,config_version=ready.config_version,
        execution_generation=app.state.model_tests.generation,enabled=app.state.model_enabled,
        available=available,generation_verified=provider._verified,stream_verified=provider._stream_verified)])

def resolve_catalog_model(app,model_ref:str):
    # Future callers must revalidate the generation-bound selection on the server.
    entry=next((m for m in current_catalog(app).models if m.id==model_ref and m.available),None)
    if entry is None:
        raise PublicError(409,'MODEL_SELECTION_EXPIRED','模型未启用或选择已失效，请刷新并重新选择。')
    return app.state.model_provider

@router.get('/catalog',response_model=ModelCatalog)
def catalog(request:Request,auth:AuthContext=Depends(identity)):
    authorize(auth)
    return current_catalog(request.app)

class ModelEnableRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    execution_generation: str
    config_version: str
    enabled: bool = Field(strict=True)

@router.post('/connection/enabled',response_model=ModelConnectionAck)
async def enable_connection(request:Request,body:ModelEnableRequest,auth:AuthContext=Depends(identity)):
    authorize(auth)
    app=request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409,'MODEL_CONNECTION_BUSY','请求进行中，请结束后更新模型状态。')
    async with app.state.model_configuration_lock:
        provider=app.state.model_provider
        if provider._busy:
            raise PublicError(409,'MODEL_CONNECTION_BUSY','请求进行中，请结束后更新模型状态。')
        if (body.execution_generation!=app.state.model_tests.generation
            or body.config_version!=provider.configuration.version):
            raise PublicError(409,'MODEL_TEST_CONTEXT_EXPIRED','配置已变化，请刷新并重新测试。')
        if body.enabled:
            if not provider._verified or not provider.status().test_available or not budget_available(provider):
                raise PublicError(409,'MODEL_NOT_VERIFIED','当前配置尚未实测通过或不可调用，请先完成最小测试。')
            app.state.model_enabled=True
            note='已启用当前实测模型目录；选择模型不调用、不执行SQL，流式/工具仍未验证。'
        else:
            app.state.model_enabled=False
            provider._verified=False;provider._stream_verified=False
            app.state.model_tests=ModelTests()
            from .model_stream_routes import StreamTests
            app.state.model_stream_tests=StreamTests()
            note='已禁用模型并使旧测试/选择失效；Key仅后台内存保留，重新启用须重测，预算未清空。'
        return ModelConnectionAck(configured=bool(provider.key),execution_generation=app.state.model_tests.generation,
            config_version=provider.configuration.version,note=note)
