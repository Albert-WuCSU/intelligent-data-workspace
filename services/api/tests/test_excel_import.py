import json
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pytest
from xlsx_fixture import workbook_bytes
from test_source_profiles import app,client,HEADERS
from data_workspace.excel_import import validate_package,ExcelImportError


def test_xlsx_real_upload_mcp_multisheet_date_headers_100_rows(client):
    content=workbook_bytes()
    uploaded=client.post('/api/v1/source-profiles/upload',files={'file':('数据.xlsx',content)},headers=HEADERS)
    assert uploaded.status_code==200,uploaded.text
    tested=client.post('/api/v1/source-profiles/test',json={'name':'Excel数据','file_id':uploaded.json()['file_id'],'usage_authorized':True},headers=HEADERS)
    assert tested.status_code==200,tested.text
    assert len(tested.json()['tables'])==2
    saved=client.post('/api/v1/source-profiles/save',json={'test_id':tested.json()['test_id']},headers=HEADERS).json()
    metadata=client.get(f"/api/v1/source-profiles/{saved['id']}/tables").json()
    assert [t['name'] for t in metadata['tables']]==['workbook.订单表','workbook.字典表']
    preview=client.get(f"/api/v1/source-profiles/{saved['id']}/tables/t0/preview").json()['preview']
    assert preview['returned_row_count']==100 and preview['truncated'] is True
    assert [c['name'] for c in preview['columns']]==['编号','created_at','发货日期','金额']
    assert preview['columns'][1]['type']=='TIMESTAMP'
    assert preview['rows'][0]==['row0','2025-01-01T12:00:00','2025-01-02T00:00:00',0]
    dictionary=client.get(f"/api/v1/source-profiles/{saved['id']}/tables/t1/preview").json()['preview']
    assert dictionary['rows']==[['a','Alpha']]


@pytest.mark.parametrize('kwargs,message',[({'formula':True},'公式'),({'hidden':True},'隐藏')])
def test_xlsx_unsupported_semantics_have_actionable_error(client,kwargs,message):
    uploaded=client.post('/api/v1/source-profiles/upload',files={'file':('data.xlsx',workbook_bytes(**kwargs))},headers=HEADERS).json()
    response=client.post('/api/v1/source-profiles/test',json={'name':'Test','file_id':uploaded['file_id'],'usage_authorized':True},headers=HEADERS)
    assert response.status_code==422 and response.json()['code']=='INVALID_XLSX' and message in response.json()['safe_message']
    assert client.get('/api/v1/source-profiles').json()['profiles']==[]


def test_xlsx_invalid_external_and_bomb_rejected_before_parser(client):
    for content in [b'not-xlsx',workbook_bytes(external=True)]:
        response=client.post('/api/v1/source-profiles/upload',files={'file':('data.xlsx',content)},headers=HEADERS)
        assert response.status_code==422 and response.json()['code']=='INVALID_XLSX'
    buf=BytesIO()
    with ZipFile(buf,'w',ZIP_DEFLATED) as archive:archive.writestr('xl/bomb.xml',b'x'*(33*1024*1024))
    with pytest.raises(ExcelImportError):validate_package(buf.getvalue())


def test_xlsx_entity_and_path_rejection():
    for name,value in [('../outside.xml',b'x'),('xl/book.xml',b'<!DOCTYPE x [<!ENTITY a "b">]>')]:
        buf=BytesIO()
        with ZipFile(buf,'w') as archive:archive.writestr(name,value)
        with pytest.raises(ExcelImportError):validate_package(buf.getvalue())
