from datetime import datetime, timezone
from uuid import uuid4
import logging
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import identity, DevelopmentIdentityProvider, PublicError
from .config import Settings
from .contracts import (AuthContext, QuerySpec, Task, TaskStatus, ErrorEnvelope, SessionResponse,
                        CapabilitiesResponse, ModuleCapability, ValidationResponse, DatasetAsset, ConnectorCapability)
from .model_provider import MessagesProvider, ModelConfiguration
from .model_routes import router as model_router, ModelTests
from .model_stream_routes import router as stream_router, StreamTests
from .agent_routes import router as agent_router
from .semantic_store import SemanticStore
from .semantic_routes import router as semantic_router
from .repository import MemoryTaskRepository
from .source_profiles import SourceStore
from .remote_access import RemoteAccessPolicy
from .source_routes import router as source_router
from .connector_routes import ConnectorManager, connector_lifespan, router as connector_router

MODULES = [("query", "取数工作台", "M04"), ("connectors", "连接器", "M02"),
           ("knowledge", "知识库", "M03"), ("assets", "数据资产", "M05"),
           ("dashboards", "可视化看板", "M06"), ("reports", "分析报告", "M07")]
CONTRACTS = {m.__name__: m for m in (QuerySpec, Task, DatasetAsset, ConnectorCapability)}

def create_app(settings: Settings | None = None):
    cfg = settings or Settings.from_env()
    @asynccontextmanager
    async def lifespan(app):
        from .retention_runner import RetentionRunner
        runner=RetentionRunner(app.state.sources) if cfg.retention_cleanup else None
        app.state.sources.retention_runner=runner
        try:
            async with connector_lifespan(app):
                if runner:await runner.start()
                try:yield
                finally:
                    if runner:await runner.stop()
        finally:
            if runner:await runner.stop()
            if app.state.agent is not None:await app.state.agent.close()
            await app.state.model_stream_tests.close()
    app = FastAPI(title="Data Workspace API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = cfg
    app.state.connector = ConnectorManager(cfg.owned_warehouse)
    app.include_router(connector_router)
    app.include_router(source_router)
    app.include_router(semantic_router)
    app.state.semantics=SemanticStore()
    app.include_router(agent_router)
    app.state.sdk_web_test_base_url = cfg.sdk_web_test_base_url
    if cfg.mode=='development' and cfg.dev_identity:
        from .agent_hybrid import HybridAgentService
        app.state.agent=HybridAgentService(app)
    else:
        app.state.agent=None
    app.include_router(model_router)
    app.include_router(stream_router)
    app.state.model_stream_tests=StreamTests()
    app.state.model_tests=ModelTests()
    app.state.model_enabled=False
    app.state.model_configuration_lock=__import__("asyncio").Lock()
    app.state.model_provider=MessagesProvider.from_env() if cfg.mode == "development" and cfg.dev_identity else MessagesProvider(ModelConfiguration(), "")
    app.state.model_preset=None
    app.state.model_registry=None
    if app.state.model_provider.key and app.state.model_provider.configuration.valid():
        from .model_routes import AdditionalModelRegistry
        preset='ai_plan' if app.state.model_provider.configuration.endpoint=='http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages' else 'custom'
        app.state.model_preset=preset
        app.state.model_registry=AdditionalModelRegistry(
            app.state.model_provider.key,preset,app.state.model_provider.configuration.endpoint,
            app.state.model_provider.configuration.protocol,app.state.model_provider.configuration.authentication,
            app.state.model_provider.configuration.access_policy,app.state.model_provider.budget,
            app.state.model_provider.configuration.model_id,app.state.model_tests.generation)
    app.state.sources=SourceStore(remote_policy=RemoteAccessPolicy.from_env())
    app.state.identity_provider = DevelopmentIdentityProvider()
    app.state.repository = MemoryTaskRepository()
    app.state.upload_admission = BoundedSemaphore(2)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    def error(request, status, code, message):
        return JSONResponse(status_code=status, content=ErrorEnvelope(code=code, safe_message=message,
                            trace_id=getattr(request.state, "trace_id", str(uuid4()))).model_dump())

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        request.state.trace_id = str(uuid4())
        origins = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, cfg.port)}
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return error(request, 403, "ORIGIN_DENIED", "此请求来源未获授权。")
        if request.method not in {"GET", "HEAD"} and request.headers.get("x-workspace-request") != "1":
            return error(request, 403, "REQUEST_DENIED", "请求缺少工作台校验头。")
        admitted=False
        try:
            if request.method=='POST' and request.url.path=='/api/v1/source-profiles/upload':
                # Bound request-body concurrency before reading/spooling any upload.
                try:request.app.state.sources.authorize(identity(request))
                except PublicError as exc:return error(request,exc.status,exc.code,exc.message)
                if not request.app.state.upload_admission.acquire(blocking=False):
                    return error(request,429,'UPLOAD_BUSY','上传已达本机并发上限，请等待当前上传结束后重试；未接收本次文件。')
                admitted=True
            if request.url.path.startswith("/api/v1/agent") or request.url.path.startswith("/api/v1/semantics") or request.url.path in {"/api/v1/source-profiles/upload", "/api/v1/source-profiles/import-config", "/api/v1/source-profiles/test", "/api/v1/model-service/test", "/api/v1/model-service/stream-test", "/api/v1/model-service/connection", "/api/v1/model-service/connection/clear", "/api/v1/model-service/connection/enabled"}:
                if request.url.path.startswith('/api/v1/model-service/connection'):
                    try:identity(request)
                    except PublicError as exc:return error(request,exc.status,exc.code,exc.message)
                # Bound the multipart/secret body before its parser may spool to disk.
                limit = 8192 if request.url.path.startswith("/api/v1/agent") else 32768 if request.url.path.startswith("/api/v1/semantics") else 8192 if request.url.path.startswith('/api/v1/model-service/connection') else 21 * 1024 * 1024 if request.url.path.endswith("/upload") else 64 * 1024 if request.url.path.endswith("/test") else 128 * 1024
                try:
                    declared = int(request.headers.get("content-length", "0"))
                except ValueError:
                    return error(request, 400, "INVALID_UPLOAD", "上传请求长度无效。")
                if declared > limit:
                    return error(request, 413, "UPLOAD_TOO_LARGE", "上传超过允许大小，请缩小文件。")
                chunks=[];total=0
                async for chunk in request.stream():
                    total += len(chunk)
                    if total > limit:
                        return error(request, 413, "UPLOAD_TOO_LARGE", "上传超过允许大小，请缩小文件。")
                    chunks.append(chunk)
                # Starlette caches the body for the downstream multipart parser.
                request._body = b"".join(chunks)
            try:
                response = await call_next(request)
            except Exception as exc:
                # Do not log request bodies, credential values or raw exception messages.
                logging.getLogger("workspace").error("request_failed trace_id=%s class=%s", request.state.trace_id, type(exc).__name__)
                response = error(request, 500, "INTERNAL_ERROR", "服务暂时不可用，请使用追踪编号排查。")
            response.headers["X-Trace-ID"] = request.state.trace_id
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        finally:
            if admitted:request.app.state.upload_admission.release()

    @app.exception_handler(PublicError)
    async def known(request, exc):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return error(request, 422, "INVALID_REQUEST", "输入不符合接口要求，请检查配置、字段和版本。")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "HTTP_ERROR", "请求的接口不可用。")

    @app.get("/health/live")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/v1/session", response_model=SessionResponse)
    def session(request: Request, auth: AuthContext = Depends(identity)):
        return SessionResponse(identity=auth, storage="memory_development", warning="仅限本地开发；任务在内存中，重启丢失。专属合成数据预览已接入；自然语言Agent与正式认证未接入。" if request.app.state.connector.verified else "仅限本地开发；任务保存在内存，重启会丢失。真实认证与数仓执行未接入。")

    @app.get("/api/v1/capabilities", response_model=CapabilitiesResponse)
    def capabilities(request: Request, auth: AuthContext = Depends(identity)):
        manager=request.app.state.connector
        allowed=(auth.mode,auth.tenant_id,auth.principal_id)==("development","local-workspace","local-developer")
        ready=allowed and manager.verified
        connectors=[ConnectorCapability(connector_id="owned-synthetic",configured=True,sql_dialect="duckdb",metadata="supported" if ready else "unknown",asynchronous="unsupported",cancel="unsupported",query_cost="unsupported",column_acl="unknown")] if allowed and manager.enabled else []
        return CapabilitiesResponse(modules=[ModuleCapability(id=i,label=label,available=(ready and i=="connectors") or (allowed and i in {"knowledge","query"}),milestone=m) for i,label,m in MODULES], connectors=connectors)

    @app.post("/api/v1/query-spec/validate", response_model=ValidationResponse)
    def validate_spec(spec: QuerySpec, auth: AuthContext = Depends(identity)):
        return ValidationResponse(query_spec=spec, note="数据契约通过结构校验；业务口径、字段权限及SQL执行尚未验证。")

    @app.post("/api/v1/tasks", response_model=Task, status_code=201)
    def create_task(spec: QuerySpec, request: Request, auth: AuthContext = Depends(identity)):
        stamp = datetime.now(timezone.utc)
        task = Task(task_id=str(uuid4()),tenant_id=auth.tenant_id,principal_id=auth.principal_id,
                    query_spec=spec,status=TaskStatus.CREATED,created_at=stamp,updated_at=stamp,trace_id=request.state.trace_id)
        task.transition(TaskStatus.FAILED, error=ErrorEnvelope(code="EXECUTOR_NOT_CONFIGURED",
                        safe_message="任务已登记，但数仓执行器尚未接入；未运行SQL、未生成数据。",trace_id=task.trace_id))
        return request.app.state.repository.add(task)

    @app.get("/api/v1/tasks/{task_id}", response_model=Task)
    def get_task(task_id: str, request: Request, auth: AuthContext = Depends(identity)):
        return request.app.state.repository.get(task_id, auth)

    @app.post("/api/v1/tasks/{task_id}/cancel", response_model=Task)
    def cancel_task(task_id: str, request: Request, auth: AuthContext = Depends(identity)):
        task = request.app.state.repository.get(task_id, auth)
        # M01 has no running executor, so all registered tasks are already terminal.
        raise PublicError(409, "TASK_TERMINAL", "任务已终止，无运行中的SQL可取消。")

    @app.get("/api/v1/contracts/{name}")
    def get_contract(name: str, auth: AuthContext = Depends(identity)):
        if name not in CONTRACTS:
            raise PublicError(404, "CONTRACT_NOT_FOUND", "数据契约不存在。")
        return CONTRACTS[name].model_json_schema()

    return app

if __name__ == "__main__":
    import uvicorn
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, proxy_headers=False, access_log=False)
