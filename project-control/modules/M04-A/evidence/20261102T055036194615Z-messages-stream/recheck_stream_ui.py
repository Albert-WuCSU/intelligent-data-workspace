from pathlib import Path
import json,hashlib,subprocess,sys,os
from datetime import datetime,timezone
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from check import sources
from dev import node_path
baseline=ROOT/'project-control/modules/M04-A/evidence/20261102T055036Z'
old=json.loads((baseline/'sources.json').read_text(encoding='utf-8'))
manifest,fingerprint=sources()
# Only App/form/settings navigation and browser tests changed after the full run.
unchanged={path:sha for path,sha in old.items() if not path.startswith(('apps/web/','tests/'))}
assert all(manifest.get(path)==sha for path,sha in unchanged.items()), 'Backend or contracts changed; full backend rerun required'
previous=json.loads((baseline/'results.json').read_text(encoding='utf-8'))
assert all(c['exit_code']==0 for c in previous['checks'] if c['id'] in ('backend','dependency-check'))
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-stream-ui-final'
target=ROOT/'project-control/modules/M04-A/evidence'/stamp;target.mkdir()
(target/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'backend-reuse.json').write_text(json.dumps({'source_baseline':str(baseline.relative_to(ROOT)).replace(chr(92),'/'),'scope':'517 backend cases and dependency-check reused, not rerun: all non-frontend source/contracts/runtime scripts/locks unchanged','verified_paths':list(unchanged),'prior_code_fingerprint':previous['code_fingerprint'],'current_code_fingerprint':fingerprint,'verdict':'unchanged_pass'},ensure_ascii=False,indent=2),encoding='utf-8')
web=ROOT/'apps/web';node=node_path()
tasks=[('types',[node,str(web/'node_modules/typescript/bin/tsc'),'--noEmit'],web),('build',[node,str(web/'node_modules/vite/bin/vite.js'),'build'],web),('frontend',[node,str(web/'node_modules/vitest/vitest.mjs'),'run'],web),('browser',[node,str(web/'node_modules/@playwright/test/cli.js'),'test','--config','playwright.config.mjs'],ROOT)]
checks=[];env={**os.environ,'PYTHONUTF8':'1','WORKSPACE_XLSX_FIXTURE':str(baseline/'xlsx-fixture.xlsx'),'WORKSPACE_BROWSER_EVIDENCE':str((target/'browser').relative_to(ROOT)).replace(chr(92),'/')}
for label,command,cwd in tasks:
 print('Checking',label,flush=True);r=subprocess.run(command,cwd=cwd,env=env,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (target/(label+'.txt')).write_text(r.stdout,encoding='utf-8');print(r.stdout,flush=True)
 checks.append({'id':label,'command':command,'cwd':str(cwd.relative_to(ROOT)) or '.','exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','environment':'local','integration':'real' if label=='browser' else 'unit','code_fingerprint':fingerprint,'log':str((target/(label+'.txt')).relative_to(ROOT)).replace(chr(92),'/')})
if sources()[1]!=fingerprint:checks.append({'id':'source-stability','exit_code':1,'status':'failed','message':'sources changed; rerun required'})
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fingerprint,'checks':checks,'backend_reuse_ref':str((target/'backend-reuse.json').relative_to(ROOT)).replace(chr(92),'/')},ensure_ascii=False,indent=2),encoding='utf-8')
print('Evidence:',target,flush=True)
sys.exit(0 if all(c['status']=='passed' for c in checks) else 1)
