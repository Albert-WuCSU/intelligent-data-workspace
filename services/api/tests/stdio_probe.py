"""Fixed test-only stdio native-fault fixture, never a product entrypoint."""
import json,os,sys,time
from pathlib import Path
bootstrap=json.loads(sys.stdin.buffer.readline())
mode=bootstrap['warehouse']
if bootstrap['database']:Path(bootstrap['database']).write_text(str(os.getpid()))
if mode=='cpu':
    while True:pass
elif mode=='output':
    sys.stdout.write('x'*(512*1024+4096));sys.stdout.flush();time.sleep(30)
elif mode=='crash':os._exit(9)
elif mode=='memory':
    try:value=bytearray(96*1024*1024);refused=False
    except MemoryError:refused=True
    sys.stdout.write(json.dumps({'jsonrpc':'2.0','method':'notifications/memory','params':{'refused':refused}})+'\n');sys.stdout.flush();time.sleep(30)
else:
    sys.stdout.write(json.dumps({'jsonrpc':'2.0','method':'notifications/ready'})+'\n');sys.stdout.flush();time.sleep(30)
