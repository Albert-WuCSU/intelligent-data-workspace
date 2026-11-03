"""Governed remote navigation; known MCP adapter only, no arbitrary SQL/tools."""
from datetime import timedelta
import json
import math
import re
from uuid import uuid4
import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from .auth import PublicError
from .remote_access import HTTPMCPDraft, ProductSecrets
from .warehouse.client import TOOLS
from .warehouse.http_boundary import HTTPEndpointPolicy, create_governed_http_client

INPUTS = {'list_tables': {}, 'describe_table': {'table':'string'}, 'list_partitions': {'table':'string'}, 'submit_query': {'request':'object', 'idempotency_key':'string'}, 'get_query_status': {'task_id':'string'}, 'get_query_result': {'task_id':'string'}}

def invalid():
    raise PublicError(502, 'REMOTE_RESPONSE_INVALID', '远端返回不符合已审定的表导航合同或超过限额；请检查适配器，不会展示不完整数据为成功。')

def catalog(value, allowed):
    if not isinstance(value, dict) or value.get('ok') is not True:
        invalid()
    metadata = value.get('metadata')
    if not isinstance(metadata, dict): invalid()
    tables = metadata.get('tables')
    if not isinstance(tables, list) or len(tables)>50: invalid()
    result=[];seen=set()
    for t in tables:
        if not isinstance(t,dict) or not isinstance(t.get('id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',t['id']) or not isinstance(t.get('name'),str) or not 1<=len(t['name'])<=200 or t['id'] in seen: invalid()
        seen.add(t['id'])
        if t['id'] in allowed: result.append({'id':t['id'],'name':t['name']})
    return {'source':'external_mcp','tables':result}

def preview_result(value):
    if not isinstance(value,dict) or value.get('ok') is not True or not isinstance(value.get('result'),dict): invalid()
    raw=value['result'];columns=raw.get('columns');rows=raw.get('rows')
    if not isinstance(columns,list) or not 1<=len(columns)<=100 or not isinstance(rows,list) or len(rows)>100: invalid()
    names=set()
    for c in columns:
        if not isinstance(c,dict) or not isinstance(c.get('name'),str) or not 1<=len(c['name'])<=200 or not isinstance(c.get('type'),str) or not 1<=len(c['type'])<=128 or c['name'] in names: invalid()
        names.add(c['name'])
    for row in rows:
        if not isinstance(row,list) or len(row)!=len(columns): invalid()
        for cell in row:
            if cell is not None and not isinstance(cell,(str,int,float,bool)): invalid()
            if isinstance(cell,float) and not math.isfinite(cell): invalid()
    if raw.get('returned_row_count') != len(rows) or not isinstance(raw.get('truncated'),bool): invalid()
    if len(json.dumps([columns,rows],ensure_ascii=False).encode())>200000: invalid()
    return {'source':'external_mcp','columns':[{'name':c['name'],'type':c['type']} for c in columns], 'rows':rows,'returned_row_count':len(rows),'truncated':raw['truncated'],'reported_total_rows':None,'currency':None,'quality':{'status':'WARN','limitations':['External MCP preview; business semantics and quality are not certified','At most 100 rows; no filters or ordering guarantees']}}

def safe_error(exc):
    # Async context-manager cleanup may wrap the fixed PublicError; never expose raw errors.
    if isinstance(exc,PublicError): return exc
    for child in getattr(exc,'exceptions',[]):
        found=safe_error(child)
        if found.code != 'REMOTE_CONNECTION_FAILED': return found
    if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in {401,403}:
        return PublicError(403,'REMOTE_ACCESS_DENIED','远端拒绝当前凭证或权限；请申请授权或更新专用凭证，不会切换账号绕过。')
    return PublicError(422,'REMOTE_CONNECTION_FAILED','远端连接、协议或读取失败；请检查批准地址和适配器。若查询已提交，结果可能未知，不会自动重复提交。')

async def http_navigation(draft, policy, operation, table=None, secrets=None):
    grant=policy.authorize(draft)
    credential=(secrets or ProductSecrets()).resolve(draft.secret_ref) if draft.secret_ref else None
    try:
        with anyio.fail_after(15):
            async with create_governed_http_client(draft.url, HTTPEndpointPolicy((grant.url,)), credential=credential) as client:
                async with streamable_http_client(draft.url,http_client=client) as (read,write,_):
                    async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=10)) as session:
                        await session.initialize()
                        tools=await session.list_tools()
                        if {t.name for t in tools.tools} != TOOLS:
                            raise PublicError(422,'PROTOCOL_MISMATCH','MCP工具与已审定的workspace_navigation_v1适配器不兼容，请选择匹配的服务。')
                        for tool in tools.tools:
                            schema=tool.inputSchema;expected=INPUTS[tool.name]
                            if schema.get('type')!='object' or set(schema.get('required',[]))!=set(expected) or set(schema.get('properties',{}))!=set(expected) or any(schema['properties'][k].get('type')!=v for k,v in expected.items()):
                                raise PublicError(422,'PROTOCOL_MISMATCH','MCP工具参数合同不兼容；不会根据远端描述执行其他工具。')
                        async def call(name,args):
                            result=await session.call_tool(name,args)
                            if result.isError or not isinstance(result.structuredContent,dict): invalid()
                            return result.structuredContent
                        metadata=catalog(await call('list_tables',{}),grant.table_ids)
                        if operation=='tables': return metadata
                        if table not in {t['id'] for t in metadata['tables']}:
                            raise PublicError(403,'RESOURCE_DENIED','该表未在后端授权范围或实际目录中；请选择已授权的表。')
                        if operation=='describe':
                            value=await call('describe_table',{'table':table})
                            if value.get('ok') is not True or not isinstance(value.get('metadata'),dict):invalid()
                            expected=next(t['name'] for t in metadata['tables'] if t['id']==table)
                            if value['metadata'].get('table')!=expected:invalid()
                            return value['metadata']
                        receipt=await call('submit_query',{'request':{'table':table,'limit':100},'idempotency_key':str(uuid4())})
                        task=receipt.get('task',{})
                        if receipt.get('ok') is not True or not isinstance(task.get('task_id'),str) or len(task['task_id'])>100: invalid()
                        # No retry/resubmission. This adapter requires completion in the receipt.
                        if task.get('status')!='SUCCEEDED':
                            raise PublicError(409,'REMOTE_RESULT_NOT_READY','远端查询尚未成功完成或失败；本预览适配器不自动重试提交，请检查远端任务。')
                        return preview_result(await call('get_query_result',{'task_id':task['task_id']}))
    except Exception as exc:
        raise safe_error(exc) from None

async def bounded_remote_navigation(draft,policy,operation,table=None,secrets=None):
    from .worker_runtime import run_worker,WorkerLimits,WorkerFailure,public_worker_error
    grant=policy.authorize(draft)
    credential=(secrets or ProductSecrets()).resolve(draft.secret_ref).get_secret_value() if draft.secret_ref else None
    if isinstance(draft,HTTPMCPDraft):
        name='http_navigation'
        payload={'draft':draft.model_dump(),'policy':{'http_mcp':[grant.model_dump()]},'operation':operation,'table':table,'credential':credential}
        limits=WorkerLimits(wall_seconds=20)
    else:
        name='postgres_navigation'
        payload={'draft':draft.model_dump(),'schemas':grant.schemas,'operation':operation,'table':table,'password':credential}
        limits=WorkerLimits(wall_seconds=12)
    try:
        value=await anyio.to_thread.run_sync(lambda:run_worker(name,payload,limits=limits))
    except WorkerFailure as exc:raise public_worker_error(exc) from None
    if value.get('ok') is not True:
        # Fixed child worker safe envelope, not arbitrary remote response.
        raise PublicError(value.get('status',422),value.get('code','REMOTE_CONNECTION_FAILED'),value.get('safe_message','读取失败，请检查来源与只读权限。'))
    return value['data']

async def postgres_navigation(draft,policy,operation,table=None,secrets=None):
    return await bounded_remote_navigation(draft,policy,operation,table,secrets)

async def remote_navigation(draft,policy,operation,table=None,secrets=None):
    return await bounded_remote_navigation(draft,policy,operation,table,secrets)
