"""Fixed pipe-gated bootstrap. Launched with base Python -S, no user entrypoints."""
import json
from pathlib import Path
import sys

# Reading the pipe blocks until parent JobObject assignment succeeds.
raw=sys.stdin.buffer.read(65537)
if len(raw)>65536:raise SystemExit(2)
root=Path(__file__).resolve().parents[4]
site=root/'services/api/.venv/Lib/site-packages'
sys.path[:0]=[str(root/'services/api/src'),str(site),str(site/'win32'),str(site/'win32/lib'),str(site/'Pythonwin')]
# Explicit approved pywin32 DLL directory, not executable .pth/sitecustomize hooks.
import os
_dll=os.add_dll_directory(str(site/'pywin32_system32'))


def execute(operation,payload):
    if operation=='retention_cycle':
        from data_workspace.retention_cycle import worker_cycle
        return worker_cycle(payload)
    if operation=='upload_preflight':
        from data_workspace.upload_preflight import inspect_upload
        return inspect_upload(payload)
    if operation=='snapshot':
        from data_workspace.source_profiles import SourceStore,ProfileDraft
        store=SourceStore(payload['root'],payload['allowed_root'])
        path,label=store.snapshot(ProfileDraft.model_validate(payload['draft']),snapshot_id=payload['snapshot_id'])
        return {'database':str(path),'label':label}
    if operation=='postgres_navigation':
        from data_workspace.warehouse.postgres_worker import navigate
        return navigate(payload)
    if operation=='http_navigation':
        import asyncio
        from pydantic import SecretStr
        from data_workspace.remote_access import HTTPMCPDraft,RemoteAccessPolicy
        from data_workspace.remote_sources import http_navigation
        class ResolvedSecret:
            def resolve(self,reference):
                if reference!=payload['draft']['secret_ref']:raise ValueError('reference mismatch')
                return SecretStr(payload['credential'])
        return asyncio.run(http_navigation(HTTPMCPDraft.model_validate(payload['draft']),RemoteAccessPolicy.model_validate(payload['policy']),payload['operation'],payload.get('table'),ResolvedSecret()))
    raise ValueError('operation denied')

try:
    request=json.loads(raw.decode('utf-8'))
    value={'ok':True,'data':execute(request['operation'],request['payload'])}
except Exception as exc:
    # Only known class/category and safe public status; raw text/tracebacks suppressed.
    from data_workspace.auth import PublicError
    from data_workspace.excel_import import ExcelImportError
    from data_workspace.warehouse.postgres_worker import ResourceDenied
    if isinstance(exc,PublicError):value={'ok':False,'code':exc.code,'status':exc.status,'safe_message':exc.message}
    elif isinstance(exc,ExcelImportError):value={'ok':False,'code':'INVALID_XLSX','status':422,'safe_message':str(exc)}
    elif isinstance(exc,ResourceDenied):value={'ok':False,'code':'RESOURCE_DENIED','status':403,'safe_message':'该表不在授权读取范围。'}
    else:value={'ok':False,'code':'SOURCE_OPERATION_FAILED','status':422,'safe_message':'读取失败，请检查来源、类型、只读权限和资源限额；原配置保留。'}
sys.stdout.write(json.dumps(value,ensure_ascii=False,allow_nan=False))
