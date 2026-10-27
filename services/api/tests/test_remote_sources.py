import asyncio,json,socket,time,sys,sqlite3
from threading import Thread
from datetime import date,datetime
from decimal import Decimal
import pytest
import uvicorn
from fastapi.testclient import TestClient
from pydantic import ValidationError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.auth import PublicError
from data_workspace.remote_access import RemoteAccessPolicy,HTTPGrant,PostgresGrant,HTTPMCPDraft,PostgresDraft,ProductSecrets,SECRET_PREFIX
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.remote_sources import preview_result,catalog,postgres_navigation
from data_workspace.warehouse.postgres_worker import navigate,table_id

HEADERS={'X-Workspace-Request':'1'}
TOKEN='test-only-credential-sentinel-never-real'

@pytest.fixture
def http_fixture(tmp_path):
    from data_workspace.warehouse.mcp_server import create_server
    allowed=tmp_path/'allowed';allowed.mkdir();source=allowed/'data.csv'
    source.write_text('id,created_at,shipped_on\n'+''.join(f'{i},2025-01-01 12:00:00,2025-01-02\n' for i in range(120)),encoding='utf-8')
    store=SourceStore(tmp_path/'snapshot',allowed)
    database,_=store.snapshot(ProfileDraft(name='fixture',path=str(source),usage_authorized=True))
    app=create_server(tmp_path,database).streamable_http_app()
    requests=[]
    class Authenticated:
        async def __call__(self,scope,receive,send):
            if scope['type']=='http':
                headers=dict(scope['headers'])
                requests.append(scope['path'])
                if headers.get(b'authorization') != ('Bearer '+TOKEN).encode():
                    await send({'type':'http.response.start','status':403,'headers':[]})
                    await send({'type':'http.response.body','body':b'denied'})
                    return
            await app(scope,receive,send)
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    url=f'http://127.0.0.1:{sock.getsockname()[1]}/mcp'
    server=uvicorn.Server(uvicorn.Config(Authenticated(),host='127.0.0.1',log_level='error',access_log=False))
    thread=Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        until=time.monotonic()+8
        while not server.started and thread.is_alive() and time.monotonic()<until:time.sleep(.02)
        assert server.started
        yield url,requests
    finally:
        server.should_exit=True;thread.join(8);sock.close();assert not thread.is_alive()


def draft(url):return {'kind':'http_mcp','name':'Authenticated fixture','url':url,'auth_mode':'bearer','secret_ref':'HTTP_TEST','usage_authorized':True}

def application(tmp_path,url,table_ids=['t0']):
    app=create_app(Settings(mode='development',dev_identity=True))
    app.state.sources=SourceStore(tmp_path/'profiles',tmp_path/'allowed',RemoteAccessPolicy(http_mcp=[HTTPGrant(url=url,secret_ref='HTTP_TEST',table_ids=table_ids)]))
    return app


def test_real_authenticated_http_import_test_save_reload_preview_disable_and_no_secret_leak(tmp_path,http_fixture,monkeypatch,caplog):
    url,requests=http_fixture;monkeypatch.setenv(SECRET_PREFIX+'HTTP_TEST',TOKEN)
    app=application(tmp_path,url)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        body=draft(url)
        imported=client.post('/api/v1/source-profiles/import-config',files={'file':('config.json',json.dumps({'schema_version':'1.0','profile':body}))},headers=HEADERS)
        assert imported.status_code==200 and not requests
        tested=client.post('/api/v1/source-profiles/test',json=body,headers=HEADERS)
        assert tested.status_code==200,tested.text
        assert len(tested.json()['tables'])==1
        saved=client.post('/api/v1/source-profiles/save',json={'test_id':tested.json()['test_id']},headers=HEADERS)
        assert saved.status_code==200,saved.text
        profile=saved.json();id=profile['id'];assert profile['kind']=='http_mcp' and profile['connection']['secret_ref']=='HTTP_TEST'
        assert TOKEN not in str(saved.json())+str(tested.json())
        # Restart the store; policy is server-owned and connection re-authenticates.
        app.state.sources=SourceStore(app.state.sources.root,app.state.sources.allowed_root,app.state.sources.remote_policy)
        tables=client.get(f'/api/v1/source-profiles/{id}/tables');assert tables.status_code==200,tables.text
        result=client.get(f'/api/v1/source-profiles/{id}/tables/t0/preview');assert result.status_code==200,result.text
        preview=result.json()['preview'];assert preview['returned_row_count']==100 and preview['truncated']
        assert [c['name'] for c in preview['columns']]==['id','created_at','shipped_on']
        assert preview['rows'][0][1:]==['2025-01-01T12:00:00','2025-01-02']
        assert preview['source']=='external_mcp' and preview['currency'] is None
        assert client.get(f'/api/v1/source-profiles/{id}/tables/not_allowed/preview').status_code==403
        disabled=client.post(f'/api/v1/source-profiles/{id}/toggle',json={'enabled':False,'expected_version':1},headers=HEADERS);assert disabled.status_code==200
        count=len(requests);assert client.get(f'/api/v1/source-profiles/{id}/tables').status_code==409 and len(requests)==count
        monkeypatch.delenv(SECRET_PREFIX+'HTTP_TEST')
        client.post(f'/api/v1/source-profiles/{id}/toggle',json={'enabled':True,'expected_version':2},headers=HEADERS)
        missing=client.get(f'/api/v1/source-profiles/{id}/tables');assert missing.status_code==409 and missing.json()['code']=='CREDENTIAL_NOT_CONFIGURED'
        assert len(requests)==count and TOKEN not in missing.text+caplog.text
    assert TOKEN.encode() not in (app.state.sources.root/'profiles.sqlite3').read_bytes()


def test_missing_and_unapproved_credentials_never_make_http_request(tmp_path,http_fixture,monkeypatch):
    url,requests=http_fixture;app=application(tmp_path,url)
    monkeypatch.delenv(SECRET_PREFIX+'HTTP_TEST',raising=False)
    monkeypatch.setenv('HOST_TOOL_TOKEN',TOKEN)
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        missing=client.post('/api/v1/source-profiles/test',json=draft(url),headers=HEADERS)
        assert missing.status_code==409 and not requests and TOKEN not in missing.text
        unapproved={**draft(url),'secret_ref':'HOST_TOOL_TOKEN'}
        denied=client.post('/api/v1/source-profiles/test',json=unapproved,headers=HEADERS)
        assert denied.status_code==403 and not requests
        for key in ['password','token','headers','command','env','tenant_id']:
            invalid=client.post('/api/v1/source-profiles/test',json={**draft(url),key:TOKEN},headers=HEADERS)
            assert invalid.status_code==422 and TOKEN not in invalid.text and not requests


def test_http_denied_credentials_are_safe_and_input_can_be_retested(tmp_path,http_fixture,monkeypatch,caplog):
    url,requests=http_fixture;app=application(tmp_path,url)
    monkeypatch.setenv(SECRET_PREFIX+'HTTP_TEST','invalid-test-value')
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:
        denied=client.post('/api/v1/source-profiles/test',json=draft(url),headers=HEADERS)
        assert denied.status_code in {403,422} and 'invalid-test-value' not in denied.text+caplog.text
        assert client.get('/api/v1/source-profiles').json()['profiles']==[]
        monkeypatch.setenv(SECRET_PREFIX+'HTTP_TEST',TOKEN)
        good=client.post('/api/v1/source-profiles/test',json=draft(url),headers=HEADERS)
        assert good.status_code==200,good.text


def test_schema_migration_preserves_old_local_profiles(tmp_path):
    root=tmp_path/'profiles';root.mkdir()
    db=sqlite3.connect(root/'profiles.sqlite3')
    db.execute('CREATE TABLE profiles (id TEXT PRIMARY KEY,owner TEXT,name TEXT,version INTEGER,enabled INTEGER,database_path TEXT,source_label TEXT,last_test_at TEXT)')
    db.execute("INSERT INTO profiles VALUES ('old','local-workspace:local-developer','Original',1,1,'snapshot','original','now')");db.commit();db.close()
    from data_workspace.contracts import AuthContext
    auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
    profile=SourceStore(root).profiles(auth).profiles[0]
    assert profile.id=='old' and profile.kind=='local_file' and profile.connection is None


def test_frontend_and_pg_subprocess_do_not_inherit_host_or_product_secrets(tmp_path,monkeypatch):
    sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[3]/'scripts'))
    from dev import frontend_environment,backend_environment
    env={'PATH':'node-path','SYSTEMROOT':'windows','WORKSPACE_CONNECTOR_POLICY':'{}','WORKSPACE_CONNECTOR_SECRET_TEST':TOKEN,'HOST_TOOL_TOKEN':TOKEN,'AWS_SECRET_ACCESS_KEY':TOKEN,'VITE_SECRET':TOKEN}
    front=frontend_environment(env);assert TOKEN not in str(front)
    back=backend_environment(env);assert back['WORKSPACE_CONNECTOR_SECRET_TEST']==TOKEN and 'AWS_SECRET_ACCESS_KEY' not in back and 'HOST_TOOL_TOKEN' not in back
    def fake_run(operation,payload,**kwargs):
        from data_workspace.worker_runtime import worker_environment
        assert TOKEN not in str(worker_environment())
        assert operation=='postgres_navigation' and payload['password']==TOKEN
        assert kwargs['limits'].wall_seconds==12 and kwargs['limits'].cpu_seconds==8
        return {'ok':True,'data':{'tables':[]}}
    monkeypatch.setattr('data_workspace.worker_runtime.run_worker',fake_run);monkeypatch.setenv(SECRET_PREFIX+'PG_TEST',TOKEN)
    d=PostgresDraft(kind='postgresql',name='PG',host='127.0.0.1',database='test',username='reader',sslmode='disable',secret_ref='PG_TEST',usage_authorized=True)
    policy=RemoteAccessPolicy(postgresql=[PostgresGrant(host=d.host,port=d.port,database=d.database,username=d.username,secret_ref='PG_TEST',schemas=['public'])])
    assert asyncio.run(postgres_navigation(d,policy,'tables'))=={'tables':[]}


def test_pg_fixed_readonly_sql_quotes_identifiers_preserves_dates_and_caps_rows():
    statements=[];kwargs={}
    class Cursor:
        def __init__(self,data):self.data=data
        def fetchall(self):return self.data
        def fetchmany(self,n):assert n==101;return self.data[:n]
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def execute(self,query,params=None):
            text=query.as_string() if hasattr(query,'as_string') else query
            statements.append((text,params))
            if 'has_table_privilege' in text:return Cursor([('public','odd"table')])
            if 'format_type' in text:return Cursor([('id','integer'),('created_at','timestamp without time zone'),('shipped_on','date'),('amount','numeric')])
            if text.startswith('SELECT *'):return Cursor([[i,datetime(2025,1,1,12),date(2025,1,2),Decimal('1.23')] for i in range(120)])
            return Cursor([])
    def connect(**values):kwargs.update(values);return Connection()
    payload={'draft':{'kind':'postgresql','name':'PG','host':'127.0.0.1','database':'fixture','username':'reader','sslmode':'disable','secret_ref':'PG_TEST','usage_authorized':True},'schemas':['public'],'password':TOKEN,'operation':'preview','table':table_id('public','odd"table')}
    data=navigate(payload,connect)
    assert data['returned_row_count']==100 and data['truncated'] and len(data['columns'])==4
    assert data['rows'][0][1:]==['2025-01-01T12:00:00','2025-01-02','1.23']
    assert 'BEGIN READ ONLY' in [s for s,p in statements]
    query=[s for s,p in statements if s.startswith('SELECT *')][0]
    assert query=='SELECT * FROM "public"."odd""table" LIMIT 101' and 'WHERE' not in query
    assert kwargs['hostaddr']=='127.0.0.1' and kwargs['password']==TOKEN and kwargs['passfile']==__import__('os').devnull


@pytest.mark.parametrize('mutation',[{'rows':[[{'arbitrary':'object'}]]},{'rows':[[float('nan')]]},{'returned_row_count':99},{'columns':[]},{'truncated':'yes'}])
def test_untrusted_preview_rejects_inconsistent_or_oversized_results(mutation):
    value={'columns':[{'name':'id','type':'INTEGER'}],'rows':[[1]],'returned_row_count':1,'truncated':False,**mutation}
    with pytest.raises(PublicError):preview_result({'ok':True,'result':value})
