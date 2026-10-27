import io,json
from pathlib import Path
from copy import deepcopy
from fastapi.testclient import TestClient
import pytest
from data_workspace.main import create_app
from data_workspace.config import Settings
from data_workspace.source_profiles import SourceStore
from data_workspace.contracts import AuthContext

HEADERS={'X-Workspace-Request':'1'}
CSV=('code,created_at,shipped_on,amount\n'+''.join(f'c{i},2025-01-01 12:00:00,2025-01-02,{i}\n' for i in range(120))).encode()

@pytest.fixture
def app(tmp_path):
    value=create_app(Settings(mode='development',dev_identity=True))
    value.state.sources=SourceStore(root=tmp_path/'connections',allowed_root=tmp_path/'allowed')
    return value

@pytest.fixture
def client(app):
    with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as c:yield c


def create(client,name='My source',content=CSV):
    upload=client.post('/api/v1/source-profiles/upload',files={'file':('source.csv',content,'text/csv')},headers=HEADERS)
    assert upload.status_code==200,upload.text
    draft={'kind':'local_file','name':name,'file_id':upload.json()['file_id'],'usage_authorized':True}
    test=client.post('/api/v1/source-profiles/test',json=draft,headers=HEADERS)
    assert test.status_code==200,test.text
    saved=client.post('/api/v1/source-profiles/save',json={'test_id':test.json()['test_id']},headers=HEADERS)
    assert saved.status_code==200,saved.text
    return saved.json(),draft


def test_user_onboarding_dates_preserved_preview_real_mcp_save_edit_disable(client,app):
    assert client.get('/api/v1/source-profiles').json()['profiles']==[]
    profile,draft=create(client)
    assert profile['state']=='SAVED'
    metadata=client.get(f"/api/v1/source-profiles/{profile['id']}/tables")
    assert metadata.status_code==200,metadata.text
    table=metadata.json()['tables'][0]['id']
    result=client.get(f"/api/v1/source-profiles/{profile['id']}/tables/{table}/preview")
    assert result.status_code==200,result.text
    preview=result.json()['preview']
    assert preview['returned_row_count']==100 and preview['truncated'] is True
    assert [c['name'] for c in preview['columns']]==['code','created_at','shipped_on','amount']
    assert preview['columns'][1]['type']=='TIMESTAMP' and preview['columns'][2]['type']=='DATE'
    assert preview['rows'][0][1]=='2025-01-01T12:00:00' and preview['rows'][0][2]=='2025-01-02'
    assert preview['source']=='user_provided' and preview['currency'] is None
    # Rebuild the store without losing configured profiles (not active sessions).
    app.state.sources=SourceStore(app.state.sources.root,app.state.sources.allowed_root)
    listed=client.get('/api/v1/source-profiles').json()['profiles']
    assert listed[0]['id']==profile['id']
    disabled=client.post(f"/api/v1/source-profiles/{profile['id']}/toggle",json={'enabled':False,'expected_version':1},headers=HEADERS)
    assert disabled.status_code==200
    assert client.get(f"/api/v1/source-profiles/{profile['id']}/tables").status_code==409
    assert client.get(f"/api/v1/source-profiles/{profile['id']}/tables/{table}/preview").status_code==409
    changed={**draft,'name':'Renamed source'}
    tested=client.post('/api/v1/source-profiles/test',json=changed,headers=HEADERS).json()
    conflict=client.post('/api/v1/source-profiles/save',json={'test_id':tested['test_id'],'profile_id':profile['id'],'expected_version':1},headers=HEADERS)
    assert conflict.status_code==409
    edited=client.post('/api/v1/source-profiles/save',json={'test_id':tested['test_id'],'profile_id':profile['id'],'expected_version':2},headers=HEADERS)
    assert edited.status_code==200 and edited.json()['name']=='Renamed source' and edited.json()['version']==3


def test_config_import_only_checks_nonsecret_draft_not_connection(client):
    value={'schema_version':'1.0','profile':{'kind':'local_file','name':'Imported','path':'data/my-source.csv','usage_authorized':True}}
    response=client.post('/api/v1/source-profiles/import-config',files={'file':('connection.json',json.dumps(value).encode(),'application/json')},headers=HEADERS)
    assert response.status_code==200 and response.json()['name']=='Imported'
    assert client.get('/api/v1/source-profiles').json()['profiles']==[]
    for mutation in [{'password':'sentinel-private'},{'command':'powershell'},{'env':{'token':'sentinel-private'}},{'tenant_id':'other'}]:
        invalid=deepcopy(value);invalid['profile'].update(mutation)
        response=client.post('/api/v1/source-profiles/import-config',files={'file':('connection.json',json.dumps(invalid).encode(),'application/json')},headers=HEADERS)
        assert response.status_code==422 and 'sentinel-private' not in response.text


def test_source_refuses_path_escape_and_unsupported_file(client,app,tmp_path):
    outside=tmp_path/'secret.csv';outside.write_bytes(CSV)
    request={'kind':'local_file','name':'Unsafe','path':str(outside),'usage_authorized':True}
    result=client.post('/api/v1/source-profiles/test',json=request,headers=HEADERS)
    assert result.status_code==422 and 'secret.csv' not in result.text
    for filename,content in [('script.exe',b'x'),('fake.parquet',b'bad'),('fake.duckdb',b'bad'),('text.csv',b'\xff')]:
        response=client.post('/api/v1/source-profiles/upload',files={'file':(filename,content)},headers=HEADERS)
        assert response.status_code==422
    assert client.post('/api/v1/source-profiles/upload',files={'file':('x.csv',CSV)}).status_code==403


def test_source_identity_ownership_denied(app,client):
    old=app.state.identity_provider
    class Other:
        def resolve(self,request):return AuthContext(principal_id='other',tenant_id='local-workspace',mode='development')
    app.state.identity_provider=Other()
    try:
        assert client.get('/api/v1/source-profiles').status_code==403
        assert client.post('/api/v1/source-profiles/upload',files={'file':('x.csv',CSV)},headers=HEADERS).status_code==403
    finally:app.state.identity_provider=old


def test_no_time_data_and_empty_data_still_have_headers(client):
    for content,expected in [(b'code,label\na,Alpha\n',1),(b'code,label\n',0)]:
        profile,_=create(client,content=content)
        table=client.get(f"/api/v1/source-profiles/{profile['id']}/tables").json()['tables'][0]['id']
        response=client.get(f"/api/v1/source-profiles/{profile['id']}/tables/{table}/preview")
        assert response.status_code==200,response.text
        value=response.json()['preview']
        assert value['returned_row_count']==expected and len(value['columns'])==2


def test_duckdb_upload_preserves_original_dates_and_nonanalytics_schema(client,tmp_path):
    import duckdb
    db=tmp_path/'input.duckdb'
    with duckdb.connect(str(db)) as con:
        con.execute('CREATE TABLE main.orders(id INTEGER, registered_on DATE, posted_at TIMESTAMP)')
        con.execute("INSERT INTO main.orders VALUES (1, '2020-01-01','2025-05-06 12:00:00')")
    content=db.read_bytes()
    upload=client.post('/api/v1/source-profiles/upload',files={'file':('input.duckdb',content)},headers=HEADERS)
    assert upload.status_code==200,upload.text
    test=client.post('/api/v1/source-profiles/test',json={'name':'Database','file_id':upload.json()['file_id'],'usage_authorized':True},headers=HEADERS)
    assert test.status_code==200,test.text
    profile=client.post('/api/v1/source-profiles/save',json={'test_id':test.json()['test_id']},headers=HEADERS).json()
    tables=client.get(f"/api/v1/source-profiles/{profile['id']}/tables").json()['tables']
    assert tables[0]['name']=='main.orders'
    result=client.get(f"/api/v1/source-profiles/{profile['id']}/tables/t0/preview").json()['preview']
    assert result['rows']==[[1,'2020-01-01','2025-05-06T12:00:00']]
    assert db.read_bytes()==content

def test_upload_body_budget_rejects_before_parser(client):
    response=client.post('/api/v1/source-profiles/upload',content=b'',headers={**HEADERS,'Content-Length':str(22*1024*1024),'Content-Type':'multipart/form-data; boundary=x'})
    assert response.status_code==413


def test_local_path_and_parquet_real_connection(client,app,tmp_path):
    import duckdb
    allowed=tmp_path/'allowed';allowed.mkdir()
    target=allowed/'original.parquet'
    with duckdb.connect() as con:
        con.execute("COPY (SELECT 1 AS id, DATE '2024-01-01' AS effective_date) TO ? (FORMAT PARQUET)",[str(target)])
    tested=client.post('/api/v1/source-profiles/test',json={'name':'Path file','path':str(target),'usage_authorized':True},headers=HEADERS)
    assert tested.status_code==200,tested.text
    saved=client.post('/api/v1/source-profiles/save',json={'test_id':tested.json()['test_id']},headers=HEADERS).json()
    preview=client.get(f"/api/v1/source-profiles/{saved['id']}/tables/t0/preview").json()['preview']
    assert preview['rows']==[[1,'2024-01-01']]
    assert preview['columns'][1]['name']=='effective_date'
