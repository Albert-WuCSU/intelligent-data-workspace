"""Non-secret read-only retention policy, candidate and durable receipt view."""
from itertools import islice
from pathlib import Path
from typing import Literal
from .auth import PublicError
from .contracts import Contract
from .retention import (MAX_FOLDERS,canonical_id,retention_preview,storage_lease)
from .upload_preflight import checked_runtime_path


class RetentionStatus(Contract):
    policy: Literal['A_24H']='A_24H'
    automatic_cleanup: bool=False
    scan_state: Literal['COMPLETE','BLOCKED','NOT_SCANNED']='NOT_SCANNED'
    candidate_folders: int | None=None
    protected_folders: int | None=None
    completed_cleanup_folders: int=0
    pending_cleanup_folders: int=0
    unverified_receipts: int=0
    last_state: Literal['NOT_RUN','DONE','PENDING','UNKNOWN']='NOT_RUN'
    last_run_at: str | None=None
    error_code: str | None=None
    note: str='A方案已批准：测试草稿有效24小时。自动回收尚未启用；候选计数不是删除计划，原文件、已保存/禁用及归属不明副本保留。'


def retention_status(store,auth):
    from .storage_inventory import read_object
    store.authorize(auth)
    # Old/empty roots are not migrated or modified merely by viewing inventory.
    if not (store.root/'.retention.lock').is_file():return RetentionStatus()
    value=RetentionStatus()
    try:
        preview=retention_preview(store,auth)
        value.scan_state='COMPLETE'
        value.candidate_folders=sum(a['eligible'] for a in preview['areas'].values())
        value.protected_folders=sum(a['protected'] for a in preview['areas'].values())
    except PublicError as error:
        value.scan_state='BLOCKED';value.error_code=error.code
    with store.lock,storage_lease(store.root):
        parent=store.root/'cleanup-journal'
        if not parent.exists():return value
        checked_runtime_path(store.root,parent)
        children=list(islice(parent.iterdir(),MAX_FOLDERS+1))
        if len(children)>MAX_FOLDERS:
            value.scan_state='BLOCKED';value.error_code='STORAGE_SCAN_INCOMPLETE';return value
        from .retention_executor import validate_journal
        latest=None
        for path in children:
            try:
                checked_runtime_path(store.root,path)
                if path.suffix!='.json' or not canonical_id(path.stem) or path.stat().st_nlink!=1:raise ValueError('unverified receipt')
                record=read_object(path);area=record.get('area')
                if area not in {'uploads','snapshots','staging'}:raise ValueError('unknown area')
                validate_journal(store.root,area,path.stem,record,store.clock())
                if record['state']=='DONE':
                    if checked_runtime_path(store.root,store.root/area/path.stem).exists():raise ValueError('UUID recreated')
                    value.completed_cleanup_folders+=1
                else:value.pending_cleanup_folders+=1
                if latest is None or record['started_at']>latest['started_at']:latest=record
            except (ValueError,OSError,UnicodeError,TypeError,KeyError):value.unverified_receipts+=1
        if latest:
            value.last_run_at=latest['started_at'];value.last_state='DONE' if latest['state']=='DONE' else 'PENDING'
        if value.unverified_receipts:value.last_state='UNKNOWN'
        return value
