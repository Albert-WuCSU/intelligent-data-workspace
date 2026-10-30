"""Fixed independent cleanup interruption fixture; never registered as a product operation."""
import json,sys,time,os
from pathlib import Path
raw=sys.stdin.buffer.read(65537)
root=Path(__file__).resolve().parents[3];site=root/'services/api/.venv/Lib/site-packages'
sys.path[:0]=[str(root/'services/api/src'),str(site),str(site/'win32'),str(site/'win32/lib'),str(site/'Pythonwin')]
_dll=os.add_dll_directory(str(site/'pywin32_system32'))
payload=json.loads(raw)['payload']
from data_workspace.source_profiles import SourceStore
from data_workspace.contracts import AuthContext
import data_workspace.retention_executor as executor
from data_workspace.retention_cycle import execute_cycle

def pause(stage):
    if stage=='file_deleted':
        Path(payload['signal']).write_text(str(os.getpid()))
        time.sleep(30)
executor.observe=pause
value=execute_cycle(SourceStore(payload['root']),AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer'))
print(json.dumps({'ok':True,'data':value}))
