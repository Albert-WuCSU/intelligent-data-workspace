"""Retention safety primitives. No deletion, scheduler or cleanup execution here.

The OS byte-range lease serializes cooperating SourceStore instances/processes.
It is not a filesystem security boundary against arbitrary external writers.
"""
from contextlib import contextmanager
from functools import wraps
import inspect
from itertools import islice
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from .auth import PublicError
from .upload_preflight import checked_runtime_path

TTL = timedelta(hours=24)
MARKER = 'temporary.receipt.json'
SCHEMA = 'workspace-temporary-v1'
OWNER = 'local-workspace:local-developer'
MAX_FOLDERS = 2000
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_HASH_BYTES = 64 * 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('unverifiable time')
    return result.astimezone(timezone.utc)


def canonical_id(value):
    try:return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError,TypeError,AttributeError):return False


@contextmanager
def storage_lease(root):
    """Non-blocking lease; OS releases it on close/crash, never delete lock files."""
    if os.name != 'nt':
        raise PublicError(503, 'STORAGE_LOCK_UNAVAILABLE', '当前系统缺少已验证的存储引用锁；没有执行清理。')
    import msvcrt
    stream = None
    locked = False
    try:
        root = Path(root)
        checked_runtime_path(root, root)
        root.mkdir(parents=True, exist_ok=True)
        path = checked_runtime_path(root, root / '.retention.lock')
        stream = path.open('a+b')
        if path.stat().st_nlink != 1:
            raise OSError('linked lock')
        if path.stat().st_size == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        locked = True
    except (OSError, ValueError):
        if stream is not None: stream.close()
        raise PublicError(409, 'STORAGE_BUSY', '正在核对存储或处理连接，请稍后重试；没有执行清理。') from None
    try:
        yield
    finally:
        try:
            if locked:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            stream.close()


def root_key(root):
    return hashlib.sha256(str(Path(root).resolve()).encode('utf-8')).hexdigest()


def write_marker(root, folder, *, kind, owner, created_at, upload_id=None, complete=False):
    """Only server-selected fresh UUID folders; never retrofit legacy artifacts."""
    folder = checked_runtime_path(root, folder)
    if not canonical_id(folder.name) or kind not in {'upload', 'snapshot'}:
        raise ValueError('invalid artifact')
    if folder.parent != Path(root) / ('snapshots' if kind == 'snapshot' else 'staging'):
        raise ValueError('invalid creation area')
    timestamp(created_at)
    marker = {'schema': SCHEMA, 'id': folder.name, 'root_key': root_key(root),
              'kind': kind, 'owner': owner, 'created_at': created_at,
              'upload_id': upload_id, 'complete': complete, 'files': {}}
    if complete:
        children = list(islice(folder.iterdir(), 9))
        if len(children) > 8: raise ValueError('artifact child budget')
        for child in children:
            checked_runtime_path(root, child)
            if child.name == MARKER: continue
            if not child.is_file() or child.stat().st_nlink != 1 or child.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('unexpected artifact child')
            marker['files'][child.name] = {'size': child.stat().st_size, 'sha256': bounded_digest(child)}
    path = checked_runtime_path(root, folder / MARKER)
    temp = checked_runtime_path(root, folder / (MARKER + '.tmp'))
    with temp.open('x', encoding='utf-8') as stream:
        json.dump(marker, stream); stream.flush(); os.fsync(stream.fileno())
    temp.replace(path)


def verified_marker(root, folder, now, budget=None):
    """Fail closed for legacy, incomplete, altered, foreign or copied artifacts."""
    from .storage_inventory import read_object
    folder = checked_runtime_path(root, folder)
    if not canonical_id(folder.name) or not folder.is_dir(): raise ValueError('invalid artifact')
    path = checked_runtime_path(root, folder / MARKER)
    if path.stat().st_nlink != 1: raise ValueError('linked marker')
    marker = read_object(path)
    kind = 'snapshot' if folder.parent.name == 'snapshots' else 'upload'
    if (set(marker) != {'schema','id','root_key','kind','owner','created_at','upload_id','complete','files'}
            or marker['schema'] != SCHEMA or marker['id'] != folder.name
            or marker['root_key'] != root_key(root) or marker['kind'] != kind
            or marker['owner'] != OWNER or marker['complete'] is not True):
        raise ValueError('unverified provenance')
    created = timestamp(marker['created_at'])
    if created > now: raise ValueError('future creation')
    if marker['upload_id'] is not None and not canonical_id(marker['upload_id']): raise ValueError('invalid upload link')
    children = list(islice(folder.iterdir(), 9))
    if len(children) > 8 or {p.name for p in children} != {*marker['files'], MARKER}:
        raise ValueError('changed children')
    expected = {'source.duckdb', 'source.manifest.json'} if kind == 'snapshot' else {'upload.receipt.json'}
    if kind == 'upload':
        sources = [n for n in marker['files'] if n in {'source.csv','source.xlsx','source.parquet','source.duckdb'}]
        if len(sources) != 1: raise ValueError('invalid upload files')
        expected.add(sources[0])
    if set(marker['files']) != expected: raise ValueError('unknown files')
    for child in children:
        checked_runtime_path(root, child)
        if not child.is_file() or child.stat().st_nlink != 1: raise ValueError('linked child')
        if child.name == MARKER: continue
        record = marker['files'][child.name]
        if child.stat().st_size > MAX_FILE_BYTES or child.stat().st_size != record['size']:
            raise ValueError('changed size')
        if budget is not None:
            budget[0] += child.stat().st_size
            if budget[0] > MAX_HASH_BYTES:
                raise PublicError(422, 'STORAGE_SCAN_INCOMPLETE', '候选内容核验达到预算；没有执行删除。')
        if bounded_digest(child) != record['sha256']:
            raise ValueError('changed content')
    if kind == 'snapshot':
        manifest = read_object(folder / 'source.manifest.json')
        if manifest.get('upload_file_id') != marker['upload_id'] or manifest.get('version') != folder.name:
            raise ValueError('conflicting provenance')
    return marker, created


def retention_preview(store, auth):
    """Read-only internal safety probe. A preview is never a reusable deletion plan.

    No HTTP execution endpoint yet; fail closed if references cannot be proven.
    Only counts/categories are returned, not filenames, paths, rows or secrets.
    """
    import sqlite3
    from .storage_inventory import read_object
    store.authorize(auth)
    with store.lock, storage_lease(store.root):
        if store.active or store.uploads_in_flight:
            raise PublicError(409, 'STORAGE_BUSY', '正在处理来源，不能核查清理候选；没有删除。')
        now = store.clock()
        snapshots, uploads, legacy = retention_references(store)
        budget = [0]
        result = {'automatic_cleanup': False, 'execution': 'not_run', 'areas': {}}
        for area, refs in (('uploads', uploads), ('snapshots', snapshots), ('staging', set())):
            counts = {'eligible': 0, 'protected': 0, 'fresh': 0, 'unknown': 0}
            parent = store.root / area
            if parent.exists():
                checked_runtime_path(store.root, parent)
                for index, folder in enumerate(parent.iterdir()):
                    if index >= MAX_FOLDERS:
                        raise PublicError(422, 'STORAGE_SCAN_INCOMPLETE', '候选盘点超限；没有提供执行计划或删除。')
                    if folder.name in refs or (area == 'uploads' and legacy):
                        counts['protected'] += 1; continue
                    try:
                        _, created = verified_marker(store.root, folder, now, budget)
                        counts['eligible' if now - created > TTL else 'fresh'] += 1
                    except (ValueError, OSError, UnicodeError, TypeError, KeyError): counts['unknown'] += 1
            result['areas'][area] = counts
        return result


def storage_operation(function):
    """Hold a crash-released lease for the full operation, including async waits."""
    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def async_operation(self, auth, *args, **kwargs):
            self.authorize(auth)
            with storage_lease(self.root):
                return await function(self, auth, *args, **kwargs)
        return async_operation
    @wraps(function)
    def operation(self, auth, *args, **kwargs):
        self.authorize(auth)
        with storage_lease(self.root):
            return function(self, auth, *args, **kwargs)
    return operation


def write_test_reference(root, id, *, owner, at, snapshot_id, upload_id):
    """Non-secret reference protection survives restart; NOT persisted test drafts."""
    if not canonical_id(id) or any(v is not None and not canonical_id(v) for v in (snapshot_id,upload_id)):
        raise ValueError('invalid test reference')
    timestamp(at)
    parent = checked_runtime_path(root, Path(root) / 'test-references')
    parent.mkdir(parents=True, exist_ok=True)
    path = checked_runtime_path(root, parent / (id + '.json'))
    temp = checked_runtime_path(root, parent / (id + '.tmp'))
    value = {'schema':SCHEMA,'id':id,'root_key':root_key(root),'owner':owner,'at':at,
             'snapshot_id':snapshot_id,'upload_id':upload_id}
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)


def retention_references(store):
    """Caller owns storage lease; validate ALL persisted references, fail closed."""
    import sqlite3
    from .storage_inventory import read_object
    now = store.clock()
    snapshots, uploads = set(), set()
    legacy = False
    dbpath = store.root / 'profiles.sqlite3'
    if dbpath.exists():
        try:
            checked_runtime_path(store.root, dbpath)
            with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True, timeout=1) as db:
                db.execute('BEGIN')
                rows = db.execute('SELECT database_path FROM profiles LIMIT 51').fetchall()
                if len(rows) > 50: raise ValueError('profile budget')
                for (saved,) in rows:
                    if not saved: continue
                    path = checked_runtime_path(store.root, Path(saved))
                    if path.parent.parent != store.root / 'snapshots' or path.name != 'source.duckdb':
                        raise ValueError('invalid saved reference')
                    snapshots.add(path.parent.name)
                    try:
                        manifest = read_object(checked_runtime_path(store.root, path.with_suffix('.manifest.json')))
                        if 'upload_file_id' not in manifest: raise ValueError('legacy manifest')
                        upload = manifest['upload_file_id']
                        if upload is not None:
                            if not canonical_id(upload): raise ValueError('invalid link')
                            uploads.add(upload)
                    except (ValueError, OSError, UnicodeError): legacy = True
        except (ValueError, OSError, sqlite3.Error):
            raise PublicError(422, 'STORAGE_REFERENCES_INVALID', '引用无法安全核实；没有提供可回收候选或执行删除。') from None
    for test in store.tests.values():
        # Malformed times are not valid tests but retain their references conservatively.
        try: live = now - timestamp(test['at']) < TTL
        except (ValueError, TypeError, KeyError): live = True
        if not live: continue
        if test.get('database'): snapshots.add(Path(test['database']).parent.name)
        upload = getattr(test.get('draft'), 'file_id', None)
        if upload: uploads.add(upload)
    reference_dir = store.root / 'test-references'
    if reference_dir.exists():
        try:
            checked_runtime_path(store.root, reference_dir)
            for index, path in enumerate(reference_dir.iterdir()):
                if index >= MAX_FOLDERS: raise ValueError('reference budget')
                checked_runtime_path(store.root, path)
                if path.suffix != '.json' or not canonical_id(path.stem) or path.stat().st_nlink != 1:
                    raise ValueError('unknown reference')
                ref = read_object(path)
                if (set(ref) != {'schema','id','root_key','owner','at','snapshot_id','upload_id'}
                        or ref['schema'] != SCHEMA or ref['id'] != path.stem
                        or ref['root_key'] != root_key(store.root) or ref['owner'] != OWNER):
                    raise ValueError('invalid reference')
                created = timestamp(ref['at'])
                # Future times are unverifiable, not evidence that a reference expired.
                if created > now: raise ValueError('future reference')
                for field in ('snapshot_id','upload_id'):
                    if ref[field] is not None and not canonical_id(ref[field]): raise ValueError('invalid reference link')
                if now - created < TTL:
                    if ref['snapshot_id']: snapshots.add(ref['snapshot_id'])
                    if ref['upload_id']: uploads.add(ref['upload_id'])
        except (ValueError,OSError,UnicodeError,TypeError,KeyError):
            raise PublicError(422, 'STORAGE_REFERENCES_INVALID', '测试引用无法安全核实；没有提供可回收候选或执行删除。') from None
    return snapshots, uploads, legacy


def bounded_digest(path):
    digest = hashlib.sha256(); total = 0
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            total += len(chunk)
            if total > MAX_FILE_BYTES: raise ValueError('file hash budget')
            digest.update(chunk)
    return digest.hexdigest()
