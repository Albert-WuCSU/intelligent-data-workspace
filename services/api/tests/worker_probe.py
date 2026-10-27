"""Standalone OS fault fixture, never a production worker operation."""
import json,os,subprocess,sys,time
from pathlib import Path
request=json.loads(sys.stdin.buffer.read())['payload']
mode=request['mode']
if 'pid_file' in request:Path(request['pid_file']).write_text(str(os.getpid()))
if mode in {'child_timeout','child_crash'}:
    child=subprocess.Popen([sys.executable,'-S','-c','import time;time.sleep(30)'],creationflags=subprocess.CREATE_NO_WINDOW)
    Path(request['child_file']).write_text(str(child.pid))
if mode=='process_limit':
    try:
        child=subprocess.Popen([sys.executable,'-S','-c','pass'],creationflags=subprocess.CREATE_NO_WINDOW)
        refused=child.wait(timeout=2)!=0
    except OSError:refused=True
    print(json.dumps({'ok':True,'data':{'process_refused':refused}}))
elif mode=='memory':
    try:value=bytearray(96*1024*1024)
    except MemoryError:
        print(json.dumps({'ok':True,'data':{'allocation_refused':True}}));raise SystemExit(0)
    print(json.dumps({'ok':True,'data':{'allocation_refused':False}}))
elif mode=='cpu':
    while True:pass
elif mode in {'timeout','child_timeout'}:time.sleep(30)
elif mode in {'crash','child_crash'}:os._exit(9)
elif mode=='output':
    sys.stdout.write('x'*100000);sys.stdout.flush();time.sleep(30)
else:print(json.dumps({'ok':True,'data':{'pid':os.getpid(),'secret_env_absent':not any('SECRET' in k or k.startswith('PG') for k in os.environ)}}))
