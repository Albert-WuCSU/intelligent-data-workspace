import json,hashlib,subprocess,sys,os
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
from dev import node_path
sys.path.insert(0,str(root/'services/api/tests'));from xlsx_fixture import workbook_bytes
manifest,fp=sources();previous=Path('project-control/modules/M02/evidence/20261027T073609Z');old=json.loads((previous/'sources.json').read_text(encoding='utf-8'))
changed=[n for n in manifest if old.get(n)!=manifest[n]]
assert changed==['tests/source-onboarding.spec.mjs'],changed
(target/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');(target/'xlsx-fixture.xlsx').write_bytes(workbook_bytes())
(target/'reuse.json').write_text(json.dumps({'previous_results':(previous/'results.json').as_posix(),'changed_sources':changed,'backend_frontend_contracts_locks':'byte-identical; prior passed55/261/10/type/build/pip checks retained with original fingerprints, NOT represented as rerun','browser':'rerun all23 with real independent current-code source fixture'},indent=2),encoding='utf-8')
command=[node_path(),str(root/'apps/web/node_modules/@playwright/test/cli.js'),'test','--config','playwright.config.mjs']
env={**os.environ,'WORKSPACE_XLSX_FIXTURE':str(target.resolve()/'xlsx-fixture.xlsx'),'WORKSPACE_BROWSER_EVIDENCE':str(target/'browser'),'PYTHONUTF8':'1'}
r=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace');(target/'browser.txt').write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout+r.stderr,flush=True)
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fp,'source_stable':sources()[1]==fp,'checks':[{'id':'browser','command':command,'cwd':'.','exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','environment':'local','integration':'real','scope':'current independent SourceStore API/MCP for local/XLSX/retention and one explicit expiry-metadata compatibility fixture; core accepted UI on default old API; default enablement not_run','code_fingerprint':fp,'log':(target/'browser.txt').as_posix()}]},indent=2),encoding='utf-8')
sys.exit(r.returncode)
