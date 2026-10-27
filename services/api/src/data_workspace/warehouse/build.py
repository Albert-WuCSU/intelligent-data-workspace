"""Trusted offline initialization; runtime MCP has no build/export tools."""
import argparse
import hashlib
import json
from pathlib import Path
import duckdb
from data_workspace.demo_data.generate import SOURCE, TABLES, validate
from . import DEFAULT_SEED, DEFAULT_WAREHOUSE
from .catalog import COLUMNS, ddl


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(seed=DEFAULT_SEED, destination=DEFAULT_WAREHOUSE):
    seed, destination = Path(seed).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("warehouse version already exists; refusing overwrite")
    manifest_path = seed / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source") != SOURCE or manifest.get("synthetic") is not True or manifest.get("external_sources") != [] or set(manifest["tables"]) != set(TABLES):
        raise ValueError("only independently generated synthetic seeds are accepted")
    data = {}
    for table in TABLES:
        item = manifest["tables"][table]
        if item["path"] != f"{table}.jsonl":
            raise ValueError("unexpected seed path")
        path = seed / item["path"]
        if not path.is_file() or path.stat().st_size > 10_000_000 or sha(path) != item["sha256"]:
            raise ValueError("seed integrity/size check failed")
        data[table] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        fields = {name for name, _ in COLUMNS[table]}
        if not 0 < len(data[table]) <= 20_000 or len(data[table]) != item["row_count"] or any(set(row) != fields for row in data[table]):
            raise ValueError("seed fields/count invalid")
    validate(data)
    # mkdir is exclusive; partial failures remain visible and are never overwritten.
    destination.mkdir(parents=True)
    parquet = destination / "parquet"
    parquet.mkdir()
    database = destination / "warehouse.duckdb"
    script = "CREATE SCHEMA analytics;\n" + ";\n".join(ddl(t) for t in TABLES) + ";\n"
    (destination / "schema.sql").write_text(script, encoding="utf-8")
    with duckdb.connect(str(database), config={"threads": "1", "memory_limit": "256MB"}) as con:
        con.execute("BEGIN")
        con.execute("CREATE SCHEMA analytics")
        for table in TABLES:
            con.execute(ddl(table))
            columns = [name for name, _ in COLUMNS[table]]
            con.executemany(f'INSERT INTO analytics."{table}" VALUES (' + ",".join("?" for _ in columns) + ")", [[row[name] for name in columns] for row in data[table]])
        con.execute("COMMIT")
        counts = {table: con.execute(f'SELECT COUNT(*) FROM analytics."{table}"').fetchone()[0] for table in TABLES}
        actual = {"order_count": counts["fact_order"], "paid_order_count": con.execute("SELECT COUNT(*) FROM analytics.fact_order WHERE status IN ('paid','completed')").fetchone()[0], "paid_amount_cents": con.execute("SELECT SUM(paid_amount_cents) FROM analytics.fact_order").fetchone()[0]}
        if any(actual[name] != manifest["golden_checks"][name] for name in actual):
            raise ValueError("SQL golden mismatch")
        exported = {}
        for table in TABLES:
            target = parquet / f"{table}.parquet"
            safe = str(target).replace("'", "''")
            con.execute(f"COPY analytics.\"{table}\" TO '{safe}' (FORMAT PARQUET)")
            exported[table] = {"path": f"parquet/{table}.parquet", "sha256": sha(target), "row_count": counts[table]}
        con.execute("CHECKPOINT")
    report = {"schema_version": "1.0", "dataset_version": "synthetic-v1", "source": SOURCE, "synthetic": True, "external_sources": [], "sql_dialect": "duckdb", "duckdb_version": duckdb.__version__, "timezone": "UTC", "currency": "TEST", "seed_manifest_sha256": sha(manifest_path), "database_sha256": sha(database), "table_counts": counts, "parquet": exported, "golden_sql_checks": {"status": "passed", "actual": actual}, "partitioning": "date columns; one Parquet snapshot per table, not physically date-partitioned", "limitations": manifest["limitations"]}
    (destination / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=str(DEFAULT_SEED))
    parser.add_argument("--output", default=str(DEFAULT_WAREHOUSE))
    args = parser.parse_args()
    print(json.dumps(build(args.seed, args.output), ensure_ascii=False))
