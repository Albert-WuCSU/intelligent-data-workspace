"""Start the two loopback-only development services; Ctrl+C stops owned processes."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[1]

def node_path():
    configured = os.getenv('WORKSPACE_NODE')
    if configured:
        if not Path(configured).is_file():raise RuntimeError('WORKSPACE_NODE does not point to a file')
        return configured
    found = shutil.which('node')
    if found:return found
    bundled = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    if bundled.is_file():return str(bundled)
    raise RuntimeError('Install Node.js >=22.12 or set WORKSPACE_NODE')

def frontend_environment(environment):
    # Browser build tools must never inherit backend product secrets or host credentials.
    allowed = {'SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','HOME','PATH','PATHEXT','LOCALAPPDATA','APPDATA','LANG','PYTHONUTF8','WORKSPACE_BROWSER_EVIDENCE','WORKSPACE_XLSX_FIXTURE'}
    return {k:v for k,v in environment.items() if k.upper() in allowed}

def backend_environment(environment):
    result=frontend_environment(environment)
    for key,value in environment.items():
        if key in {'WORKSPACE_MODE','WORKSPACE_DEV_IDENTITY','WORKSPACE_HOST','WORKSPACE_PORT','WORKSPACE_OWNED_WAREHOUSE','WORKSPACE_CONNECTOR_POLICY'} or key.startswith('WORKSPACE_CONNECTOR_SECRET_'):
            result[key]=value
    return result

if __name__ == '__main__':
    python = ROOT/'services/api/.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    vite = ROOT/'apps/web/node_modules/vite/bin/vite.js'
    if not python.is_file() or not vite.is_file():raise SystemExit('Project dependencies missing; follow DEVELOPMENT.md')
    for port in (5173,8000):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1',port))==0:raise SystemExit(f'Port {port} already in use. Stop its owner or review before starting.')
    env={**os.environ,'WORKSPACE_MODE':'development','WORKSPACE_DEV_IDENTITY':'1','WORKSPACE_HOST':'127.0.0.1','WORKSPACE_PORT':'8000','PYTHONUTF8':'1','WORKSPACE_OWNED_WAREHOUSE':os.getenv('WORKSPACE_OWNED_WAREHOUSE','1')}
    children=[]
    flags = subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    try:
        children.append(subprocess.Popen([str(python),'-m','data_workspace.main'],cwd=ROOT,env=backend_environment(env),creationflags=flags))
        children.append(subprocess.Popen([node_path(),str(vite),'--host','127.0.0.1','--port','5173','--strictPort'],cwd=ROOT/'apps/web',env=frontend_environment(env),creationflags=flags))
        print('Local development: http://127.0.0.1:5173  | API: http://127.0.0.1:8000',flush=True)
        print('Loopback only; development identity; memory tasks; owned synthetic MCP opt-in (natural-language agent not connected). Ctrl+C stops services.',flush=True)
        while all(p.poll() is None for p in children):time.sleep(.5)
        raise SystemExit('A service stopped; see output above.')
    except KeyboardInterrupt:
        print('Stopping owned development services...',flush=True)
    finally:
        for p in children:
            if p.poll() is None:p.terminate()
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
