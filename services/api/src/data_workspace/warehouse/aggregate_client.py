"""Governed MCP client for one explicitly local development identity.

Not enterprise authentication. The stdio process is a per-client capability;
no principal/tenant/path/tool URL is accepted from a browser.
"""
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
import sys
from mcp import ClientSession
from .stdio_transport import governed_stdio
from data_workspace.auth import PublicError
from . import DEFAULT_WAREHOUSE, PROJECT_ROOT

TOOLS = frozenset({"aggregate_metadata","submit_aggregate","aggregate_status","aggregate_result"})

class AggregateMCPClient:
    def __init__(self, auth, warehouse=DEFAULT_WAREHOUSE, database=None):
        self.auth = auth
        self.directory = Path(warehouse).resolve()
        self.database=Path(database).resolve() if database else None
        self.session = None
        self.initialization = None
        self.transport = None
        self._authorize()

    def _authorize(self):
        if (self.auth.mode, self.auth.tenant_id, self.auth.principal_id) != ("development", "local-workspace", "local-developer"):
            raise PublicError(403, "CONNECTOR_DENIED", "自有测试仓仅允许已配置的本机开发身份。")

    @asynccontextmanager
    async def connected(self, inherit_job=False):
        self._authorize()
        async with governed_stdio(self.directory,self.database,entry=Path(__file__).with_name('aggregate_entry.py'),inherit_job=inherit_job) as (reader,writer,state):
            self.transport=state
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=15)) as session:
                self.session = session
                try:
                    self.initialization = await session.initialize()
                    tools = await session.list_tools()
                    if {tool.name for tool in tools.tools} != TOOLS:
                        raise PublicError(503, "PROTOCOL_MISMATCH", "连接器工具合同不兼容。")
                    expected={'aggregate_metadata':{'table':'string'},'submit_aggregate':{'request':'object','idempotency_key':'string'},'aggregate_status':{'task_id':'string'},'aggregate_result':{'task_id':'string'}}
                    for tool in tools.tools:
                        schema=tool.inputSchema;fields=expected[tool.name]
                        if set(schema.get('required',[]))!=set(fields) or set(schema.get('properties',{}))!=set(fields) or any(schema['properties'][key].get('type')!=value for key,value in fields.items()):
                            raise PublicError(503,'PROTOCOL_MISMATCH','受控聚合工具参数合同不兼容。')
                    yield self
                finally:
                    self.session = None
                    self.transport = None

    async def call(self, name, arguments=None):
        self._authorize()
        if name not in TOOLS:
            raise PublicError(403, "TOOL_DENIED", "连接器工具未获授权。")
        if self.session is None:
            raise PublicError(503, "CONNECTOR_NOT_CONNECTED", "本机MCP尚未连接。")
        try:
            import anyio
            with anyio.fail_after(15):
                result = await self.session.call_tool(name, arguments or {})
        except BaseException:
            if self.transport:self.transport.abort()
            raise
        if result.isError or not isinstance(result.structuredContent, dict):
            raise PublicError(502, "CONNECTOR_RESPONSE_INVALID", "MCP返回不符合连接器合同。")
        return result.structuredContent

    @property
    def healthy(self):return self.session is not None and self.transport is not None and self.transport.healthy
