"""Minimal OOXML bytes for parser/connector tests, not user workbook authoring."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape

def workbook_bytes(formula=False,hidden=False,external=False):
    files={
        '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml':f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="订单表" sheetId="1" r:id="rId1"/><sheet name="字典表" sheetId="2" r:id="rId2" state="{"hidden" if hidden else "visible"}"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'xl/styles.xml':'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font/></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="22"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
    }
    def text(ref,value):return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
    headers='<row r="1">'+text('A1','编号')+text('B1','created_at')+text('C1','发货日期')+text('D1','金额')+'</row>'
    rows=[]
    for i in range(120):
        n=i+2;number=f'<c r="D{n}"><v>{i}</v></c>'
        if formula and i==0:number=f'<c r="D{n}"><f>1+1</f><v>2</v></c>'
        rows.append(f'<row r="{n}">'+text(f'A{n}',f'row{i}')+f'<c r="B{n}" s="2"><v>45658.5</v></c><c r="C{n}" s="1"><v>45659</v></c>'+number+'</row>')
    root='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'
    files['xl/worksheets/sheet1.xml']=root.format(headers+''.join(rows))
    files['xl/worksheets/sheet2.xml']=root.format('<row r="1">'+text('A1','code')+text('B1','label')+'</row><row r="2">'+text('A2','a')+text('B2','Alpha')+'</row>')
    if external:files['xl/externalLinks/externalLink1.xml']='<externalLink/>'
    data=BytesIO()
    with ZipFile(data,'w',ZIP_DEFLATED) as archive:
        for name,content in files.items():archive.writestr(name,content.encode())
    return data.getvalue()
