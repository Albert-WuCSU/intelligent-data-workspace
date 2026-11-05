"""Isolated Claude Agent SDK runner for fixture, experiment and Web catalog modes."""
import asyncio
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)
from claude_agent_sdk._cli_version import __cli_version__

from .auth import PublicError
from .semantic_contracts import SemanticMetric
from .sdk_agent_backend import (
    AUTH,
    SdkBudget,
    SyntheticGovernedBackend,
    WebGovernedBackend,
    create_governed_server,
)

FIXTURE_TOKEN = "fixture-only-not-a-credential"
SKILL_VERSION = "1.0.6"
APPROVED_SDK_BASE_URL = "http://ada-cli-golang.ctripcorp.com/coding-plan"
REJECTED_MODEL_ALIAS = "deepseek-v4-1-flash-261017"


@dataclass
class SdkRunnerConfig:
    database: Path
    question: str
    base_url: str
    runtime_root: Path
    task_id: str
    model: str = "claude-sonnet-5-5"
    auto_confirm_fixture: bool = True
    mode: str = "fixture"
    budget: SdkBudget = field(default_factory=SdkBudget)
    model_ref: str = ""
    model_config_version: str = ""
    semantic_version_id: str = ""
    semantic_state_revision: int = 0
    source_id: str = ""
    source_version: int = 0
    semantic_fingerprint: str = ""
    warehouse_schema_hash: str = ""
    table: str = "t0"
    metrics: list[dict] = field(default_factory=list)
    grain: list[str] = field(default_factory=lambda: ["id"])
    time_meaning: dict | None = None
    binding_hash: str = ""
    idempotency_key: str = ""
    confirmation_timeout_seconds: int = 600
    test_gateway: bool = False

    @classmethod
    def from_dict(cls, value):
        allowed = {
            "database", "question", "base_url", "runtime_root", "task_id", "model",
            "auto_confirm_fixture", "wall_clock_seconds", "mode", "model_ref",
            "model_config_version", "semantic_version_id", "semantic_state_revision",
            "source_id", "source_version", "semantic_fingerprint", "warehouse_schema_hash",
            "table", "metrics", "grain", "time_meaning", "binding_hash", "idempotency_key",
            "confirmation_timeout_seconds", "test_gateway",
        }
        unknown = set(value) - allowed
        if unknown:
            raise PublicError(422, "SDK_CONFIG_INVALID", "runner配置包含未批准字段。")
        budget = SdkBudget(wall_clock_seconds=value.get("wall_clock_seconds", 600 if value.get("mode") == "web_catalog" else 300))
        if type(budget.wall_clock_seconds) is not int or not 1 <= budget.wall_clock_seconds <= 600:
            raise PublicError(422, "SDK_WALLCLOCK_INVALID", "墙钟预算必须为1至600秒。")
        if value.get("mode") == "web_catalog":
            budget.max_model_steps = 16
            budget.max_tool_calls = 20
            budget.max_metadata_calls = 6
            budget.max_total_tokens = 200_000
        return cls(
            database=Path(value["database"]),
            question=value["question"],
            base_url=value["base_url"],
            runtime_root=Path(value["runtime_root"]),
            task_id=value["task_id"],
            model=value.get("model", "claude-sonnet-5-5"),
            auto_confirm_fixture=value.get("auto_confirm_fixture", True),
            mode=value.get("mode", "fixture"),
            budget=budget,
            model_ref=value.get("model_ref", ""),
            model_config_version=value.get("model_config_version", ""),
            semantic_version_id=value.get("semantic_version_id", ""),
            semantic_state_revision=value.get("semantic_state_revision", 0),
            source_id=value.get("source_id", ""),
            source_version=value.get("source_version", 0),
            semantic_fingerprint=value.get("semantic_fingerprint", ""),
            warehouse_schema_hash=value.get("warehouse_schema_hash", ""),
            table=value.get("table", "t0"),
            metrics=value.get("metrics", []),
            grain=value.get("grain", ["id"]),
            time_meaning=value.get("time_meaning"),
            binding_hash=value.get("binding_hash", ""),
            idempotency_key=value.get("idempotency_key", ""),
            confirmation_timeout_seconds=value.get("confirmation_timeout_seconds", 600),
            test_gateway=value.get("test_gateway", False),
        )

    def validate(self):
        if os.environ.get("SDK_RUNNER_MINIMAL") != "1" or os.environ.get("SDK_RUNNER_JOB") != "1":
            raise PublicError(503, "SDK_ISOLATION_REQUIRED", "runner必须由最小环境及专属Windows Job启动。")
        try:
            uuid.UUID(self.task_id)
        except (ValueError, AttributeError):
            raise PublicError(422, "SDK_TASK_INVALID", "任务编号无效。") from None
        if not self.question.strip() or len(self.question) > 1600:
            raise PublicError(422, "SDK_QUESTION_INVALID", "问题为空或超过本轮上限。")
        if not self.database.is_file():
            raise PublicError(422, "SDK_FIXTURE_NOT_FOUND", "合成fixture数据库不存在。")
        target = urlsplit(self.base_url)
        if self.mode == "fixture":
            if not self.auto_confirm_fixture:
                raise PublicError(403, "SDK_REAL_CONFIRMATION_NOT_CONFIGURED", "fixture模式必须使用显式模拟确认。")
            if (
                target.scheme != "http"
                or target.hostname not in {"127.0.0.1", "::1"}
                or not target.port
                or target.path not in {"", "/"}
                or target.query
                or target.fragment
                or target.username
                or target.password
            ):
                raise PublicError(403, "SDK_GATEWAY_NOT_APPROVED", "当前runner只允许独立loopback假网关，未批准真实端点。")
            if self.model != "claude-sonnet-5-5":
                raise PublicError(403, "SDK_MODEL_NOT_APPROVED", "当前fixture仅绑定指定Claude模型名，不自动切换。")
        elif self.mode == "real_gateway_experiment":
            # D-M04B-SDK-REAL-072 D: one explicitly approved non-Claude compatibility
            # experiment. It is not a supported Claude SDK path and must not be
            # exposed as a product capability.
            if not self.auto_confirm_fixture:
                raise PublicError(403, "SDK_REAL_CONFIRMATION_NOT_CONFIGURED", "真实实验只支持显式模拟确认。")
            if self.base_url != APPROVED_SDK_BASE_URL:
                raise PublicError(403, "SDK_GATEWAY_NOT_APPROVED", "真实实验只批准既有AIPlan coding-plan端点。")
            if self.model != "deepseek-v4.1-flash":
                raise PublicError(403, "SDK_MODEL_NOT_APPROVED", "真实实验只允许已确认可用的deepseek-v4.1-flash。")
            token = os.environ.get("SDK_EXPERIMENT_AUTH_TOKEN", "")
            if not isinstance(token, str) or not 8 <= len(token) <= 4096 or any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
                raise PublicError(503, "SDK_EXPERIMENT_KEY_REQUIRED", "真实实验需要本机隐藏输入的产品专用Key。")
        elif self.mode == "web_catalog":
            self._validate_web_catalog(target)
        else:
            raise PublicError(422, "SDK_MODE_INVALID", "runner模式无效。")

    def _validate_web_catalog(self, target):
        if self.auto_confirm_fixture:
            raise PublicError(403, "SDK_REAL_CONFIRMATION_NOT_CONFIGURED", "Web模式必须使用真实用户确认，不能自动确认。")
        loopback = (
            target.scheme == "http"
            and target.hostname in {"127.0.0.1", "::1"}
            and bool(target.port)
            and target.path in {"", "/"}
            and not target.query
            and not target.fragment
            and not target.username
            and not target.password
        )
        if loopback:
            if os.environ.get("SDK_WEB_TEST") != "1" or not self.test_gateway:
                raise PublicError(403, "SDK_GATEWAY_NOT_APPROVED", "Web模式loopback只允许隔离测试。")
        elif self.base_url != APPROVED_SDK_BASE_URL:
            raise PublicError(403, "SDK_GATEWAY_NOT_APPROVED", "Web模式只批准既有AIPlan coding-plan端点或隔离测试loopback。")
        if not re.fullmatch(r"[A-Za-z0-9_.:\[\]-]{1,120}", self.model):
            raise PublicError(422, "SDK_MODEL_INVALID", "模型名格式无效。")
        if self.model == REJECTED_MODEL_ALIAS:
            raise PublicError(403, "SDK_MODEL_NOT_APPROVED", "该名称是网关返回版本别名，不能作为请求名。")
        if not self.model_ref or len(self.model_ref) > 200:
            raise PublicError(422, "SDK_MODEL_REF_INVALID", "缺少服务端catalog模型引用。")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.model_config_version):
            raise PublicError(422, "SDK_MODEL_CONFIG_INVALID", "模型配置版本无效。")
        try:
            uuid.UUID(self.semantic_version_id)
            uuid.UUID(self.source_id)
            uuid.UUID(self.idempotency_key)
        except (ValueError, AttributeError):
            raise PublicError(422, "SDK_BINDING_INVALID", "语义、来源或幂等引用无效。") from None
        for value in (self.semantic_fingerprint, self.warehouse_schema_hash, self.binding_hash):
            if not re.fullmatch(r"[a-f0-9]{64}", value):
                raise PublicError(422, "SDK_BINDING_INVALID", "绑定指纹无效。")
        if not self.table or len(self.table) > 100:
            raise PublicError(422, "SDK_TABLE_INVALID", "授权表引用无效。")
        if not 1 <= len(self.metrics) <= 12:
            raise PublicError(422, "SDK_METRICS_INVALID", "已发布指标数量无效。")
        for item in self.metrics:
            try:
                SemanticMetric.model_validate(item)
            except (ValueError, TypeError):
                raise PublicError(422, "SDK_METRICS_INVALID", "已发布指标合同无效。") from None
        if not 1 <= len(self.grain) <= 4 or not all(isinstance(item, str) and item for item in self.grain):
            raise PublicError(422, "SDK_GRAIN_INVALID", "已批准粒度无效。")
        if self.time_meaning is not None and not isinstance(self.time_meaning, dict):
            raise PublicError(422, "SDK_TIME_INVALID", "时间口径无效。")
        if type(self.confirmation_timeout_seconds) is not int or not 30 <= self.confirmation_timeout_seconds <= 1800:
            raise PublicError(422, "SDK_CONFIRMATION_TIMEOUT_INVALID", "确认等待必须为30至1800秒。")
        token = os.environ.get("SDK_WEB_AUTH_TOKEN", "")
        if not isinstance(token, str) or not 8 <= len(token) <= 4096 or any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
            raise PublicError(503, "SDK_WEB_KEY_REQUIRED", "Web模型调用需要服务端解析的产品专用Key。")


@dataclass
class SkillInstallation:
    cwd: Path
    config: Path
    home: Path
    temp: Path
    plugin: Path
    sha256: str


def install_versioned_skill(runtime_root: Path, task_id: str) -> SkillInstallation:
    root = runtime_root.resolve() / task_id
    root.mkdir(parents=True, exist_ok=False)
    cwd = root / "cwd"
    config = root / "config"
    home = root / "home"
    temp = root / "temp"
    plugin = cwd / "governed-plugin"
    skill_dir = plugin / "skills" / "data-query"
    manifest_dir = plugin / ".claude-plugin"
    for path in (skill_dir, manifest_dir, config, home, temp):
        path.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name("sdk_skills") / "data-query" / "SKILL.md"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target = skill_dir / "SKILL.md"
    target.write_bytes(source.read_bytes())
    (manifest_dir / "plugin.json").write_text(json.dumps({"name": "governed", "version": SKILL_VERSION, "description": "Audited offline data query skill"}), encoding="utf-8")
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise PublicError(503, "SDK_SKILL_INSTALL_FAILED", "产品Skill安装校验失败。")
    return SkillInstallation(cwd=cwd, config=config, home=home, temp=temp, plugin=plugin, sha256=digest)


def minimal_runner_environment(home: Path, config: Path, temp: Path) -> dict[str, str]:
    """Construct a clean outer-process environment; never copy host credentials/settings."""
    home.mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", ""),
        "PATHEXT": os.environ.get("PATHEXT", ".EXE"),
        "COMSPEC": os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:/Windows"),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData/Roaming"),
        "LOCALAPPDATA": str(home / "AppData/Local"),
        "TEMP": str(temp),
        "TMP": str(temp),
        "CLAUDE_CONFIG_DIR": str(config),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
        "DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "PYTHONUTF8": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SDK_RUNNER_MINIMAL": "1",
        "NO_COLOR": "1",
    }


def capabilities(mode: str = "fixture") -> dict:
    return {
        "implementation": "claude_agent_sdk_skills_v1",
        "available_fixture_only": mode == "fixture",
        "sdk_version": "0.2.177",
        "cli_version": __cli_version__,
        "real_gateway_available": mode == "web_catalog",
        "non_claude_compatibility_experiment": mode in {"real_gateway_experiment", "web_catalog"},
        "web_catalog_binding": mode == "web_catalog",
        "production_available": False,
        "durable_tasks": False,
        "legacy_implementation": "langgraph_governed_single_table_v1",
    }


def _state_writer(path: Path):
    def write(value):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    return write


def _build_backend(config: SdkRunnerConfig, skill_sha256: str):
    if config.mode == "web_catalog":
        state_path = config.runtime_root.resolve() / config.task_id / "state.json"
        confirmation_path = config.runtime_root.resolve() / config.task_id / "confirmation.json"
        metrics = [SemanticMetric.model_validate(item) for item in config.metrics]
        return WebGovernedBackend(
            config.database,
            table=config.table,
            metrics=metrics,
            grain=config.grain,
            time_meaning=config.time_meaning,
            warehouse_schema_hash=config.warehouse_schema_hash,
            skill_sha256=skill_sha256,
            budget=config.budget,
            confirmation_path=confirmation_path,
            binding_hash=config.binding_hash,
            idempotency_key=config.idempotency_key,
            confirmation_timeout_seconds=config.confirmation_timeout_seconds,
            state_writer=_state_writer(state_path),
        )
    metric = SemanticMetric(
        id="total",
        name="Total amount",
        operator="sum",
        column="amount",
        unit="declared units",
        additive=True,
    )
    return SyntheticGovernedBackend(config.database, metric, skill_sha256, config.budget)


def valid_result_usage(usage):
    """A publication cannot substitute for a nonempty, measured model receipt."""
    if not isinstance(usage, dict) or not usage:
        return False
    total = 0
    for model, item in usage.items():
        if not isinstance(model, str) or not model or not isinstance(item, dict):
            return False
        if "inputTokens" not in item or "outputTokens" not in item:
            return False
        for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
            value = item.get(key, 0)
            if type(value) is not int or value < 0:
                return False
            total += value
    return total > 0


async def run_sdk_fixture(config: SdkRunnerConfig) -> dict:
    config.validate()
    installation = install_versioned_skill(config.runtime_root, config.task_id)
    if config.mode == "fixture":
        auth_token = FIXTURE_TOKEN
    elif config.mode == "real_gateway_experiment":
        auth_token = os.environ["SDK_EXPERIMENT_AUTH_TOKEN"]
    else:
        auth_token = os.environ["SDK_WEB_AUTH_TOKEN"]
    backend = _build_backend(config, installation.sha256)
    text_parts = []
    events = []
    result_status = None
    result_usage = None
    total_cost_usd = None
    stream_events = 0

    async def on_backend_event(name, value):
        events.append({"type": name, "confirmation_id": value})
        if name == "AWAITING_CONFIRMATION" and config.mode != "web_catalog":
            # Explicit simulated user action in the isolated fixture, never a model grant.
            backend.approve_confirmation(value)

    backend.event_handler = on_backend_event

    async def permission(tool_name, input_data, context):
        short = tool_name.split("__")[-1]
        if short == "execute_approved_query":
            backend.execute_authorized(input_data["plan_hash"], input_data["confirmation_id"])
            return PermissionResultAllow(updated_input=input_data)
        if short == "publish_result":
            backend.publish_authorized(input_data["plan_hash"], input_data["query_receipt_id"], input_data["quality_receipt_id"])
            return PermissionResultAllow(updated_input=input_data)
        return PermissionResultDeny(message="SDK_TOOL_PERMISSION_DENIED：该工具未获当前任务批准。", interrupt=False)

    async def pre_tool_use(input_data, tool_use_id, context):
        # MCP calls are counted exactly once in their backend handlers; hook delivery may repeat.
        if input_data["tool_name"].startswith("mcp__"):
            return {}
        config.budget.tool(input_data["tool_name"], tool_use_id)
        return {}

    env = {
        "ANTHROPIC_BASE_URL": config.base_url,
        "ANTHROPIC_AUTH_TOKEN": auth_token,
        "ANTHROPIC_MODEL": config.model,
        "CLAUDE_CONFIG_DIR": str(installation.config),
        "HOME": str(installation.home),
        "USERPROFILE": str(installation.home),
        "APPDATA": str(installation.home / "AppData/Roaming"),
        "LOCALAPPDATA": str(installation.home / "AppData/Local"),
        "TEMP": str(installation.temp),
        "TMP": str(installation.temp),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
        "DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
        "CLAUDE_CODE_MAX_RETRIES": "0",
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(config.budget.max_output_tokens),
        "API_TIMEOUT_MS": "60000",
        "CLAUDE_STREAM_IDLE_TIMEOUT_MS": "30000",
    }
    safe_tools = [
        "mcp__governed__search_semantics",
        "mcp__governed__resolve_route",
        "mcp__governed__read_authorized_metadata",
        "mcp__governed__list_authorized_tables",
        "mcp__governed__search_authorized_fields",
        "mcp__governed__load_topic_sql_template",
        "mcp__governed__propose_topic_query",
        "mcp__governed__propose_metric_query",
        "mcp__governed__propose_sql_query",
        "mcp__governed__request_clarification",
        "mcp__governed__request_confirmation",
        "mcp__governed__get_receipt",
    ]
    options = ClaudeAgentOptions(
        model=config.model,
        cwd=str(installation.cwd),
        tools=["Skill"],
        mcp_servers={"governed": create_governed_server(backend)},
        allowed_tools=safe_tools,
        setting_sources=[],
        skills=["governed:data-query"],
        plugins=[{"type": "local", "path": str(installation.plugin)}],
        permission_mode="default",
        can_use_tool=permission,
        hooks={"PreToolUse": [HookMatcher(hooks=[pre_tool_use], on_failure="block")]},
        max_turns=config.budget.max_model_steps,
        max_budget_usd=config.budget.max_budget_usd,
        fallback_model=None,
        agents={},
        include_partial_messages=True,
        env=env,
        system_prompt="You are a governed conversational data query assistant. Use the loaded product skill and only governed tools. Give concise user-facing explanations of confirmed scope, actual findings, limitations and required clarification; never disclose private thinking or claim uncalled tools succeeded. Never invent business values, execution, quality results or downloads. After execution or publish_result reports PUBLISHED, stop calling tools and write a readable report in the user's language with headings/bullets for scope, source, quality, limitations and actionable next steps. Exact numbers come from the backend-rendered result table; do not reconstruct them. Do not make a result card the only answer. Do not call get_receipt again.",
    )
    total_timeout = config.budget.wall_clock_seconds
    if config.mode == "web_catalog":
        total_timeout += config.confirmation_timeout_seconds
    async with asyncio.timeout(total_timeout):
        async with ClaudeSDKClient(options=options) as client:
            await client.query(config.question)
            async for message in client.receive_response():
                if isinstance(message, StreamEvent):
                    stream_events += 1
                elif isinstance(message, SystemMessage) and message.subtype == "init":
                    skills = message.data.get("skills", [])
                    if "governed:data-query" not in skills:
                        raise PublicError(503, "SDK_SKILL_NOT_LOADED", "SDK init未确认批准的governed:data-query Skill。")
                    plugins = message.data.get("plugins", [])
                    if not any(item.get("name") == "governed" for item in plugins) or message.data.get("plugin_errors"):
                        raise PublicError(503, "SDK_SKILL_PLUGIN_INVALID", "受控Skill plugin未完整加载。")
                    events.append({"type": "SDK_INIT", "skills": skills})
                elif isinstance(message, AssistantMessage):
                    config.budget.model_step(message.message_id)
                    if any(isinstance(block, TextBlock) for block in message.content):
                        text_parts.clear()
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            events.append({"type": "TOOL_USE", "name": block.name})
                            if block.name == "Skill":
                                name = block.input.get("skill") or block.input.get("name")
                                backend.record_skill(name, installation.sha256)
                        elif isinstance(block, TextBlock):
                            text_parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    result_status = message.subtype
                    result_usage = message.model_usage
                    total_cost_usd = message.total_cost_usd
                    config.budget.usage(result_usage)

    def budget_state():
        return {
            "model_steps": config.budget.model_steps,
            "tool_calls": config.budget.tool_calls,
            "metadata_calls": config.budget.metadata_calls,
            "total_tokens": config.budget.total_tokens,
            "estimated_reserve_usd": config.budget.estimated_reserve_usd,
            "max_model_steps": config.budget.max_model_steps,
            "max_tool_calls": config.budget.max_tool_calls,
            "max_total_tokens": config.budget.max_total_tokens,
            "wall_clock_seconds": config.budget.wall_clock_seconds,
            "confirmation_timeout_seconds": config.confirmation_timeout_seconds if config.mode == "web_catalog" else None,
        }

    def fail(code, message):
        # Preserve non-secret failure diagnostics inside the isolated task dir so a
        # failed run can be explained without another model call.
        diagnostic = {
            "status": "FAILED",
            "error": code,
            "message": message,
            "mode": config.mode,
            "model": config.model,
            "model_ref": config.model_ref,
            "model_config_version": config.model_config_version,
            "events": events,
            "backend_events": backend.events,
            "clarification": backend.clarification,
            "model_text": "".join(text_parts),
            "usage": result_usage,
            "total_cost_usd_client_estimate": total_cost_usd,
            "budget": budget_state(),
            "stream_events": stream_events,
            "result_status": result_status,
        }
        try:
            target = config.runtime_root / config.task_id / "failure-diagnostics.json"
            target.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        raise PublicError(502, code, message)

    real_gateway_called = config.mode == "real_gateway_experiment" or (config.mode == "web_catalog" and not config.test_gateway)
    if backend.clarification_error:
        fail(backend.clarification_error, "澄清等待超时或次数已达上限，未执行查询；请整理口径后新建问题。")
    if backend.clarification is not None:
        return {
            "status": "NEEDS_CLARIFICATION",
            "capability": capabilities(config.mode),
            "mode": config.mode,
            "model": config.model,
            "returned_model_id": next(iter(result_usage), None) if isinstance(result_usage, dict) else None,
            "model_id": config.model,
            "model_ref": config.model_ref,
            "model_config_version": config.model_config_version,
            "semantic_version_id": config.semantic_version_id,
            "source_id": config.source_id,
            "binding_hash": config.binding_hash,
            "clarification": backend.clarification,
            "model_text": "".join(text_parts),
            "events": events,
            "backend_events": backend.events,
            "usage": result_usage,
            "total_cost_usd_client_estimate": total_cost_usd,
            "budget": budget_state(),
            "stream_events": stream_events,
            "result_rows_returned_to_model": False,
            "real_gateway_called": real_gateway_called,
            "production_sql_executed": False,
        }
    if result_status != "success":
        # A valid publication is stronger evidence than a loop that ended on
        # max_turns after the backend already executed, QA'd and published.
        if backend.publication is None:
            fail("SDK_RUN_FAILED", "SDK工具循环未成功完成，不发布结果。")
    if not valid_result_usage(result_usage):
        fail("SDK_USAGE_INVALID", "缺少有效模型用量回执，不发布结果或继续调用。")
    if backend.publication is None:
        fail("SDK_PUBLICATION_MISSING", "缺少经回执核验的发布结果。")
    returned_model_id = next(iter(result_usage), None) if isinstance(result_usage, dict) else None
    return {
        "status": "SUCCEEDED",
        "capability": capabilities(config.mode),
        "mode": config.mode,
        "model": config.model,
        "returned_model_id": returned_model_id,
        "model_id": config.model,
        "model_ref": config.model_ref,
        "model_config_version": config.model_config_version,
        "semantic_version_id": config.semantic_version_id,
        "source_id": config.source_id,
        "binding_hash": config.binding_hash,
        "plan_hash": backend.plan_hash,
        "plan": backend.plan.model_dump(mode="json") if backend.plan is not None else None,
        "sql": backend.plan_sql,
        "experiment": {
            "mode": config.mode,
            "model": config.model,
            "base_url": config.base_url,
            "official_support": "unsupported_non_claude_experiment" if config.mode == "real_gateway_experiment" else "web_catalog_binding" if config.mode == "web_catalog" else "offline_fixture",
        },
        "skill": {"name": "data-query", "version": SKILL_VERSION, "sha256": installation.sha256},
        "route_receipt": backend.route,
        "query_receipt": backend.query_receipt,
        "quality_receipt": backend.quality_receipt,
        "publication": backend.publication,
        "confirmation_source": backend.confirmation_source,
        "model_text": "".join(text_parts),
        "events": events,
        "backend_events": backend.events,
        "usage": result_usage,
        "total_cost_usd_client_estimate": total_cost_usd,
        "budget": budget_state(),
        "stream_events": stream_events,
        "result_rows_returned_to_model": False,
        "real_gateway_called": real_gateway_called,
        "production_sql_executed": False,
        "loop_status": result_status,
    }
