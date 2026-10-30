import json,subprocess,sys,os
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
from dev import node_path
sys.path.insert(0,str(root/'services/api/tests'));from xlsx_fixture import workbook_bytes
manifest,fp=sources();(target/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
previous=json.loads(Path('project-control/modules/M02/evidence/20261028T024336Z/sources.json').read_text(encoding='utf-8'))
changed=[n for n,h in manifest.items() if previous.get(n)!=h]
assert not any(n.startswith(('services/api/src/','services/api/tests/','contracts/')) for n in changed),changed
(target/'reuse.json').write_text(json.dumps({'unchanged_backend_results':'project-control/modules/M02/evidence/20261028T024336Z/results.json','reuse_reason':'all backend source/tests/contracts and locks byte-identical; UI changes rerun full frontend/browser;281 backend not rerun or relabeled with new fingerprint','changed_sources':changed,'model_requests':'not_run; no credentials copied or external providers called'},indent=2),encoding='utf-8')
(target/'xlsx-fixture.xlsx').write_bytes(workbook_bytes())
node=node_path();web=root/'apps/web';env={**os.environ,'PYTHONUTF8':'1','WORKSPACE_XLSX_FIXTURE':str(target.resolve()/'xlsx-fixture.xlsx'),'WORKSPACE_BROWSER_EVIDENCE':str(target/'browser')}
tasks=[('types',[node,str(web/'node_modules/typescript/bin/tsc'),'--noEmit'],web),('frontend',[node,str(web/'node_modules/vitest/vitest.mjs'),'run'],web),('build',[node,str(web/'node_modules/vite/bin/vite.js'),'build'],web),('browser',[node,str(web/'node_modules/@playwright/test/cli.js'),'test','--config','playwright.config.mjs'],root),('prd-consistency',[sys.executable,'project-control/prd/validate.py','--root','.','--installed-skill','D:/Users/luqianwu/.codex/skills/project-pdca'],root)]
results=[]
for id,command,cwd in tasks:
 q=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace');log=target/(id+'.txt');log.write_text(q.stdout+q.stderr,encoding='utf-8');print(id,q.returncode,q.stdout+q.stderr,flush=True)
 results.append({'id':id,'command':command,'cwd':cwd.relative_to(root).as_posix(),'exit_code':q.returncode,'status':'passed' if q.returncode==0 else 'failed','environment':'local','integration':'real' if id=='browser' else 'unit','code_fingerprint':fp,'log':log.as_posix()})
stable=sources()[1]==fp
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fp,'source_stable':stable,'checks':results},ensure_ascii=False,indent=2),encoding='utf-8');sys.exit(0 if stable and all(c['exit_code']==0 for c in results) else 1)
