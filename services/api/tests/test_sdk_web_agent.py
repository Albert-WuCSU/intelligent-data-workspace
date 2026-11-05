"""Web task binding to the governed SDK runner; fake gateway and synthetic MCP only."""
import asyncio
import json
import threading
import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.model_budget import EstimatedBudget
from data_workspace.model_provider import MessagesProvider, ModelConfiguration
from data_workspace.sdk_agent_runner import SdkRunnerConfig
from data_workspace.semantic_contracts import PublishInput, SemanticDraftInput
from data_workspace.semantic_metadata import read_schema
from data_workspace.semantic_store import SemanticStore
from test_agent import AUTH, H, BASE, fixture, metric
from test_sdk_agent import FIXTURE_TOKEN, FakeGateway

SDK_MODEL = "deepseek-v4.1-flash"
AI_PLAN_ENDPOINT = "http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages"


def build_app(tmp_path, gateway_port):
    app = create_app(Settings(
        mode="development",
        dev_identity=True,
        sdk_web_agent=True,
        sdk_web_test_base_url=f"http://127.0.0.1:{gateway_port}",
    ))
    store, database = fixture(tmp_path)
    app.state.sources = store
    app.state.semantics = SemanticStore(tmp_path / "semantics")
    source_id = str(uuid4())
    with store.db() as db:
        db.execute(
            "INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES(?,?,?,?,?,?,?,?)",
            [source_id, store.owner(AUTH), "sdk web fixture", 1, 1, str(database), "independent fixture", "2026-11-04"],
        )
    body = SemanticDraftInput(
        domain="orders",
        name="Totals",
        owner_note="fixture only",
        source_id=source_id,
        table_id="t0",
        grain=["id"],
        grain_note="per record",
        metrics=[metric()],
    )
    draft = app.state.semantics.draft(AUTH, body)
    schema = asyncio.run(read_schema(store, AUTH, source_id, "t0"))
    published = app.state.semantics.publish(
        AUTH,
        PublishInput(draft_id=draft.draft_id, validation_id=str(uuid4()), request_id=str(uuid4()), approve_definition=True),
        draft,
        schema,
    )
    def model_response(request):
        return httpx.Response(200, json={
            "type": "message",
            "role": "assistant",
            "model": SDK_MODEL,
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "{}"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })
    app.state.model_provider = MessagesProvider(
        ModelConfiguration(AI_PLAN_ENDPOINT, SDK_MODEL, "anthropic_messages", "bearer"),
        FIXTURE_TOKEN,
        EstimatedBudget(tmp_path / "budget"),
        httpx.MockTransport(model_response),
    )
    app.state.model_provider._verified = True
    app.state.model_enabled = True
    app.state.model_preset = "ai_plan"
    model_ref = f"{app.state.model_tests.generation}:{app.state.model_provider.configuration.version}"
    return app, source_id, published, model_ref


def request_body(source_id, published, model_ref, question="What is total amount?"):
    return {
        "request_id": str(uuid4()),
        "question": question,
        "model_ref": model_ref,
        "semantic_version_id": published.id,
        "selected_source_refs": [source_id],
        "accept_model_egress": True,
    }


def wait_task(client, task_id, phase=None, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/agent/tasks/{task_id}")
        assert response.status_code == 200, response.text
        task = response.json()
        if phase is not None:
            if task["phase"] == phase:
                return task
        elif task["phase"] not in ("PLANNING", "VALIDATING", "EXECUTING", "CHECKING"):
            return task
        time.sleep(0.1)
    raise AssertionError(f"task {task_id} did not reach {phase or 'terminal'}")


@pytest.fixture
def gateway():
    server = FakeGateway()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)


def test_web_sdk_binding_uses_catalog_model_confirmation_and_receipts(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        assert response.status_code == 200, response.text
        task_id = response.json()["id"]
        task = wait_task(client, task_id, "AWAITING_CONFIRMATION")
        assert task["engine"] == "claude_agent_sdk_skills_v1"
        assert task["dialogue"] and any("search_semantics" in d["tools"] for d in task["dialogue"])
        assert any("授权表" in d["text"] for d in task["dialogue"])
        assert task["plan_hash"] and task["plan"]["metric"]["id"] == "total"
        assert task["sql"] and not task["sql_executed"]
        assert gateway.step == 5
        landed = client.post(
            f"/api/v1/agent/tasks/{task_id}/confirm",
            json={"plan_hash": task["plan_hash"], "execution_generation": task["execution_generation"], "confirm_execute": True},
            headers=H,
        )
        assert landed.status_code == 200, landed.text
        result = wait_task(client, task_id, "SUCCEEDED")
        assert result["result"]["rows"] == [[11325]]
        assert result["result"]["input_rows"] == 150 and result["result"]["full_input_aggregate"] is True
        assert result["sql_executed"] is True
        assert result["execution_receipt"]["quality_receipt"]["status"] == "PASS"
        assert result["execution_receipt"]["query_receipt"]["status"] == "SUCCEEDED"
        assert result["returned_model_id"] == SDK_MODEL
        assert result["answer"] and "结果卡" in result["answer"]
        assert result["dialogue"][-1]["tools"] == ["receipt-gated publication"]
        assert not any("11325" in d["text"] for d in result["dialogue"])
        assert FIXTURE_TOKEN not in json.dumps(result)
        assert gateway.step == 8 and not gateway.errors
        assert gateway.auth_ok and not gateway.rows_leaked and gateway.skill_context_seen
        assert not gateway.host_context_leaked
        summary = app.state.model_provider.budget.summary()
        assert summary.reserved_requests == 8
        assert summary.estimated_reserved_usd == "2.00"
        # A second confirmation is a read of the same terminal task, not a new execution.
        again = client.post(
            f"/api/v1/agent/tasks/{task_id}/confirm",
            json={"plan_hash": result["plan_hash"], "execution_generation": result["execution_generation"], "confirm_execute": True},
            headers=H,
        )
        assert again.status_code == 200 and again.json()["phase"] == "SUCCEEDED"
        assert gateway.step == 8


def test_web_sdk_governed_filters_reach_full_input_mcp(tmp_path, gateway):
    gateway.filters = [{"column": "region", "operator": "eq", "values": ["A"]}]
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref, question="What is total amount for region A?")
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        assert response.status_code == 200, response.text
        task_id = response.json()["id"]
        task = wait_task(client, task_id, "AWAITING_CONFIRMATION")
        assert task["plan"]["filters"] == [{"column": "region", "operator": "eq", "values": ["A"]}]
        client.post(
            f"/api/v1/agent/tasks/{task_id}/confirm",
            json={"plan_hash": task["plan_hash"], "execution_generation": task["execution_generation"], "confirm_execute": True},
            headers=H,
        )
        result = wait_task(client, task_id, "SUCCEEDED")
        assert result["result"]["rows"] == [[5625]]
        assert result["result"]["input_rows"] == 150 and result["result"]["matched_rows"] == 75
        assert result["result"]["quality"] == "PASS" and result["sql_executed"] is True
        assert gateway.step == 8 and not gateway.errors
        assert app.state.model_provider.budget.summary().reserved_requests == 8


def test_web_sdk_clarification_waits_same_task_without_execution(tmp_path, gateway):
    gateway.clarify = True
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref, question="How many orders?")
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        assert response.status_code == 200, response.text
        task = wait_task(client, response.json()["id"], "NEEDS_CLARIFICATION")
        assert task["clarification"] == "Which time range should I use?"
        assert task["sql_executed"] is False and task["result"] is None
        assert task["clarification_id"] and not app.state.agent.sdk.records[task["id"]].terminal
        assert gateway.step == 2 and not gateway.errors
        assert app.state.model_provider.budget.summary().reserved_requests == 8
        cancelled = client.post(f"/api/v1/agent/tasks/{task['id']}/cancel", json={}, headers=H)
        assert cancelled.json()["phase"] == "CANCELLED"


def test_model_change_expires_waiting_plan_without_execution(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        task_id = response.json()["id"]
        task = wait_task(client, task_id, "AWAITING_CONFIRMATION")
        app.state.model_enabled = False
        assert client.get(f"/api/v1/agent/tasks/{task_id}").json()["phase"] == "EXPIRED"
        expired = wait_task(client, task_id, "EXPIRED")
        assert expired["result"] is None and not expired["sql_executed"]
        assert gateway.step == 5 and not gateway.errors
        assert app.state.model_provider.budget.summary().reserved_requests == 8


def test_cancel_waiting_confirmation_never_executes(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        task_id = response.json()["id"]
        wait_task(client, task_id, "AWAITING_CONFIRMATION")
        cancelled = client.post(f"/api/v1/agent/tasks/{task_id}/cancel", json={}, headers=H)
        assert cancelled.status_code == 200
        assert cancelled.json()["phase"] == "CANCELLED"
        time.sleep(0.5)
        assert client.get(f"/api/v1/agent/tasks/{task_id}").json()["phase"] == "CANCELLED"
        assert gateway.step == 5 and not gateway.errors


def test_sdk_task_budget_is_reserved_before_any_model_call(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    async def exhaust():
        for _ in range(53):
            await app.state.model_provider.budget.reserve(request_bytes=100, max_output_tokens=128)
    asyncio.run(exhaust())
    body = request_body(source_id, published, model_ref)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        response = client.post("/api/v1/agent/tasks", json=body, headers=H)
        assert response.status_code == 409
        assert response.json()["code"] == "MODEL_ESTIMATED_BUDGET_EXHAUSTED"
        assert gateway.step == 0 and not app.state.agent.tasks


def test_same_request_id_returns_existing_task_without_new_budget(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        first = client.post("/api/v1/agent/tasks", json=body, headers=H).json()
        wait_task(client, first["id"], "AWAITING_CONFIRMATION")
        second = client.post("/api/v1/agent/tasks", json=body, headers=H).json()
        assert second["id"] == first["id"]
        assert app.state.model_provider.budget.summary().reserved_requests == 8
        assert gateway.step == 5


def test_sdk_capabilities_are_reported(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        value = client.get("/api/v1/agent/capabilities").json()
        assert value["sdk_web_binding"] is True
        assert value["implementation"] == "claude_agent_sdk_skills_v1"
        assert "claude_agent_sdk_skills_v1" in value["engines"]
        assert "langgraph_governed_single_table_v1" in value["engines"]


def web_config(tmp_path, database=None, **overrides):
    value = {
        "database": str(database if database is not None else fixture(tmp_path)),
        "question": "What is total amount?",
        "base_url": "http://127.0.0.1:9999",
        "runtime_root": str(tmp_path / "runtime"),
        "task_id": str(uuid4()),
        "model": SDK_MODEL,
        "mode": "web_catalog",
        "auto_confirm_fixture": False,
        "wall_clock_seconds": 300,
        "model_ref": "generation:configversion",
        "model_config_version": "abcdef1234567890",
        "semantic_version_id": str(uuid4()),
        "source_id": str(uuid4()),
        "semantic_fingerprint": "a" * 64,
        "warehouse_schema_hash": "b" * 64,
        "binding_hash": "c" * 64,
        "idempotency_key": str(uuid4()),
        "metrics": [metric().model_dump(mode="json")],
        "grain": ["id"],
        "time_meaning": None,
        "confirmation_timeout_seconds": 600,
        "test_gateway": True,
    }
    value.update(overrides)
    return SdkRunnerConfig.from_dict(value)


def test_web_catalog_runner_config_gates(tmp_path, monkeypatch):
    monkeypatch.setenv("SDK_RUNNER_MINIMAL", "1")
    monkeypatch.setenv("SDK_RUNNER_JOB", "1")
    monkeypatch.setenv("SDK_WEB_TEST", "1")
    monkeypatch.setenv("SDK_WEB_AUTH_TOKEN", "x" * 32)
    database = fixture(tmp_path)[1]
    web_config(tmp_path, database=database).validate()
    with pytest.raises(PublicError, match="SDK_REAL_CONFIRMATION_NOT_CONFIGURED"):
        web_config(tmp_path, database=database, auto_confirm_fixture=True).validate()
    with pytest.raises(PublicError, match="SDK_MODEL_NOT_APPROVED"):
        web_config(tmp_path, database=database, model="deepseek-v4-1-flash-261017").validate()
    with pytest.raises(PublicError, match="SDK_BINDING_INVALID"):
        web_config(tmp_path, database=database, binding_hash="").validate()
    with pytest.raises(PublicError, match="SDK_GATEWAY_NOT_APPROVED"):
        web_config(tmp_path, database=database, base_url="http://evil.example").validate()
    monkeypatch.delenv("SDK_WEB_TEST")
    with pytest.raises(PublicError, match="SDK_GATEWAY_NOT_APPROVED"):
        web_config(tmp_path, database=database).validate()


def clarification_body(task, answer="All time; no date filter"):
    return {"request_id": str(uuid4()), "clarification_id": task["clarification_id"],
            "execution_generation": task["execution_generation"], "answer": answer, "accept_model_egress": True}


def test_web_sdk_answer_continues_same_task_and_reservation_then_confirms(tmp_path, gateway):
    gateway.clarify = True
    gateway.clarify_continue = True
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref)
    body["conversation_id"] = str(uuid4())
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        task_id = client.post("/api/v1/agent/tasks", json=body, headers=H).json()["id"]
        waiting = wait_task(client, task_id, "NEEDS_CLARIFICATION")
        answer = clarification_body(waiting)
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json={**answer, "accept_model_egress": False}, headers=H).status_code == 422
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json={**answer, "answer": FIXTURE_TOKEN}, headers=H).status_code == 422
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json={**answer, "execution_generation": "old"}, headers=H).status_code == 409
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json={**answer, "clarification_id": str(uuid4())}, headers=H).status_code == 409
        response = client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json=answer, headers=H)
        assert response.status_code == 200, response.text
        task = wait_task(client, task_id, "AWAITING_CONFIRMATION")
        assert task["id"] == task_id and task["request_id"] == body["request_id"] and task["conversation_id"] == body["conversation_id"]
        assert task["clarification"] is None and task["clarification_id"] is None
        assert task["clarification_turns"][0]["answer"] == answer["answer"]
        kinds=[d["kind"] for d in task["dialogue"]]
        assert kinds.index("clarification") < kinds.index("user")
        assert any(d["text"]==answer["answer"] for d in task["dialogue"] if d["kind"]=="user")
        assert not task["sql_executed"] and task["result"] is None
        assert gateway.step == 6 and len(app.state.agent.sdk.tasks) == 1
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json=answer, headers=H).status_code == 200
        conflict = client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json={**answer, "answer": "different"}, headers=H)
        assert conflict.status_code == 409 and conflict.json()["code"] == "AGENT_CLARIFICATION_CONFLICT"
        confirm = client.post(f"/api/v1/agent/tasks/{task_id}/confirm", json={"plan_hash": task["plan_hash"], "execution_generation": task["execution_generation"], "confirm_execute": True}, headers=H)
        assert confirm.status_code == 200
        result = wait_task(client, task_id, "SUCCEEDED")
        assert result["result"]["rows"] == [[11325]] and result["execution_receipt"]["quality_receipt"]["status"] == "PASS"
        assert result["clarification_turns"][0]["answer"] == answer["answer"] and result["sql_executed"]
        assert gateway.step == 9 and not gateway.errors and not gateway.rows_leaked and not gateway.host_context_leaked
        assert any(answer["answer"] in json.dumps(request) for request in gateway.requests)
        assert app.state.model_provider.budget.summary().reserved_requests == 8
        assert client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json=answer, headers=H).status_code == 409


@pytest.mark.parametrize("action", ["cancel", "model_change", "schema_change"])
def test_web_sdk_waiting_clarification_rejects_cancelled_or_changed_binding(tmp_path, gateway, action):
    gateway.clarify = True
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        task_id = client.post("/api/v1/agent/tasks", json=request_body(source_id, published, model_ref), headers=H).json()["id"]
        waiting = wait_task(client, task_id, "NEEDS_CLARIFICATION")
        if action == "cancel":
            client.post(f"/api/v1/agent/tasks/{task_id}/cancel", json={}, headers=H)
        elif action == "model_change":
            app.state.model_enabled = False
        else:
            import duckdb
            import hashlib
            database = app.state.agent.sdk.records[task_id].database
            manifest_path = database.with_suffix('.manifest.json')
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            physical = manifest['tables']['t0']
            with duckdb.connect(str(database)) as db:
                db.execute(f'ALTER TABLE "{physical["schema"]}"."{physical["name"]}" ADD COLUMN changed INTEGER')
            physical['columns'].append({'name':'changed','type':'INTEGER'})
            manifest['database_sha256'] = hashlib.sha256(database.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
        response = client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json=clarification_body(waiting), headers=H)
        assert response.status_code in (200,409)
        task = client.get(f"/api/v1/agent/tasks/{task_id}").json()
        assert task["phase"] in ("CANCELLED", "EXPIRED") and not task["sql_executed"] and task["result"] is None
        assert gateway.step == 2 and not gateway.errors
        assert app.state.model_provider.budget.summary().reserved_requests == 8


def test_web_sdk_clarification_cancellation_during_recheck_writes_no_answer(tmp_path, gateway):
    gateway.clarify = True
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        task_id = client.post("/api/v1/agent/tasks", json=request_body(source_id, published, model_ref), headers=H).json()["id"]
        task = wait_task(client, task_id, "NEEDS_CLARIFICATION")
        sdk = app.state.agent.sdk
        record = sdk.records[task_id]
        async def cancel_during_recheck(current):
            await sdk.cancel(current.auth, current.task.id)
            return True, None
        sdk._live_binding_valid = cancel_during_recheck
        answer_path = record.runtime_root / task_id / "clarification.json"
        response = client.post(f"/api/v1/agent/tasks/{task_id}/clarify", json=clarification_body(task), headers=H)
        assert response.status_code == 409 and response.json()["code"] == "AGENT_CLARIFICATION_EXPIRED"
        assert not answer_path.exists() and not record.clarification_answers
        assert not record.submitted and gateway.step == 2


def test_web_sdk_confirmation_rechecks_hash_after_state_sync(tmp_path, gateway):
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 1)) as client:
        task_id = client.post("/api/v1/agent/tasks", json=request_body(source_id, published, model_ref), headers=H).json()["id"]
        task = wait_task(client, task_id, "AWAITING_CONFIRMATION")
        sdk = app.state.agent.sdk
        original_sync = sdk._sync_state
        def changed_state(record):
            original_sync(record)
            record.task.plan_hash = "b" * 64
        sdk._sync_state = changed_state
        response = client.post(f"/api/v1/agent/tasks/{task_id}/confirm", json={"plan_hash":task["plan_hash"],"execution_generation":task["execution_generation"],"confirm_execute":True}, headers=H)
        assert response.status_code == 409 and response.json()["code"] == "AGENT_PLAN_EXPIRED"
        assert not sdk.records[task_id].confirmation_path.exists() and not sdk.records[task_id].submitted
        client.post(f"/api/v1/agent/tasks/{task_id}/cancel",json={},headers=H)
        assert gateway.step == 5


def test_web_sdk_l2_template_discovery_plan_confirmation_and_real_qa(tmp_path, gateway):
    gateway.topic_path = True
    app, source_id, published, model_ref = build_app(tmp_path, gateway.server_port)
    body = request_body(source_id, published, model_ref, question="unmapped custom request")
    with TestClient(app, base_url=BASE, client=("127.0.0.1",1)) as client:
        response=client.post('/api/v1/agent/tasks',json=body,headers=H)
        assert response.status_code==200, response.text
        task_id=response.json()['id']
        task=wait_task(client,task_id,'AWAITING_CONFIRMATION')
        assert task['query_path']=='L2' and task['plan']['dimensions']==['region']
        assert task['plan']['metric']['column']=='amount' and not task['sql_executed']
        tools=[tool for d in task['dialogue'] for tool in d['tools']]
        assert 'list_authorized_tables' in tools and 'search_authorized_fields' in tools and 'load_topic_sql_template' in tools
        assert gateway.step==7
        confirmed=client.post(f'/api/v1/agent/tasks/{task_id}/confirm',json={'plan_hash':task['plan_hash'],'execution_generation':task['execution_generation'],'confirm_execute':True},headers=H)
        assert confirmed.status_code==200,confirmed.text
        result=wait_task(client,task_id,'SUCCEEDED')
        assert result['query_path']=='L2' and result['result']['quality']=='PASS'
        assert result['result']['input_rows']==150 and result['result']['matched_rows']==51
        assert sum(row[-1] for row in result['result']['rows'])==6375
        assert gateway.step==9 and not gateway.errors and not gateway.rows_leaked and not gateway.host_context_leaked
        assert app.state.model_provider.budget.summary().reserved_requests==8
        assert any('主题' in d['text'] for d in result['dialogue'])
