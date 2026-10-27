"""Bounded, non-executing .xlsx reader for local table navigation."""
from datetime import date,datetime,time
from io import BytesIO
from pathlib import PurePosixPath
import math
import re
from zipfile import ZipFile,BadZipFile

class ExcelImportError(ValueError):
    pass


def validate_package(content):
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries=archive.infolist()
            if len(entries)>2000 or len({i.filename for i in entries})!=len(entries):raise ExcelImportError('Excel文件条目过多或重复。')
            total=0
            for item in entries:
                path=PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in item.filename or item.flag_bits&1:raise ExcelImportError('拒绝加密或异常路径的Excel文件。')
                total+=item.file_size
                if item.file_size>32*1024*1024 or total>64*1024*1024 or (item.file_size>1024*1024 and item.file_size/max(item.compress_size,1)>200):raise ExcelImportError('Excel解压大小超过限制，请缩小工作簿。')
                name=item.filename.lower()
                if 'vbaproject' in name or name.startswith('xl/externallinks/') or name.startswith('xl/embeddings/'):raise ExcelImportError('不接收宏、外部工作簿链接或嵌入对象。')
                if name.endswith(('.xml','.rels')):
                    data=archive.read(item)
                    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ExcelImportError('拒绝XML实体声明。')
            required={'[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels'}
            if not required<={i.filename for i in entries}:raise ExcelImportError('文件内容不是有效.xlsx工作簿。')
    except (BadZipFile,KeyError,RuntimeError) as exc:raise ExcelImportError('文件不是有效.xlsx或已经损坏。') from None


def cell_value(cell):
    if cell.data_type=='f':raise ExcelImportError('检测到公式。当前不计算公式，请在副本中将公式粘贴为值后导入；原文件不会修改。')
    if cell.data_type=='e':raise ExcelImportError('检测到Excel错误值，请修正后重新导入。')
    value=cell.value
    if isinstance(value,str) and len(value)>10000:raise ExcelImportError('单元格文本超过10000字符。')
    if isinstance(value,float) and not math.isfinite(value):raise ExcelImportError('非有限数值不支持。')
    if isinstance(value,time):return value.isoformat()
    return value


def kind(values):
    nonempty=[v for v in values if v is not None]
    if not nonempty:return 'VARCHAR'
    if all(isinstance(v,bool) for v in nonempty):return 'BOOLEAN'
    if all(isinstance(v,datetime) for v in nonempty):return 'TIMESTAMP'
    if all(isinstance(v,date) and not isinstance(v,datetime) for v in nonempty):return 'DATE'
    if all(isinstance(v,int) and not isinstance(v,bool) and -(2**63)<=v<2**63 for v in nonempty):return 'BIGINT'
    if all(isinstance(v,(int,float)) and not isinstance(v,bool) and abs(v)<1e308 for v in nonempty):return 'DOUBLE'
    return 'VARCHAR'


def import_workbook(content,con):
    validate_package(content)
    from openpyxl import load_workbook
    workbook=load_workbook(BytesIO(content),read_only=True,data_only=False,keep_links=False)
    quote=lambda value:'"'+value.replace('"','""')+'"'
    tables={}
    try:
        if len(workbook.worksheets)>50:raise ExcelImportError('最多支持50个工作表。')
        for sheet in workbook.worksheets:
            if sheet.sheet_state!='visible':raise ExcelImportError('含隐藏工作表，请在副本中明确移除或取消隐藏后导入。')
            # Avoid trusting forged dimension metadata; iteration limits below
            # bound actual rows/cells including sparse cells and blank gaps.
            sheet.reset_dimensions()
            rows=[];header=None;width=0;cells=0
            for index,row in enumerate(sheet.iter_rows()):
                if index>20000:raise ExcelImportError('单工作表最多20000条数据行，请拆分工作簿。')
                if len(row)>100:raise ExcelImportError('工作表最多100列。')
                cells+=len(row)
                if cells>500000:raise ExcelImportError('工作表单元格数量超过限制。')
                values=[cell_value(c) for c in row]
                if index==0:
                    while values and values[-1] is None:values.pop()
                    if not values:continue
                    header=[];used=set();width=len(values)
                    for i,value in enumerate(values):
                        name=str(value).strip() if value is not None else f'Column_{i+1}'
                        if not name:name=f'Column_{i+1}'
                        if len(name)>160:raise ExcelImportError('表头超过160字符。')
                        base=name;n=2
                        while name.casefold() in used:name=f'{base}_{n}';n+=1
                        used.add(name.casefold());header.append(name)
                    continue
                if header is None:
                    if any(v is not None for v in values):raise ExcelImportError('第一行需要是列标题，请整理为表格后导入。')
                    continue
                if len(values)>width and any(v is not None for v in values[width:]):raise ExcelImportError('存在没有表头的数据列，请补齐第一行标题。')
                rows.append((values+[None]*width)[:width])
            if header is None:continue
            # No data predicate is applied. Only worksheet trailing blank rows
            # outside the populated table are excluded, preserving inner blanks.
            while rows and all(v is None for v in rows[-1]):rows.pop()
            types=[kind([row[i] for row in rows]) for i in range(width)]
            table=sheet.title
            con.execute('CREATE SCHEMA IF NOT EXISTS workbook')
            con.execute('CREATE TABLE workbook.'+quote(table)+' ('+','.join(quote(n)+' '+t for n,t in zip(header,types))+')')
            converted=[[str(v) if v is not None and types[i]=='VARCHAR' else v for i,v in enumerate(row)] for row in rows]
            for offset in range(0,len(converted),100):
                batch=converted[offset:offset+100];placeholders='('+','.join('?' for _ in header)+')'
                con.execute('INSERT INTO workbook.'+quote(table)+' VALUES '+','.join(placeholders for _ in batch),[v for row in batch for v in row])
            tables[f't{len(tables)}']={'schema':'workbook','name':table,'columns':[{'name':n,'type':t,'nullable':True} for n,t in zip(header,types)]}
        if not tables:raise ExcelImportError('工作簿没有包含第一行表头的非空工作表。')
        return tables
    finally:workbook.close()
