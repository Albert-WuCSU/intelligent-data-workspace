"""Read-only bounded storage inventory; NEVER executes cleanup or chooses TTL.

Unreferenced != safe to delete. Missing legacy provenance/links/active writes
are reported conservatively. No filenames, source contents or secrets returned.
"""
import json
from itertools import islice
from pathlib import Path
import re
import sqlite3
from .auth import PublicError
from .contracts import Contract
from .upload_preflight import checked_runtime_path

LIMIT=2000
ID=re.compile(r'^[a-f0-9-]{36}$')

class StorageArea(Contract):
    folders: int
    bytes: int
    referenced_folders: int
    review_only_folders: int
    unknown_folders: int

class StorageSummary(Contract):
    scan_state: str
    uploads: StorageArea
    snapshots: StorageArea
    staging: StorageArea
    saved_profiles: int
    unsaved_tests: int
    automatic_cleanup: bool = False
    retention: 'RetentionStatus | None' = None
    note: str = '仅只读盘点，不执行删除。未引用不等于可安全删除，禁用连接仍保留数据；历史归属不明副本需要人工核查。'


def read_object(path):
    if not path.is_file() or path.stat().st_size>65536:raise ValueError('receipt budget')
    with path.open('rb') as stream:raw=stream.read(65537)
    if len(raw)>65536:raise ValueError('receipt budget')
    value=json.loads(raw.decode('utf-8'))
    if not isinstance(value,dict):raise ValueError('receipt shape')
    return value


from .retention_status import RetentionStatus,retention_status
StorageSummary.model_rebuild()

def storage_summary(store,auth):
    store.authorize(auth)
    with store.lock:
        if store.active or store.uploads_in_flight:
            raise PublicError(409,'STORAGE_BUSY','正在上传或读取数据，请结束后重新盘点；没有执行清理。')
        root=store.root
        try:checked_runtime_path(root,root)
        except ValueError:raise PublicError(422,'STORAGE_LOCATION_INVALID','隔离存储路径不可核查，请由管理员检查；没有读取或删除外部目录。') from None
        references=set();uploaded_refs=set();legacy=False;profiles=0
        dbpath=root/'profiles.sqlite3'
        if dbpath.exists():
            try:
                checked_runtime_path(root,dbpath)
                db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=1)
                try:
                    # References across rows are protected, including disabled connections.
                    rows=db.execute('SELECT database_path FROM profiles LIMIT 51').fetchall()
                    if len(rows)>50:raise ValueError('profile budget')
                    profiles=len(rows)
                    for (path,) in rows:
                        if not path:continue
                        saved=checked_runtime_path(root,Path(path))
                        if saved.parent.parent != root/'snapshots' or not ID.fullmatch(saved.parent.name):
                            raise ValueError('unexpected saved snapshot')
                        references.add(saved.parent.name)
                        try:
                            manifest=read_object(checked_runtime_path(root,saved.with_suffix('.manifest.json')))
                            if 'upload_file_id' not in manifest:legacy=True
                            upload=manifest.get('upload_file_id')
                            if upload is not None:
                                if not isinstance(upload,str) or not ID.fullmatch(upload):raise ValueError('invalid upload provenance')
                                uploaded_refs.add(upload)
                        except (ValueError,OSError,UnicodeError):legacy=True
                finally:db.close()
            except (ValueError,OSError,sqlite3.Error):
                raise PublicError(422,'STORAGE_REFERENCES_INVALID','保存配置与存储引用无法安全核对；请由管理员检查，不提供删除候选。') from None
        for test in store.tests.values():
            if test.get('database'):
                path=Path(test['database'])
                if path.parent.parent==root/'snapshots':references.add(path.parent.name)
            draft=test.get('draft')
            if getattr(draft,'file_id',None):uploaded_refs.add(draft.file_id)
        incomplete=False
        def area(name,protected):
            nonlocal incomplete
            parent=root/name;folders=size=referenced=review=unknown=0
            if not parent.exists():return StorageArea(folders=0,bytes=0,referenced_folders=0,review_only_folders=0,unknown_folders=0)
            try:
                checked_runtime_path(root,parent)
                for index,folder in enumerate(parent.iterdir()):
                    if index>=LIMIT:incomplete=True;break
                    folders+=1
                    try:
                        checked_runtime_path(root,folder)
                        if not folder.is_dir() or not ID.fullmatch(folder.name):raise ValueError('unknown folder')
                        children=list(islice(folder.iterdir(),9))
                        if len(children)>8:raise ValueError('folder budget')
                        folder_bytes=0
                        for child in children:
                            checked_runtime_path(root,child)
                            if not child.is_file():raise ValueError('unexpected nested folder')
                            folder_bytes+=child.stat().st_size
                        size+=folder_bytes
                        if folder.name in protected:
                            referenced+=1
                        elif name=='uploads':
                            receipt=read_object(checked_runtime_path(root,folder/'upload.receipt.json'))
                            if receipt.get('schema_version')!='1.0' or receipt.get('owner')!=store.owner(auth) or legacy:raise ValueError('unknown legacy provenance')
                            review+=1
                        else:review+=1
                    except (ValueError,OSError,UnicodeError):unknown+=1
            except (ValueError,OSError):incomplete=True
            return StorageArea(folders=folders,bytes=size,referenced_folders=referenced,review_only_folders=review,unknown_folders=unknown)
        uploads=area('uploads',uploaded_refs);snapshots=area('snapshots',references);staging=area('staging',set())
        retention=retention_status(store,auth)
        return StorageSummary(automatic_cleanup=retention.automatic_cleanup,scan_state='PARTIAL' if incomplete else 'COMPLETE',uploads=uploads,snapshots=snapshots,staging=staging,saved_profiles=profiles,unsaved_tests=len(store.tests),retention=retention)
