"""Run M01 checks and record real commands, exits, source hashes and logs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from dev import node_path,ROOT


def sources():
    files=[]
    for directory in ('services/api/src','services/api/tests','apps/web/src','contracts','scripts','tests'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ('CONNECTORS.md','WAREHOUSE.md','services/api/requirements.warehouse.lock.txt','services/api/requirements.excel.lock.txt','services/api/requirements.postgres.lock.txt','services/api/pyproject.toml','services/api/requirements.lock.txt','apps/web/package.json',
                 'apps/web/tsconfig.json','apps/web/vite.config.ts','apps/web/pnpm-lock.yaml','apps/web/pnpm-workspace.yaml',
                 'apps/web/index.html','playwright.config.mjs','DEVELOPMENT.md','start-workspace.cmd'):
        files.append(ROOT/name)
    files.append(ROOT/'services/api/requirements.langgraph.lock.txt')
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}
    fingerprint=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return manifest,fingerprint

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser();parser.add_argument('--browser',action='store_true');parser.add_argument('--module',choices=['M01','M02','M04-A','M03','M04'],default='M01');args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=ROOT/f'project-control/modules/{args.module}/evidence'/stamp
    target.mkdir(parents=True,exist_ok=False)
    python=str(ROOT/'services/api/.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
    node=node_path();web=ROOT/'apps/web'
    tasks=[('backend',[python,'-m','pytest','services/api/tests','-q'],ROOT),
           ('dependency-check',[python,'-m','pip','check'],ROOT),
           ('types',[node,str(web/'node_modules/typescript/bin/tsc'),'--noEmit'],web),
           ('build',[node,str(web/'node_modules/vite/bin/vite.js'),'build'],web),
           ('frontend',[node,str(web/'node_modules/vitest/vitest.mjs'),'run'],web)]
    if args.browser:
        sys.path.insert(0,str(ROOT/'services/api/tests'))
        from xlsx_fixture import workbook_bytes
        (target/'xlsx-fixture.xlsx').write_bytes(workbook_bytes())
    if args.browser:tasks.append(('browser',[node,str(web/'node_modules/@playwright/test/cli.js'),'test','--config','playwright.config.mjs'],ROOT))
    manifest,fingerprint=sources()
    (target/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    results=[]
    env={**os.environ,'WORKSPACE_XLSX_FIXTURE':str(target/'xlsx-fixture.xlsx'),'PYTHONUTF8':'1','WORKSPACE_BROWSER_EVIDENCE':str((target/'browser').relative_to(ROOT)).replace(chr(92),'/')}
    for label,command,cwd in tasks:
        print('Checking',label,flush=True)
        result=subprocess.run(command,cwd=cwd,env=env,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (target/(label+'.txt')).write_text(result.stdout,encoding='utf-8')
        results.append({'id':label,'command':command,'cwd':str(cwd.relative_to(ROOT)) or '.',
                        'exit_code':result.returncode,'status':'passed' if result.returncode==0 else 'failed',
                        'environment':'local','integration':'real' if label=='browser' else 'unit',
                        'code_fingerprint':fingerprint,'log':str((target/(label+'.txt')).relative_to(ROOT)).replace('\\','/')})
        print(result.stdout,flush=True)
    if sources()[1]!=fingerprint:
        results.append({'id':'source-stability','exit_code':1,'status':'failed','message':'Sources changed during verification. Repeat checks.'})
    (target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fingerprint,'checks':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Evidence:',target,flush=True)
    sys.exit(0 if all(t['status']=='passed' for t in results) else 1)
