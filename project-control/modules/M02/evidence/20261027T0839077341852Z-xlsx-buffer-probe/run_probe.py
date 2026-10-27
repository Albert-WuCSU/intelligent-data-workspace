import subprocess,sys,json,os
from pathlib import Path
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
from dev import node_path
sys.path.insert(0,str(root/'services/api/tests'));from xlsx_fixture import workbook_bytes
manifest,fp=sources();(target/'sources.json').write_text(json.dumps(manifest,indent=2));(target/'xlsx-fixture.xlsx').write_bytes(workbook_bytes())
command=[node_path(),str(root/'apps/web/node_modules/@playwright/test/cli.js'),'test','tests/source-onboarding.spec.mjs','--grep','xlsx workbook','--config','playwright.config.mjs']
env={**os.environ,'WORKSPACE_XLSX_FIXTURE':str(target.resolve()/'xlsx-fixture.xlsx'),'WORKSPACE_BROWSER_EVIDENCE':str(target/'browser'),'PYTHONUTF8':'1'}
r=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace');(target/'browser.txt').write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout+r.stderr)
(target/'results.json').write_text(json.dumps({'code_fingerprint':fp,'checks':[{'id':'xlsx-frame-probe','command':command,'exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','integration':'real','environment':'local','code_fingerprint':fp,'log':(target/'browser.txt').as_posix()}]},indent=2));sys.exit(r.returncode)
