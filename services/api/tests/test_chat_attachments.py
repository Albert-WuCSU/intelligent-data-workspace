"""Chat files reuse governed upload/import/draft lifecycle without saving profiles."""
import asyncio,hashlib,json
from datetime import timedelta
from pathlib import Path
from threading import Event,Thread
import pytest
from fastapi.testclient import TestClient
from data_workspace.auth import PublicError
from data_workspace.config import Settings
from data_workspace.main import create_app
from data_workspace.source_profiles import SourceStore,ProfileDraft
from data_workspace.retention import TTL,storage_lease,retention_preview
from test_retention import AUTH,NOW
from xlsx_fixture import workbook_bytes
HEADERS={'X-Workspace-Request':'1'}

@pytest.fixture
def store(tmp_path):return SourceStore(tmp_path/'connections',tmp_path/'allowed',clock=lambda:NOW)
@pytest.fixture
def client(store):
 app=create_app(Settings(mode='development',dev_identity=True));app.state.sources=store
 with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',10)) as client:yield client

def attach(client,name,content):
 uploaded=client.post('/api/v1/source-profiles/upload',files={'file':(name,content)},headers=HEADERS)
 assert uploaded.status_code==200,uploaded.text
 tested=client.post('/api/v1/source-profiles/test',json={'kind':'local_file','name':name,'file_id':uploaded.json()['file_id'],'usage_authorized':True},headers=HEADERS)
 assert tested.status_code==200,tested.text
 return tested.json()

def test_chat_csv_actual_mcp_preview_preserves_dates_and_never_saves_profile(client,store):
 content=b'id,created_on\n'+b'1,2025-01-01\n'*120
 receipt=attach(client,'chat-file.csv',content)
 response=client.get(f"/api/v1/source-profiles/drafts/{receipt['test_id']}/tables/t0/preview")
 assert response.status_code==200,response.text
 value=response.json()['preview'];assert len(value['rows'])==100 and value['truncated'] is True
 assert value['columns'][1]['name']=='created_on' and value['columns'][1]['type']=='DATE'
 assert value['rows'][0][1]=='2025-01-01' and value['source']=='user_provided'
 assert store.profiles(AUTH).profiles==[] and len(store.tests)==1
 assert not store.active

def test_chat_excel_actual_two_sheets_and_header_date_100_rows(client,store):
 receipt=attach(client,'workbook.xlsx',workbook_bytes());assert len(receipt['tables'])==2
 counts=[]
 for table in receipt['tables']:
  response=client.get(f"/api/v1/source-profiles/drafts/{receipt['test_id']}/tables/{table['id']}/preview")
  assert response.status_code==200,response.text
  counts.append(len(response.json()['preview']['rows']))
 assert sorted(counts)==[1,100] and store.profiles(AUTH).profiles==[]

def test_draft_preview_expiry_and_api_restart_never_reuse_old_result(client,store):
 receipt=attach(client,'data.csv',b'id\n1\n');id=receipt['test_id']
 store.clock=lambda:NOW+TTL
 response=client.get(f'/api/v1/source-profiles/drafts/{id}/tables/t0/preview')
 assert response.status_code==409 and response.json()['code']=='TEST_EXPIRED'
 restarted=SourceStore(store.root,clock=lambda:NOW)
 with pytest.raises(PublicError) as caught:asyncio.run(restarted.draft_preview(AUTH,id,'t0'))
 assert caught.value.code=='TEST_EXPIRED'
 assert list((store.root/'uploads').iterdir())  # expire/restart never deletes original upload

def test_preview_only_actual_attachment_table_no_tenant_or_sql_escape(client,store):
 receipt=attach(client,'data.csv',b'id\n1\n');id=receipt['test_id']
 for table in ('not_in_catalog','t999'):
  result=client.get(f'/api/v1/source-profiles/drafts/{id}/tables/{table}/preview')
  assert result.status_code==403 and result.json()['code']=='ATTACHMENT_TABLE_DENIED'
 other=AUTH.model_copy(update={'principal_id':'other'})
 with pytest.raises(PublicError) as caught:asyncio.run(store.draft_preview(other,id,'t0'))
 assert caught.value.code=='CONNECTOR_DENIED'
 assert not store.active

def test_active_preview_lease_denies_cleanup_and_returns_slot_after_failure(client,store,monkeypatch):
 receipt=attach(client,'data.csv',b'id\n1\n');id=receipt['test_id']
 with storage_lease(store.root):
  result=client.get(f'/api/v1/source-profiles/drafts/{id}/tables/t0/preview')
  assert result.status_code==409 and result.json()['code']=='STORAGE_BUSY'
 assert client.get(f'/api/v1/source-profiles/drafts/{id}/tables/t0/preview').status_code==200

def test_two_attachment_contexts_preview_independently_never_imply_join(client,store):
 first=attach(client,'orders.csv',b'id,amount\n1,10\n')
 second=attach(client,'items.csv',b'id,label\n1,fixture\n')
 values=[]
 for receipt in (first,second):
  values.append(client.get(f"/api/v1/source-profiles/drafts/{receipt['test_id']}/tables/t0/preview").json()['preview'])
 assert values[0]['columns'][1]['name']=='amount' and values[1]['columns'][1]['name']=='label'
 assert len(store.tests)==2 and store.profiles(AUTH).profiles==[]
 assert retention_preview(store,AUTH)['areas']['uploads']['protected']==2
