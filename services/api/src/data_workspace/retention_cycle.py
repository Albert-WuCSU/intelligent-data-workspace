"""Bounded automatic policy A selection + existing pinned executor.

Only the fixed worker calls worker_cycle with a server-chosen runtime root.
Selection is not authorization: every target is revalidated while both guards
are held. No SQL submissions, original source reads, or recursive deletion.
"""
from itertools import islice
from pathlib import Path
import os
from .auth import PublicError
from .contracts import AuthContext
from .retention import (MARKER,SCHEMA,OWNER,TTL,MAX_FOLDERS,MAX_HASH_BYTES,canonical_id,
                        root_key,timestamp,storage_lease,retention_references)
from .retention_executor import (profiles_guard,cleanup_one_locked,prune_references_locked,
                                validate_journal)
from .storage_inventory import read_object
from .upload_preflight import checked_runtime_path

MAX_TARGETS=8
METADATA_BYTES=8*1024*1024


def execute_cycle(store,auth):
    store.authorize(auth)
    summary={'state':'SUCCEEDED','scanned':0,'reclaimed':0,'recovered':0,
             'protected':0,'unknown':0,'fresh':0,'deferred':0,'references_removed':0,
             'error_code':None}
    with store.lock,storage_lease(store.root),profiles_guard(store.root):
        if store.active or store.uploads_in_flight:raise PublicError(409,'STORAGE_BUSY','来源正在使用，周期跳过。')
        now=store.clock();metadata_bytes=[0]
        snapshots,uploads,legacy=retention_references(store,_metadata=metadata_bytes)
        candidates={}
        def read(path):
            checked_runtime_path(store.root,path)
            if path.stat().st_nlink!=1:raise ValueError('linked metadata')
            metadata_bytes[0]+=path.stat().st_size
            if metadata_bytes[0]>METADATA_BYTES:raise PublicError(409,'STORAGE_SCAN_INCOMPLETE','周期元数据核查超限，未开始回收。')
            return read_object(path)
        def children(parent):
            if not parent.exists():return []
            checked_runtime_path(store.root,parent)
            items=list(islice(parent.iterdir(),MAX_FOLDERS+1))
            if len(items)>MAX_FOLDERS:raise PublicError(409,'STORAGE_SCAN_INCOMPLETE','周期目录核查超限，未开始回收。')
            return items
        def referenced(area,id):return (id in snapshots if area=='snapshots' else id in uploads or legacy)
        # Interrupted per-object journals first, even if the directory already disappeared.
        # Stored plans never bypass reference checks, native identity, time, or content checks.
        for path in children(store.root/'cleanup-journal'):
            try:
                if path.suffix not in {'.json','.tmp'} or not canonical_id(path.stem):raise ValueError('unknown journal')
                record=read(path);area=record.get('area')
                if area not in {'uploads','snapshots','staging'}:raise ValueError('unknown area')
                validate_journal(store.root,area,path.stem,record,now)
                if record['state']=='DONE':continue
                if referenced(area,path.stem):summary['protected']+=1;continue
                candidates[(area,path.stem)]=record['created_at']
            except (ValueError,OSError,TypeError,KeyError,UnicodeError):summary['unknown']+=1
        for area in ('snapshots','uploads','staging'):
            for folder in children(store.root/area):
                summary['scanned']+=1
                try:
                    checked_runtime_path(store.root,folder)
                    if not folder.is_dir() or not canonical_id(folder.name):raise ValueError('unknown folder')
                    if referenced(area,folder.name):summary['protected']+=1;continue
                    marker=read(folder/MARKER)
                    if (set(marker)!={'schema','id','root_key','kind','owner','created_at','upload_id','complete','files'}
                            or marker['schema']!=SCHEMA or marker['owner']!=OWNER or marker['root_key']!=root_key(store.root)
                            or marker['id']!=folder.name or marker['kind']!=('snapshot' if area=='snapshots' else 'upload')
                            or type(marker['complete']) is not bool):raise ValueError('unknown provenance')
                    created=timestamp(marker['created_at'])
                    if created>now:raise ValueError('future creation')
                    if now-created<=TTL:summary['fresh']+=1;continue
                    if area=='uploads' and not marker['complete']:raise ValueError('incomplete promoted upload')
                    candidates.setdefault((area,folder.name),marker['created_at'])
                except (ValueError,OSError,TypeError,KeyError,UnicodeError):summary['unknown']+=1
        # All directory/reference coverage is checked before ANY object is reclaimed.
        # Preflight the aggregate data budget (pinned executor rechecks each file).
        selected=[];total=0
        for (area,id),created in sorted(candidates.items(),key=lambda pair:(pair[1],pair[0])):
            if len(selected)>=MAX_TARGETS:summary['deferred']+=1;continue
            folder=store.root/area/id
            try:
                if folder.exists():
                    items=list(islice(folder.iterdir(),9))
                    if len(items)>8:raise ValueError('unexpected children')
                    size=0
                    for child in items:
                        checked_runtime_path(store.root,child)
                        if not child.is_file() or child.stat().st_nlink!=1:raise ValueError('unknown child')
                        size+=child.stat().st_size
                    if total+size>MAX_HASH_BYTES:summary['deferred']+=1;continue
                    total+=size
                selected.append((area,id))
            except (ValueError,OSError):summary['unknown']+=1
        actual_budget=[0]
        for area,id in selected:
            try:
                result=cleanup_one_locked(store,auth,area,id,_budget=actual_budget,_metadata=metadata_bytes)
                if result['already_done']:summary['recovered']+=1
                else:summary['reclaimed']+=1
            except PublicError as error:
                summary['state']='PARTIAL';summary['error_code']=error.code
                # Preserve changes/receipt and stop the cycle, do not hide a partial outcome.
                break
        if summary['state']=='SUCCEEDED':
            references=prune_references_locked(store,auth)
            summary['references_removed']=references['removed']
            summary['unknown']+=references['unknown']
        if summary['deferred'] and summary['state']=='SUCCEEDED':summary['state']='PARTIAL';summary['error_code']='CYCLE_BUDGET'
        return summary


def worker_cycle(payload):
    if not isinstance(payload,dict) or set(payload)!={'root'} or not isinstance(payload['root'],str):raise ValueError('invalid retention operation')
    if os.name!='nt':raise ValueError('native retention unavailable')
    from .source_profiles import SourceStore
    root=Path(payload['root'])
    if not root.is_absolute():raise ValueError('relative cleanup root')
    checked_runtime_path(root,root)
    store=SourceStore(root=root)
    auth=AuthContext(mode='development',tenant_id='local-workspace',principal_id='local-developer')
    return execute_cycle(store,auth)
