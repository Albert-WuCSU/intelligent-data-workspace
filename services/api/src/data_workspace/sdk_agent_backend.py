"""Governed SDK tools for fixture, experiment and Web catalog bindings.

The backend owns plan validity, confirmation, execution, quality receipts and
publication. Model output is never the authority for any of those transitions.
"""
import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .auth import PublicError
from .contracts import AuthContext
from .semantic_contracts import SemanticMetric
from .warehouse.aggregate_client import AggregateMCPClient
from .warehouse.aggregate_contract import AggregateFilter, AggregateRequest, AggregateResult, compile_aggregate, schema_hash
from .warehouse.local_file import LocalFileWarehouse
from .warehouse.policy import QueryDenied

AUTH = AuthContext(mode="development", tenant_id="local-workspace", principal_id="local-developer")


@dataclass
class SdkBudget:
    max_model_steps: int = 8
    max_tool_calls: int = 10
    max_metadata_calls: int = 3
    max_total_tokens: int = 100_000
    max_output_tokens: int = 4096
    wall_clock_seconds: int = 300
    max_budget_usd: float = 1.75
    estimated_reserve_usd: float = 2.0
    model_steps: int = 0
    tool_calls: int = 0
    metadata_calls: int = 0
    total_tokens: int = 0
    _model_ids: set[str] = field(default_factory=set)

    _tool_ids: set[str] = field(default_factory=set)

    def tool(self, name: str, tool_use_id: str | None = None) -> None:
        if tool_use_id:
            if tool_use_id in self._tool_ids:
                return
            self._tool_ids.add(tool_use_id)
        self.tool_calls += 1
        if self.tool_calls > self.max_tool_calls:
            raise PublicError(429, "SDK_TOOL_BUDGET_EXCEEDED", "本任务工具调用已达到上限，不会继续执行。")
        if name in {"search_semantics", "read_authorized_metadata", "list_authorized_tables", "search_authorized_fields", "load_topic_sql_template"}:
            self.metadata_calls += 1
            if self.metadata_calls > self.max_metadata_calls:
                raise PublicError(429, "SDK_METADATA_BUDGET_EXCEEDED", "本任务元数据探索已达到上限，请先明确范围。")

    def model_step(self, message_id: str | None) -> None:
        if not message_id or message_id in self._model_ids:
            return
        self._model_ids.add(message_id)
        self.model_steps += 1
        if self.model_steps > self.max_model_steps:
            raise PublicError(429, "SDK_TURN_BUDGET_EXCEEDED", "本任务模型步骤已达到上限，不会自动继续。")

    def usage(self, model_usage: dict[str, Any] | None) -> None:
        if not model_usage:
            return
        total = 0
        for item in model_usage.values():
            for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
                value = item.get(key, 0)
                if type(value) is not int or value < 0:
                    raise PublicError(502, "SDK_USAGE_INVALID", "模型用量回执无效，停止发布。")
                total += value
        self.total_tokens = total
        if total > self.max_total_tokens:
            raise PublicError(429, "SDK_TOKEN_BUDGET_EXCEEDED", "本任务累计token已达到上限，不会自动压缩或继续。")


class GovernedQueryBackend:
    """One governed single-table backend shared by fixture and Web catalog modes.

    Fixture mode auto-confirms through an explicit test callback. Web mode waits
    for a server-written confirmation file whose binding is checked again here.
    """

    def __init__(
        self,
        database: Path,
        *,
        table: str,
        metrics: list[SemanticMetric],
        grain: list[str],
        time_meaning: dict[str, Any] | None,
        warehouse_schema_hash: str | None,
        skill_sha256: str,
        budget: SdkBudget,
        confirmation_mode: str = "fixture",
        confirmation_timeout_seconds: int = 10,
        confirmation_path: Path | None = None,
        binding_hash: str = "",
        idempotency_key: str | None = None,
        allow_sql_path: bool = True,
        auth: AuthContext = AUTH,
        state_writer=None,
    ):
        self.database = Path(database).resolve()
        self.table = table
        self.metrics = list(metrics)
        self.metric = self.metrics[0] if self.metrics else None
        self.grain = list(grain)
        self.time_meaning = time_meaning.model_dump() if hasattr(time_meaning, "model_dump") else time_meaning
        self.warehouse_schema_hash = warehouse_schema_hash
        self.skill_sha256 = skill_sha256
        self.budget = budget
        self.confirmation_mode = confirmation_mode
        self.confirmation_timeout_seconds = confirmation_timeout_seconds
        self.confirmation_path = Path(confirmation_path) if confirmation_path else None
        self.binding_hash = binding_hash
        self.idempotency_key = idempotency_key
        self.allow_sql_path = allow_sql_path
        self.auth = auth
        self.state_writer = state_writer
        self.skill_loaded = False
        self.route: dict[str, Any] | None = None
        self.plan: AggregateRequest | None = None
        self.plan_hash: str | None = None
        self.plan_sql: str | None = None
        self.confirmation_id: str | None = None
        self.confirmed = False
        self.confirmation_source: str | None = None
        self._confirmation_event = asyncio.Event()
        self.event_handler = None
        self.submitted = False
        self.idempotency_model_key: str | None = None
        self.mcp_idempotency_key: str | None = None
        self.query_receipt: dict[str, Any] | None = None
        self.quality_receipt: dict[str, Any] | None = None
        self.result: AggregateResult | None = None
        self.publication: dict[str, Any] | None = None
        self.clarification: dict[str, Any] | None = None
        self.clarification_turns: list[dict[str, Any]] = []
        self.clarification_error: str | None = None
        self.topic_template: dict[str, Any] | None = None
        self.metadata_read = False
        self.query_path = None
        self.clarification_path = self.confirmation_path.with_name("clarification.json") if self.confirmation_path else None
        self.events: list[dict[str, Any]] = []
        self.current_phase = "PLANNING"

    # -- state and audit events -------------------------------------------------
    def _state(self, phase: str, error: str | None = None) -> None:
        self.current_phase = phase
        if self.state_writer is None:
            return
        try:
            self.state_writer({
                "phase": phase,
                "plan_hash": self.plan_hash,
                "plan": self.plan.model_dump(mode="json") if self.plan is not None else None,
                "sql": self.plan_sql,
                "query_path": self.query_path,
                "confirmation_id": self.confirmation_id,
                "binding_hash": self.binding_hash,
                "submitted": self.submitted,
                "clarification": (self.clarification or {}).get("question"),
                "clarification_id": (self.clarification or {}).get("clarification_id"),
                "clarification_turns": self.clarification_turns,
                "error": error,
                "events": self.events[-50:],
            })
        except OSError:
            # State is a UI/diagnostic mirror only; the runner output and receipts
            # remain the authoritative result of this task.
            pass

    def _event(self, name: str, **data) -> None:
        self.events.append({"type": name, **{k: v for k, v in data.items() if v is not None}})
        if len(self.events) > 100:
            del self.events[:-100]
        self._state(self.current_phase)

    # -- routing ---------------------------------------------------------------
    def record_skill(self, name: str, sha256: str) -> None:
        if name != "governed:data-query" or sha256 != self.skill_sha256:
            raise PublicError(403, "SDK_SKILL_DENIED", "未加载批准的产品Skill版本，拒绝取数。")
        if not self.skill_loaded:
            self.skill_loaded = True
            self._event("SKILL_LOADED")

    def _require_route(self, route_receipt: str) -> dict[str, Any]:
        if not self.skill_loaded or not self.route or route_receipt != self.route["route_receipt"]:
            raise PublicError(403, "SDK_ROUTE_DENIED", "Skill路由回执缺失、失效或不匹配。")
        return self.route

    @staticmethod
    def _metric_matches(metric: SemanticMetric, folded_question: str) -> bool:
        terms = [metric.id, metric.name, *metric.aliases, metric.column, metric.numerator, metric.denominator]
        return any(term and term.casefold() in folded_question for term in terms)

    def search_semantics(self, question: str) -> dict[str, Any]:
        if not self.skill_loaded:
            raise PublicError(403, "SDK_SKILL_REQUIRED", "必须先调用批准的data-query Skill。")
        if self.submitted:
            raise PublicError(409, "SDK_TASK_ALREADY_SUBMITTED", "查询已提交或完成，不能通过改路由改变既有执行。")
        if not question.strip() or len(question) > 1600:
            raise PublicError(422, "SDK_QUESTION_INVALID", "问题为空或超过本轮上限。")
        # A new route invalidates any earlier unexecuted plan and confirmation.
        self.topic_template = None
        self.query_path = None
        self.plan = None
        self.plan_hash = None
        self.plan_sql = None
        self.confirmation_id = None
        self.confirmed = False
        self.confirmation_source = None
        self._confirmation_event = asyncio.Event()
        folded = question.casefold()
        matched = [metric for metric in self.metrics if self._metric_matches(metric, folded)]
        digest = hashlib.sha256((self.skill_sha256 + "\n" + question).encode()).hexdigest()
        self.route = {
            "route_receipt": "route-" + digest[:32],
            "skill": "governed:data-query",
            "skill_sha256": self.skill_sha256,
            "published_metric_match": bool(matched),
        }
        self.current_phase = "PLANNING"
        self._event("ROUTE_READY", metric_matched=bool(matched), metrics=[metric.id for metric in matched])
        return {**self.route, "candidates": [metric.model_dump(mode="json") for metric in matched]}

    def resolve_route(self, route_receipt: str) -> dict[str, Any]:
        return self._require_route(route_receipt)

    def read_authorized_metadata(self, table: str) -> dict[str, Any]:
        if not self.skill_loaded:
            raise PublicError(403, "SDK_SKILL_REQUIRED", "必须先加载批准的产品Skill。")
        if table != self.table:
            raise PublicError(403, "SDK_SOURCE_DENIED", "该表不在当前授权范围内。")
        description = LocalFileWarehouse(self.database).describe(table)
        if self.warehouse_schema_hash is not None and schema_hash(description) != self.warehouse_schema_hash:
            raise PublicError(409, "SDK_SCHEMA_CHANGED", "当前字段与已批准语义不一致，请重新规划。")
        self.metadata_read = True
        self._event("METADATA_READ", table=description["table"])
        return description

    def list_authorized_tables(self):
        # One bound semantic table only, never the warehouse-wide host catalog.
        description = self.read_authorized_metadata(self.table)
        self._event("TABLES_DISCOVERED")
        return {"tables": [{"id": self.table, "name": description["table"], "field_count": len(description["fields"])}],
                "scope": "current_bound_single_table", "rows_read": False,
                "approved_topic_metrics": [{"id": metric.id, "name": metric.name} for metric in self.metrics],
                "partitions": None, "partition_status": "not_exposed_by_local_snapshot"}

    def search_authorized_fields(self, table: str, search: str):
        if not isinstance(search, str) or len(search) > 200:
            raise PublicError(422, "SDK_METADATA_SEARCH_INVALID", "字段检索词需为最多200字符。")
        description = self.read_authorized_metadata(table)
        fields = [{"name": f["name"], "type": f["type"]} for f in description["fields"]
                  if search.casefold() in f["name"].casefold()]
        self._event("FIELDS_DISCOVERED", field_count=len(fields))
        return {"table": table, "fields": fields, "rows_read": False, "schema_hash": schema_hash(description)}

    def load_topic_sql_template(self, route_receipt: str, metric_id: str):
        self._clarification_ready()
        if self.submitted:
            raise PublicError(409, "SDK_TASK_ALREADY_SUBMITTED", "已提交任务不能更换模板。")
        route = self._require_route(route_receipt)
        if route["published_metric_match"]:
            raise PublicError(409, "SDK_METRIC_ROUTE_REQUIRED", "L1已有匹配指标，不能改走主题SQL。")
        metric = next((m for m in self.metrics if m.id == metric_id), None)
        if metric is None:
            raise PublicError(403, "SDK_METRIC_DENIED", "模板只能使用本任务已批准的指标口径。")
        description = self.read_authorized_metadata(self.table)
        payload = {"template_version": "1.0.0", "skill_sha256": self.skill_sha256,
                   "route_receipt": route_receipt, "binding": self.binding_hash,
                   "table": self.table, "schema_hash": schema_hash(description),
                   "metric": metric.model_dump(mode="json"), "grain": self.grain,
                   "time_meaning": self.time_meaning, "clarification_rounds": len(self.clarification_turns)}
        payload["template_receipt"] = "topic-" + hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        self.topic_template = payload
        self._event("TOPIC_TEMPLATE_LOADED")
        return {k:v for k,v in payload.items() if k not in {"binding", "skill_sha256"}} | {
            "source": "approved_semantic_parameterized_template", "readonly": True,
            "supported_filters": ["eq", "in", "gte", "lt"], "join_available": False,
            "instruction": "Use only this canonical metric/table/grain; clarify intent before proposing. No arbitrary SQL or new metric definitions."}

    def propose_topic_query(self, route_receipt: str, template_receipt: str, dimensions: list[str],
                            time_range=None, filters=None):
        self._clarification_ready()
        route = self._require_route(route_receipt)
        if route["published_metric_match"]:
            raise PublicError(409, "SDK_METRIC_ROUTE_REQUIRED", "L1已有匹配指标，不能改走主题SQL。")
        template = self.topic_template
        if (not template or template_receipt != template["template_receipt"]
            or template["route_receipt"] != route_receipt
            or template["binding"] != self.binding_hash
            or template["skill_sha256"] != self.skill_sha256
            or template["clarification_rounds"] != len(self.clarification_turns)):
            raise PublicError(409, "SDK_TOPIC_TEMPLATE_EXPIRED", "主题模板未加载或已失效，请重新核对。")
        description = LocalFileWarehouse(self.database).describe(self.table)
        if schema_hash(description) != template["schema_hash"]:
            raise PublicError(409, "SDK_SCHEMA_CHANGED", "模板字段已变化，请重新规划。")
        return self._build_metric_plan(template["metric"]["id"], dimensions, time_range, filters, "topic_sql")

    def _clarification_ready(self):
        if self.clarification is not None or self.clarification_error:
            raise PublicError(409, "SDK_CLARIFICATION_PENDING", "澄清未完成或已超时，不能规划、确认或执行查询。")

    def _set_plan(self, plan: AggregateRequest, engine: str) -> dict[str, Any]:
        self._clarification_ready()
        if self.submitted:
            raise PublicError(409, "SDK_TASK_ALREADY_SUBMITTED", "已提交任务不能改变计划或再次执行。")
        if plan.table != self.table:
            raise PublicError(403, "SDK_SOURCE_DENIED", "计划表不在当前授权范围内。")
        description = LocalFileWarehouse(self.database).describe(plan.table)
        if plan.table != self.table:
            raise PublicError(403, "SDK_SOURCE_DENIED", "计划表不在当前授权范围内。")
        if plan.schema_hash != schema_hash(description):
            raise PublicError(409, "SDK_SCHEMA_CHANGED", "执行端字段与计划不一致，拒绝查询。")
        if plan.grain != self.grain:
            raise PublicError(422, "SDK_GRAIN_DENIED", "计划粒度与已批准语义不一致。")
        canonical = next((metric for metric in self.metrics if metric.id == plan.metric.id), None)
        if canonical is None or canonical.model_dump() != plan.metric.model_dump():
            raise PublicError(403, "SDK_METRIC_DENIED", "指标定义与已批准口径不一致，不能仅凭同名ID执行。")
        sql, _, _, _ = compile_aggregate(plan, description)
        self.plan = plan
        self.query_path = "L1" if engine == "published_metric" else "L2" if engine == "topic_sql" else "L3"
        self.plan_sql = sql
        self.plan_hash = hashlib.sha256(
            json.dumps([engine, self.route, plan.model_dump(mode="json"), sql, self.binding_hash, self.clarification_turns], sort_keys=True).encode()
        ).hexdigest()
        self.confirmation_id = None
        self.confirmed = False
        self.confirmation_source = None
        self._confirmation_event = asyncio.Event()
        self.current_phase = "PLANNING"
        self._event("PLAN_READY", engine=engine)
        return {"plan_hash": self.plan_hash, "engine": engine, "confirmation_required": True}

    def propose_metric_query(
        self,
        route_receipt: str,
        metric_id: str,
        dimensions: list[str],
        time_range: dict[str, Any] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        route = self._require_route(route_receipt)
        if not route["published_metric_match"]:
            raise PublicError(409, "SDK_METRIC_NOT_MATCHED", "没有匹配的已发布指标，请改用受控SQL申请。")
        return self._build_metric_plan(metric_id, dimensions, time_range, filters, "published_metric")

    def _build_metric_plan(self, metric_id, dimensions, time_range, filters, engine):
        metric = next((item for item in self.metrics if item.id == metric_id), None)
        if metric is None:
            raise PublicError(403, "SDK_METRIC_DENIED", "指标未获批准。")
        description = LocalFileWarehouse(self.database).describe(self.table)
        parsed_filters = []
        if filters:
            if not isinstance(filters, list) or len(filters) > 5:
                raise PublicError(422, "SDK_FILTER_INVALID", "筛选条件最多5组。")
            for item in filters:
                try:
                    parsed_filters.append(AggregateFilter.model_validate(item))
                except (ValueError, TypeError):
                    raise PublicError(422, "SDK_FILTER_INVALID", "筛选条件格式无效；只能使用授权字段、eq/in/gte/lt和匹配类型的值。") from None
        time_filter = None
        if time_range:
            if not isinstance(time_range, dict):
                raise PublicError(422, "SDK_TIME_INVALID", "时间范围格式无效。")
            if not self.time_meaning:
                raise PublicError(409, "SDK_TIME_NOT_DEFINED", "该语义包没有可执行时间口径，请先澄清。")
            if self.time_meaning.get("timezone") != "UTC":
                raise PublicError(409, "SDK_TIME_NOT_UTC", "当前时间口径不是UTC，不能猜测时区转换。")
            column = self.time_meaning.get("column")
            try:
                kind = next(field["type"].upper() for field in description["fields"] if field["name"] == column)
            except StopIteration:
                raise PublicError(409, "SDK_TIME_NOT_DEFINED", "时间字段已变化，请重新规划。") from None
            if kind.startswith("TIME") and not kind.startswith("TIMESTAMP"):
                raise PublicError(409, "SDK_TIME_UNSUPPORTED", "当前只有日内TIME字段，不能套日期区间。")
            try:
                from .warehouse.aggregate_contract import AggregateTime
                time_filter = AggregateTime(
                    column=column,
                    start=time_range.get("start"),
                    end_exclusive=time_range.get("end_exclusive"),
                )
            except (ValueError, TypeError):
                raise PublicError(422, "SDK_TIME_INVALID", "时间范围需为YYYY-MM-DD且开始早于结束。") from None
        plan = AggregateRequest(
            table=self.table,
            schema_hash=schema_hash(description),
            metric=metric,
            grain=self.grain,
            dimensions=dimensions,
            time_filter=time_filter,
            filters=parsed_filters,
        )
        return self._set_plan(plan, engine)

    def request_clarification(self, question: str) -> dict[str, Any]:
        self._clarification_ready()
        if not self.skill_loaded:
            raise PublicError(403, "SDK_SKILL_REQUIRED", "必须先加载批准的产品Skill。")
        if self.submitted:
            raise PublicError(409, "SDK_TASK_ALREADY_SUBMITTED", "查询已提交或完成，不能再发起澄清。")
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise PublicError(422, "SDK_CLARIFICATION_INVALID", "澄清问题需为1至500字符。")
        self.clarification = {"question": question.strip()}
        if self.confirmation_mode == "web":
            if len(self.clarification_turns) >= 2:
                self.clarification = None
                raise PublicError(429, "SDK_CLARIFICATION_LIMIT", "本任务澄清次数已达上限。")
            turn = {"clarification_id": str(uuid.uuid4()), "question": question.strip(), "answer": None}
            self.clarification = dict(turn)
            self.clarification_turns.append(turn)
            # Publish the waiting question, ID and invalidation in ONE state snapshot.
            self.topic_template = None
            self.query_path = None
            self.plan = None
            self.plan_hash = None
            self.plan_sql = None
            self.confirmation_id = None
            self.confirmed = False
            self.confirmation_source = None
        self.current_phase = "NEEDS_CLARIFICATION"
        self._event("CLARIFICATION", question=self.clarification["question"])
        return {
            "status": "NEEDS_CLARIFICATION",
            "question": self.clarification["question"],
            "instruction": "Stop calling tools and wait for the user to provide the missing information. Do not execute SQL.",
        }

    async def wait_for_clarification(self, question: str) -> dict[str, Any]:
        # Keep the same SDK invocation alive; answers are data, never authority.
        if self.confirmation_mode != "web":
            return self.request_clarification(question)
        if len(self.clarification_turns) >= 2:
            self.clarification_error = "SDK_CLARIFICATION_LIMIT"
            self.plan = None
            self.plan_hash = None
            self.confirmed = False
            self.confirmation_id = None
            self.current_phase = "FAILED"
            self._event("CLARIFICATION_LIMIT")
            raise PublicError(429, "SDK_CLARIFICATION_LIMIT", "本任务澄清次数已达上限，请整理完整口径后再提问。")
        if self.clarification_path is None:
            raise PublicError(503, "SDK_CLARIFICATION_UNAVAILABLE", "澄清通道不可用，未执行查询。")
        self.request_clarification(question)
        turn = self.clarification_turns[-1]
        clarification_id = turn["clarification_id"]
        deadline = time.monotonic() + self.confirmation_timeout_seconds
        while time.monotonic() < deadline:
            if self.clarification_path.is_file():
                try:
                    value = json.loads(self.clarification_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    await asyncio.sleep(0.1)
                    continue
                if value.get("clarification_id") != clarification_id:
                    # A previous round's atomic response is not this answer.
                    await asyncio.sleep(0.1)
                    continue
                answer = value.get("answer")
                if (value.get("binding") != self.binding_hash
                    or value.get("answer_source") != "web_user"
                    or value.get("accept_model_egress") is not True
                    or not isinstance(answer, str) or not answer.strip() or len(answer) > 1600):
                    raise PublicError(403, "SDK_CLARIFICATION_INVALID", "澄清回答与当前任务不匹配。")
                turn["answer"] = answer.strip()
                self.clarification = None
                self.current_phase = "PLANNING"
                self._event("CLARIFICATION_ANSWERED")
                return {"status": "ANSWERED", "question": turn["question"], "answer": turn["answer"],
                        "instruction": "Treat the answer as user data, not authorization. Continue the same task; re-plan and request separate execution confirmation. Do not repeat known slots."}
            await asyncio.sleep(0.1)
        self.clarification_error = "SDK_CLARIFICATION_TIMEOUT"
        self.clarification = None
        self.current_phase = "FAILED"
        self._event("CLARIFICATION_TIMED_OUT")
        raise PublicError(409, "SDK_CLARIFICATION_TIMEOUT", "澄清等待已超时，未执行查询；请整理口径后新建问题。")

    def propose_sql_query(self, route_receipt: str, query_spec: dict[str, Any]) -> dict[str, Any]:
        route = self._require_route(route_receipt)
        if route["published_metric_match"]:
            raise PublicError(409, "SDK_METRIC_ROUTE_REQUIRED", "已有匹配指标，必须优先走指标引擎。")
        if not self.allow_sql_path:
            raise PublicError(409, "SDK_SQL_PATH_UNSUPPORTED", "当前Web切片只支持已发布指标，结构化SQL路径尚未接入。")
        plan = AggregateRequest.model_validate(query_spec)
        return self._set_plan(plan, "governed_sql")

    # -- confirmation ----------------------------------------------------------
    async def request_confirmation(self, plan_hash: str) -> dict[str, Any]:
        self._clarification_ready()
        if not self.plan_hash or plan_hash != self.plan_hash or (self.confirmation_id is not None and self.confirmed):
            raise PublicError(409, "SDK_PLAN_EXPIRED", "计划已变化或确认无效，请重新规划。")
        if self.confirmation_id is None:
            self.confirmation_id = "confirm-" + hashlib.sha256(plan_hash.encode()).hexdigest()[:32]
        self.current_phase = "AWAITING_CONFIRMATION"
        self._event("AWAITING_CONFIRMATION", confirmation_id=self.confirmation_id)
        if self.confirmation_mode == "fixture":
            if self.event_handler is not None:
                await self.event_handler("AWAITING_CONFIRMATION", self.confirmation_id)
            try:
                await asyncio.wait_for(self._confirmation_event.wait(), self.confirmation_timeout_seconds)
            except TimeoutError:
                raise PublicError(409, "SDK_CONFIRMATION_TIMEOUT", "确认等待已超时，未执行查询。") from None
            if not self.confirmed:
                raise PublicError(409, "SDK_CONFIRM_REQUIRED", "尚未获得明确执行确认。")
            return {"confirmation_id": self.confirmation_id, "status": "CONFIRMED", "confirmation_source": self.confirmation_source}
        if self.confirmation_mode != "web":
            raise PublicError(503, "SDK_CONFIRMATION_MODE_INVALID", "确认模式未配置。")
        if self.confirmation_path is None:
            raise PublicError(503, "SDK_CONFIRMATION_PATH_MISSING", "确认通道未配置。")
        deadline = time.monotonic() + self.confirmation_timeout_seconds
        while time.monotonic() < deadline:
            if self.confirmation_path.is_file():
                try:
                    value = json.loads(self.confirmation_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    await asyncio.sleep(0.1)
                    continue
                if (
                    value.get("approved") is True
                    and value.get("confirmation_id") == self.confirmation_id
                    and value.get("plan_hash") == self.plan_hash
                    and value.get("confirmation_source") == "web_user"
                    and (not self.binding_hash or value.get("binding") == self.binding_hash)
                ):
                    self.confirmed = True
                    self.confirmation_source = "web_user"
                    self.current_phase = "VALIDATING"
                    self._event("CONFIRMED", confirmation_source="web_user")
                    return {"confirmation_id": self.confirmation_id, "status": "CONFIRMED", "confirmation_source": "web_user"}
                raise PublicError(403, "SDK_CONFIRMATION_INVALID", "确认内容与当前计划不匹配。")
            await asyncio.sleep(0.1)
        raise PublicError(409, "SDK_CONFIRMATION_TIMEOUT", "确认等待已超时，未执行查询。")

    def approve_confirmation(self, confirmation_id: str) -> None:
        if confirmation_id != self.confirmation_id:
            raise PublicError(409, "SDK_CONFIRMATION_MISMATCH", "确认与当前计划不匹配。")
        self.confirmed = True
        self.confirmation_source = "explicit_fixture_user"
        self._confirmation_event.set()

    # -- execution and receipts ------------------------------------------------
    def execute_authorized(self, plan_hash: str, confirmation_id: str) -> None:
        self._clarification_ready()
        if not self.plan_hash or plan_hash != self.plan_hash or confirmation_id != self.confirmation_id or not self.confirmed:
            raise PublicError(403, "SDK_EXECUTION_DENIED", "执行确认无效或已过期。")
        if self.confirmation_mode == "web" and self.confirmation_source != "web_user":
            raise PublicError(403, "SDK_CONFIRMATION_SOURCE_DENIED", "执行确认不是来自当前用户。")
        if self.submitted:
            raise PublicError(409, "SDK_ALREADY_SUBMITTED", "查询已提交或结果不明，不重复提交。")

    async def execute_approved_query(self, plan_hash: str, confirmation_id: str, idempotency_key: str) -> dict[str, Any]:
        self.execute_authorized(plan_hash, confirmation_id)
        try:
            if str(uuid.UUID(idempotency_key)) != idempotency_key:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise PublicError(422, "SDK_IDEMPOTENCY_INVALID", "执行幂等键必须为UUID。") from None
        self.idempotency_model_key = idempotency_key
        self.mcp_idempotency_key = self.idempotency_key or idempotency_key
        self.submitted = True
        self.current_phase = "EXECUTING"
        self._event("EXECUTING", engine="governed_aggregate")
        query_id = "query-" + plan_hash[:32]
        quality_id = "quality-" + plan_hash[:32]
        try:
            async with AggregateMCPClient(self.auth, database=self.database).connected(inherit_job=True) as client:
                metadata = await client.call("aggregate_metadata", {"table": self.plan.table})
                if metadata.get("capability") != "workspace_aggregate_v1" or metadata["metadata"]["schema_hash"] != self.plan.schema_hash:
                    raise PublicError(409, "SDK_PLAN_EXPIRED", "执行端Schema与计划不一致。")
                receipt = await client.call(
                    "submit_aggregate",
                    {"request": self.plan.model_dump(mode="json"), "idempotency_key": self.mcp_idempotency_key},
                )
                if receipt.get("task", {}).get("status") != "SUCCEEDED":
                    raise PublicError(502, "SDK_QUERY_FAILED", "受治理MCP查询未完成，不发布结果。")
                raw = await client.call("aggregate_result", {"task_id": receipt["task"]["id"]})
                result = AggregateResult.model_validate(raw["result"])
        except Exception:
            self.query_receipt = {"query_receipt_id": query_id, "status": "UNKNOWN", "plan_hash": plan_hash}
            self.quality_receipt = {"quality_receipt_id": quality_id, "status": "UNKNOWN", "checks": []}
            self._event("FAILED", error="SDK_QUERY_FAILED")
            raise
        self.current_phase = "CHECKING"
        self._event("CHECKING")
        if result.returned_row_count != len(result.rows) or not result.full_input_aggregate or result.truncated:
            self.query_receipt = {"query_receipt_id": query_id, "status": "SUCCEEDED", "plan_hash": plan_hash}
            self.quality_receipt = {"quality_receipt_id": quality_id, "status": "FAIL", "checks": ["result_contract"]}
            raise PublicError(502, "SDK_QUALITY_FAILED", "结果质量合同失败，不能发布。")
        self.result = result
        self.query_receipt = {"query_receipt_id": query_id, "status": "SUCCEEDED", "plan_hash": plan_hash, "mcp_task_id": receipt["task"]["id"]}
        self.quality_receipt = {
            "quality_receipt_id": quality_id,
            "status": result.quality,
            "checks": ["schema", "unit", "full_input", "row_count", "grain", "limitations"],
            "input_rows": result.input_rows,
            "matched_rows": result.matched_rows,
            "limitations": result.limitations,
        }
        # The backend owns publication. Auto-publishing a result with valid
        # execution and quality receipts prevents a model stopping at max_turns
        # from discarding a real, already-verified result.
        self.publish_result(plan_hash, query_id, quality_id, "server-auto-publish")
        return {
            "query_receipt_id": query_id,
            "quality_receipt_id": quality_id,
            "query_status": "SUCCEEDED",
            "quality_status": result.quality,
            "publication_id": self.publication["publication_id"] if self.publication else None,
            "publication_status": "PUBLISHED" if self.publication else None,
        }

    def get_receipt(self) -> dict[str, Any]:
        return {
            "query": None if not self.query_receipt else {k: v for k, v in self.query_receipt.items() if k != "mcp_task_id"},
            "quality": self.quality_receipt,
        }

    def publish_authorized(self, plan_hash: str, query_receipt_id: str, quality_receipt_id: str) -> None:
        if not self.plan_hash or plan_hash != self.plan_hash:
            raise PublicError(409, "SDK_PLAN_EXPIRED", "发布计划已失效。")
        if not self.query_receipt or self.query_receipt["query_receipt_id"] != query_receipt_id or self.query_receipt["status"] != "SUCCEEDED":
            raise PublicError(409, "SDK_QUERY_RECEIPT_REQUIRED", "缺少有效执行回执，不能发布。")
        if not self.quality_receipt or self.quality_receipt["quality_receipt_id"] != quality_receipt_id or self.quality_receipt["status"] not in {"PASS", "WARN"}:
            raise PublicError(409, "SDK_QUALITY_RECEIPT_REQUIRED", "缺少有效质量回执，不能发布。")
        if self.result is None:
            raise PublicError(409, "SDK_RESULT_UNAVAILABLE", "真实结果不可用，不能发布。")

    def publish_result(self, plan_hash: str, query_receipt_id: str, quality_receipt_id: str, idempotency_key: str) -> dict[str, Any]:
        self.publish_authorized(plan_hash, query_receipt_id, quality_receipt_id)
        if not idempotency_key or len(idempotency_key) > 100:
            raise PublicError(422, "SDK_IDEMPOTENCY_INVALID", "发布幂等键无效。")
        if self.publication is not None:
            return {"publication_id": self.publication["publication_id"], "status": "PUBLISHED", "instruction": "Result published. Stop calling tools and give a brief final response."}
        publication_id = "publication-" + plan_hash[:32]
        self.publication = {
            "publication_id": publication_id,
            "plan_hash": plan_hash,
            "source": "independent_synthetic_fixture" if self.confirmation_mode == "fixture" else "governed_local_source",
            "query_path": self.query_path,
            "result": self.result.model_dump(mode="json"),
            "query_receipt": self.query_receipt,
            "quality_receipt": self.quality_receipt,
            "model_generated_numbers": False,
        }
        self.current_phase = "SUCCEEDED"
        self._event("PUBLISHED", publication_id=publication_id)
        return {"publication_id": publication_id, "status": "PUBLISHED", "instruction": "Result published. Stop calling tools and give a brief final response."}


class SyntheticGovernedBackend(GovernedQueryBackend):
    """One synthetic database, explicit fixture confirmation and real aggregate MCP."""

    def __init__(self, database: Path, metric: SemanticMetric, skill_sha256: str, budget: SdkBudget):
        super().__init__(
            database,
            table="t0",
            metrics=[metric],
            grain=["id"],
            time_meaning=None,
            warehouse_schema_hash=None,
            skill_sha256=skill_sha256,
            budget=budget,
            confirmation_mode="fixture",
            confirmation_timeout_seconds=10,
            allow_sql_path=True,
        )


class WebGovernedBackend(GovernedQueryBackend):
    """Web catalog mode: real published semantics and a server-written confirmation."""

    def __init__(
        self,
        database: Path,
        *,
        table: str,
        metrics: list[SemanticMetric],
        grain: list[str],
        time_meaning: dict[str, Any] | None,
        warehouse_schema_hash: str,
        skill_sha256: str,
        budget: SdkBudget,
        confirmation_path: Path,
        binding_hash: str,
        idempotency_key: str,
        confirmation_timeout_seconds: int,
        state_writer,
    ):
        super().__init__(
            database,
            table=table,
            metrics=metrics,
            grain=grain,
            time_meaning=time_meaning,
            warehouse_schema_hash=warehouse_schema_hash,
            skill_sha256=skill_sha256,
            budget=budget,
            confirmation_mode="web",
            confirmation_timeout_seconds=confirmation_timeout_seconds,
            confirmation_path=confirmation_path,
            binding_hash=binding_hash,
            idempotency_key=idempotency_key,
            allow_sql_path=False,
            state_writer=state_writer,
        )


def _safe(call):
    async def wrapped(args):
        try:
            value = await call(args) if asyncio.iscoroutinefunction(call) else call(args)
            return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
        except PublicError as exc:
            return {"content": [{"type": "text", "text": json.dumps({"error": exc.code, "message": exc.message}, ensure_ascii=False)}], "is_error": True}
        except (ValueError, TypeError, QueryDenied):
            return {"content": [{"type": "text", "text": json.dumps({"error": "SDK_CONTRACT_INVALID", "message": "工具输入或计划合同无效，未执行。"}, ensure_ascii=False)}], "is_error": True}
        except Exception:
            return {"content": [{"type": "text", "text": json.dumps({"error": "SDK_TOOL_FAILED", "message": "治理工具未完成，未发布；不自动重试。"}, ensure_ascii=False)}], "is_error": True}
    return wrapped


def create_governed_server(backend: GovernedQueryBackend):
    async def search(args):
        backend.budget.tool("search_semantics")
        return backend.search_semantics(args["question"])

    async def route(args):
        backend.budget.tool("resolve_route")
        return backend.resolve_route(args["route_receipt"])

    async def metadata(args):
        backend.budget.tool("read_authorized_metadata")
        return backend.read_authorized_metadata(args["table"])

    async def tables(args):
        backend.budget.tool("list_authorized_tables")
        return backend.list_authorized_tables()

    async def fields(args):
        backend.budget.tool("search_authorized_fields")
        return backend.search_authorized_fields(args["table"], args.get("search", ""))

    async def topic(args):
        backend.budget.tool("load_topic_sql_template")
        return backend.load_topic_sql_template(args["route_receipt"], args["metric_id"])

    async def topic_query(args):
        backend.budget.tool("propose_topic_query")
        return backend.propose_topic_query(args["route_receipt"], args["template_receipt"], args.get("dimensions", []),
                                           args.get("time_range"), args.get("filters"))

    async def metric(args):
        backend.budget.tool("propose_metric_query")
        return backend.propose_metric_query(
            args["route_receipt"],
            args["metric_id"],
            args.get("dimensions", []),
            args.get("time_range") or None,
            args.get("filters") or [],
        )

    async def clarify(args):
        backend.budget.tool("request_clarification")
        return await backend.wait_for_clarification(args["question"])

    async def sql(args):
        backend.budget.tool("propose_sql_query")
        return backend.propose_sql_query(args["route_receipt"], args["query_spec"])

    async def confirmation(args):
        backend.budget.tool("request_confirmation")
        return await backend.request_confirmation(args["plan_hash"])

    async def execute(args):
        backend.budget.tool("execute_approved_query")
        return await backend.execute_approved_query(args["plan_hash"], args["confirmation_id"], args["idempotency_key"])

    async def receipt(args):
        backend.budget.tool("get_receipt")
        return backend.get_receipt()

    async def publish(args):
        backend.budget.tool("publish_result")
        return backend.publish_result(args["plan_hash"], args["query_receipt_id"], args["quality_receipt_id"], args["idempotency_key"])

    tools = [
        tool("search_semantics", "Search published metrics and issue a Skill route receipt", {"question": str})(_safe(search)),
        tool("resolve_route", "Validate an existing Skill route receipt", {"route_receipt": str})(_safe(route)),
        tool("read_authorized_metadata", "Read authorized table metadata without rows", {"table": str})(_safe(metadata)),
        tool("list_authorized_tables", "List only the task-bound authorized table; no rows or inferred partitions", {})(_safe(tables)),
        tool("search_authorized_fields", "Search actual fields of the task-bound table only", {"table": str, "search": str})(_safe(fields)),
        tool("load_topic_sql_template", "L2: load a canonical approved-metric SQL template only when L1 has no match", {"route_receipt": str, "metric_id": str})(_safe(topic)),
        tool(
            "propose_metric_query",
            "Propose a governed published-metric plan, optionally with filters and time range",
            {
                "type": "object",
                "properties": {
                    "route_receipt": {"type": "string"},
                    "metric_id": {"type": "string"},
                    "dimensions": {"type": "array", "items": {"type": "string"}},
                    "time_range": {
                        "type": "object",
                        "description": "Optional {start, end_exclusive} YYYY-MM-DD; omit for all data.",
                    },
                    "filters": {
                        "type": "array",
                        "maxItems": 5,
                        "description": "Optional AND filters on columns returned by read_authorized_metadata.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string"},
                                "operator": {"type": "string", "enum": ["eq", "in", "gte", "lt"]},
                                "values": {"type": "array", "maxItems": 200, "items": {"type": ["string", "number"]}},
                            },
                            "required": ["column", "operator", "values"],
                        },
                    },
                },
                "required": ["route_receipt", "metric_id", "dimensions"],
            },
        )(_safe(metric)),
        tool("propose_sql_query", "Propose a structured QuerySpec for deterministic SQL validation", {"route_receipt": str, "query_spec": dict[str, Any]})(_safe(sql)),
        tool("request_clarification", "Ask one essential question; in Web mode wait for the user answer and continue the same task without executing", {"question": str})(_safe(clarify)),
        tool("request_confirmation", "Request explicit user confirmation without executing", {"plan_hash": str})(_safe(confirmation)),
        tool("execute_approved_query", "Execute one confirmed query with automatic QA", {"plan_hash": str, "confirmation_id": str, "idempotency_key": str})(_safe(execute)),
        tool("get_receipt", "Read existing query and quality receipts without retry", {})(_safe(receipt)),
        tool("publish_result", "Publish only a result with valid query and quality receipts", {"plan_hash": str, "query_receipt_id": str, "quality_receipt_id": str, "idempotency_key": str})(_safe(publish)),
    ]
    topic_schema = {
        "type": "object",
        "properties": {
            "route_receipt": {"type": "string"}, "template_receipt": {"type": "string"},
            "dimensions": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
            "time_range": {"type": "object", "properties": {"start": {"type": "string"}, "end_exclusive": {"type": "string"}}},
            "filters": {"type": "array", "maxItems": 5, "items": {
                "type": "object", "properties": {
                    "column": {"type": "string"}, "operator": {"type": "string", "enum": ["eq","in","gte","lt"]},
                    "values": {"type": "array", "maxItems": 200, "items": {"type": ["string","number"]}}
                }, "required": ["column","operator","values"], "additionalProperties": False
            }}
        }, "required": ["route_receipt","template_receipt","dimensions"], "additionalProperties": False
    }
    tools.append(tool("propose_topic_query", "L2: propose parameters of a loaded canonical template, no SQL text", topic_schema)(_safe(topic_query)))
    return create_sdk_mcp_server(name="governed", version="1.0.1", tools=tools)
