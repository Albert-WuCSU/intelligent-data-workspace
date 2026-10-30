import sys,subprocess,json
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd();target=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));from check import sources
manifest,fp=sources();(target/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
command=[sys.executable,'-m','pytest','services/api/tests/test_retention_cycle.py','services/api/tests/test_retention_execution.py','services/api/tests/test_retention.py','-q']
r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');log=target/'tests.txt';log.write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout+r.stderr)
(target/'results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'code_fingerprint':fp,'source_stable':sources()[1]==fp,'checks':[{'id':'retention-cycle-and-recovery','command':command,'cwd':'.','exit_code':r.returncode,'status':'passed' if r.returncode==0 else 'failed','environment':'local','integration':'real','code_fingerprint':fp,'scope':'native deletion/cycle/Job only independent new temporary fixtures; metadata/clock faults isolated; default data not run','log':log.as_posix()}]},indent=2),encoding='utf-8');sys.exit(r.returncode)
