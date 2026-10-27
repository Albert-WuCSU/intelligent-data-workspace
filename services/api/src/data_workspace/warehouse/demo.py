"""Verify real MCP metadata and preview; numbers remain synthetic."""
import asyncio
import json
from data_workspace.contracts import AuthContext
from .client import OwnedMCPClient

async def demo():
    auth = AuthContext(principal_id="local-developer", tenant_id="local-workspace", mode="development")
    async with OwnedMCPClient(auth).connected() as client:
        metadata = await client.call("list_tables")
        schema = await client.call("describe_table", {"table": "fact_order"})
        partitions = await client.call("list_partitions", {"table": "fact_order"})
        receipt = await client.call("submit_query", {"request": {"table": "fact_order", "columns": ["order_id", "status", "paid_amount_cents", "currency"], "limit": 5}, "idempotency_key": "demo-preview-v1"})
        if not receipt.get("ok") or receipt["task"]["status"] != "SUCCEEDED":
            raise RuntimeError("real MCP preview did not succeed")
        task_id = receipt["task"]["task_id"]
        status = await client.call("get_query_status", {"task_id": task_id})
        result = await client.call("get_query_result", {"task_id": task_id})
        denied = await client.call("submit_query", {"request": {"table": "read_csv_auto('secret')", "columns": ["order_id"]}, "idempotency_key": "denied-preview"})
        assert denied.get("ok") is False
        print(json.dumps({"protocol_version": client.initialization.protocolVersion, "metadata": metadata, "schema": schema, "partition_count": len(partitions["metadata"]["partitions"]), "status": status, "preview": result, "unsafe_request": denied}, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(demo())
