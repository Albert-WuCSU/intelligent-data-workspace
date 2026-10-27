"""Offline artifact verification, not an MCP tool or user-supplied query."""
import json
from pathlib import Path
import duckdb
from . import DEFAULT_WAREHOUSE
from .build import sha
from .catalog import COLUMNS
from .engine import OwnedWarehouse


def verify(directory=DEFAULT_WAREHOUSE):
    directory = Path(directory).resolve()
    warehouse = OwnedWarehouse(directory)
    counts = {}
    with warehouse.connect() as con:
        for table in COLUMNS:
            counts[table] = con.execute(f'SELECT count(*) FROM analytics."{table}"').fetchone()[0]
        actual = {"order_count": counts["fact_order"], "paid_order_count": con.execute("SELECT count(*) FROM analytics.fact_order WHERE status IN ('paid','completed')").fetchone()[0], "paid_amount_cents": con.execute("SELECT sum(paid_amount_cents) FROM analytics.fact_order").fetchone()[0]}
        mismatched = con.execute("SELECT count(*) FROM analytics.fact_order o JOIN (SELECT order_id, sum(line_amount_cents) amount FROM analytics.fact_order_item GROUP BY order_id) i ON o.order_id=i.order_id WHERE o.gross_amount_cents != i.amount").fetchone()[0]
    if counts != warehouse.manifest["table_counts"] or actual != warehouse.manifest["golden_sql_checks"]["actual"] or mismatched:
        raise ValueError("warehouse SQL verification failed")
    # Only this trusted offline command can read local Parquet. Runtime MCP keeps
    # enable_external_access false and never exposes this function.
    parquet_counts = {}
    with duckdb.connect(config={"autoinstall_known_extensions":"false", "autoload_known_extensions":"false", "threads":"1"}) as con:
        for table in COLUMNS:
            info = warehouse.manifest["parquet"][table]
            if info["path"] != f"parquet/{table}.parquet":
                raise ValueError("invalid parquet path")
            path = directory/info["path"]
            if sha(path) != info["sha256"]:
                raise ValueError("parquet integrity check failed")
            parquet_counts[table] = con.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
    if parquet_counts != counts:
        raise ValueError("parquet/database count mismatch")
    return {"status":"passed", "source":warehouse.manifest["source"], "dataset_version":warehouse.manifest["dataset_version"], "table_counts":counts, "parquet_counts":parquet_counts, "golden_sql_checks":actual, "mismatched_order_totals":mismatched, "database_sha256":sha(warehouse.database)}

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
