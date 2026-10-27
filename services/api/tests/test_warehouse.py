import asyncio
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import duckdb
import pytest
from pydantic import ValidationError
from data_workspace.auth import PublicError
from data_workspace.contracts import AuthContext
from data_workspace.demo_data.generate import write_dataset
from data_workspace.warehouse.build import build, sha
from data_workspace.warehouse.engine import OwnedWarehouse
from data_workspace.warehouse.execution import ExecutionService
from data_workspace.warehouse.policy import PreviewRequest, QueryDenied, compile_preview, validate_template
from data_workspace.warehouse.client import OwnedMCPClient

@pytest.fixture(scope="module")
def warehouse_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("owned-warehouse")
    seed = root / "seed"
    write_dataset(seed, seed=2, customers=12, products=5, orders=30, days=7)
    destination = root / "warehouse"
    build(seed, destination)
    return destination

@pytest.fixture
def request_spec():
    return {"table": "fact_order", "columns": ["order_id", "paid_amount_cents"], "limit": 5}


def test_real_warehouse_counts_and_golden(warehouse_dir):
    warehouse = OwnedWarehouse(warehouse_dir)
    assert len(warehouse.list_tables()["tables"]) == 5
    with warehouse.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM analytics.fact_order").fetchone()[0] == 30
        assert con.execute("SELECT SUM(paid_amount_cents) FROM analytics.fact_order").fetchone()[0] == warehouse.manifest["golden_sql_checks"]["actual"]["paid_amount_cents"]
    assert warehouse.describe("fact_order")["fields"][8]["type"] == "BIGINT"
    assert len(warehouse.partitions("fact_order")["partitions"]) <= 7
    for info in warehouse.manifest["parquet"].values():
        assert sha(warehouse_dir/info["path"]) == info["sha256"]
    with pytest.raises(FileExistsError):
        build(destination=warehouse_dir)


def test_real_preview_truncated_empty_and_types(warehouse_dir, request_spec):
    warehouse = OwnedWarehouse(warehouse_dir)
    result = warehouse.preview(request_spec)
    assert result["truncated"] is True and result["returned_row_count"] == 5
    assert result["reported_total_rows"] is None
    assert all(isinstance(row[1], int) for row in result["rows"])
    assert result["quality"]["status"] == "WARN"
    request_spec.update(table="dim_customer", columns=["customer_id"], limit=100)
    result = warehouse.preview(request_spec)
    assert len(result["rows"]) == 12 and result["truncated"] is False


@pytest.mark.parametrize("mutation", [{"table": "fact_order; DROP TABLE analytics.fact_order"}, {"columns": ["*"]}, {"columns": ["order_id", "order_id"]}, {"columns": ["password"]}, {"start": "2025-01-01", "end_exclusive": "2026-01-01"}, {"limit": 101}, {"tenant_id": "attacker"}, {"sql": "SELECT 1"}])
def test_request_rejects_scope_and_injection(request_spec, mutation):
    request_spec.update(mutation)
    with pytest.raises((ValidationError,QueryDenied)):
        compile_preview(request_spec)


@pytest.mark.parametrize("sql", ["SELECT 1", "SELECT * FROM analytics.fact_order LIMIT 10", "COPY analytics.fact_order TO 'out.csv'", "SELECT * FROM read_csv_auto('secret.csv') LIMIT 10", "SELECT * FROM analytics.fact_order; DELETE FROM analytics.fact_order", "PRAGMA version", "SET enable_external_access = true", "INSTALL httpfs", "LOAD httpfs", "ATTACH 'other.duckdb'", "SELECT order_id FROM analytics.fact_order WHERE partition_date >= ? LIMIT 10000", "SELECT order_id FROM analytics.fact_order WHERE partition_date >= ? LIMIT 10 -- secret"])
def test_ast_rejects_non_templates(sql):
    with pytest.raises(QueryDenied):
        validate_template(sql, "fact_order")


def test_compiled_parameters_not_interpolated(request_spec):
    sql, bindings, _ = compile_preview(request_spec)
    assert "2025-01-01" not in sql
    assert bindings == []
    assert "WHERE" not in sql and "ORDER BY" not in sql


def test_engine_rejects_write_files_and_reconfiguration(warehouse_dir, tmp_path):
    secret = tmp_path / "sensitive.txt"
    secret.write_text("sentinel-do-not-read")
    with OwnedWarehouse(warehouse_dir).connect() as con:
        for query in ["DELETE FROM analytics.fact_order", "SET enable_external_access = true", "INSTALL httpfs", "ATTACH ':memory:' AS other", f"SELECT * FROM read_text('{str(secret).replace(chr(92), '/')}')"]:
            with pytest.raises(duckdb.Error):
                con.execute(query)
        assert con.execute("SELECT current_setting('enable_external_access')").fetchone()[0] is False
        assert con.execute("SELECT current_setting('lock_configuration')").fetchone()[0] is True


def test_idempotency_and_safe_failure(warehouse_dir, request_spec):
    service = ExecutionService(OwnedWarehouse(warehouse_dir))
    first = service.submit(request_spec, "key")
    assert first["task"]["status"] == "SUCCEEDED"
    assert service.submit(request_spec, "key")["task"]["task_id"] == first["task"]["task_id"]
    request_spec["limit"] = 4
    assert service.submit(request_spec, "key")["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert service.result("foreign")["error"]["code"] == "TASK_NOT_FOUND"
    class Broken:
        def preview(self, request):
            raise RuntimeError("secret-do-not-show")
    broken = ExecutionService(Broken())
    failed = broken.submit(request_spec, "failed")
    assert failed["task"]["status"] == "FAILED"
    assert "secret-do-not-show" not in json.dumps(failed)
    assert broken.result(failed["task"]["task_id"])["error"]["code"] == "QUERY_FAILED"


@pytest.mark.parametrize("principal,tenant,mode", [("another-user","local-workspace","development"), ("local-developer","other","development"), ("local-developer","local-workspace","production")])
def test_identity_denied_before_process(principal, tenant, mode):
    with pytest.raises(PublicError):
        OwnedMCPClient(AuthContext(principal_id=principal, tenant_id=tenant, mode=mode))


def test_seed_tamper_rejected(tmp_path):
    seed = tmp_path / "seed"
    write_dataset(seed, seed=1, customers=3, products=2, orders=5, days=3)
    with (seed / "fact_order.jsonl").open("a") as file:
        file.write("{}\n")
    with pytest.raises(ValueError):
        build(seed, tmp_path / "warehouse")
    assert not (tmp_path / "warehouse").exists()


def test_real_mcp_handshake_metadata_execution_and_session_isolation(warehouse_dir, request_spec):
    async def exercise():
        auth = AuthContext(principal_id="local-developer", tenant_id="local-workspace", mode="development")
        async with OwnedMCPClient(auth, warehouse_dir).connected() as client:
            assert client.initialization.protocolVersion
            assert len((await client.call("list_tables"))["metadata"]["tables"]) == 5
            assert (await client.call("describe_table", {"table": "fact_order"}))["metadata"]["fields"]
            receipt = await client.call("submit_query", {"request":request_spec, "idempotency_key":"real-preview"})
            task_id = receipt["task"]["task_id"]
            assert receipt["task"]["status"] == "SUCCEEDED"
            assert (await client.call("get_query_status", {"task_id":task_id}))["status"] == "SUCCEEDED"
            assert (await client.call("get_query_result", {"task_id":task_id}))["result"]["returned_row_count"] == 5
            assert (await client.call("submit_query", {"request":request_spec, "idempotency_key":"real-preview"}))["task"]["task_id"] == task_id
            bad = deepcopy(request_spec); bad["columns"] = ["sentinel-secret-input"]
            denied = await client.call("submit_query", {"request":bad, "idempotency_key":"unsafe"})
            assert denied["ok"] is False and "sentinel-secret-input" not in json.dumps(denied)
            with pytest.raises(PublicError):
                await client.call("cancel_query", {"task_id":task_id})
        async with OwnedMCPClient(auth, warehouse_dir).connected() as other:
            assert (await other.call("get_query_result", {"task_id":task_id}))["error"]["code"] == "TASK_NOT_FOUND"
    asyncio.run(exercise())

def test_real_engine_deadline_interrupt(warehouse_dir):
    from threading import Timer
    with OwnedWarehouse(warehouse_dir).connect() as con:
        timer = Timer(0.05, con.interrupt)
        try:
            timer.start()
            with pytest.raises(duckdb.InterruptException):
                con.execute("SELECT sum(a.i * b.i) FROM range(1000000) a(i), range(1000000) b(i)").fetchall()
        finally:
            timer.cancel()
            timer.join()


def test_receipt_capacity_running_and_interrupt_mapping(request_spec):
    from threading import Event, Thread
    entered, release = Event(), Event()
    class Waiting:
        def preview(self, request):
            entered.set()
            assert release.wait(5)
            return {"rows": []}
    service = ExecutionService(Waiting())
    output = []
    thread = Thread(target=lambda: output.append(service.submit(request_spec, "running")))
    thread.start()
    try:
        assert entered.wait(5)
        receipt = service.submit(request_spec, "running")
        task_id = receipt["task"]["task_id"]
        assert service.status(task_id)["status"] == "RUNNING"
        assert service.result(task_id)["error"]["code"] == "NOT_READY"
        assert service.submit(request_spec, "another")["error"]["code"] == "CAPACITY_EXCEEDED"
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert output[0]["task"]["status"] == "SUCCEEDED"
    class Interrupted:
        def preview(self, request):
            raise duckdb.InterruptException("internal-sensitive-message")
    service = ExecutionService(Interrupted())
    receipt = service.submit(request_spec, "interrupted")
    assert receipt["task"]["status"] == "FAILED"
    assert receipt["task"]["error"]["code"] == "QUERY_INTERRUPTED"
    assert "internal-sensitive-message" not in json.dumps(receipt)

def test_generic_compiler_supports_no_date_columns():
    catalog={'lookup':[('code','VARCHAR'),('label','VARCHAR')]}
    sql,bindings,request=compile_preview({'table':'lookup'},catalog)
    assert sql=='SELECT "code","label" FROM analytics."lookup" LIMIT 101'
    assert bindings==[] and request.limit==100
    with duckdb.connect() as con:
        con.execute('CREATE SCHEMA analytics')
        con.execute('CREATE TABLE analytics.lookup(code VARCHAR,label VARCHAR)')
        con.execute("INSERT INTO analytics.lookup VALUES ('a','Alpha')")
        assert con.execute(sql).fetchall()==[('a','Alpha')]


def test_generic_compiler_does_not_guess_date_meaning():
    sql,bindings,_=compile_preview({'table':'dates'}, {'dates':[('created_at','TIMESTAMP'),('shipped_on','DATE')]})
    assert 'WHERE' not in sql and 'ORDER BY' not in sql and bindings==[]
