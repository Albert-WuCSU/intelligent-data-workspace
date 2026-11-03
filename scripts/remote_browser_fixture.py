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
            for i in range(3):
                sock=socket.socket();sock.bind(('127.0.0.1',0));socks.append(sock)
            mcp_url=f'http://127.0.0.1:{socks[0].getsockname()[1]}/mcp'
            port=socks[1].getsockname()[1]
            api=create_app(Settings(mode='development',dev_identity=True,port=port,owned_warehouse=True))
            from data_workspace.semantic_store import SemanticStore
            api.state.semantics=SemanticStore(root/'semantics')
            @api.post('/fixture-only/inject-personal-chat-transport')
            async def inject_personal_chat_transport():
                import httpx
                def handler(request):
                    return httpx.Response(200,json={'model':'fixture-model','choices':[{'finish_reason':'stop',
                        'message':{'role':'assistant','content':'personal fixture OK'}}],
                        'usage':{'prompt_tokens':8,'completion_tokens':4}})
                api.state.model_provider.transport=httpx.MockTransport(handler)
                return {'fixture_only':True}
            @api.post('/fixture-only/enable-observed-model-alias')
            async def enable_observed_alias_fixture():
                import httpx
                from data_workspace.model_provider import MessagesProvider, ModelConfiguration
                from data_workspace.model_budget import EstimatedBudget
                from data_workspace.model_routes import ModelTests
                def handler(request):
                    return httpx.Response(200,json={'type':'message','role':'assistant',
                        'model':'deepseek-v4-1-flash-261017','stop_reason':'end_turn',
                        'content':[{'type':'thinking','thinking':'fixture hidden reasoning'},
                                   {'type':'text','text':'OK'}], 'usage':{'input_tokens':49,'output_tokens':16}})
                api.state.model_provider=MessagesProvider(ModelConfiguration(
                    'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','deepseek-v4.1-flash','anthropic_messages','bearer'),
                    'fixture-only-model-key',EstimatedBudget(root/'observed-alias-budget'),httpx.MockTransport(handler))
                api.state.model_tests=ModelTests()
                return {'fixture_only':True}
            @api.post('/fixture-only/enable-model-diagnostics')
            async def enable_model_diagnostics_fixture():
                import httpx
                from data_workspace.model_provider import MessagesProvider, ModelConfiguration
                from data_workspace.model_budget import EstimatedBudget
                from data_workspace.model_routes import ModelTests
                def handler(request):
                    return httpx.Response(200,json={'type':'message','role':'assistant',
                        'model':'deepseek-v4.1-flash','stop_reason':'max_tokens',
                        'content':[{'type':'text','text':'fixture partial output is not verified'}],
                        'usage':{'input_tokens':10,'output_tokens':128}})
                api.state.model_provider=MessagesProvider(ModelConfiguration(
                    'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','deepseek-v4.1-flash','anthropic_messages','bearer'),
                    'fixture-only-model-key',EstimatedBudget(root/'model-diagnostics-budget'),httpx.MockTransport(handler))
                api.state.model_tests=ModelTests()
                return {'fixture_only':True}
            @api.post('/fixture-only/semantic-source')
            async def semantic_source_fixture():
                from uuid import uuid4
                from data_workspace.contracts import AuthContext
                auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
                id=str(uuid4())
                semantic_source=root/'allowed'/'semantic-fixture.csv'
                semantic_source.write_text('id,amount,cost,created_at\n1,10,3,2025-01-01\n2,20,4,2025-01-02\n',encoding='utf-8')
                semantic_database,_=SourceStore(root/'semantic-snapshots',allowed).snapshot(ProfileDraft(name='semantic fixture',path=str(semantic_source),usage_authorized=True))
                with api.state.sources.db() as db:
                    db.execute('INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES(?,?,?,?,?,?,?,?)',[id,api.state.sources.owner(auth),'Semantic fixture rows',1,1,str(semantic_database),'independent local fixture', '2026-11-02'])
                return {'id':id,'table':'t0'}
            @api.post('/fixture-only/agent-ready')
            async def agent_ready_fixture(request:__import__('fastapi').Request):
                mode=(await request.json()).get('mode','normal')
                from uuid import uuid4
                import httpx
                from data_workspace.contracts import AuthContext
                from data_workspace.semantic_contracts import SemanticDraftInput,SemanticMetric,PublishInput
                from data_workspace.semantic_metadata import read_schema
                from data_workspace.model_provider import MessagesProvider,ModelConfiguration
                from data_workspace.model_budget import EstimatedBudget
                auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
                file=allowed/'agent-fixture.csv';file.write_text('id,region,amount,cost,created_at\n'+''.join(f'{i},A,{i},1,2026-10-01\n' for i in range(1,151)),encoding='utf-8')
                database,_=SourceStore(root/'agent-snapshots',allowed).snapshot(ProfileDraft(name='agent fixture',path=str(file),usage_authorized=True))
                source_id=str(uuid4())
                with api.state.sources.db() as db:db.execute('INSERT INTO profiles(id,owner,name,version,enabled,database_path,source_label,last_test_at) VALUES(?,?,?,?,?,?,?,?)',[source_id,api.state.sources.owner(auth),'Agent fixture source150rows-'+source_id[:6],1,1,str(database),'independent fixture','2026-11-02'])
                metric=SemanticMetric(id='amount_sum',name='总金额',operator='sum',column='amount',unit='测试单位',additive=True)
                draft=api.state.semantics.draft(auth,SemanticDraftInput(domain='agent_fixture_'+source_id[:8],name='受控问数测试口径',owner_note='fixture not enterprise data',source_id=source_id,table_id='t0',grain=['id'],grain_note='one row per id',metrics=[metric]))
                schema=await read_schema(api.state.sources,auth,source_id,'t0')
                published=api.state.semantics.publish(auth,PublishInput(draft_id=draft.draft_id,validation_id=str(uuid4()),request_id=str(uuid4()),approve_definition=True),draft,schema)
                def handler(req):return httpx.Response(200,json={'type':'message','role':'assistant','model':'fixture-agent-model','stop_reason':'max_tokens' if mode=='incomplete' else 'end_turn','content':[{'type':'text','text':json.dumps({'metric_id':'amount_sum','dimensions':[],'time_range':None,'needs_clarification':'none'})}],'usage':{'input_tokens':30,'output_tokens':28}})
                api.state.model_provider=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','fixture-agent-model','anthropic_messages','bearer'),'fake-fixture-agent-key',EstimatedBudget(root/'agent-budget'),httpx.MockTransport(handler));api.state.model_provider._verified=True;api.state.model_enabled=True
                return {'source_name':'Agent fixture source150rows-'+source_id[:6],'source_id':source_id,'semantic_version_id':published.id,'model_ref':api.state.model_tests.generation+':'+api.state.model_provider.configuration.version}
            @api.post('/fixture-only/semantic-restart')
            async def semantic_restart_fixture():
                api.state.semantics=SemanticStore(root/'semantics')
                return {'fixture_only':True}
            @api.post('/fixture-only/enable-stream-test')
            async def enable_stream_fixture(request:__import__('fastapi').Request):
                import httpx,asyncio
                from data_workspace.model_provider import MessagesProvider,ModelConfiguration
                from data_workspace.model_budget import EstimatedBudget
                from data_workspace.model_stream_routes import StreamTests
                from data_workspace.model_routes import ModelTests
                mode=(await request.json()).get('mode','complete')
                key='fixture-only-stream-key';model='fixture-stream-model'
                class Stream(httpx.AsyncByteStream):
                    async def __aiter__(self):
                        events=[{'type':'message_start','message':{'type':'message','role':'assistant','model':model,'content':[],'stop_reason':None,'usage':{'input_tokens':8}}},
                            {'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}},
                            {'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':'Live fixture text safe. '*4}}]
                        if mode=='complete':events += [{'type':'content_block_stop','index':0},{'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':20}},{'type':'message_stop'}]
                        for event in events:
                            yield ('event: '+event['type']+'\ndata: '+json.dumps(event)+'\n\n').encode()
                            await asyncio.sleep(.12)
                        if mode=='cancel':await asyncio.sleep(30)
                def handler(req):
                    if mode=='denied':return httpx.Response(403,text='fixture-private-error-'+key)
                    return httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Stream())
                await api.state.model_stream_tests.close()
                api.state.model_provider=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',model,'anthropic_messages','bearer'),key,EstimatedBudget(root/'stream-budget'),httpx.MockTransport(handler))
                api.state.model_tests=ModelTests();api.state.model_stream_tests=StreamTests();api.state.model_enabled=False
                return {'fixture_only':True}
            @api.post('/fixture-only/enable-claude-test')
            async def enable_claude_fixture():
                import httpx
                from data_workspace.model_provider import MessagesProvider, ModelConfiguration
                from data_workspace.model_budget import EstimatedBudget
                from data_workspace.model_routes import ModelTests
                def handler(request):
                    if request.headers.get('Authorization')!='Bearer fixture-only-model-key' or 'x-api-key' in request.headers:
                        raise RuntimeError('fixture auth mismatch')
                    return httpx.Response(401,text='fixture-only raw auth body must not be displayed')
                api.state.model_provider=MessagesProvider(ModelConfiguration(
                    'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','claude-haiku-4-5','anthropic_messages','bearer'),
                    'fixture-only-model-key',EstimatedBudget(root/'claude-test-budget'),httpx.MockTransport(handler))
                api.state.model_tests=ModelTests()
                return {'fixture_only':True}
            @api.post('/fixture-only/enable-model-budget-test')
            async def enable_model_budget_fixture():
                import httpx
                from data_workspace.model_provider import ModelConfiguration
                from data_workspace.responses_provider import ResponsesProvider
                from data_workspace.model_budget import EstimatedBudget
                from data_workspace.model_routes import ModelTests
                def handler(request):
                    return httpx.Response(200,json={'object':'response','status':'completed',
                        'model':'fixture-model','output':[{'type':'message','role':'assistant','status':'completed',
                        'content':[{'type':'output_text','text':'isolated fixture OK'}]}],
                        'usage':{'input_tokens':10,'output_tokens':4}})
                api.state.model_provider=ResponsesProvider(ModelConfiguration(
                    'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/responses','fixture-model','openai_responses'),
                    'fixture-only-model-key',EstimatedBudget(root/'model-test-budget'),httpx.MockTransport(handler))
                api.state.model_tests=ModelTests()
                return {'fixture_only':True}
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
            # Third independent API runs the real default cadence (5s startup,
            # then600s) on dedicated marked test copies, not project runtime data.
            from datetime import timedelta
            from data_workspace.contracts import AuthContext
            from data_workspace.source_profiles import SaveProfile,ToggleProfile
            import asyncio
            auto_port=socks[2].getsockname()[1]
            automatic=create_app(Settings(mode='development',dev_identity=True,port=auto_port,retention_cleanup=True))
            from data_workspace.responses_provider import ResponsesProvider
            from data_workspace.model_provider import ModelConfiguration
            # Nonsecret candidate on an isolated real API, no key and no fee permit/network call.
            automatic.state.model_provider=ResponsesProvider(ModelConfiguration(
                'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/responses','gpt-6.1-sol[1M]','openai_responses'),'')
            auto_store=SourceStore(root/'automatic',allowed)
            auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
            clock=auto_store.clock;old=clock()-timedelta(hours=25);auto_store.clock=lambda:old
            first=auto_store.upload(auth,'expired-test.csv',b'id,created_on\n1,2025-01-01\n')
            protected=auto_store.upload(auth,'saved-test.csv',b'id,created_on\n2,2025-01-01\n')
            tested=asyncio.run(auto_store.test(auth,ProfileDraft(name='protected isolated source',file_id=protected.file_id,usage_authorized=True)))
            saved=auto_store.save(auth,SaveProfile(test_id=tested.test_id))
            auto_store.toggle(auth,saved.id,ToggleProfile(enabled=False,expected_version=saved.version))
            auto_store.clock=clock;automatic.state.sources=auto_store
            for application,sock in zip([Auth(),api,automatic],socks):
                server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',log_level='error',access_log=False))
                thread=Thread(target=lambda s=server,k=sock:s.run(sockets=[k]),daemon=True)
                servers.append(server);threads.append(thread);thread.start()
            deadline=time.monotonic()+10
            while not all(s.started for s in servers) and time.monotonic()<deadline:time.sleep(.02)
            if not all(s.started for s in servers):raise RuntimeError('fixture unavailable')
            print(json.dumps({'api_url':f'http://127.0.0.1:{port}','mcp_url':mcp_url,'secret_ref':reference,'automatic_api_url':f'http://127.0.0.1:{auto_port}'}),flush=True)
            sys.stdin.readline()
        finally:
            for server in servers:server.should_exit=True
            for thread in threads:thread.join(8)
            for sock in socks:sock.close()
            if any(t.is_alive() for t in threads):raise RuntimeError('fixture did not stop')
