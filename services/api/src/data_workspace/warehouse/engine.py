"""Read-only engine access with external IO disabled and bounded previews."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
from threading import Timer
import duckdb
from data_workspace.demo_data.generate import SOURCE
from .build import sha
from .catalog import COLUMNS, RELATIONS
from .policy import compile_preview

ENGINE_CONFIG = {"enable_external_access": "false", "autoinstall_known_extensions": "false", "autoload_known_extensions": "false", "allow_unsigned_extensions": "false", "memory_limit": "128MB", "threads": "1", "max_temp_directory_size": "0B"}

class WarehouseError(ValueError):
    pass

class OwnedWarehouse:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.database = self.directory / "warehouse.duckdb"
        self.manifest = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
        if self.manifest.get("source") != SOURCE or self.manifest.get("synthetic") is not True or sha(self.database) != self.manifest["database_sha256"]:
            raise WarehouseError("warehouse integrity check failed")

    def connect(self):
        con = duckdb.connect(str(self.database), read_only=True, config=ENGINE_CONFIG)
        con.execute("SET lock_configuration = true")
        return con

    def list_tables(self):
        with self.connect() as con:
            names = [name for name, in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics' ORDER BY table_name").fetchall()]
        if set(names) != set(COLUMNS):
            raise WarehouseError("unexpected warehouse catalog")
        return {"source": SOURCE, "dataset_version": self.manifest["dataset_version"], "sql_dialect": "duckdb", "tables": [{"name": f"analytics.{name}", "row_count": self.manifest["table_counts"][name]} for name in names], "quality_scope": "synthetic seed and SQL golden checks only"}

    def describe(self, table):
        if table not in COLUMNS:
            raise WarehouseError("table unavailable")
        with self.connect() as con:
            fields = con.execute("SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema = 'analytics' AND table_name = ? ORDER BY ordinal_position", [table]).fetchall()
        return {"table": f"analytics.{table}", "source": SOURCE, "fields": [{"name": name, "type": kind, "nullable": nullable == "YES", "unit": "TEST cents" if name.endswith("_cents") else None} for name, kind, nullable in fields], "relations": RELATIONS[table], "timezone": "UTC"}

    def partitions(self, table):
        if table not in COLUMNS:
            raise WarehouseError("table unavailable")
        field = "snapshot_date" if table.startswith("dim_") else "partition_date"
        with self.connect() as con:
            rows = con.execute(f'SELECT DISTINCT "{field}" FROM analytics."{table}" ORDER BY "{field}" LIMIT 91').fetchall()
        return {"table": f"analytics.{table}", "field": field, "partitions": [d.isoformat() for d, in rows[:90]], "truncated": len(rows) > 90, "physical_partitioning": False}

    def preview(self, request):
        sql, parameters, request = compile_preview(request)
        with self.connect() as con:
            timer = Timer(3.0, con.interrupt)
            try:
                timer.start()
                cursor = con.execute(sql, parameters)
                fields = [{"name": name, "type": str(kind)} for name, kind, *_ in cursor.description]
                rows = cursor.fetchmany(request.limit + 1)
            finally:
                timer.cancel()
                timer.join()
        visible = [[value.isoformat() if isinstance(value, (datetime, date)) else value for value in row] for row in rows[:request.limit]]
        if len(json.dumps(visible).encode("utf-8")) > 100_000:
            raise WarehouseError("preview response too large")
        return {"source": SOURCE, "dataset_version": self.manifest["dataset_version"], "sql_dialect": "duckdb", "columns": fields, "rows": visible, "returned_row_count": len(visible), "reported_total_rows": None, "truncated": len(rows) > request.limit, "retrieved_at": datetime.now(timezone.utc).isoformat(), "currency": "TEST", "quality": {"status": "WARN", "limitations": ["Synthetic data, not enterprise business evidence", "Bounded preview is not a complete data asset", "Only seed invariants and golden SQL checks have been verified"]}}
