"""Approved A cleanup executor, internal only until product enablement gates pass.

No scheduler/API registration here. All targets are server-selected fixed UUID
runtime objects. The default service is not touched by isolated execution tests.
"""
from contextlib import contextmanager, ExitStack
import hashlib
from itertools import islice
import json
from pathlib import Path
import sqlite3
import os
from .auth import PublicError
from .retention import (MARKER,SCHEMA,OWNER,TTL,MAX_FOLDERS,MAX_HASH_BYTES,MAX_FILE_BYTES,
                        canonical_id,root_key,timestamp,storage_lease,retention_references)
from .retention_native import PinnedObject,pin_directories
from .upload_preflight import checked_runtime_path
from .storage_inventory import read_object

AREAS=frozenset({'uploads','snapshots','staging'})
JOURNAL_SCHEMA='workspace-cleanup-v1'


def observe(stage):
    """No-op internal test seam. Never accept faults/commands from an API."""


@contextmanager
def profiles_guard(root):
    path=Path(root)/'profiles.sqlite3';db=None
    with ExitStack() as stack:
        try:
            pin_directories(stack,root,Path(root),delete_folder=False)
            if path.exists():
                # Permit SQLite I/O, but hold a no-delete handle on the verified DB
                # and its ancestors for the entire transaction; no alias replacement.
                stack.enter_context(PinnedObject(root,path,mutable=True))
                db=sqlite3.connect(path,timeout=0)
                db.execute('BEGIN IMMEDIATE')
            yield
        except PublicError:raise
        except Exception:
            raise PublicError(409,'STORAGE_REFERENCES_BUSY','保存配置正在变化或无法锁定；清理停止，请稍后核查。') from None
        finally:
            if db is not None:db.rollback();db.close()


def allowed_files(area,complete):
    if area=='snapshots':
        return {'source.duckdb','source.manifest.json'} | (set() if complete else {'source.duckdb.wal'})
    return {'source.csv','source.xlsx','source.parquet','source.duckdb','upload.receipt.json'}


def validate_artifact(root,area,id,objects,now):
    if MARKER not in objects:raise ValueError('legacy marker missing')
    marker=json.loads(objects[MARKER].read(65536).decode('utf-8'))
    kind='snapshot' if area=='snapshots' else 'upload'
    if (set(marker)!={'schema','id','root_key','kind','owner','created_at','upload_id','complete','files'}
            or marker['schema']!=SCHEMA or marker['id']!=id or marker['root_key']!=root_key(root)
            or marker['kind']!=kind or marker['owner']!=OWNER or type(marker['complete']) is not bool):
        raise ValueError('artifact provenance invalid')
    created=timestamp(marker['created_at'])
    if created>now or now-created<=TTL:raise ValueError('artifact not expired')
    if marker['upload_id'] is not None and not canonical_id(marker['upload_id']):raise ValueError('unknown upload link')
    names=set(objects)-{MARKER}
    if not names.issubset(allowed_files(area,marker['complete'])):raise ValueError('unknown descendant')
    if not marker['complete']:
        # Only never-promoted staging or failed snapshot, explicitly marked by this app.
        if area=='uploads' or marker['files']!={}:raise ValueError('incomplete upload provenance')
    else:
        if not isinstance(marker['files'],dict) or names!=set(marker['files']):raise ValueError('changed descendants')
        expected={'source.duckdb','source.manifest.json'} if area=='snapshots' else {'upload.receipt.json'}
        if area!='snapshots':
            sources=names-{'upload.receipt.json'}
            if len(sources)!=1:raise ValueError('unknown upload descendants')
            expected|=sources
        if names!=expected:raise ValueError('changed descendants')
    records={};total=0
    for name,obj in objects.items():
        total+=obj.size
        if total>MAX_HASH_BYTES:raise ValueError('artifact hash budget')
        record=obj.record();records[name]=record
        if marker['complete'] and name!=MARKER:
            saved=marker['files'][name]
            if saved!={'size':record['size'],'sha256':record['sha256']}:raise ValueError('changed artifact content')
    if marker['complete'] and area=='snapshots':
        manifest=json.loads(objects['source.manifest.json'].read(65536).decode('utf-8'))
        if manifest.get('upload_file_id')!=marker['upload_id'] or manifest.get('version')!=id:raise ValueError('conflicting upload link')
    return marker,records


def journal_path(root,id):
    parent=checked_runtime_path(root,Path(root)/'cleanup-journal');parent.mkdir(parents=True,exist_ok=True)
    path=checked_runtime_path(root,parent/(id+'.json'))
    if not path.exists() and len(list(islice(parent.iterdir(),MAX_FOLDERS+1)))>=MAX_FOLDERS:
        raise ValueError('journal capacity reached')
    return path


def persist_journal(root,record):
    path=journal_path(root,record['id']);temp=checked_runtime_path(root,path.with_suffix('.tmp'))
    # A crash may leave our same-id temp. Never remove or overwrite an ambiguous temp.
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(record,stream);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)


def validate_journal(root,area,id,record,now):
    if (set(record)!={'schema','root_key','owner','area','id','created_at','started_at','directory','files','state','deleted'}
            or record['schema']!=JOURNAL_SCHEMA or record['root_key']!=root_key(root) or record['owner']!=OWNER
            or record['area']!=area or record['id']!=id or record['state'] not in {'PLANNED','DELETING','DONE'}):
        raise ValueError('invalid cleanup journal')
    created=timestamp(record['created_at'])
    if created>now or now-created<=TTL:raise ValueError('journal creation unverifiable')
    if not isinstance(record['directory'],dict) or set(record['directory'])!={'volume','index'}:raise ValueError('directory identity missing')
    started=timestamp(record['started_at'])
    if started<created or started>now:raise ValueError('journal run time unverifiable')
    files=record['files']
    if not isinstance(files,dict) or not 1<=len(files)<=8 or MARKER not in files:raise ValueError('invalid journal files')
    if not set(files).issubset(allowed_files(area,False)|{MARKER}):raise ValueError('unknown journal path')
    total=0
    for file in files.values():
        if (not isinstance(file,dict) or set(file)!={'volume','index','size','sha256'}
                or type(file['volume']) is not int or type(file['index']) is not int
                or type(file['size']) is not int or not 0<=file['size']<=MAX_FILE_BYTES
                or not isinstance(file['sha256'],str) or len(file['sha256'])!=64):raise ValueError('invalid file identity')
        total+=file['size']
    if total>MAX_HASH_BYTES:raise ValueError('journal budget')
    if not isinstance(record['deleted'],list) or len(set(record['deleted']))!=len(record['deleted']) or not set(record['deleted']).issubset(files):raise ValueError('invalid deletion receipt')
    return record


def assert_unreferenced(store,area,id,*,_metadata=None):
    snapshots,uploads,legacy=retention_references(store,_metadata=_metadata)
    if (area=='snapshots' and id in snapshots) or (area in {'uploads','staging'} and (id in uploads or legacy)):
        raise PublicError(409,'STORAGE_REFERENCED','副本已被保存连接或有效测试引用；没有继续清理。')


def cleanup_one(store,auth,area,id):
    """Revalidate on every call/restart; never execute a stored preview. Internal only."""
    store.authorize(auth)
    if area not in AREAS or not canonical_id(id):raise PublicError(422,'CLEANUP_TARGET_INVALID','清理目标不在受控临时副本范围。')
    with store.lock,storage_lease(store.root),profiles_guard(store.root):
        return cleanup_one_locked(store,auth,area,id)


def cleanup_one_locked(store,auth,area,id,*,_budget=None,_metadata=None):
    """Internal: caller owns runtime lease and profile write guard for whole cycle."""
    if store.active or store.uploads_in_flight:raise PublicError(409,'STORAGE_BUSY','正在处理来源；没有执行清理。')
    assert_unreferenced(store,area,id,_metadata=_metadata)
    path=store.root/'cleanup-journal'/(id+'.json')
    record=None;now=store.clock()
    try:
        folder=checked_runtime_path(store.root,store.root/area/id)
        recovery_temp=None
        if path.exists():
            checked_runtime_path(store.root,path)
            if path.stat().st_nlink!=1:raise ValueError('linked journal')
            record=validate_journal(store.root,area,id,read_object(path),now)
        temp=path.with_suffix('.tmp')
        if temp.exists():
            checked_runtime_path(store.root,temp)
            if temp.stat().st_nlink!=1:raise ValueError('linked journal temp')
            proposed=validate_journal(store.root,area,id,read_object(temp),now)
            if record:
                fixed=set(record)-{'state','deleted'}
                if any(record[k]!=proposed[k] for k in fixed):raise ValueError('conflicting journal temp')
                order={'PLANNED':0,'DELETING':1,'DONE':2}
                if order[proposed['state']]<order[record['state']] or not set(record['deleted']).issubset(proposed['deleted']):raise ValueError('journal regressed')
            record=proposed;recovery_temp=temp
        if record and record['state']=='DONE':
            if folder.exists():raise ValueError('completed UUID recreated')
            if recovery_temp is not None:recovery_temp.replace(path)
            return {'state':'DONE','deleted_files':0,'already_done':True}
        if not folder.exists():
            if not record or record['state']!='DELETING':raise ValueError('no verifiable pending operation')
            if recovery_temp is not None:recovery_temp.replace(path)
            record['state']='DONE';persist_journal(store.root,record)
            return {'state':'DONE','deleted_files':0,'already_done':True}
        with ExitStack() as stack:
            directory=pin_directories(stack,store.root,folder)
            children=list(islice(folder.iterdir(),9))
            if len(children)>8:raise ValueError('descendant budget')
            objects={child.name:stack.enter_context(PinnedObject(store.root,child,delete=True)) for child in children}
            if _budget is not None:
                _budget[0]+=sum(obj.size for obj in objects.values())
                if _budget[0]>MAX_HASH_BYTES:raise PublicError(409,'CYCLE_BUDGET','周期核验字节超限，保留剩余对象。')
            if record is None:
                marker,files=validate_artifact(store.root,area,id,objects,now)
                record={'schema':JOURNAL_SCHEMA,'root_key':root_key(store.root),'owner':OWNER,'area':area,'id':id,
                        'created_at':marker['created_at'],'started_at':now.isoformat(),'directory':directory.identity,'files':files,'state':'PLANNED','deleted':[]}
                persist_journal(store.root,record)
            else:
                if directory.identity!=record['directory']:raise ValueError('directory replaced')
                if not set(objects).issubset(record['files']):raise ValueError('unexpected descendants')
                if record['state']=='PLANNED' and set(objects)!=set(record['files']):raise ValueError('planned object missing')
                if set(objects)&set(record['deleted']):raise ValueError('deleted object recreated')
                for name,obj in objects.items():
                    if obj.record()!=record['files'][name]:raise ValueError('pinned object changed')
            if recovery_temp is not None:recovery_temp.replace(path)
            observe('validated')
            assert_unreferenced(store,area,id,_metadata=_metadata)  # test seam/race must not allow a stale plan
            record['state']='DELETING';persist_journal(store.root,record);observe('deleting')
            count=0
            # Delete provenance last; outstanding handles pin all bytes and descendants.
            for name in sorted(objects,key=lambda n:n==MARKER):
                objects[name].dispose();count+=1;observe('file_deleted')
                record['deleted'].append(name);persist_journal(store.root,record)
            directory.dispose();observe('directory_deleted')
        record['state']='DONE';persist_journal(store.root,record)
        return {'state':'DONE','deleted_files':count,'already_done':False}
    except PublicError:raise
    except Exception:
        # No path/content/credential echo. Keep partial work and journal for verified retry.
        raise PublicError(409,'CLEANUP_STOPPED','清理安全核查或写入未完成，已停止；请核查后重试，原文件与已保存数据不在回收范围。') from None

def prune_expired_references(store,auth):
    """Bounded maintenance only for valid server-owned expired test references."""
    store.authorize(auth)
    with store.lock,storage_lease(store.root),profiles_guard(store.root):
        return prune_references_locked(store,auth)


def prune_references_locked(store,auth,max_removed=64):
    """Internal bounded reference maintenance; caller owns both guards."""
    if store.active or store.uploads_in_flight:raise PublicError(409,'STORAGE_BUSY','正在处理来源；未维护测试引用。')
    parent=store.root/'test-references'
    if not parent.exists():return {'removed':0,'retained':0,'unknown':0}
    checked_runtime_path(store.root,parent)
    children=list(islice(parent.iterdir(),MAX_FOLDERS+1))
    if len(children)>MAX_FOLDERS:raise PublicError(409,'STORAGE_SCAN_INCOMPLETE','测试引用超限，请由管理员核查；没有清理引用。')
    result={'removed':0,'retained':0,'unknown':0};now=store.clock()
    for path in children:
        try:
            if path.suffix!='.json' or not canonical_id(path.stem):raise ValueError('unknown reference file')
            with ExitStack() as stack:
                pin_directories(stack,store.root,parent)
                obj=stack.enter_context(PinnedObject(store.root,path,delete=True))
                ref=json.loads(obj.read(65536).decode('utf-8'))
                if (set(ref)!={'schema','id','root_key','owner','at','snapshot_id','upload_id'} or ref['schema']!=SCHEMA
                        or ref['id']!=path.stem or ref['root_key']!=root_key(store.root) or ref['owner']!=OWNER):raise ValueError('invalid reference')
                if any(v is not None and not canonical_id(v) for v in (ref['snapshot_id'],ref['upload_id'])):raise ValueError('unknown reference link')
                created=timestamp(ref['at'])
                if created>now:raise ValueError('future reference')
                if now-created<=TTL:result['retained']+=1
                elif result['removed']<max_removed:obj.dispose();result['removed']+=1
                else:result['retained']+=1
        except Exception:result['unknown']+=1
    return result
