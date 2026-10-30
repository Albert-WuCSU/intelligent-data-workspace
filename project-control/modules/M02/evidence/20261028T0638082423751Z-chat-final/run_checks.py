import json,subprocess,sys,os
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
from dev import node_path
sys.path.insert(0,str(root/'services/api/tests'));from xlsx_fixture import workbook_bytes
manifest,fp=sources();old=json.loads(Path('project-control/modules/M02/evidence/20261028T062915Z/sources.json').read_text(encoding='utf-8'));changes=[n for n,h in manifest.items() if old.get(n)!=h]
assert set(changes)=={'apps/web/src/DataSourceWorkspace.tsx','tests/remote-onboarding.spec.mjs'},changes
(target/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');(target/'reuse.json').write_text(json.dumps({'unchanged_backend':'project-control/modules/M02/evidence/20261028T062915Z/results.json','changes':changes,'reuse':'actual287backend/pip results remain at original fingerprint; all source/tests/contracts/locks byte-identical. Frontend/full27 browser rerun after restore expiry behavior/legacy foldedcard locator, no backend claim of rerun'},indent=2),encoding='utf-8');(target/'xlsx-fixture.xlsx').write_bytes(workbook_bytes())
node=node_path();web=root/'apps/web';env={**os.environ,'PYTHONUTF8':'1','WORKSPACE_XLSX_FIXTURE':str(target.resolve()/'xlsx-fixture.xlsx'),'WORKSPACE_BROWSER_EVIDENCE':str(target/'browser')}
checks=[]
for id,cmd,cwd in [('types',[node,str(web/'node_modules/typescript/bin/tsc'),'--noEmit'],web),('frontend',[node,str(web/'node_modules/vitest/vitest.mjs'),'run'],web),('build',[node,str(web/'node_modules/vite/bin/vite.js'),'build'],web),('browser',[node,str(web/'node_modules/@playwright/test/cli.js'),'test','--config','playwright.config.mjs'],root)]:
 q=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace');log=target/(id+'.txt');log.write_text(q.stdout+q.stderr,encoding='utf-8');print(id,q.returncode,q.stdout+q.stderr,flush=True);checks.append({'id':id,'command':cmd,'cwd':cwd.relative_to(root).as_posix(),'exit_code':q.returncode,'status':'passed' if q.returncode==0 else 'failed','environment':'local','integration':'real' if id=='browser' else 'unit','code_fingerprint':fp,'log':log.as_posix()})
stable=sources()[1]==fp;(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'source_stable':stable,'code_fingerprint':fp,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8');sys.exit(0 if stable and all(c['exit_code']==0 for c in checks) else 1)
