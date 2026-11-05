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
        app.state.model_preset=body.preset
        old_registry=getattr(app.state,'model_registry',None)
        app.state.model_registry=AdditionalModelRegistry(
            provider.key, body.preset, body.endpoint, body.protocol, body.authentication,
            provider.configuration.access_policy, provider.budget, body.model_id,
            app.state.model_tests.generation)
        old.key='';old._verified=False;old._stream_verified=False
        if old_registry is not None:
            old_registry.clear()
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
        old_registry=getattr(app.state,'model_registry',None)
        if old_registry is not None:
            old_registry.clear()
        app.state.model_registry=None
        app.state.model_preset=None
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
    label: str = ''
    source: Literal['personal_api','ai_plan'] = 'personal_api'
    default: bool = False
    context_window: int | None = None
    price_status: Literal['unknown','configured'] = 'unknown'
    price_note: str = '价格未知'
    note: str = ''

class ModelCatalog(BaseModel):
    models: list[ModelCatalogEntry]
    default_model_id: str | None = None
    storage: Literal['backend_session_memory'] = 'backend_session_memory'
    query_available: Literal[False] = False


def budget_available(provider):
    if provider.budget is None:return False
    if hasattr(provider.budget,'summary'):
        summary=provider.budget.summary()
        return summary.reserved_requests<summary.max_requests
    return True


class AdditionalModel:
    """One user-added model sharing the current connection's endpoint/auth/budget."""
    def __init__(self, model_id: str, label: str, provider, tests: ModelTests):
        self.model_id = model_id
        self.label = label or model_id
        self.provider = provider
        self.tests = tests
        self.enabled = False


class AdditionalModelRegistry:
    """Server-side multi-model catalog for one approved connection.

    It never enumerates upstream models and never stores a key in browser-visible
    state. Additional models share the connection key but have independent
    verification/enable state.
    """
    def __init__(self, key, preset, endpoint, protocol, authentication, access_policy, budget, primary_model_id, generation):
        self.key = key
        self.preset = preset
        self.endpoint = endpoint
        self.protocol = protocol
        self.authentication = authentication
        self.access_policy = access_policy
        self.budget = budget
        self.primary_model_id = primary_model_id
        self.generation = generation
        self.entries: dict[str, AdditionalModel] = {}
        self.lock = asyncio.Lock()

    @property
    def source(self):
        return 'ai_plan' if self.preset == 'ai_plan' else 'personal_api'

    def _build_provider(self, model_id):
        from .model_provider import ModelConfiguration, MessagesProvider
        from .responses_provider import ResponsesProvider
        from .chat_model_provider import ChatCompletionsProvider
        config = ModelConfiguration(self.endpoint, model_id, self.protocol, self.authentication, self.access_policy)
        if not config.valid():
            raise PublicError(422, 'MODEL_CONFIGURATION_INVALID', '模型名或当前连接配置不合法。')
        cls = {'openai_responses': ResponsesProvider, 'openai_chat_completions': ChatCompletionsProvider, 'anthropic_messages': MessagesProvider}[self.protocol]
        provider = cls(config, self.key)
        provider.budget = self.budget
        return provider

    def add(self, model_id, label=''):
        if model_id == self.primary_model_id:
            raise PublicError(409, 'MODEL_ALREADY_PRIMARY', '该模型已是当前连接的主模型。')
        if model_id in self.entries:
            raise PublicError(409, 'MODEL_ALREADY_ADDED', '该模型已在当前目录中。')
        if not model_id or len(model_id) > 120 or any(ch in model_id for ch in ('\n', '\r', '\t')):
            raise PublicError(422, 'MODEL_ID_INVALID', '模型名无效。')
        if self.key and self.key in model_id:
            raise PublicError(422, 'MODEL_CONFIGURATION_INVALID', '不能在模型名中填写Key。')
        provider = self._build_provider(model_id)
        tests = ModelTests()
        tests.generation = self.generation
        entry = AdditionalModel(model_id, label, provider, tests)
        self.entries[model_id] = entry
        return entry

    def remove(self, model_id):
        entry = self.entries.pop(model_id, None)
        if entry is None:
            raise PublicError(404, 'MODEL_NOT_IN_CATALOG', '该模型不在当前目录中。')
        if entry.provider._busy:
            raise PublicError(409, 'MODEL_CONNECTION_BUSY', '模型请求进行中，不能移除。')
        entry.provider.key = ''
        entry.provider._verified = False
        entry.provider._stream_verified = False
        entry.enabled = False
        return entry

    def clear(self):
        for entry in self.entries.values():
            entry.provider.key = ''
            entry.provider._verified = False
            entry.provider._stream_verified = False
            entry.enabled = False
        self.entries.clear()
        self.key = ''

    def disable_all(self):
        for entry in self.entries.values():
            entry.enabled = False
            entry.provider._verified = False
            entry.provider._stream_verified = False
            entry.tests = ModelTests()
            entry.tests.generation = self.generation

    def reset_generation(self, generation):
        self.generation = generation
        for entry in self.entries.values():
            entry.enabled = False
            entry.provider._verified = False
            entry.provider._stream_verified = False
            entry.tests = ModelTests()
            entry.tests.generation = generation

    def ref(self, entry):
        return f'{self.generation}:{entry.provider.configuration.version}:{entry.model_id}'

    def catalog_entries(self, app):
        models = []
        free = not app.state.model_configuration_lock.locked()
        for entry in self.entries.values():
            provider = entry.provider
            ready = provider.status()
            available = bool(entry.enabled and provider._verified and free and not provider._busy and ready.test_available and budget_available(provider))
            models.append(ModelCatalogEntry(
                id=self.ref(entry), model_id=entry.model_id, protocol=provider.configuration.protocol,
                config_version=provider.configuration.version, execution_generation=self.generation,
                enabled=entry.enabled, available=available, generation_verified=provider._verified,
                stream_verified=provider._stream_verified, label=entry.label, source=self.source,
                default=False, note='手动添加；独立测试/启用' if not entry.enabled else '已启用；仅模型连接',
            ))
        return models

    def find(self, app, model_ref, ignore_busy=False):
        for entry in self.entries.values():
            if self.ref(entry) != model_ref:
                continue
            provider = entry.provider
            ready = provider.status()
            if not (entry.enabled and provider._verified and ready.test_available and budget_available(provider)):
                return None
            if not ignore_busy and provider._busy:
                return None
            return provider
        return None


def current_catalog(app):
    provider=app.state.model_provider
    ready=provider.status()
    models=[]
    default_model_id=None
    # Only this authenticated runtime's configured models; never enumerate upstream models.
    if ready.credential_configured and ready.model_id is not None:
        free=not app.state.model_configuration_lock.locked() and not provider._busy
        available=bool(app.state.model_enabled and provider._verified and free and ready.test_available and budget_available(provider))
        source='ai_plan' if getattr(app.state,'model_preset',None)=='ai_plan' else 'personal_api'
        models.append(ModelCatalogEntry(
            id=f'{app.state.model_tests.generation}:{ready.config_version}',
            model_id=ready.model_id,protocol=ready.protocol,config_version=ready.config_version,
            execution_generation=app.state.model_tests.generation,enabled=app.state.model_enabled,
            available=available,generation_verified=provider._verified,stream_verified=provider._stream_verified,
            label=ready.model_id,source=source,default=True,
            note='MVP 默认模型' if ready.model_id=='deepseek-v4.1-flash' else '当前主模型'))
        default_model_id=ready.model_id
    registry=getattr(app.state,'model_registry',None)
    if registry is not None:
        models.extend(registry.catalog_entries(app))
    return ModelCatalog(models=models, default_model_id=default_model_id)

def resolve_catalog_model(app,model_ref:str):
    # Future callers must revalidate the generation-bound selection on the server.
    entry=next((m for m in current_catalog(app).models if m.id==model_ref and m.available),None)
    if entry is None:
        raise PublicError(409,'MODEL_SELECTION_EXPIRED','模型未启用或选择已失效，请刷新并重新选择。')
    provider=app.state.model_provider
    if model_ref==f'{app.state.model_tests.generation}:{provider.configuration.version}':
        return provider
    registry=getattr(app.state,'model_registry',None)
    if registry is not None:
        selected=registry.find(app,model_ref)
        if selected is not None:
            return selected
    raise PublicError(409,'MODEL_SELECTION_EXPIRED','模型未启用或选择已失效，请刷新并重新选择。')

def resolve_bound_model(app,model_ref:str):
    """Validate an already-bound task selection while the config lock is held.

    The caller owns the connection lock, so the busy flag must not be used here;
    it is set by the model call itself after this check.
    """
    provider=app.state.model_provider
    if model_ref==f'{app.state.model_tests.generation}:{provider.configuration.version}':
        if not app.state.model_enabled or not provider._verified:
            raise PublicError(409,'MODEL_SELECTION_EXPIRED','模型未启用或选择已失效，请刷新并重新选择。')
        return provider
    registry=getattr(app.state,'model_registry',None)
    if registry is not None:
        selected=registry.find(app,model_ref,ignore_busy=True)
        if selected is not None:
            return selected
    raise PublicError(409,'MODEL_SELECTION_EXPIRED','模型未启用或选择已失效，请刷新并重新选择。')

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
            registry=getattr(app.state,'model_registry',None)
            if registry is not None:
                registry.reset_generation(app.state.model_tests.generation)
            from .model_stream_routes import StreamTests
            app.state.model_stream_tests=StreamTests()
            note='已禁用模型并使旧测试/选择失效；Key仅后台内存保留，重新启用须重测，预算未清空。'
        return ModelConnectionAck(configured=bool(provider.key),execution_generation=app.state.model_tests.generation,
            config_version=provider.configuration.version,note=note)


class ModelAddRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    execution_generation: str
    config_version: str
    model_id: str = Field(min_length=1,max_length=120)
    label: str = Field(default='',max_length=120)

class ModelRemoveRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    execution_generation: str
    config_version: str
    model_id: str = Field(min_length=1,max_length=120)

class ModelTargetTestRequest(ModelTestRequest):
    model_id: str = Field(min_length=1,max_length=120)

class ModelTargetEnableRequest(ModelEnableRequest):
    model_id: str = Field(min_length=1,max_length=120)


def _registry_or_404(app):
    registry = getattr(app.state, 'model_registry', None)
    if registry is None:
        raise PublicError(409, 'MODEL_CONNECTION_REQUIRED', '请先保存模型连接，再添加模型。')
    return registry


@router.post('/connection/models', response_model=ModelCatalogEntry)
async def add_catalog_model(request: Request, body: ModelAddRequest, auth: AuthContext = Depends(identity)):
    authorize(auth)
    app = request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409, 'MODEL_CONNECTION_BUSY', '正在测试或更新连接，请等待后再添加模型。')
    async with app.state.model_configuration_lock:
        provider = app.state.model_provider
        if (body.execution_generation != app.state.model_tests.generation
                or body.config_version != provider.configuration.version):
            raise PublicError(409, 'MODEL_TEST_CONTEXT_EXPIRED', '连接已变化，请刷新后再添加模型。')
        registry = _registry_or_404(app)
        entry = registry.add(body.model_id, body.label)
        match = next((m for m in current_catalog(app).models if m.id == registry.ref(entry)), None)
        if match is None:
            raise PublicError(503, 'MODEL_CATALOG_INCONSISTENT', '模型已加入但目录未生成，请刷新。')
        return match


@router.post('/connection/models/remove', response_model=ModelConnectionAck)
async def remove_catalog_model(request: Request, body: ModelRemoveRequest, auth: AuthContext = Depends(identity)):
    authorize(auth)
    app = request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409, 'MODEL_CONNECTION_BUSY', '正在测试或更新连接，请等待后再移除模型。')
    async with app.state.model_configuration_lock:
        provider = app.state.model_provider
        if (body.execution_generation != app.state.model_tests.generation
                or body.config_version != provider.configuration.version):
            raise PublicError(409, 'MODEL_TEST_CONTEXT_EXPIRED', '连接已变化，请刷新后再移除模型。')
        registry = _registry_or_404(app)
        registry.remove(body.model_id)
        return ModelConnectionAck(configured=bool(provider.key), execution_generation=app.state.model_tests.generation,
            config_version=provider.configuration.version, note='已移除该模型并使旧测试/选择失效；主模型不变。')


@router.post('/models/test', response_model=ModelTestReceipt)
async def test_catalog_model(request: Request, body: ModelTargetTestRequest, auth: AuthContext = Depends(identity)):
    authorize(auth)
    app = request.app
    if body.request_id in app.state.model_stream_tests.receipts:
        raise PublicError(409, 'MODEL_TEST_ID_REUSED', '编号已用于流式测试，不重新调用。')
    if app.state.model_configuration_lock.locked():
        raise PublicError(409, 'MODEL_CONNECTION_BUSY', '已有模型测试或配置操作进行中；本次未排队、未调用，请等待后显式重试。')
    async with app.state.model_configuration_lock:
        registry = _registry_or_404(app)
        entry = registry.entries.get(body.model_id)
        if entry is None:
            raise PublicError(404, 'MODEL_NOT_IN_CATALOG', '该模型不在当前目录中。')
        if (body.execution_generation != app.state.model_tests.generation
                or body.config_version != entry.provider.configuration.version):
            raise PublicError(409, 'MODEL_TEST_CONTEXT_EXPIRED', '模型配置已变化，请刷新状态；不会重提旧请求。')
        if entry.provider._busy:
            raise PublicError(409, 'MODEL_CONNECTION_BUSY', '该模型请求进行中，请等待。')
        try:
            receipt = await entry.tests.run(entry.provider, body)
        except asyncio.CancelledError:
            entry.enabled = False
            entry.provider._verified = False
            entry.provider._stream_verified = False
            raise
        if receipt.status != 'succeeded':
            entry.enabled = False
            entry.provider._verified = False
            entry.provider._stream_verified = False
        return receipt


@router.post('/models/enabled', response_model=ModelConnectionAck)
async def enable_catalog_model(request: Request, body: ModelTargetEnableRequest, auth: AuthContext = Depends(identity)):
    authorize(auth)
    app = request.app
    if app.state.model_configuration_lock.locked():
        raise PublicError(409, 'MODEL_CONNECTION_BUSY', '请求进行中，请结束后更新模型状态。')
    async with app.state.model_configuration_lock:
        registry = _registry_or_404(app)
        entry = registry.entries.get(body.model_id)
        if entry is None:
            raise PublicError(404, 'MODEL_NOT_IN_CATALOG', '该模型不在当前目录中。')
        if (body.execution_generation != app.state.model_tests.generation
                or body.config_version != entry.provider.configuration.version):
            raise PublicError(409, 'MODEL_TEST_CONTEXT_EXPIRED', '配置已变化，请刷新并重新测试。')
        if body.enabled:
            if not entry.provider._verified or not entry.provider.status().test_available or not budget_available(entry.provider):
                raise PublicError(409, 'MODEL_NOT_VERIFIED', '该模型尚未实测通过或不可调用，请先完成最小测试。')
            entry.enabled = True
            note = '已启用该模型；选择不调用、不执行SQL，工具/业务问数仍受治理门禁。'
        else:
            entry.enabled = False
            entry.provider._verified = False
            entry.provider._stream_verified = False
            entry.tests = ModelTests()
            entry.tests.generation = registry.generation
            note = '已禁用该模型并使旧测试/选择失效；Key仍在后端内存。'
        return ModelConnectionAck(configured=bool(app.state.model_provider.key),
            execution_generation=app.state.model_tests.generation,
            config_version=entry.provider.configuration.version, note=note)
