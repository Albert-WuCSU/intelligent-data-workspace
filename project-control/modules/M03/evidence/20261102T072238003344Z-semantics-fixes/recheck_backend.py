"""Recheck all backend cases after test-only PID readiness repair, preserve actual unchanged UI evidence."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,subprocess,os
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from check import sources
baseline=ROOT/'project-control/modules/M03/evidence/20261102T072241Z'
old=json.loads((baseline/'sources.json').read_text(encoding='utf-8'))
manifest,fingerprint=sources();changed=[p for p in set(old)|set(manifest) if old.get(p)!=manifest.get(p)]
assert changed==['services/api/tests/test_retention_cycle.py'], ('Only fixture changed',changed)
previous=json.loads((baseline/'results.json').read_text(encoding='utf-8'))
assert all(c['status']=='passed' for c in previous['checks'] if c['id']!='backend')
target=ROOT/'project-control/modules/M03/evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-semantics-final');target.mkdir()
(target/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'frontend-reuse.json').write_text(json.dumps({'verdict':'unchanged_pass','baseline':str(baseline.relative_to(ROOT)).replace(chr(92),'/'),'actual_checks_reused':['16frontend','41browser','types','build','pip dependency check'],'changed_files':changed,'all_product_frontend_browser_sources_contracts_runtime_locks':'unchanged SHA256','old_code_fingerprint':previous['code_fingerprint'],'current_code_fingerprint':fingerprint,'scope':'only backend test fixture readiness changed; no production/backend/UI functionality changed after actual UI pass'},ensure_ascii=False,indent=2),encoding='utf-8')
python=str(ROOT/'services/api/.venv/Scripts/python.exe');command=[python,'-m','pytest','services/api/tests','-q']
print('Checking full backend',flush=True)
r=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONUTF8':'1'},text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(target/'backend.txt').write_text(r.stdout,encoding='utf-8');print(r.stdout,flush=True)
checks=[{'id':'backend','command':command,'cwd':'.','exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','environment':'local','integration':'unit','code_fingerprint':fingerprint,'log':str((target/'backend.txt').relative_to(ROOT)).replace(chr(92),'/')}]
checks += [{**c,'verification':'reused_unchanged_product_sources','reuse_proof':str((target/'frontend-reuse.json').relative_to(ROOT)).replace(chr(92),'/')} for c in previous['checks'] if c['id']!='backend']
if sources()[1]!=fingerprint:checks.append({'id':'source-stability','exit_code':1,'status':'failed','message':'sources changed, repeat checks'})
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fingerprint,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print('Evidence:',target,flush=True);sys.exit(0 if all(c['status']=='passed' for c in checks) else 1)
