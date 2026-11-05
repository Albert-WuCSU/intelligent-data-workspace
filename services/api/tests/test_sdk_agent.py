"""Offline Claude Agent SDK fixture and governance tests; no real model or company gateway."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from uuid import uuid4

import pytest

from data_workspace.auth import PublicError
from data_workspace.sdk_agent_backend import SdkBudget, SyntheticGovernedBackend, _safe
from data_workspace.sdk_agent_runner import SdkRunnerConfig, install_versioned_skill, minimal_runner_environment
from data_workspace.sdk_process import run_sdk_process
from data_workspace.semantic_contracts import SemanticMetric
from data_workspace.source_profiles import ProfileDraft, SourceStore
from data_workspace.warehouse.aggregate_contract import AggregateRequest, schema_hash
from data_workspace.warehouse.local_file import LocalFileWarehouse
from data_workspace.warehouse.policy import QueryDenied

QUESTION = "What is total amount?"
FIXTURE_TOKEN = "fixture-only-not-a-credential"


def fixture(tmp_path):
    source = tmp_path / "allowed" / "rows.csv"
    source.parent.mkdir(parents=True)
    source.write_text(
        "id,region,amount,cost,created_at\n"
        + "".join(f'{i},{"A" if i % 2 else "B"},{i},1,2026-10-{(i % 20) + 1:02}\n' for i in range(1, 151)),
        encoding="utf-8",
    )
    store = SourceStore(tmp_path / "connections", source.parent)
    database, _ = store.snapshot(ProfileDraft(name="sdk fixture", path=str(source), usage_authorized=True))
    return database


def metric():
    return SemanticMetric(id="total", name="Total amount", operator="sum", column="amount", unit="declared units", additive=True)


def backend(tmp_path):
    return SyntheticGovernedBackend(fixture(tmp_path), metric(), "a" * 64, SdkBudget())


def test_skill_install_and_minimal_env_exclude_host(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_HOST_KEY", "must-not-leak")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "must-not-leak")
    installation = install_versioned_skill(tmp_path / "runtime", str(uuid4()))
    assert (installation.plugin / "skills/data-query/SKILL.md").is_file()
    assert (installation.plugin / ".claude-plugin/plugin.json").is_file()
    assert not (installation.cwd / ".claude/settings.json").exists()
    assert not (installation.cwd / ".claude/settings.local.json").exists()
    assert not (installation.cwd / "CLAUDE.md").exists()
    env = minimal_runner_environment(installation.home, installation.config, installation.temp)
    assert env["SDK_RUNNER_MINIMAL"] == "1"
    assert not {"SENTINEL_HOST_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OTEL_EXPORTER_OTLP_ENDPOINT"} & set(env)
    assert not {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"} & set(env)
    assert "must-not-leak" not in json.dumps(env)


def test_budget_is_cumulative_and_bounded():
    budget = SdkBudget()
    budget.model_step("same")
    budget.model_step("same")
    assert budget.model_steps == 1
    for index in range(7):
        budget.model_step(f"m{index}")
    with pytest.raises(PublicError, match="SDK_TURN_BUDGET_EXCEEDED"):
        budget.model_step("overflow")
    for _ in range(10):
        budget.tool("Skill")
    with pytest.raises(PublicError, match="SDK_TOOL_BUDGET_EXCEEDED"):
        budget.tool("Skill")
    limited = SdkBudget(max_metadata_calls=3)
    for _ in range(3):
        limited.tool("search_semantics")
    with pytest.raises(PublicError, match="SDK_METADATA_BUDGET_EXCEEDED"):
        limited.tool("read_authorized_metadata")
    with pytest.raises(PublicError, match="SDK_TOKEN_BUDGET_EXCEEDED"):
        budget.usage({"claude": {"inputTokens": 60_000, "outputTokens": 40_001, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}})


def test_metric_backend_real_mcp_confirmation_qa_and_receipt_gate(tmp_path):
    async def scenario():
        subject = backend(tmp_path)
        with pytest.raises(PublicError, match="SDK_SKILL_REQUIRED"):
            subject.search_semantics(QUESTION)
        with pytest.raises(PublicError, match="SDK_SKILL_DENIED"):
            subject.record_skill("governed:data-query", "wrong")
        subject.record_skill("governed:data-query", "a" * 64)
        route = subject.search_semantics(QUESTION)
        assert route["published_metric_match"] is True
        metadata = subject.read_authorized_metadata("t0")
        assert metadata["table"] == "main.data" and metadata["fields"]
        with pytest.raises(PublicError, match="SDK_SOURCE_DENIED"):
            subject.read_authorized_metadata("other")
        plan = subject.propose_metric_query(route["route_receipt"], "total", [])
        with pytest.raises(PublicError, match="SDK_EXECUTION_DENIED"):
            subject.execute_authorized(plan["plan_hash"], "wrong")
        pending = asyncio.create_task(subject.request_confirmation(plan["plan_hash"]))
        for _ in range(20):
            if subject.confirmation_id:
                break
            await asyncio.sleep(0)
        with pytest.raises(PublicError, match="SDK_EXECUTION_DENIED"):
            subject.execute_authorized(plan["plan_hash"], subject.confirmation_id)
        subject.approve_confirmation(subject.confirmation_id)
        confirmation = await pending
        assert confirmation["confirmation_source"] == "explicit_fixture_user"
        execution_key = str(uuid4())
        execution = await subject.execute_approved_query(plan["plan_hash"], subject.confirmation_id, execution_key)
        assert execution["query_status"] == "SUCCEEDED" and execution["quality_status"] == "PASS"
        assert "11325" not in json.dumps(execution)
        with pytest.raises(PublicError, match="SDK_ALREADY_SUBMITTED"):
            await subject.execute_approved_query(plan["plan_hash"], subject.confirmation_id, execution_key)
        with pytest.raises(PublicError, match="SDK_TASK_ALREADY_SUBMITTED"):
            subject.search_semantics(QUESTION)
        receipts = subject.get_receipt()
        assert "mcp_task_id" not in receipts["query"] and receipts["quality"]["status"] == "PASS"
        publication = subject.publish_result(plan["plan_hash"], execution["query_receipt_id"], execution["quality_receipt_id"], str(uuid4()))
        assert publication["status"] == "PUBLISHED"
        assert subject.publication["result"]["rows"] == [[11325]]
        assert subject.publication["result"]["input_rows"] == 150
        assert subject.publication["model_generated_numbers"] is False
    asyncio.run(scenario())


def test_sql_path_requires_no_metric_match_and_deterministic_contract(tmp_path):
    subject = backend(tmp_path)
    subject.record_skill("governed:data-query", "a" * 64)
    route = subject.search_semantics("custom aggregation without published metric")
    description = LocalFileWarehouse(subject.database).describe("t0")
    spec = AggregateRequest(table="t0", schema_hash=schema_hash(description), metric=metric(), grain=["id"])
    plan = subject.propose_sql_query(route["route_receipt"], spec.model_dump(mode="json"))
    assert plan["engine"] == "governed_sql" and len(plan["plan_hash"]) == 64
    matched = subject.search_semantics(QUESTION)
    with pytest.raises(PublicError, match="SDK_METRIC_ROUTE_REQUIRED"):
        subject.propose_sql_query(matched["route_receipt"], spec.model_dump(mode="json"))
    bad = spec.model_dump(mode="json")
    bad["table"] = "other"
    unmatched = subject.search_semantics("another unmatched request")
    with pytest.raises((PublicError, QueryDenied, ValueError)):
        subject.propose_sql_query(unmatched["route_receipt"], bad)


def test_publish_cannot_bypass_query_or_quality_receipt(tmp_path):
    subject = backend(tmp_path)
    subject.plan_hash = "a" * 64
    with pytest.raises(PublicError, match="SDK_QUERY_RECEIPT_REQUIRED"):
        subject.publish_authorized(subject.plan_hash, "query-x", "quality-x")


def test_route_change_invalidates_unexecuted_plan(tmp_path):
    subject = backend(tmp_path)
    subject.record_skill("governed:data-query", "a" * 64)
    route = subject.search_semantics(QUESTION)
    plan = subject.propose_metric_query(route["route_receipt"], "total", [])
    subject.confirmation_id = "confirm-old"
    subject.search_semantics("different unmatched question")
    with pytest.raises(PublicError, match="SDK_EXECUTION_DENIED"):
        subject.execute_authorized(plan["plan_hash"], "confirm-old")


def test_safe_tool_errors_never_echo_raw_exception_details():
    async def invalid(args):
        raise ValueError("raw-sensitive-validation-detail")

    async def unexpected(args):
        raise RuntimeError("raw-sensitive-internal-detail")

    first = asyncio.run(_safe(invalid)({}))
    second = asyncio.run(_safe(unexpected)({}))
    assert first["is_error"] is True and first["content"][0]["text"].find("SDK_CONTRACT_INVALID") >= 0
    assert second["is_error"] is True and second["content"][0]["text"].find("SDK_TOOL_FAILED") >= 0
    assert "raw-sensitive" not in json.dumps([first, second])


def test_wallclock_must_be_finite_and_bounded(tmp_path):
    with pytest.raises(PublicError, match="SDK_WALLCLOCK_INVALID"):
        SdkRunnerConfig.from_dict({
            "database": str(fixture(tmp_path)),
            "question": QUESTION,
            "base_url": "http://127.0.0.1:12345",
            "runtime_root": str(tmp_path / "runtime"),
            "task_id": str(uuid4()),
            "wall_clock_seconds": 0,
        })


def test_real_gateway_experiment_is_exactly_gated(tmp_path, monkeypatch):
    monkeypatch.setenv("SDK_RUNNER_MINIMAL", "1")
    monkeypatch.setenv("SDK_RUNNER_JOB", "1")
    monkeypatch.delenv("SDK_EXPERIMENT_AUTH_TOKEN", raising=False)
    database = fixture(tmp_path)

    def config(**overrides):
        value = {
            "database": str(database),
            "question": QUESTION,
            "base_url": "http://ada-cli-golang.ctripcorp.com/coding-plan",
            "runtime_root": str(tmp_path / "runtime"),
            "task_id": str(uuid4()),
            "model": "deepseek-v4.1-flash",
            "mode": "real_gateway_experiment",
            "wall_clock_seconds": 120,
        }
        value.update(overrides)
        return SdkRunnerConfig.from_dict(value)

    with pytest.raises(PublicError, match="SDK_GATEWAY_NOT_APPROVED"):
        config(base_url="http://evil.example/coding-plan").validate()
    with pytest.raises(PublicError, match="SDK_GATEWAY_NOT_APPROVED"):
        config(base_url="http://ada-cli-golang.ctripcorp.com/v1/messages").validate()
    with pytest.raises(PublicError, match="SDK_MODEL_NOT_APPROVED"):
        config(model="claude-sonnet-5-5").validate()
    with pytest.raises(PublicError, match="SDK_MODEL_NOT_APPROVED"):
        config(model="deepseek-v4-1-flash-261017").validate()
    with pytest.raises(PublicError, match="SDK_EXPERIMENT_KEY_REQUIRED"):
        config().validate()
    with pytest.raises(PublicError, match="SDK_GATEWAY_NOT_APPROVED"):
        config(mode="fixture", model="claude-sonnet-5-5").validate()

    monkeypatch.setenv("SDK_EXPERIMENT_AUTH_TOKEN", "x" * 32)
    config().validate()


def values(document, key):
    found = []
    def visit(value):
        if isinstance(value, dict):
            for name, item in value.items():
                if name == key and isinstance(item, str):
                    found.append(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str) and value[:1] in {"{", "["}:
            try:
                parsed = json.loads(value)
            except ValueError:
                return
            visit(parsed)
    visit(document)
    if not found:
        raise AssertionError(f"missing {key} in model conversation")
    return found[-1]


class FakeGateway(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self):
        super().__init__(("127.0.0.1", 0), FakeHandler)
        self.step = 0
        self.requests = []
        self.errors = []
        self.auth_ok = True
        self.rows_leaked = False
        self.skill_context_seen = False
        self.host_context_leaked = False
        self.text_only = False
        self.topic_path = False
        self.response_model = "claude-sonnet-5-5"
        self.clarify = False
        self.clarify_continue = False
        self.filters = []
        self.after_publish_tool = False


class FakeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        if self.path == "/api/hello":
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        try:
            if self.path not in {"/v1/messages", "/v1/messages?beta=true"}:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if len(raw) > 2 * 1024 * 1024:
                raise AssertionError("fixture request too large")
            if self.headers.get("Authorization") != "Bearer " + FIXTURE_TOKEN:
                self.server.auth_ok = False
                raise AssertionError("unexpected fixture credential")
            body = json.loads(raw)
            self.server.requests.append(body)
            self.server.response_model = body.get("model", "claude-sonnet-5-5")
            if "11325" in raw.decode("utf-8"):
                self.server.rows_leaked = True
            if "Data query skill" in raw.decode("utf-8"):
                self.server.skill_context_seen = True
            if "Behavioral guidelines to reduce common LLM coding mistakes" in raw.decode("utf-8") or ".claude\\CLAUDE.md" in raw.decode("utf-8"):
                self.server.host_context_leaked = True
            self.server.step += 1
            step = self.server.step
            if self.server.clarify and self.server.clarify_continue and step <= 2:
                if step == 1:
                    self.tool(step, "Skill", {"skill": "governed:data-query"})
                else:
                    self.tool(step, "mcp__governed__request_clarification", {"question": "Which time range should I use?"})
                return
            logic_step = step - 1 if self.server.clarify_continue else step
            if self.server.topic_path:
                if step == 1: self.tool(step, "Skill", {"skill": "governed:data-query"})
                elif step == 2: self.tool(step, "mcp__governed__search_semantics", {"question": "unmapped custom request"})
                elif step == 3: self.tool(step, "mcp__governed__list_authorized_tables", {})
                elif step == 4: self.tool(step, "mcp__governed__search_authorized_fields", {"table": "t0", "search": "region"})
                elif step == 5: self.tool(step, "mcp__governed__load_topic_sql_template", {"route_receipt": values(body,"route_receipt"), "metric_id": "total"})
                elif step == 6: self.tool(step, "mcp__governed__propose_topic_query", {"route_receipt": values(body,"route_receipt"), "template_receipt": values(body,"template_receipt"), "dimensions": ["region"], "filters": [{"column":"amount","operator":"gte","values":[100]}]})
                elif step == 7: self.tool(step, "mcp__governed__request_confirmation", {"plan_hash": values(body,"plan_hash")})
                elif step == 8: self.tool(step, "mcp__governed__execute_approved_query", {"plan_hash": values(body,"plan_hash"), "confirmation_id": values(body,"confirmation_id"), "idempotency_key":"00000000-0000-4000-8000-000000000001"})
                elif step == 9: self.text(step, "主题模板查询已经通过执行与质量回执，口径、来源和限制见正文报告。")
                else: raise AssertionError("topic fixture exceeded finite loop")
            elif self.server.text_only:
                self.text(step, "No tool needed.")
            elif self.server.clarify and not self.server.clarify_continue:
                if step == 1:
                    self.tool(step, "Skill", {"skill": "governed:data-query"})
                elif step == 2:
                    self.tool(step, "mcp__governed__request_clarification", {"question": "Which time range should I use?"})
                elif step == 3:
                    self.text(step, "Please provide the time range.")
                else:
                    raise AssertionError("clarification fixture exceeded scripted finite loop")
            elif logic_step == 1:
                self.tool(step, "Skill", {"skill": "governed:data-query"})
            elif logic_step == 2:
                self.tool(step, "mcp__governed__search_semantics", {"question": QUESTION})
            elif logic_step == 3:
                self.tool(step, "mcp__governed__read_authorized_metadata", {"table": "t0"})
            elif logic_step == 4:
                self.tool(step, "mcp__governed__propose_metric_query", {"route_receipt": values(body, "route_receipt"), "metric_id": "total", "dimensions": [], "time_range": {}, "filters": self.server.filters})
            elif logic_step == 5:
                self.tool(step, "mcp__governed__request_confirmation", {"plan_hash": values(body, "plan_hash")})
            elif logic_step == 6:
                self.tool(step, "mcp__governed__execute_approved_query", {"plan_hash": values(body, "plan_hash"), "confirmation_id": values(body, "confirmation_id"), "idempotency_key": "00000000-0000-4000-8000-000000000001"})
            elif logic_step == 7:
                self.tool(step, "mcp__governed__publish_result", {"plan_hash": values(body, "plan_hash"), "query_receipt_id": values(body, "query_receipt_id"), "quality_receipt_id": values(body, "quality_receipt_id"), "idempotency_key": "sdk-e2e-publish-1"})
            elif logic_step == 8:
                if self.server.after_publish_tool:
                    self.tool(step, "mcp__governed__get_receipt", {})
                else:
                    self.text(step, "查询已完成，请查看经质量核验的结果卡。")
            else:
                raise AssertionError("model exceeded scripted finite loop")
        except Exception as exc:
            self.server.errors.append(f"{type(exc).__name__}: {exc}")
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def events(self, step, block, stop_reason):
        message = {"id": f"msg_sdk_fixture_{step}", "type": "message", "role": "assistant", "model": self.server.response_model, "content": [], "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 50, "output_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}
        yield "message_start", {"type": "message_start", "message": message}
        yield "content_block_start", {"type": "content_block_start", "index": 0, "content_block": block}
        if block["type"] == "tool_use":
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"], separators=(",", ":"))}
        else:
            delta = {"type": "text_delta", "text": block["text"]}
        yield "content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}
        yield "content_block_stop", {"type": "content_block_stop", "index": 0}
        yield "message_delta", {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None}, "usage": {"output_tokens": 20}}
        yield "message_stop", {"type": "message_stop"}

    def respond(self, step, block, stop_reason):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for event, data in self.events(step, block, stop_reason):
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode())
            self.wfile.flush()
        self.close_connection = True

    def tool(self, step, name, tool_input):
        self.respond(step, {"type": "tool_use", "id": f"toolu_sdk_fixture_{step}", "name": name, "input": tool_input}, "tool_use")

    def text(self, step, text):
        self.respond(step, {"type": "text", "text": text}, "end_turn")


def test_full_sdk_cli_loop_with_fake_gateway_and_real_synthetic_mcp(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_HOST_KEY", "must-not-leak")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    database = fixture(tmp_path)
    server = FakeGateway()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    task_id = str(uuid4())
    runtime = tmp_path / "runtime"
    config_path = tmp_path / "sdk-config.json"
    output_path = tmp_path / "sdk-output.json"
    config_path.write_text(json.dumps({
        "database": str(database),
        "question": QUESTION,
        "base_url": f"http://127.0.0.1:{server.server_port}",
        "runtime_root": str(runtime),
        "task_id": task_id,
        "model": "claude-sonnet-5-5",
        "auto_confirm_fixture": True,
        "wall_clock_seconds": 120,
    }), encoding="utf-8")
    env = minimal_runner_environment(tmp_path / "outer-home", tmp_path / "outer-config", tmp_path / "outer-temp")
    env["SDK_FIXTURE_DEBUG"] = "1"
    assert "SENTINEL_HOST_KEY" not in env and "ANTHROPIC_API_KEY" not in env
    try:
        completed = run_sdk_process(config_path, output_path, tmp_path / "runner-stdout.txt", tmp_path / "runner-stderr.txt", env)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)
    (tmp_path / "gateway-requests.json").write_text(json.dumps(server.requests, ensure_ascii=False, indent=2), encoding="utf-8")
    diagnostics = {
        "process": {k: v for k, v in completed.items() if k != "result"},
        "stdout": (tmp_path / "runner-stdout.txt").read_text(encoding="utf-8", errors="replace"),
        "stderr": (tmp_path / "runner-stderr.txt").read_text(encoding="utf-8", errors="replace"),
        "gateway_errors": server.errors,
        "gateway_steps": server.step,
    }
    (tmp_path / "diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    assert completed["returncode"] == 0, diagnostics
    result = completed["result"]
    assert result["status"] == "SUCCEEDED", diagnostics
    assert result["capability"]["implementation"] == "claude_agent_sdk_skills_v1"
    assert result["capability"]["real_gateway_available"] is False
    assert result["skill"]["version"] == "1.0.6"
    assert result["query_receipt"]["status"] == "SUCCEEDED"
    assert result["quality_receipt"]["status"] == "PASS"
    assert result["publication"]["result"]["rows"] == [[11325]]
    assert result["publication"]["result"]["input_rows"] == 150
    assert result["publication"]["model_generated_numbers"] is False
    assert result["result_rows_returned_to_model"] is False
    assert result["real_gateway_called"] is False and result["production_sql_executed"] is False
    assert result["budget"]["model_steps"] == 8
    assert result["budget"]["tool_calls"] == 7
    assert result["budget"]["metadata_calls"] == 2
    assert result["budget"]["total_tokens"] <= 100_000
    assert result["stream_events"] > 0
    assert "11325" not in result["model_text"]
    assert server.step == 8 and not server.errors
    assert server.auth_ok and not server.rows_leaked and server.skill_context_seen and not server.host_context_leaked
    assert completed["timed_out"] is False
    assert completed["job_memory_limit"] == 2 * 1024 * 1024 * 1024
    assert completed["job_process_limit"] == 10
    assert completed["job_peak_processes"] <= completed["job_process_limit"]


def test_publication_survives_max_turns_after_backend_publish(tmp_path, monkeypatch):
    database = fixture(tmp_path)
    server = FakeGateway()
    server.after_publish_tool = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    task_id = str(uuid4())
    runtime = tmp_path / "runtime"
    config_path = tmp_path / "sdk-config.json"
    output_path = tmp_path / "sdk-output.json"
    config_path.write_text(json.dumps({
        "database": str(database),
        "question": QUESTION,
        "base_url": f"http://127.0.0.1:{server.server_port}",
        "runtime_root": str(runtime),
        "task_id": task_id,
        "model": "claude-sonnet-5-5",
        "auto_confirm_fixture": True,
        "wall_clock_seconds": 120,
    }), encoding="utf-8")
    env = minimal_runner_environment(tmp_path / "outer-home", tmp_path / "outer-config", tmp_path / "outer-temp")
    env["SDK_FIXTURE_DEBUG"] = "1"
    try:
        completed = run_sdk_process(config_path, output_path, tmp_path / "runner-stdout.txt", tmp_path / "runner-stderr.txt", env)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)
    assert completed["returncode"] == 0, completed
    result = completed["result"]
    assert result["status"] == "SUCCEEDED"
    assert result["loop_status"] == "error_max_turns"
    assert result["publication"]["result"]["rows"] == [[11325]]
    assert result["query_receipt"]["status"] == "SUCCEEDED"
    assert result["quality_receipt"]["status"] == "PASS"


def test_failure_diagnostics_written_for_missing_publication(tmp_path):
    database = fixture(tmp_path)
    server = FakeGateway()
    server.text_only = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    task_id = str(uuid4())
    runtime = tmp_path / "runtime"
    config_path = tmp_path / "sdk-config.json"
    output_path = tmp_path / "sdk-output.json"
    config_path.write_text(json.dumps({
        "database": str(database),
        "question": QUESTION,
        "base_url": f"http://127.0.0.1:{server.server_port}",
        "runtime_root": str(runtime),
        "task_id": task_id,
        "model": "claude-sonnet-5-5",
        "auto_confirm_fixture": True,
        "wall_clock_seconds": 60,
    }), encoding="utf-8")
    env = minimal_runner_environment(tmp_path / "outer-home", tmp_path / "outer-config", tmp_path / "outer-temp")
    env["SDK_FIXTURE_DEBUG"] = "1"
    try:
        completed = run_sdk_process(config_path, output_path, tmp_path / "runner-stdout.txt", tmp_path / "runner-stderr.txt", env)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)
    assert completed["returncode"] == 2
    assert completed["result"]["status"] == "FAILED"
    assert completed["result"]["error"] == "SDK_PUBLICATION_MISSING"
    diagnostic_path = runtime / task_id / "failure-diagnostics.json"
    assert diagnostic_path.is_file()
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    assert diagnostic["status"] == "FAILED"
    assert diagnostic["error"] == "SDK_PUBLICATION_MISSING"
    assert diagnostic["model_text"] == "No tool needed."
    assert diagnostic["usage"]
    assert diagnostic["events"] and diagnostic["budget"]["model_steps"] == 1
    assert not server.errors


def test_web_clarification_rounds_invalidate_confirmation_and_bound_wait(tmp_path):
    subject = backend(tmp_path)
    subject.confirmation_mode = "web"
    subject.confirmation_timeout_seconds = 1
    subject.clarification_path = tmp_path / "answer.json"
    subject.binding_hash = "b" * 64
    subject.record_skill("governed:data-query", "a" * 64)
    route = subject.search_semantics(QUESTION)
    original = subject.propose_metric_query(route["route_receipt"], "total", [])
    original_hash = original["plan_hash"]
    subject.confirmed = True
    subject.confirmation_id = "old-confirm"
    async def scenario():
        for index in range(2):
            waiting = asyncio.create_task(subject.wait_for_clarification("Which scope?"))
            await asyncio.sleep(0.01)
            current_id = subject.clarification["clarification_id"]
            assert subject.plan is None and not subject.confirmed and subject.confirmation_id is None
            assert not subject.submitted
            with pytest.raises(PublicError):
                subject.propose_metric_query(route["route_receipt"], "total", [])
            with pytest.raises(PublicError):
                subject.execute_authorized(original_hash,"old-confirm")
            # Wrong/old clarification cannot become the current answer.
            subject.clarification_path.write_text(json.dumps({"clarification_id":"old","answer":"bad"}),encoding="utf-8")
            await asyncio.sleep(0.12)
            assert not waiting.done()
            subject.clarification_path.write_text(json.dumps({"clarification_id":current_id,"answer":"All time","binding":subject.binding_hash,"answer_source":"web_user","accept_model_egress":True}),encoding="utf-8")
            result = await waiting
            assert result["status"] == "ANSWERED" and subject.clarification is None
            plan = subject.propose_metric_query(route["route_receipt"], "total", [])
            assert plan["plan_hash"] != original_hash and not subject.confirmed

        with pytest.raises(PublicError) as error:
            await subject.wait_for_clarification("One more?")
        assert error.value.code == "SDK_CLARIFICATION_LIMIT" and len(subject.clarification_turns) == 2
        assert subject.clarification_error == "SDK_CLARIFICATION_LIMIT" and subject.current_phase == "FAILED"
        with pytest.raises(PublicError):
            subject.propose_metric_query(route["route_receipt"], "total", [])
    asyncio.run(scenario())


def test_web_clarification_timeout_disables_execution(tmp_path):
    subject = backend(tmp_path)
    subject.confirmation_mode = "web"
    subject.confirmation_timeout_seconds = 0.1
    subject.clarification_path = tmp_path / "answer.json"
    subject.record_skill("governed:data-query", "a" * 64)
    async def scenario():
        with pytest.raises(PublicError) as error:
            await subject.wait_for_clarification("Which scope?")
        assert error.value.code == "SDK_CLARIFICATION_TIMEOUT"
        assert subject.current_phase == "FAILED" and subject.clarification is None
        with pytest.raises(PublicError):
            subject.execute_authorized("old", "old")
        assert not subject.submitted and subject.publication is None
    asyncio.run(scenario())


def test_publication_requires_nonempty_measured_usage_receipt():
    from data_workspace.sdk_agent_runner import valid_result_usage
    for usage in (None, {}, {"m":{}}, {"m":{"inputTokens":0,"outputTokens":0}},
                  {"m":{"inputTokens":1}}, {"m":{"inputTokens":True,"outputTokens":1}},
                  {"m":{"inputTokens":-1,"outputTokens":1}}, {"m":{"inputTokens":"1","outputTokens":1}}):
        assert not valid_result_usage(usage)
    assert valid_result_usage({"m":{"inputTokens":1,"outputTokens":0}})
    assert valid_result_usage({"m":{"inputTokens":0,"outputTokens":0,"cacheReadInputTokens":10}})
