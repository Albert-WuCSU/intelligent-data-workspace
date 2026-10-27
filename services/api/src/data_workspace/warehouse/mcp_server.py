"""Real local MCP server. stdio lifetime is owned by the backend client."""
import argparse
from typing import Any
from functools import wraps
import anyio
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from . import DEFAULT_WAREHOUSE
from .engine import OwnedWarehouse, WarehouseError
from .execution import ExecutionService
from .policy import QueryDenied


def create_server(directory,database=None):
    if database:
        from .local_file import LocalFileWarehouse
        warehouse=LocalFileWarehouse(database)
    else:warehouse = OwnedWarehouse(directory)
    execution = ExecutionService(warehouse)
    server = FastMCP("Owned synthetic analytics", log_level="ERROR")

    def safe(call):
        try:
            return call()
        except (ValueError, ValidationError, WarehouseError, QueryDenied):
            return {"ok": False, "error": {"code": "INVALID_REQUEST", "safe_message": "Requested table or fields is not allowed."}}
        except Exception:
            return {"ok": False, "error": {"code": "CONNECTOR_ERROR", "safe_message": "Local connector failed; raw exceptions are not exposed."}}

    @server.tool(structured_output=True)
    def list_tables() -> dict[str, Any]:
        """List the five real tables in the owned synthetic warehouse."""
        return safe(lambda: {"ok": True, "metadata": warehouse.list_tables()})

    @server.tool(structured_output=True)
    def describe_table(table: str) -> dict[str, Any]:
        """Describe fields and relationships of an allowed bare table name."""
        return safe(lambda: {"ok": True, "metadata": warehouse.describe(table)})

    @server.tool(structured_output=True)
    def list_partitions(table: str) -> dict[str, Any]:
        """Read actual date partitions (logical date-column values)."""
        return safe(lambda: {"ok": True, "metadata": warehouse.partitions(table)})

    @server.tool(structured_output=True)
    async def submit_query(request: dict, idempotency_key: str) -> dict[str, Any]:
        """Execute a confirmed bounded table preview, not arbitrary SQL.

        request: table, optional columns and optional limit (default 100; 1..100). No filters.
        Completes after the actual engine execution. Not fire-and-forget.
        """
        return await anyio.to_thread.run_sync(lambda: safe(lambda: execution.submit(request, idempotency_key)))

    @server.tool(structured_output=True)
    def get_query_status(task_id: str) -> dict[str, Any]:
        """Read actual status of a task owned by this process session."""
        return safe(lambda: execution.status(task_id))

    @server.tool(structured_output=True)
    def get_query_result(task_id: str) -> dict[str, Any]:
        """Read a bounded result only after actual query success."""
        return safe(lambda: execution.result(task_id))

    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", default=str(DEFAULT_WAREHOUSE))
    parser.add_argument("--database")
    args = parser.parse_args()
    create_server(args.warehouse,args.database).run(transport="stdio")

