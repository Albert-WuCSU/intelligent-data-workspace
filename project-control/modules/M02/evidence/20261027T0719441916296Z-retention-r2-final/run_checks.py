import json,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
manifest,fp=sources();(target/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
command=[sys.executable,'-m','pytest','services/api/tests/test_retention.py','services/api/tests/test_retention_execution.py','-q']
r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');(target/'tests.txt').write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout+r.stderr,flush=True)
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fp,'source_stable':sources()[1]==fp,'checks':[{'id':'retention-isolated-execution','command':command,'cwd':'.','exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','environment':'local','integration':'real','scope':'native deletion of independent fresh test UUID artifacts only; default runtime not_run; clock/receipt faults also isolated units','code_fingerprint':fp,'log':(target/'tests.txt').as_posix()}]},indent=2),encoding='utf-8');sys.exit(r.returncode if r.returncode else subprocess.run([sys.executable,'scripts/check.py','--module','M02','--browser']).returncode)

