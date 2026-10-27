"""Local source profiles and import snapshots. Never persist passwords or commands."""
from datetime import datetime,timezone
from .retention import storage_operation, write_marker, write_test_reference, utc_now, timestamp, TTL
from contextlib import contextmanager
import json
import hashlib
from pathlib import Path
import re
import sqlite3
from threading import RLock,Timer
from uuid import uuid4
from typing import Literal
from pydantic import Field
from .contracts import Contract
from .auth import PublicError
from .remote_access import HTTPMCPDraft, PostgresDraft, RemoteAccessPolicy

ROOT=Path(__file__).resolve().parents[4]
MAX_BYTES=20*1024*1024

class ProfileDraft(Contract):
    name: str = Field(min_length=1,max_length=80)
    kind: Literal['local_file'] = 'local_file'
    file_id: str | None = Field(default=None,pattern=r'^[a-f0-9-]{36}$')
    path: str | None = Field(default=None,max_length=500)
    usage_authorized: Literal[True]

# Each variant has a strict Literal kind and forbids extra fields. Plain union
# preserves the accepted omitted-kind local default and valid OpenAPI mappings.
SourceDraft = ProfileDraft | HTTPMCPDraft | PostgresDraft

class Profile(Contract):
    id: str
    name: str
    kind: Literal['local_file','http_mcp','postgresql']='local_file'
    connection: HTTPMCPDraft | PostgresDraft | None = None
    version: int
    enabled: bool
    state: Literal['SAVED','CONNECTED','DISABLED','NEEDS_RETEST']
    source_label: str
    last_test_at: str | None

class ProfileList(Contract):
    profiles: list[Profile]
    note: str = '本机服务器保存连接配置；日期字段原样展示，连接器没有时间筛选。'

class TestedDraft(Contract):
    expires_at: str | None = None
    test_id: str
    name: str
    source_label: str
    tables: list[dict]
    note: str = '真实MCP连接测试通过，尚未保存；点击保存后可复用。'

class SaveProfile(Contract):
    test_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    profile_id: str | None = Field(default=None,pattern=r'^[a-f0-9-]{36}$')
    expected_version: int | None = None

class ToggleProfile(Contract):
    enabled: bool
    expected_version: int

class ConfigImport(Contract):
    schema_version: Literal['1.0']
    profile: SourceDraft

class FileReceipt(Contract):
    file_id: str
    source_label: str
    note: str = '文件已复制到本机后端隔离目录；不是原地修改。请测试连接后保存。'

class NavigationPreview(Contract):
    profile_id: str
    table_id: str
    preview: dict

class SourceStore:
    def __init__(self,root=None,allowed_root=None,remote_policy=None,clock=None):
        self.root=Path(root or ROOT/'data/connections').resolve()
        self.allowed_root=Path(allowed_root or ROOT/'data').resolve()
        self.remote_policy=remote_policy or RemoteAccessPolicy()
        self.clock=clock or utc_now
        self.lock=RLock();self.tests={};self.active=False;self.needs_retest=set();self.uploads_in_flight=set()

    def authorize(self,auth):
        if (auth.mode,auth.tenant_id,auth.principal_id)!=('development','local-workspace','local-developer'):
            raise PublicError(403,'CONNECTOR_DENIED','配置数据源仅开放给当前本机开发身份。')

    @contextmanager
    def db(self):
        self.root.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.root/'profiles.sqlite3')
        db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, version INTEGER NOT NULL, enabled INTEGER NOT NULL, database_path TEXT NOT NULL, source_label TEXT NOT NULL, last_test_at TEXT NOT NULL)')
        columns={r[1] for r in db.execute('PRAGMA table_info(profiles)')}
        if 'kind' not in columns:db.execute("ALTER TABLE profiles ADD COLUMN kind TEXT NOT NULL DEFAULT 'local_file'")
        if 'config_json' not in columns:db.execute("ALTER TABLE profiles ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'")
        try:
            with db:yield db
        finally:db.close()

    def owner(self,auth):return auth.tenant_id+':'+auth.principal_id

    def profiles(self,auth):
        self.authorize(auth)
        with self.lock,self.db() as db:
            rows=db.execute('SELECT * FROM profiles WHERE owner=? ORDER BY name',[self.owner(auth)]).fetchall()
        return ProfileList(profiles=[self.public(row) for row in rows])

    def public(self,row,state=None):
        connection=None
        if row['kind']!='local_file':
            cls=HTTPMCPDraft if row['kind']=='http_mcp' else PostgresDraft
            connection=cls.model_validate_json(row['config_json'])
        return Profile(kind=row['kind'],connection=connection,id=row['id'],name=row['name'],version=row['version'],enabled=bool(row['enabled']),state=state or ('DISABLED' if not row['enabled'] else 'NEEDS_RETEST' if row['id'] in self.needs_retest else 'SAVED'),source_label=row['source_label'],last_test_at=row['last_test_at'])

    def get(self,auth,id):
        self.authorize(auth)
        with self.lock,self.db() as db:row=db.execute('SELECT * FROM profiles WHERE id=? AND owner=?',[id,self.owner(auth)]).fetchone()
        if row is None:raise PublicError(404,'SOURCE_NOT_FOUND','数据源不存在或不可访问。')
        return row

    def checked_path(self,value):
        path=Path(value).expanduser()
        if not path.is_absolute():path=ROOT/path
        resolved=path.resolve(strict=True)
        if not resolved.is_relative_to(self.allowed_root) or resolved.is_relative_to(self.root):
            raise ValueError('path outside permitted data directory')
        # Reject link/junction components, not just the final pathname.
        current=path.absolute()
        while current!=current.parent:
            if current.is_symlink() or (hasattr(current,'is_junction') and current.is_junction()):raise ValueError('link path denied')
            current=current.parent
        if resolved.suffix.lower() not in {'.duckdb','.csv','.parquet','.xlsx'} or not resolved.is_file() or resolved.stat().st_size>MAX_BYTES:raise ValueError('file type or size denied')
        return resolved

    def uploaded_path(self,id):
        if not re.fullmatch(r'[a-f0-9-]{36}',id):raise ValueError('invalid upload')
        folder=self.root/'uploads'/id
        candidates=list(folder.glob('source.*'))
        if len(candidates)!=1:raise ValueError('upload unavailable')
        return candidates[0]

    @storage_operation
    def upload(self,auth,filename,content):
        self.authorize(auth)
        suffix=Path(filename or '').suffix.lower()
        if suffix not in {'.duckdb','.csv','.parquet','.xlsx'} or not 0<len(content)<=MAX_BYTES:raise PublicError(422,'INVALID_FILE','仅接收20MB以内的DuckDB、CSV、Parquet或.xlsx文件。')
        from .worker_runtime import run_worker,WorkerLimits,WorkerFailure,public_worker_error
        from .upload_preflight import checked_runtime_path
        id=str(uuid4());folder=self.root/'staging'/id;destination=self.root/'uploads'/id
        try:
            checked_runtime_path(self.root,folder);checked_runtime_path(self.root,destination)
        except ValueError:raise PublicError(422,'INVALID_UPLOAD_LOCATION','后端隔离目录不可用，请由管理员检查；不会写入其他位置。') from None
        with self.lock:self.uploads_in_flight.add(id)
        promoted=False
        try:
            folder.mkdir(parents=True,exist_ok=False)
            checked_runtime_path(self.root,folder)
            created_at=self.clock().isoformat()
            write_marker(self.root,folder,kind='upload',owner=self.owner(auth),created_at=created_at)
            source=folder/f'source{suffix}';source.write_bytes(content)
            digest=hashlib.sha256(content).hexdigest()
            payload={'root':str(self.root),'upload_id':id,'suffix':suffix,'sha256':digest}
            try:value=run_worker('upload_preflight',payload,limits=WorkerLimits(wall_seconds=10))
            except WorkerFailure as exc:raise public_worker_error(exc) from None
            if value.get('ok') is not True:
                code=value.get('code')
                if code in {'INVALID_XLSX','INVALID_FILE'}:raise PublicError(422,code,value['safe_message'])
                raise PublicError(422,'INVALID_FILE','文件预检失败，请检查格式或缩小文件；原文件不会修改。')
            if value.get('data')!={'size_bytes':len(content),'sha256':digest,'suffix':suffix}:
                raise PublicError(422,'UPLOAD_PREFLIGHT_INVALID','上传预检回执不一致，未保留可用上传。')
            # Persist only non-secret artifact provenance. Never user file contents/filename in receipt.
            receipt={'schema_version':'1.0','created_at':created_at,'owner':self.owner(auth),'sha256':digest,'size_bytes':len(content)}
            (folder/'upload.receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
            write_marker(self.root,folder,kind='upload',owner=self.owner(auth),created_at=created_at,complete=True)
            destination.parent.mkdir(parents=True,exist_ok=True)
            checked_runtime_path(self.root,folder);checked_runtime_path(self.root,destination)
            if destination.exists():raise ValueError('upload id collision')
            folder.rename(destination)  # Both absolute targets verified inside this store, same-volume promotion.
            promoted=True
            return FileReceipt(file_id=id,source_label=Path(filename).name[:100])
        except PublicError:raise
        except Exception:raise PublicError(422,'UPLOAD_FAILED','上传写入或预检失败，请检查后端隔离目录后重试；原文件未修改。') from None
        finally:
            try:
                if not promoted:self.cleanup_owned_staging('staging',id)
            finally:
                with self.lock:self.uploads_in_flight.discard(id)

    def snapshot(self,draft,snapshot_id=None):
        import duckdb
        from .warehouse.engine import ENGINE_CONFIG
        from .warehouse.build import sha
        if bool(draft.file_id)==bool(draft.path):raise ValueError('choose exactly one local source')
        source=self.uploaded_path(draft.file_id) if draft.file_id else self.checked_path(draft.path)
        id=snapshot_id or str(uuid4())
        if not re.fullmatch(r'[a-f0-9-]{36}',id):raise ValueError('invalid snapshot id')
        folder=self.root/'snapshots'/id;folder.mkdir(parents=True,exist_ok=True)
        target=folder/'source.duckdb'
        # Trusted file import has a fixed, validated input. The runtime MCP can
        # only read the materialized snapshot, with all external IO disabled.
        config={**ENGINE_CONFIG,'enable_external_access':'true'}
        tables={}
        with duckdb.connect(str(target),config=config) as dest:
            if source.suffix.lower()=='.xlsx':
                from .excel_import import import_workbook
                tables=import_workbook(source.read_bytes(),dest)
            elif source.suffix.lower()=='.duckdb':
                with duckdb.connect(str(source),read_only=True,config=ENGINE_CONFIG) as src:
                    src.execute('SET lock_configuration=true')
                    names=src.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('information_schema','pg_catalog') ORDER BY table_schema,table_name LIMIT 51").fetchall()
                    if not names or len(names)>50:raise ValueError('support 1..50 base tables')
                    for i,(schema,name) in enumerate(names):
                        quote=lambda v:'"'+v.replace('"','""')+'"'
                        fields=src.execute('SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema=? AND table_name=? ORDER BY ordinal_position',[schema,name]).fetchall()
                        if not 0<len(fields)<=100:raise ValueError('unsupported columns')
                        allowed={'VARCHAR','BOOLEAN','DATE','TIMESTAMP','TIMESTAMP WITH TIME ZONE','TINYINT','SMALLINT','INTEGER','BIGINT','HUGEINT','UTINYINT','USMALLINT','UINTEGER','UBIGINT','UHUGEINT','FLOAT','DOUBLE'}
                        if any(kind not in allowed and not re.fullmatch(r'DECIMAL\(\d+,\d+\)',kind) for _,kind,_ in fields):raise ValueError('unsupported field type')
                        key=f't{i}';dest.execute('CREATE SCHEMA IF NOT EXISTS '+quote(schema))
                        dest.execute('CREATE TABLE '+quote(schema)+'.'+quote(name)+' ('+','.join(quote(n)+' '+k for n,k,_ in fields)+')')
                        timer=Timer(5,src.interrupt);timer.start()
                        try:rows=src.execute('SELECT '+','.join(quote(n) for n,_,_ in fields)+' FROM '+quote(schema)+'.'+quote(name)+' LIMIT 20001').fetchall()
                        finally:timer.cancel();timer.join()
                        if len(rows)>20000:raise ValueError('table exceeds 20000 local snapshot rows')
                        for offset in range(0,len(rows),100):
                            batch=rows[offset:offset+100]
                            placeholders='('+','.join('?' for _ in fields)+')'
                            dest.execute('INSERT INTO '+quote(schema)+'.'+quote(name)+' VALUES '+','.join(placeholders for _ in batch),[value for row in batch for value in row])
                        tables[key]={'schema':schema,'name':name,'columns':[{'name':n,'type':k,'nullable':nullable=='YES'} for n,k,nullable in fields]}
            else:
                reader='read_csv' if source.suffix.lower()=='.csv' else 'read_parquet'
                timer=Timer(5,dest.interrupt);timer.start()
                try:
                    # Path is a bound parameter, not SQL text or a guessed table.
                    dest.execute(f'CREATE TABLE main.data AS SELECT * FROM {reader}(?) LIMIT 20001',[str(source)])
                finally:timer.cancel();timer.join()
                if dest.execute('SELECT COUNT(*) FROM main.data').fetchone()[0]>20000:raise ValueError('file exceeds 20000 rows')
                fields=dest.execute("SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_name='data' AND table_schema='main' ORDER BY ordinal_position").fetchall()
                if not 0<len(fields)<=100:raise ValueError('unsupported columns')
                tables['t0']={'schema':'main','name':'data','columns':[{'name':n,'type':k,'nullable':nullable=='YES'} for n,k,nullable in fields]}
            dest.execute('CHECKPOINT')
        manifest={'version':id,'source':'user_provided','database_sha256':sha(target),'tables':tables,'upload_file_id':draft.file_id}
        target.with_suffix('.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
        return target,source.name

    async def call(self,auth,database,tool,args=None):
        from .warehouse.client import OwnedMCPClient
        self.authorize(auth)
        try:
            async with OwnedMCPClient(auth,database=database).connected() as client:value=await client.call(tool,args or {})
        except Exception:raise PublicError(422,'SOURCE_CONNECTION_FAILED','连接测试失败；请检查文件格式、数据类型或项目MCP依赖，原配置仍保留。') from None
        if value.get('ok') is False:raise PublicError(422,'SOURCE_REQUEST_DENIED','表不存在或当前源不支持该预览；请选择实际目录中的表。')
        return value

    def cleanup_owned_staging(self,area,id):
        # Called only for a fresh failed operation, not a retention/TTL sweep.
        import shutil
        from .upload_preflight import checked_runtime_path
        if area not in {'staging','snapshots'} or not re.fullmatch(r'[a-f0-9-]{36}',id):raise ValueError('invalid staging id')
        parent=self.root/area;target=parent/id
        try:
            checked_runtime_path(self.root,target)
            if target.exists():
                if target.resolve().parent!=parent.resolve():raise ValueError('staging escaped')
                # Children must also be plain files; reject symlinks/junctions/unknown subdirectories.
                for child in target.iterdir():
                    checked_runtime_path(self.root,child)
                    if not child.is_file():raise ValueError('unexpected staging child')
                shutil.rmtree(target)
        except (ValueError,OSError):
            raise PublicError(500,'STAGING_CLEANUP_FAILED','临时目录清理未完成，请由管理员检查，原数据未删除。') from None

    def cleanup_failed_snapshot(self,id):
        self.cleanup_owned_staging('snapshots',id)

    async def remote_call(self,auth,row,operation,table=None):
        from .remote_sources import remote_navigation
        self.authorize(auth)
        cls=HTTPMCPDraft if row['kind']=='http_mcp' else PostgresDraft
        draft=cls.model_validate_json(row['config_json'])
        return await remote_navigation(draft,self.remote_policy,operation,table)

    def expire_tests(self):
        # Call only under self.lock; release memory references, never disk files.
        now=self.clock()
        for id,test in list(self.tests.items()):
            try:
                created=timestamp(test['at'])
                expired=created>now or now-created>=TTL
            except (ValueError,TypeError,KeyError):expired=True
            if expired:self.tests.pop(id,None)

    @storage_operation
    async def test(self,auth,draft):
        self.authorize(auth)
        with self.lock:
            self.expire_tests()
            if self.active or len(self.tests)>=50:raise PublicError(409,'SOURCE_BUSY','本机正在处理连接或测试草稿达到上限，请稍后重试；未保存草稿有效24小时。')
            self.active=True
        try:
            if isinstance(draft, (HTTPMCPDraft,PostgresDraft)):
                from .remote_sources import remote_navigation
                metadata=await remote_navigation(draft,self.remote_policy,'tables')
                database='';label=draft.url if isinstance(draft,HTTPMCPDraft) else f'{draft.host}:{draft.port}/{draft.database}'
                response={'metadata':metadata}
            else:
                import anyio
                from .worker_runtime import run_worker, WorkerFailure, public_worker_error
                snapshot_id=str(uuid4())
                payload={'root':str(self.root),'allowed_root':str(self.allowed_root),'snapshot_id':snapshot_id,'draft':draft.model_dump()}
                keep=False
                try:
                    from .upload_preflight import checked_runtime_path
                    folder=self.root/'snapshots'/snapshot_id
                    checked_runtime_path(self.root,folder)
                    folder.mkdir(parents=True,exist_ok=False)
                    created_at=self.clock().isoformat()
                    write_marker(self.root,folder,kind='snapshot',owner=self.owner(auth),created_at=created_at,upload_id=draft.file_id)
                    try:value=await anyio.to_thread.run_sync(lambda:run_worker('snapshot',payload))
                    except WorkerFailure as exc:raise public_worker_error(exc) from None
                    if value.get('ok') is not True:
                        if value.get('code')=='INVALID_XLSX':raise PublicError(422,'INVALID_XLSX',value['safe_message'])
                        raise PublicError(422,'INVALID_SOURCE','本地源无法导入；检查允许路径、格式、表行数或类型。日期列无需移除。')
                    database=Path(value['data']['database']);label=value['data']['label']
                    expected=self.root/'snapshots'/snapshot_id/'source.duckdb'
                    if database!=expected or not database.is_file():raise PublicError(422,'INVALID_SOURCE','本地导入未完成，未保存配置。')
                    keep=True
                finally:
                    if not keep:self.cleanup_failed_snapshot(snapshot_id)
                try:response=await self.call(auth,database,'list_tables')
                except BaseException:
                    self.cleanup_failed_snapshot(snapshot_id);raise
                try:write_marker(self.root,folder,kind='snapshot',owner=self.owner(auth),created_at=created_at,upload_id=draft.file_id,complete=True)
                except BaseException:
                    self.cleanup_failed_snapshot(snapshot_id);raise
            id=str(uuid4());tables=response['metadata']['tables']
            at=self.clock().isoformat()
            try:
                write_test_reference(self.root,id,owner=self.owner(auth),at=at,snapshot_id=Path(database).parent.name if database else None,upload_id=getattr(draft,'file_id',None))
            except (ValueError,OSError):
                raise PublicError(500,'TEST_REFERENCE_FAILED','测试引用无法安全保存，未提供可保存草稿；请检查存储后重新测试，原数据保留。') from None
            with self.lock:self.tests[id]={'owner':self.owner(auth),'draft':draft,'database':str(database),'label':label,'tables':tables,'at':at}
            return TestedDraft(test_id=id,expires_at=(timestamp(at)+TTL).isoformat(),name=draft.name,source_label=label,tables=tables,note='实际连接目录测试通过，尚未保存；测试草稿有效24小时，过期需重新测试。')
        finally:
            with self.lock:self.active=False

    @storage_operation
    def save(self,auth,request):
        self.authorize(auth)
        with self.lock:
            self.expire_tests()
            test=self.tests.get(request.test_id)
            if not test or test['owner']!=self.owner(auth):raise PublicError(409,'TEST_EXPIRED','测试草稿已过期，请重新测试连接后保存。')
            if request.profile_id:
                old=self.get(auth,request.profile_id)
                if old['version']!=request.expected_version:raise PublicError(409,'PROFILE_CHANGED','配置版本已变更，请重新读取。')
                id=old['id'];version=old['version']+1
            else:id=str(uuid4());version=1
            with self.db() as db:
                if not request.profile_id and db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0]>=50:raise PublicError(409,'PROFILE_LIMIT','已达本机50个连接配置上限。')
                db.execute('INSERT OR REPLACE INTO profiles (id,owner,name,version,enabled,database_path,source_label,last_test_at,kind,config_json) VALUES (?,?,?,?,?,?,?,?,?,?)',[id,self.owner(auth),test['draft'].name,version,1,test['database'],test['label'],test['at'],test['draft'].kind,json.dumps(test['draft'].model_dump()) if test['draft'].kind!='local_file' else '{}'])
            self.tests.pop(request.test_id)
            self.needs_retest.discard(id)
        return self.public(self.get(auth,id))

    @storage_operation
    def toggle(self,auth,id,request):
        with self.lock:
            row=self.get(auth,id)
            if row['version']!=request.expected_version:raise PublicError(409,'PROFILE_CHANGED','配置版本已变更，请重新读取。')
            with self.db() as db:db.execute('UPDATE profiles SET enabled=?,version=version+1 WHERE id=? AND owner=?',[int(request.enabled),id,self.owner(auth)])
            return self.public(self.get(auth,id))

    @storage_operation
    async def navigation(self,auth,id):
        with self.lock:
            row=self.get(auth,id)
            if not row['enabled']:raise PublicError(409,'SOURCE_DISABLED','数据源已禁用，请启用后重新连接。')
            if self.active:raise PublicError(409,'SOURCE_BUSY','当前正在读取，请稍后重试。')
            self.active=True;version=row['version']
        try:
            result={'metadata':await self.remote_call(auth,row,'tables')} if row['kind']!='local_file' else await self.call(auth,row['database_path'],'list_tables')
            with self.lock:
                current=self.get(auth,id)
                if not current['enabled'] or current['version']!=version:raise PublicError(409,'PROFILE_CHANGED','配置已变更，旧连接结果已丢弃。')
            with self.lock:self.needs_retest.discard(id)
            return result['metadata']
        except Exception:
            with self.lock:self.needs_retest.add(id)
            raise
        finally:
            with self.lock:self.active=False

    @storage_operation
    async def preview(self,auth,id,table):
        from .warehouse.client import OwnedMCPClient
        with self.lock:
            row=self.get(auth,id)
            if not row['enabled']:raise PublicError(409,'SOURCE_DISABLED','数据源已禁用。')
            if self.active:raise PublicError(409,'SOURCE_BUSY','当前正在读取，请稍后重试。')
            self.active=True;version=row['version']
        try:
            if row['kind']!='local_file':
                data={'result':await self.remote_call(auth,row,'preview',table)}
            else:
                try:
                    async with OwnedMCPClient(auth,database=row['database_path']).connected() as client:
                        receipt=await client.call('submit_query',{'request':{'table':table,'limit':100},'idempotency_key':'navigation'})
                        if receipt.get('ok') is False or receipt['task']['status']!='SUCCEEDED':raise ValueError('preview denied')
                        data=await client.call('get_query_result',{'task_id':receipt['task']['task_id']})
                        if data.get('ok') is False:raise ValueError('result failed')
                except Exception:raise PublicError(422,'PREVIEW_FAILED','预览读取失败，请检查表或文件；不会执行筛选或修改源数据。') from None
            with self.lock:
                current=self.get(auth,id)
                if not current['enabled'] or current['version']!=version:raise PublicError(409,'PROFILE_CHANGED','配置已变更，旧预览已丢弃。')
            with self.lock:self.needs_retest.discard(id)
            return NavigationPreview(profile_id=id,table_id=table,preview=data['result'])
        except Exception:
            with self.lock:self.needs_retest.add(id)
            raise
        finally:
            with self.lock:self.active=False
