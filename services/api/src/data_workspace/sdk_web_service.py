"""Web task service for the governed Claude Agent SDK runner.

The browser only ever supplies a server-catalog model reference. This service
resolves that reference, freezes the semantic/source/schema binding, reserves
the approved task budget, launches the isolated runner and keeps the existing
confirmation, idempotency, QA and receipt gates at the API boundary.
"""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from .agent_contracts import AgentConfirm, AgentRequest, AgentTask, AgentClarify, AgentClarificationTurn
from .auth import PublicError
from .sdk_dialogue import public_dialogue
from .contracts import AuthContext
from .model_routes import resolve_bound_model, resolve_catalog_model
from .semantic_metadata import read_schema
from .warehouse.aggregate_contract import AggregateRequest, AggregateResult, schema_hash

try:  # The SDK package may be absent in a non-SDK deployment; do not fake success.
    from .sdk_agent_runner import (
        APPROVED_SDK_BASE_URL,
        REJECTED_MODEL_ALIAS,
        minimal_runner_environment,
    )
    from .sdk_process import SdkProcessLimits, run_sdk_process

    SDK_IMPORT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only on an unsupported install
    APPROVED_SDK_BASE_URL = ""
    REJECTED_MODEL_ALIAS = "deepseek-v4-1-flash-261017"
    minimal_runner_environment = None
    SdkProcessLimits = None
    run_sdk_process = None
    SDK_IMPORT_AVAILABLE = False

ENGINE = "claude_agent_sdk_skills_v1"
CONFIRMATION_TIMEOUT_SECONDS = 600
MODEL_WALL_CLOCK_SECONDS = 600
PROCESS_WALL_SECONDS = MODEL_WALL_CLOCK_SECONDS + CONFIRMATION_TIMEOUT_SECONDS + 60

EVENT_LABELS = {
    "TABLES_DISCOVERED": "已列出当前授权单表",
    "FIELDS_DISCOVERED": "已检索实际授权字段",
    "TOPIC_TEMPLATE_LOADED": "已加载批准口径派生的L2单表模板",
    "ROUTE_READY": "Skill路由完成",
    "METADATA_READ": "已读取授权元数据",
    "PLAN_READY": "模型计划已通过确定性字段与指标校验",
    "CLARIFICATION": "需要补充关键口径",
    "CLARIFICATION_LIMIT": "澄清次数已达上限，未执行；请整理口径后新建问题",
    "CLARIFICATION_TIMED_OUT": "澄清等待已超时，未执行；请整理口径后新建问题",
    "CLARIFICATION_ANSWERED": "已收到补充口径，继续同一任务规划",
    "AWAITING_CONFIRMATION": "计划已生成，等待用户确认口径与执行",
    "CONFIRMED": "已获得当前用户确认",
    "EXECUTING": "受治理MCP正在执行完整输入聚合",
    "CHECKING": "收到执行回执，正在校验结果质量",
    "PUBLISHED": "结果已通过执行与质量回执发布",
    "FAILED": "任务未完成，未发布结果",
}


@dataclass
class _SdkTaskRecord:
    owner: str
    auth: AuthContext
    body: AgentRequest
    fingerprint: str
    task: AgentTask
    provider_key: str = field(repr=False, default="")
    provider_endpoint: str = ""
    budget: object = None
    model_id: str = ""
    config_version: str = ""
    semantic: object = None
    source: dict = field(default_factory=dict)
    database: Path | None = None
    source_id: str = ""
    source_version: int = 0
    semantic_state_revision: int = 0
    semantic_fingerprint: str = ""
    warehouse_schema_hash: str = ""
    binding_hash: str = ""
    runtime_root: Path | None = None
    control: Path | None = None
    config_path: Path | None = None
    output_path: Path | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    state_path: Path | None = None
    confirmation_path: Path | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    budget_ids: list[str] = field(default_factory=list)
    clarification_answers: dict = field(default_factory=dict)
    confirmation_id: str | None = None
    submitted: bool = False
    terminal: bool = False
    invalidated: bool = False
    invalid_reason: str | None = None
    cancelled: bool = False
    worker: asyncio.Task | None = None


class SdkWebAgentService:
    def __init__(self, app):
        self.app = app
        self.generation = str(uuid4())
        self.tasks: dict[str, AgentTask] = {}
        self.records: dict[str, _SdkTaskRecord] = {}
        self.keys: dict[tuple[str, str], str] = {}
        self._start_lock = asyncio.Lock()
        self._confirm_lock = asyncio.Lock()
        self._available = SDK_IMPORT_AVAILABLE

    # -- common service surface ------------------------------------------------
    def auth(self, auth):
        self.app.state.semantics.authorize(auth)

    def capabilities(self):
        return {
            "available": self._available,
            "sdk_web_binding": self._available,
            "engines": [ENGINE] if self._available else [],
        }

    def _owner(self, auth):
        return self.app.state.sources.owner(auth)

    def _record(self, auth, task_id):
        record = self.records.get(task_id)
        if record is None or record.owner != self._owner(auth):
            raise PublicError(404, "AGENT_TASK_NOT_FOUND", "任务不在当前本机会话，请不要重提未知执行。")
        return record

    def get(self, auth, task_id):
        self.auth(auth)
        record = self._record(auth, task_id)
        if not record.terminal and not record.invalidated:
            self._invalidate_if_needed(record)
        return record.task

    def list(self, auth):
        self.auth(auth)
        owner = self._owner(auth)
        result = []
        for record in self.records.values():
            if record.owner != owner:
                continue
            if not record.terminal and not record.invalidated:
                self._invalidate_if_needed(record)
            result.append(record.task)
        return result

    # -- start -----------------------------------------------------------------
    async def start(self, auth, body: AgentRequest):
        self.auth(auth)
        if not self._available:
            raise PublicError(503, "SDK_UNAVAILABLE", "当前部署未安装受控Claude Agent SDK，未启动问数。")
        try:
            if body.conversation_id and str(UUID(body.conversation_id)) != body.conversation_id:
                raise ValueError()
            if str(UUID(body.request_id)) != body.request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise PublicError(422, "AGENT_REQUEST_INVALID", "请求或会话编号无效。") from None
        digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        async with self._start_lock:
            return await self._start_locked(auth, body, digest)

    async def _start_locked(self, auth, body, digest):
        owner = self._owner(auth)
        key = (owner, body.request_id)
        if key in self.keys:
            task_id = self.keys[key]
            record = self.records[task_id]
            if record.fingerprint != digest:
                raise PublicError(409, "AGENT_REQUEST_CONFLICT", "同一编号不能用于不同问题。")
            return record.task
        if len(self.tasks) >= 60:
            raise PublicError(409, "AGENT_CAPACITY", "当前会话任务到达上限，请保存证据后新建后端会话。")
        if any(not record.terminal and record.task.phase in ("PLANNING", "VALIDATING", "EXECUTING", "CHECKING") for record in self.records.values()):
            raise PublicError(409, "AGENT_BUSY", "已有任务处理，请等待。")

        provider = resolve_catalog_model(self.app, body.model_ref)
        if not self._eligible(provider):
            raise PublicError(409, "SDK_MODEL_NOT_ELIGIBLE", "当前模型不在受控SDK问数范围；未调用模型。")
        value = self.app.state.semantics.version(auth, body.semantic_version_id)
        if value.state != "published_recheck_required":
            raise PublicError(409, "SEMANTIC_DISABLED", "请选择启用的最新语义版本。")
        if value.contract.source_id not in body.selected_source_refs:
            raise PublicError(403, "AGENT_SOURCE_DENIED", "语义定义的数据源不在本次选择范围。")
        source = self.app.state.sources.get(auth, value.contract.source_id)
        if not source["enabled"]:
            raise PublicError(409, "SOURCE_DISABLED", "数据源已停用。")
        if source["kind"] != "local_file":
            raise PublicError(409, "AGENT_SOURCE_UNSUPPORTED", "当前受限聚合只支持本机快照MCP；旧HTTP/PG仅导航，不自动扩权。")
        if not body.question.strip() or provider.key in body.question or provider.key in value.contract.model_dump_json():
            raise PublicError(422, "AGENT_INPUT_INVALID", "请勿在问题中填写密钥或空白。")
        budget = provider.budget
        if budget is None or not hasattr(budget, "reserve_sdk_task"):
            raise PublicError(409, "MODEL_BUDGET_UNVERIFIED", "尚无可靠费用控制，未调用模型。")
        budget_ids = await budget.reserve_sdk_task()

        task_id = str(uuid4())
        semantic_fingerprint = value.schema_snapshot.fingerprint
        warehouse_hash = schema_hash({
            "table": value.schema_snapshot.table_name,
            "fields": [{"name": column.name, "type": column.data_type} for column in value.schema_snapshot.columns],
        })
        binding_hash = self._binding_hash(
            task_id=task_id,
            body=body,
            provider=provider,
            value=value,
            semantic_fingerprint=semantic_fingerprint,
            warehouse_schema_hash=warehouse_hash,
        )
        runtime_root = Path(tempfile.mkdtemp(prefix="workspace-sdk-web-")).resolve()
        project_root = Path(__file__).resolve().parents[4]
        if runtime_root == project_root or project_root in runtime_root.parents:
            shutil.rmtree(runtime_root, ignore_errors=True)
            raise PublicError(503, "SDK_RUNTIME_UNSAFE", "SDK运行目录不在项目外，未启动。")
        control = runtime_root / "control"
        control.mkdir(parents=True, exist_ok=False)
        task = AgentTask(
            conversation_id=body.conversation_id,
            id=task_id,
            request_id=body.request_id,
            execution_generation=self.generation,
            phase="PLANNING",
            model_ref=body.model_ref,
            semantic_version_id=body.semantic_version_id,
            engine=ENGINE,
        )
        record = _SdkTaskRecord(
            owner=owner,
            auth=auth,
            body=body,
            fingerprint=digest,
            task=task,
            provider_key=provider.key,
            provider_endpoint=provider.configuration.endpoint,
            budget=budget,
            model_id=provider.configuration.model_id,
            config_version=provider.configuration.version,
            semantic=value,
            source=source,
            database=Path(source["database_path"]),
            source_id=value.contract.source_id,
            source_version=value.schema_snapshot.source_version,
            semantic_state_revision=value.state_revision,
            semantic_fingerprint=semantic_fingerprint,
            warehouse_schema_hash=warehouse_hash,
            binding_hash=binding_hash,
            runtime_root=runtime_root,
            control=control,
            config_path=control / "config.json",
            output_path=control / "output.json",
            stdout_path=control / "runner-stdout.txt",
            stderr_path=control / "runner-stderr.txt",
            state_path=runtime_root / task_id / "state.json",
            confirmation_path=runtime_root / task_id / "confirmation.json",
            budget_ids=budget_ids,
        )
        self.tasks[task_id] = task
        self.records[task_id] = record
        self.keys[key] = task_id
        record.worker = asyncio.create_task(self._run(task_id))
        return task

    @staticmethod
    def _eligible(provider):
        configuration = provider.configuration
        return bool(
            configuration.protocol == "anthropic_messages"
            and configuration.endpoint == APPROVED_SDK_BASE_URL + "/v1/messages"
            and configuration.model_id != REJECTED_MODEL_ALIAS
            and provider.key
        )

    def _binding_hash(self, *, task_id, body, provider, value, semantic_fingerprint, warehouse_schema_hash):
        payload = {
            "task_id": task_id,
            "model_ref": body.model_ref,
            "model_config_version": provider.configuration.version,
            "model_id": provider.configuration.model_id,
            "semantic_version_id": body.semantic_version_id,
            "semantic_state_revision": value.state_revision,
            "source_id": value.contract.source_id,
            "source_version": value.schema_snapshot.source_version,
            "semantic_fingerprint": semantic_fingerprint,
            "warehouse_schema_hash": warehouse_schema_hash,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    # -- runner lifecycle ------------------------------------------------------
    async def _run(self, task_id):
        record = self.records[task_id]
        try:
            self._write_config(record)
            runner_task = asyncio.create_task(asyncio.to_thread(self._run_process, record))
            try:
                while not runner_task.done():
                    await asyncio.sleep(0.1)
                    self._sync_state(record)
                    if not record.terminal and not record.invalidated:
                        self._invalidate_if_needed(record)
                completed = await runner_task
            except asyncio.CancelledError:
                record.cancel_event.set()
                await asyncio.gather(runner_task, return_exceptions=True)
                raise
            self._finish(record, completed)
        except PublicError as exc:
            self._fail(record, exc.code, exc.message)
        except Exception:
            self._fail(record, "SDK_WEB_TASK_FAILED", "SDK问数任务未完成，未发布结果；不自动重试。")
        finally:
            record.terminal = True
            record.provider_key = ""
            if record.runtime_root is not None:
                shutil.rmtree(record.runtime_root, ignore_errors=True)

    def _write_config(self, record):
        if minimal_runner_environment is None:
            raise PublicError(503, "SDK_UNAVAILABLE", "受控SDK不可用，未启动。")
        semantic = record.semantic
        time_meaning = semantic.contract.time.model_dump(mode="json") if semantic.contract.time else None
        test_base = getattr(self.app.state, "sdk_web_test_base_url", None)
        base_url = test_base or self._base_url(record)
        config = {
            "database": str(record.database),
            "question": record.body.question,
            "base_url": base_url,
            "runtime_root": str(record.runtime_root),
            "task_id": record.task.id,
            "model": record.model_id,
            "mode": "web_catalog",
            "auto_confirm_fixture": False,
            "wall_clock_seconds": MODEL_WALL_CLOCK_SECONDS,
            "model_ref": record.body.model_ref,
            "model_config_version": record.config_version,
            "semantic_version_id": record.body.semantic_version_id,
            "semantic_state_revision": record.semantic_state_revision,
            "source_id": record.source_id,
            "source_version": record.source_version,
            "semantic_fingerprint": record.semantic_fingerprint,
            "warehouse_schema_hash": record.warehouse_schema_hash,
            "table": semantic.contract.table_id,
            "metrics": [metric.model_dump(mode="json") for metric in semantic.contract.metrics],
            "grain": semantic.contract.grain,
            "time_meaning": time_meaning,
            "binding_hash": record.binding_hash,
            "idempotency_key": record.body.request_id,
            "confirmation_timeout_seconds": CONFIRMATION_TIMEOUT_SECONDS,
            "test_gateway": bool(test_base),
        }
        record.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _base_url(self, record):
        endpoint = record.provider_endpoint
        if endpoint.endswith("/v1/messages"):
            return endpoint[: -len("/v1/messages")]
        return endpoint

    def _run_process(self, record):
        env = minimal_runner_environment(
            record.control / "outer-home",
            record.control / "outer-config",
            record.control / "outer-temp",
        )
        env["SDK_WEB_AUTH_TOKEN"] = record.provider_key
        if getattr(self.app.state, "sdk_web_test_base_url", None):
            env["SDK_WEB_TEST"] = "1"
        limits = SdkProcessLimits(wall_seconds=PROCESS_WALL_SECONDS, cpu_seconds=600)
        return run_sdk_process(
            record.config_path,
            record.output_path,
            record.stdout_path,
            record.stderr_path,
            env,
            limits,
            record.cancel_event,
        )

    def _sync_state(self, record):
        value = self._read_state(record)
        if value is None:
            return
        if value.get("binding_hash") != record.binding_hash:
            return
        record.submitted = bool(value.get("submitted"))
        record.confirmation_id = value.get("confirmation_id") or record.confirmation_id
        if value.get("query_path") in ("L1", "L2", "L3", None):
            record.task.query_path = value.get("query_path")
        if "plan_hash" in value:
            record.task.plan_hash = value["plan_hash"]
        if "plan" in value:
            try:
                record.task.plan = AggregateRequest.model_validate(value["plan"]) if value["plan"] else None
            except (ValueError, TypeError):
                record.task.plan = None
        if "sql" in value:
            record.task.sql = value["sql"]
        phase = value.get("phase")
        mappings = {
            "PLANNING": "PLANNING",
            "NEEDS_CLARIFICATION": "NEEDS_CLARIFICATION",
            "AWAITING_CONFIRMATION": "AWAITING_CONFIRMATION",
            "VALIDATING": "VALIDATING",
            "EXECUTING": "EXECUTING",
            "CHECKING": "CHECKING",
        }
        if phase in mappings and not record.terminal and record.task.phase not in ("SUCCEEDED", "FAILED", "UNKNOWN", "EXPIRED", "CANCELLED"):
            record.task.phase = mappings[phase]
        record.task.clarification = value.get("clarification")
        record.task.clarification_id = value.get("clarification_id")
        try:
            turns = [AgentClarificationTurn.model_validate(turn) for turn in value.get("clarification_turns", [])[:2]]
            # A just-written answer must not disappear under an older state snapshot.
            for turn in turns:
                if turn.clarification_id in record.clarification_answers:
                    turn.answer = record.clarification_answers[turn.clarification_id][1]
            record.task.clarification_turns = turns
            if record.task.clarification_id in record.clarification_answers:
                record.task.clarification = None
                record.task.clarification_id = None
                if record.task.phase == "NEEDS_CLARIFICATION": record.task.phase = "PLANNING"
        except (ValueError, TypeError):
            pass
        record.task.dialogue = public_dialogue(value.get("events", []), record.task.clarification_turns, record.provider_key)
        events = self._human_events(value.get("events", []))
        if events:
            record.task.events = events

    @staticmethod
    def _read_state(record):
        if record.state_path is None or not record.state_path.is_file():
            return None
        try:
            return json.loads(record.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _human_events(events):
        labels = []
        for event in events:
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            if kind == "METADATA_READ":
                table = event.get("table")
                label = f"已读取授权元数据：{table}" if table else EVENT_LABELS["METADATA_READ"]
            elif kind == "ROUTE_READY" and event.get("metrics"):
                label = "已匹配已发布指标：" + ", ".join(str(item) for item in event["metrics"])
            elif kind == "CLARIFICATION":
                label = EVENT_LABELS["CLARIFICATION"]
            else:
                label = EVENT_LABELS.get(kind)
            if label and label not in labels:
                labels.append(label)
        return labels[-12:]

    def _invalidate_if_needed(self, record):
        if record.terminal or record.invalidated:
            return
        valid, code = self._binding_valid(record)
        if valid:
            return
        record.invalidated = True
        record.invalid_reason = code
        record.task.phase = "EXPIRED"
        record.task.error_code = code
        record.task.events = (record.task.events + ["模型、语义或来源绑定已变化，旧计划/确认失效。"])[-12:]
        record.cancel_event.set()

    def _binding_valid(self, record):
        try:
            provider = resolve_bound_model(self.app, record.task.model_ref)
        except PublicError as exc:
            return False, exc.code if exc.code == "MODEL_SELECTION_EXPIRED" else "MODEL_SELECTION_EXPIRED"
        if provider.configuration.version != record.config_version or provider.configuration.model_id != record.model_id:
            return False, "MODEL_SELECTION_EXPIRED"
        try:
            value = self.app.state.semantics.version(record.auth, record.task.semantic_version_id)
        except PublicError:
            return False, "AGENT_PLAN_EXPIRED"
        if value.state != "published_recheck_required" or value.state_revision != record.semantic_state_revision:
            return False, "AGENT_PLAN_EXPIRED"
        if value.schema_snapshot.fingerprint != record.semantic_fingerprint:
            return False, "SEMANTIC_MAPPING_STALE"
        try:
            source = self.app.state.sources.get(record.auth, value.contract.source_id)
        except PublicError:
            return False, "AGENT_PLAN_EXPIRED"
        if not source["enabled"] or source["version"] != record.source_version:
            return False, "AGENT_PLAN_EXPIRED"
        return True, None

    async def _live_binding_valid(self, record):
        valid, code = self._binding_valid(record)
        if not valid:
            return False, code
        value = self.app.state.semantics.version(record.auth, record.task.semantic_version_id)
        try:
            schema = await read_schema(
                self.app.state.sources,
                record.auth,
                value.contract.source_id,
                value.contract.table_id,
            )
        except PublicError as exc:
            return False, exc.code
        if schema.fingerprint != record.semantic_fingerprint or schema.source_version != record.source_version:
            return False, "SEMANTIC_MAPPING_STALE"
        actual = schema_hash({
            "table": schema.table_name,
            "fields": [{"name": column.name, "type": column.data_type} for column in schema.columns],
        })
        if actual != record.warehouse_schema_hash:
            return False, "SEMANTIC_MAPPING_STALE"
        return True, None

    # -- confirm / cancel ------------------------------------------------------
    async def confirm(self, auth, task_id, body: AgentConfirm):
        self.auth(auth)
        record = self._record(auth, task_id)
        task = record.task
        if body.execution_generation != self.generation or body.plan_hash != task.plan_hash:
            raise PublicError(409, "AGENT_PLAN_EXPIRED", "确认与当前计划不一致。")
        async with self._confirm_lock:
            if task.phase != "AWAITING_CONFIRMATION":
                return task
            self._sync_state(record)
            if task.phase != "AWAITING_CONFIRMATION" or not record.confirmation_id:
                return task
            if body.plan_hash != task.plan_hash:
                raise PublicError(409, "AGENT_PLAN_EXPIRED", "计划已变化，请重新核对口径后确认。")
            valid, code = await self._live_binding_valid(record)
            if not valid:
                if code == "SOURCE_BUSY":
                    raise PublicError(409, "SOURCE_BUSY", "数据源正在读取，请稍后再次确认；本次未执行。")
                record.invalidated = True
                record.invalid_reason = code
                task.phase = "EXPIRED"
                task.error_code = code
                record.cancel_event.set()
                return task
            self._sync_state(record)
            if record.cancelled or record.invalidated or record.terminal or task.phase != "AWAITING_CONFIRMATION":
                return task
            if body.plan_hash != task.plan_hash or not record.confirmation_id:
                raise PublicError(409, "AGENT_PLAN_EXPIRED", "元数据复核期间计划已变化，请重新确认。")
            confirmation = {
                "confirmation_id": record.confirmation_id,
                "plan_hash": task.plan_hash,
                "approved": True,
                "confirmation_source": "web_user",
                "binding": record.binding_hash,
            }
            temporary = record.confirmation_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(confirmation, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, record.confirmation_path)
            task.phase = "VALIDATING"
            task.events = (task.events + ["已获得当前用户确认，正在重新核验版本与权限。"])[-12:]
        return task

    async def clarify(self, auth, task_id, body: AgentClarify):
        self.auth(auth)
        record = self._record(auth, task_id)
        async with self._confirm_lock:
            if body.execution_generation != self.generation:
                raise PublicError(409, "AGENT_PLAN_EXPIRED", "任务运行代际已变化，不能继续旧澄清。")
            for value in (body.clarification_id, body.request_id):
                try:
                    if str(UUID(value)) != value: raise ValueError()
                except ValueError:
                    raise PublicError(422, "AGENT_REQUEST_INVALID", "澄清编号无效。") from None
            answer = body.answer.strip()
            if not answer or (record.provider_key and record.provider_key in answer):
                raise PublicError(422, "AGENT_INPUT_INVALID", "请勿填写密钥或空白回答。")
            self._sync_state(record)
            if record.terminal or record.cancelled or record.invalidated:
                raise PublicError(409, "AGENT_CLARIFICATION_EXPIRED", "任务已结束或失效，不能恢复；不会自动重试。")
            valid, code = await self._live_binding_valid(record)
            if not valid:
                if code == "SOURCE_BUSY":
                    raise PublicError(409, code, "来源正在读取，请稍后回答同一澄清。")
                record.invalidated = True
                record.invalid_reason = code
                record.task.phase = "EXPIRED"
                record.task.error_code = code
                record.cancel_event.set()
                return record.task
            self._sync_state(record)
            if record.terminal or record.cancelled or record.invalidated:
                raise PublicError(409, "AGENT_CLARIFICATION_EXPIRED", "复核期间任务已结束或失效，未发送回答。")
            previous = record.clarification_answers.get(body.clarification_id)
            if previous:
                if previous != (body.request_id, answer):
                    raise PublicError(409, "AGENT_CLARIFICATION_CONFLICT", "此澄清已回答，不能用旧编号改变口径。")
                return record.task
            if (record.task.phase != "NEEDS_CLARIFICATION"
                or record.task.clarification_id != body.clarification_id):
                raise PublicError(409, "AGENT_CLARIFICATION_EXPIRED", "此问题不是当前等待的澄清。")
            if any(request_id == body.request_id for request_id, _ in record.clarification_answers.values()):
                raise PublicError(409, "AGENT_CLARIFICATION_CONFLICT", "回答编号已用于另一澄清。")
            value = {"clarification_id": body.clarification_id, "request_id": body.request_id,
                     "answer": answer, "answer_source": "web_user", "binding": record.binding_hash,
                     "accept_model_egress": True}
            path = record.control.parent / record.task.id / "clarification.json"
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
            record.clarification_answers[body.clarification_id] = (body.request_id, answer)
            for turn in record.task.clarification_turns:
                if turn.clarification_id == body.clarification_id: turn.answer = answer
            record.task.clarification = None
            record.task.clarification_id = None
            record.task.phase = "PLANNING"
            record.task.events = (record.task.events + [EVENT_LABELS["CLARIFICATION_ANSWERED"]])[-12:]
            return record.task

    async def cancel(self, auth, task_id):
        self.auth(auth)
        record = self._record(auth, task_id)
        task = record.task
        if record.terminal or task.phase in ("SUCCEEDED", "FAILED", "UNKNOWN", "EXPIRED", "CANCELLED"):
            return task
        submitted = record.submitted or task.phase in ("EXECUTING", "CHECKING")
        record.cancelled = True
        record.cancel_event.set()
        task.phase = "UNKNOWN" if submitted else "CANCELLED"
        task.error_code = "AGENT_CANCELLED_UNKNOWN" if submitted else "AGENT_CANCELLED"
        task.events = (task.events + ["任务已取消；执行结果不明时不会自动重提。"])[-12:]
        return task

    # -- finalization ----------------------------------------------------------
    def _finish(self, record, completed):
        if record.invalidated:
            record.task.phase = "EXPIRED"
            record.task.error_code = record.invalid_reason
            self._finish_budget(record, None)
            return
        if record.cancelled:
            self._finish_budget(record, None)
            return
        self._sync_state(record)
        if completed.get("cancelled"):
            record.task.phase = "UNKNOWN" if record.submitted else "CANCELLED"
            record.task.error_code = "AGENT_CANCELLED_UNKNOWN" if record.submitted else "AGENT_CANCELLED"
            self._finish_budget(record, None)
            return
        if completed.get("timed_out"):
            record.task.phase = "UNKNOWN" if record.submitted else "FAILED"
            record.task.error_code = "AGENT_RESULT_UNKNOWN" if record.submitted else "SDK_TIMEOUT"
            self._finish_budget(record, None)
            return
        result = completed.get("result")
        if isinstance(result, dict) and result.get("status") == "NEEDS_CLARIFICATION":
            self._finish_clarification(record, result)
            return
        if not isinstance(result, dict) or result.get("status") != "SUCCEEDED":
            self._fail_from_output(record, result)
            return
        if not record.task.plan_hash and result.get("plan_hash"):
            record.task.plan_hash = result["plan_hash"]
        valid, code = self._binding_valid(record)
        if not valid:
            record.invalidated = True
            record.invalid_reason = code
            record.task.phase = "EXPIRED"
            record.task.error_code = code
            self._finish_budget(record, None)
            return
        try:
            data, receipts = self._validated_publication(record, result)
        except PublicError as exc:
            record.task.phase = "FAILED"
            record.task.error_code = exc.code
            record.task.events = (record.task.events + [exc.message])[-12:]
            self._finish_budget(record, None)
            return
        record.task.phase = "SUCCEEDED"
        record.task.result = data
        record.task.execution_receipt = receipts
        record.task.sql_executed = True
        record.task.returned_model_id = result.get("returned_model_id") or record.model_id
        record.task.answer = self._answer_text(record, result)
        if result.get("backend_events"):
            record.task.dialogue = public_dialogue(result["backend_events"], record.task.clarification_turns, record.provider_key)
        record.task.events = (record.task.events + ["结果已通过执行与质量回执发布。"])[-12:]
        self._finish_budget(record, self._usage_counts(result))

    def _finish_clarification(self, record, result):
        question = (result.get("clarification") or {}).get("question")
        if not isinstance(question, str) or not question.strip():
            self._fail_from_output(record, result)
            return
        record.task.phase = "NEEDS_CLARIFICATION"
        record.task.clarification = question.strip()[:500]
        record.task.returned_model_id = result.get("returned_model_id") or record.model_id
        record.task.answer = self._answer_text(record, result)
        record.task.events = (record.task.events + ["需要补充关键口径；本次未执行SQL。"])[-12:]
        self._finish_budget(record, self._usage_counts(result))

    @staticmethod
    def _answer_text(record, result):
        text = result.get("model_text")
        if not isinstance(text, str) or not text.strip():
            return None
        text = text.strip()
        if record.provider_key and record.provider_key in text:
            return None
        return text[:4000]

    @staticmethod
    def _usage_counts(result):
        usage = result.get("usage") if isinstance(result, dict) else None
        if not isinstance(usage, dict):
            return None
        try:
            return (
                sum(int(item.get("inputTokens", 0)) for item in usage.values()),
                sum(int(item.get("outputTokens", 0)) for item in usage.values()),
            )
        except (TypeError, ValueError, AttributeError):
            return None

    def _validated_publication(self, record, result):
        if result.get("model_ref") != record.task.model_ref:
            raise PublicError(502, "AGENT_RESULT_UNKNOWN", "结果模型引用与任务不一致，不能发布。")
        if result.get("model_config_version") != record.config_version:
            raise PublicError(502, "AGENT_RESULT_UNKNOWN", "结果模型版本与任务不一致，不能发布。")
        if not record.task.plan_hash or result.get("plan_hash") != record.task.plan_hash:
            raise PublicError(502, "AGENT_RESULT_UNKNOWN", "结果计划与当前任务不一致，不能发布。")
        publication = result.get("publication")
        if not isinstance(publication, dict) or publication.get("plan_hash") != record.task.plan_hash:
            raise PublicError(502, "AGENT_QUALITY_FAILED", "缺少有效发布回执，不能发布。")
        if publication.get("query_path") not in (None, "L1", "L2"):
            raise PublicError(502, "AGENT_QUALITY_FAILED", "当前Web发布路径不在批准范围。")
        if publication.get("query_path") != record.task.query_path:
            raise PublicError(502, "AGENT_QUALITY_FAILED", "发布路径与当前计划不一致。")
        if publication.get("model_generated_numbers") is not False:
            raise PublicError(502, "AGENT_QUALITY_FAILED", "结果不是由后端回执发布。")
        query = publication.get("query_receipt") or {}
        quality = publication.get("quality_receipt") or {}
        if query.get("status") != "SUCCEEDED" or quality.get("status") not in ("PASS", "WARN"):
            raise PublicError(502, "AGENT_QUALITY_FAILED", "执行或质量回执无效，不能发布。")
        plan = record.task.plan
        if plan is None:
            try:
                plan = AggregateRequest.model_validate(result.get("plan"))
            except (ValueError, TypeError):
                raise PublicError(502, "AGENT_RESULT_UNKNOWN", "结果缺少有效计划，不能发布。") from None
            record.task.plan = plan
        try:
            data = AggregateResult.model_validate(publication.get("result"))
        except (ValueError, TypeError):
            raise PublicError(502, "AGENT_RESULT_UNKNOWN", "结果合同无法解析，不能发布。") from None
        if (
            data.returned_row_count != len(data.rows)            or not data.full_input_aggregate
            or data.truncated
            or data.unit != plan.metric.unit
            or len(data.columns) != len(plan.dimensions) + 1
            or data.columns[-1].get("name") != "metric_value"
            or [column.get("name") for column in data.columns[:-1]] != plan.dimensions
            or any(len(row) != len(data.columns) for row in data.rows)
        ):
            raise PublicError(502, "AGENT_QUALITY_FAILED", "结果合同不一致，不能发布。")
        return data, {
            "publication_id": publication.get("publication_id"),
            "query_receipt": query,
            "quality_receipt": quality,
        }

    def _fail_from_output(self, record, result):
        code = result.get("error") if isinstance(result, dict) else None
        if record.submitted:
            record.task.phase = "UNKNOWN"
            record.task.error_code = "AGENT_RESULT_UNKNOWN"
        else:
            record.task.phase = "FAILED"
            record.task.error_code = code if isinstance(code, str) and code.startswith("SDK_") else "SDK_RUN_FAILED"
        message = result.get("message") if isinstance(result, dict) else None
        if isinstance(message, str) and message:
            record.task.events = (record.task.events + [message])[-12:]
        self._finish_budget(record, None)

    def _fail(self, record, code, message):
        if record.terminal or record.task.phase in ("SUCCEEDED", "UNKNOWN", "EXPIRED", "CANCELLED"):
            return
        record.task.phase = "UNKNOWN" if record.submitted else "FAILED"
        record.task.error_code = code if isinstance(code, str) and code.startswith("SDK_") else "SDK_WEB_TASK_FAILED"
        record.task.events = (record.task.events + [message])[-12:]
        self._finish_budget(record, None)

    def _finish_budget(self, record, usage):
        budget = record.budget
        if budget is None or not hasattr(budget, "finish_sdk_task") or not record.budget_ids:
            return
        try:
            if usage is None:
                budget.finish_sdk_task(record.budget_ids)
            else:
                budget.finish_sdk_task(record.budget_ids, usage[0], usage[1])
        except (ValueError, OSError):
            # The ledger is append-only; an unavailable ledger must not make a
            # completed query look successful or trigger a retry.
            pass

    async def close(self):
        workers = [record.worker for record in self.records.values() if record.worker is not None and not record.worker.done()]
        for record in self.records.values():
            record.cancel_event.set()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
