"""Dedicated real browser/API/authenticated-MCP test service; stop via stdin.

No host credentials, default product storage or company data. Only temporary
synthetic CSV and an internal test-only credential; output contains URLs only.
"""
from contextlib import ExitStack
import json,os,socket,sys,tempfile,time
from pathlib import Path
from threading import Thread
import uvicorn
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.remote_access import RemoteAccessPolicy,HTTPGrant,SECRET_PREFIX
from data_workspace.warehouse.mcp_server import create_server

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='workspace-http-browser-') as temporary:
        root=Path(temporary);allowed=root/'allowed';allowed.mkdir()
        source=allowed/'fixture.csv';source.write_text('id,created_at,shipped_on\n'+''.join(f'{i},2025-01-01 12:00:00,2025-01-02\n' for i in range(120)),encoding='utf-8')
        database,_=SourceStore(root/'snapshots',allowed).snapshot(ProfileDraft(name='fixture',path=str(source),usage_authorized=True))
        token='test-only-browser-credential-not-for-production'
        reference='BROWSER_MCP';os.environ[SECRET_PREFIX+reference]=token
        mcp=create_server(root,database).streamable_http_app()
        class Auth:
            async def __call__(self,scope,receive,send):
                if scope['type']=='http' and dict(scope['headers']).get(b'authorization')!=('Bearer '+token).encode():
                    await send({'type':'http.response.start','status':403,'headers':[]})
                    await send({'type':'http.response.body','body':b'denied'});return
                await mcp(scope,receive,send)
        socks=[];servers=[];threads=[]
        try:
            for i in range(2):
                sock=socket.socket();sock.bind(('127.0.0.1',0));socks.append(sock)
            mcp_url=f'http://127.0.0.1:{socks[0].getsockname()[1]}/mcp'
            port=socks[1].getsockname()[1]
            api=create_app(Settings(mode='development',dev_identity=True,port=port,owned_warehouse=True))
            @api.post('/fixture-only/stdio-fault')
            async def test_stdio_job_fault():
                # Isolated temporary app only; never registered in production API.
                service=api.state.connector.client
                if service and service.current:service.current.transport.abort()
                return {'fault_requested':True}
            @api.post('/fixture-only/credential')
            def test_credential_switch(body:dict):
                # Fault injection exists ONLY in the dedicated temporary fixture.
                if body.get('enabled') is True:os.environ[SECRET_PREFIX+reference]=token
                else:os.environ.pop(SECRET_PREFIX+reference,None)
                return {'enabled':body.get('enabled') is True}
            api.state.sources=SourceStore(root/'profiles',allowed,RemoteAccessPolicy(http_mcp=[HTTPGrant(url=mcp_url,secret_ref=reference,table_ids=['t0'])]))
            @api.post('/fixture-only/retention-example')
            def test_retention_example():
                # Dedicated temporary root only. Counterfactual clock is a test fault,
                # not evidence that default runtime cleanup has been enabled.
                from datetime import timedelta
                from data_workspace.retention_executor import cleanup_one
                from data_workspace.contracts import AuthContext
                store=api.state.sources
                auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
                with store.lock:
                    clock=store.clock;at=clock()-timedelta(hours=25)
                    try:
                        store.clock=lambda:at
                        receipt=store.upload(auth,'isolated.csv',b'id,created_on\n1,2025-01-01\n')
                    finally:store.clock=clock
                return cleanup_one(store,auth,'uploads',receipt.file_id)
            @api.post('/fixture-only/retention-expire-tests')
            def test_retention_expire_tests():
                from datetime import timedelta
                store=api.state.sources
                with store.lock:
                    for test in store.tests.values():
                        if getattr(test.get('draft'),'name',None)=='过期演示':
                            test['at']=(store.clock()-timedelta(hours=25)).isoformat()
                return {'fault_requested':True}
            for application,sock in zip([Auth(),api],socks):
                server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',log_level='error',access_log=False))
                thread=Thread(target=lambda s=server,k=sock:s.run(sockets=[k]),daemon=True)
                servers.append(server);threads.append(thread);thread.start()
            deadline=time.monotonic()+10
            while not all(s.started for s in servers) and time.monotonic()<deadline:time.sleep(.02)
            if not all(s.started for s in servers):raise RuntimeError('fixture unavailable')
            print(json.dumps({'api_url':f'http://127.0.0.1:{port}','mcp_url':mcp_url,'secret_ref':reference}),flush=True)
            sys.stdin.readline()
        finally:
            for server in servers:server.should_exit=True
            for thread in threads:thread.join(8)
            for sock in socks:sock.close()
            if any(t.is_alive() for t in threads):raise RuntimeError('fixture did not stop')
