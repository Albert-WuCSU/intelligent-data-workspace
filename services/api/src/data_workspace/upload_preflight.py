"""Bounded upload inspection executed only inside the fixed supervised worker."""
import hashlib
from pathlib import Path
import re

MAX_BYTES=20*1024*1024
SUFFIXES=frozenset({'.duckdb','.csv','.parquet','.xlsx'})


def checked_runtime_path(root,path):
    root=Path(root);path=Path(path)
    if not root.is_absolute() or not path.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('runtime path denied')
    current=path
    while current!=current.parent:
        if current.is_symlink() or (hasattr(current,'is_junction') and current.is_junction()):
            raise ValueError('runtime link denied')
        current=current.parent
    return path.resolve()


def inspect_upload(payload):
    from .auth import PublicError
    if set(payload)!={'root','upload_id','suffix','sha256'}:raise ValueError('invalid preflight')
    if not re.fullmatch(r'[a-f0-9-]{36}',payload['upload_id']) or payload['suffix'] not in SUFFIXES or not re.fullmatch(r'[a-f0-9]{64}',payload['sha256']):raise ValueError('invalid preflight')
    root=Path(payload['root']);folder=root/'staging'/payload['upload_id']
    source=checked_runtime_path(root,folder/('source'+payload['suffix']))
    if not source.is_file() or not 0<source.stat().st_size<=MAX_BYTES:raise ValueError('file budget')
    with source.open('rb') as stream:content=stream.read(MAX_BYTES+1)
    if len(content)>MAX_BYTES or hashlib.sha256(content).hexdigest()!=payload['sha256']:raise ValueError('upload changed')
    suffix=payload['suffix']
    if suffix=='.xlsx':
        from .excel_import import validate_package
        validate_package(content)  # ZIP/XML checks never run in the HTTP event loop.
    elif suffix=='.csv':
        try:content.decode('utf-8-sig')
        except UnicodeDecodeError:raise PublicError(422,'INVALID_FILE','CSV需要UTF-8编码。') from None
    elif suffix=='.parquet':
        if not (content.startswith(b'PAR1') and content.endswith(b'PAR1')):raise PublicError(422,'INVALID_FILE','文件头与Parquet格式不一致。')
    elif suffix=='.duckdb':
        if content[8:12]!=b'DUCK':raise PublicError(422,'INVALID_FILE','文件头与DuckDB格式不一致。')
    return {'size_bytes':len(content),'sha256':payload['sha256'],'suffix':suffix}
