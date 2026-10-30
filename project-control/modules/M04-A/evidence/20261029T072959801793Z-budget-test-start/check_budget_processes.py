from pathlib import Path
import os,sys,tempfile,subprocess,json
from data_workspace.model_budget import EstimatedBudget
root=Path(__file__).resolve().parents[5]
# Only independent temporary test storage; no product key/environment credentials inherited.
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP','PATH'}}
env['PYTHONUTF8']='1'
with tempfile.TemporaryDirectory(prefix='model-estimate-process-test-') as folder:
    storage=Path(folder)/'ledger';EstimatedBudget(storage).summary()
    code="""import asyncio,sys
from data_workspace.model_budget import EstimatedBudget
from data_workspace.auth import PublicError
try:
 for _ in range(20):asyncio.run(EstimatedBudget(sys.argv[1]).reserve(request_bytes=500,max_output_tokens=128))
 print('finished')
except PublicError as exc:print(exc.code)
"""
    children=[subprocess.Popen([sys.executable,'-c',code,str(storage)],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') for _ in range(4)]
    outputs=[p.communicate(timeout=40) for p in children]
    assert all(p.returncode==0 for p in children),outputs
    count=EstimatedBudget(storage).summary().reserved_requests
    assert count==60,(count,outputs)
    probe="""import sys,json
from data_workspace.model_budget import EstimatedBudget
from data_workspace.auth import PublicError
b=EstimatedBudget(sys.argv[1]);print(b.summary().model_dump_json())
import asyncio
try:asyncio.run(b.reserve(request_bytes=500,max_output_tokens=128));raise RuntimeError('over budget')
except PublicError as exc:assert exc.code=='MODEL_ESTIMATED_BUDGET_EXHAUSTED'
"""
    fresh=subprocess.run([sys.executable,'-c',probe,str(storage)],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',timeout=15)
    assert fresh.returncode==0,fresh.stderr
    print(json.dumps({'status':'passed','real_concurrent_child_processes':4,'persisted_request_count_after_process_exit':count,'fresh_process_summary':json.loads(fresh.stdout),'fresh_process_extra_request':'denied','scope':'temporary fixture only, no company API or real key'},ensure_ascii=False))
