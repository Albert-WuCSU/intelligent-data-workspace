"""Nonsecret immutable semantic versions; drafts/validation are session-only."""
import json,sqlite3,hashlib,os
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
from datetime import datetime,timezone
from uuid import uuid4,UUID
from .auth import PublicError
from .semantic_contracts import PublishedSemantic,DraftReceipt
from .upload_preflight import checked_runtime_path

ROOT=Path(__file__).resolve().parents[4]
class SemanticStore:
    def __init__(self,root=None):
        self.root=Path(root or ROOT/'data/semantics').absolute();self.lock=RLock();self.drafts={};self.checks={}
    def authorize(self,auth):
        if (auth.mode,auth.tenant_id,auth.principal_id)!=('development','local-workspace','local-developer'):
            raise PublicError(403,'SEMANTIC_ACCESS_DENIED','语义维护当前仅支持本机开发身份。')
    def owner(self,auth):return auth.tenant_id+':'+auth.principal_id
    @contextmanager
    def db(self):
        # Reject links/junctions in root and database; no user path or user SQL is accepted.
        current=self.root
        while current!=current.parent:
            if current.is_symlink() or current.is_junction():raise PublicError(409,'SEMANTIC_STORAGE_UNSAFE','语义版本目录不可用，请维护者检查。')
            current=current.parent
        self.root.mkdir(parents=True,exist_ok=True);path=self.root/'versions.sqlite3'
        if path.is_symlink() or path.is_junction():raise PublicError(409,'SEMANTIC_STORAGE_UNSAFE','版本文件不能为链接。')
        con=sqlite3.connect(path,timeout=2);con.row_factory=sqlite3.Row
        try:
            con.execute('CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, owner TEXT NOT NULL, pack_id TEXT NOT NULL, version INTEGER NOT NULL, domain TEXT NOT NULL, body TEXT NOT NULL, request_id TEXT NOT NULL, request_hash TEXT NOT NULL, UNIQUE(owner,pack_id,version), UNIQUE(owner,request_id))')
            con.execute('CREATE TABLE IF NOT EXISTS pack_states(owner TEXT NOT NULL, pack_id TEXT NOT NULL, enabled INTEGER NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(owner,pack_id))')
            con.execute('BEGIN IMMEDIATE');yield con;con.commit()
        except BaseException:con.rollback();raise
        finally:con.close()
    def draft(self,auth,body):
        self.authorize(auth)
        if len(body.model_dump_json().encode())>32768:raise PublicError(413,'SEMANTIC_LIMIT','语义包超限，请拆分。')
        with self.lock:
            if len(self.drafts)>=100:raise PublicError(409,'SEMANTIC_DRAFT_LIMIT','本轮草稿已到上限，请重新启动后再创建；发布版本保留。')
            if body.pack_id:
                with self.db() as con:
                    current=con.execute('SELECT MAX(version) FROM versions WHERE owner=? AND pack_id=?',[self.owner(auth),body.pack_id]).fetchone()[0]
                if current is None:raise PublicError(404,'SEMANTIC_NOT_FOUND','语义包不存在或不可访问。')
                if current!=body.expected_version:raise PublicError(409,'SEMANTIC_VERSION_CONFLICT','版本已变化，请刷新后编辑。')
                pack=body.pack_id
            else:
                if body.expected_version!=0:raise PublicError(409,'SEMANTIC_VERSION_CONFLICT','新语义包版本应为0。')
                pack=str(uuid4())
            receipt=DraftReceipt(draft_id=str(uuid4()),pack_id=pack,contract=body)
            self.drafts[receipt.draft_id]=(self.owner(auth),receipt)
            return receipt
    def get_draft(self,auth,id):
        self.authorize(auth);value=self.drafts.get(id)
        if not value or value[0]!=self.owner(auth):raise PublicError(404,'SEMANTIC_DRAFT_NOT_FOUND','草稿不在当前会话，请重新创建；发布版本保留。')
        return value[1]
    def public_version(self,con,auth,raw):
        value=PublishedSemantic.model_validate_json(raw)
        flag=con.execute('SELECT enabled,revision FROM pack_states WHERE owner=? AND pack_id=?',[self.owner(auth),value.pack_id]).fetchone()
        latest=con.execute('SELECT MAX(version) FROM versions WHERE owner=? AND pack_id=?',[self.owner(auth),value.pack_id]).fetchone()[0]
        state='disabled' if flag and not flag['enabled'] else 'superseded' if value.version!=latest else 'published_recheck_required'
        return value.model_copy(update={'state':state,'state_revision':flag['revision'] if flag else 0})
    def versions(self,auth):
        self.authorize(auth)
        with self.lock,self.db() as con:
            rows=con.execute('SELECT body FROM versions WHERE owner=? ORDER BY rowid DESC LIMIT 500',[self.owner(auth)]).fetchall()
            return [self.public_version(con,auth,row['body']) for row in rows]
    def version(self,auth,id):
        self.authorize(auth)
        with self.lock,self.db() as con:
            row=con.execute('SELECT body FROM versions WHERE owner=? AND id=?',[self.owner(auth),id]).fetchone()
            if row is None:raise PublicError(404,'SEMANTIC_NOT_FOUND','版本不存在或不可访问。')
            return self.public_version(con,auth,row['body'])
    def latest(self,auth,pack_id):
        self.authorize(auth)
        with self.lock,self.db() as con:
            row=con.execute('SELECT body FROM versions WHERE owner=? AND pack_id=? ORDER BY version DESC LIMIT 1',[self.owner(auth),pack_id]).fetchone()
            if row is None:raise PublicError(404,'SEMANTIC_NOT_FOUND','语义包不存在或不可访问。')
            return self.public_version(con,auth,row['body'])
    def toggle(self,auth,pack_id,body):
        self.authorize(auth)
        with self.lock,self.db() as con:
            row=con.execute('SELECT body FROM versions WHERE owner=? AND pack_id=? ORDER BY version DESC LIMIT 1',[self.owner(auth),pack_id]).fetchone()
            if row is None:raise PublicError(404,'SEMANTIC_NOT_FOUND','语义包不可访问。')
            current=self.public_version(con,auth,row['body'])
            if current.version!=body.expected_version or current.state_revision!=body.expected_state_revision:
                raise PublicError(409,'SEMANTIC_VERSION_CONFLICT','语义版本或启禁状态已变化，请刷新后重试。')
            con.execute('INSERT INTO pack_states VALUES(?,?,?,?) ON CONFLICT(owner,pack_id) DO UPDATE SET enabled=excluded.enabled,revision=excluded.revision',[self.owner(auth),pack_id,int(body.enabled),current.state_revision+1])
            return self.public_version(con,auth,row['body'])
    def cached_publish(self,auth,body):
        self.authorize(auth);digest=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        with self.lock,self.db() as con:
            row=con.execute('SELECT body,request_hash FROM versions WHERE owner=? AND request_id=?',[self.owner(auth),body.request_id]).fetchone()
            if row:
                if row['request_hash']!=digest:raise PublicError(409,'SEMANTIC_REQUEST_CONFLICT','同一发布编号不能用于不同请求。')
                return self.public_version(con,auth,row['body'])
    def publish(self,auth,body,draft,schema):
        self.authorize(auth);digest=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        with self.lock,self.db() as con:
            replay=con.execute('SELECT body,request_hash FROM versions WHERE owner=? AND request_id=?',[self.owner(auth),body.request_id]).fetchone()
            if replay:
                if replay['request_hash']!=digest:raise PublicError(409,'SEMANTIC_REQUEST_CONFLICT','发布编号已用于其他请求。')
                return self.public_version(con,auth,replay['body'])
            current=con.execute('SELECT MAX(version) FROM versions WHERE owner=? AND pack_id=?',[self.owner(auth),draft.pack_id]).fetchone()[0] or 0
            if current!=draft.contract.expected_version:raise PublicError(409,'SEMANTIC_VERSION_CONFLICT','版本已发布或改变，请重新编辑校验。')
            if con.execute('SELECT COUNT(*) FROM versions').fetchone()[0]>=500:raise PublicError(409,'SEMANTIC_STORAGE_LIMIT','发布版本已到上限；版本不会自动删除。')
            # Published metric terms in a domain cannot collide across different packs.
            terms={v.strip().casefold() for metric in draft.contract.metrics for v in [metric.name,*metric.aliases]}
            latest=con.execute('SELECT body FROM versions WHERE owner=? AND domain=? AND pack_id!=? AND (pack_id,version) IN (SELECT pack_id,MAX(version) FROM versions WHERE owner=? GROUP BY pack_id)',[self.owner(auth),draft.contract.domain,draft.pack_id,self.owner(auth)]).fetchall()
            for row in latest:
                old=PublishedSemantic.model_validate_json(row['body'])
                if terms & {v.strip().casefold() for metric in old.contract.metrics for v in [metric.name,*metric.aliases]}:
                    raise PublicError(409,'SEMANTIC_ALIAS_CONFLICT','该域已有同名或别名指标，请修正歧义后重验。')
            value=PublishedSemantic(id=str(uuid4()),pack_id=draft.pack_id,version=current+1,published_at=datetime.now(timezone.utc).isoformat(),approved_by=auth.principal_id,contract=draft.contract,schema_snapshot=schema)
            con.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',[value.id,self.owner(auth),draft.pack_id,current+1,draft.contract.domain,value.model_dump_json(),body.request_id,digest])
            return self.public_version(con,auth,value.model_dump_json())
