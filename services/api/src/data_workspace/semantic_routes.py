"""Semantic draft -> metadata-only check -> explicit immutable publication."""
import asyncio
from uuid import uuid4
from fastapi import APIRouter,Depends,Request
from .contracts import AuthContext
from .auth import identity,PublicError
from .semantic_contracts import (SemanticDraftInput,DraftReceipt,CheckReceipt,PublishInput,PublishedSemantic,SemanticList,ResolvedSemantic,SemanticStateInput,check_contract)
from .semantic_metadata import SemanticSchema,read_schema
router=APIRouter(prefix='/api/v1/semantics',tags=['semantics'])

@router.get('',response_model=SemanticList)
def versions(request:Request,auth:AuthContext=Depends(identity)):
    return SemanticList(versions=request.app.state.semantics.versions(auth))

@router.get('/sources/{source_id}/tables/{table_id}/schema',response_model=SemanticSchema)
async def schema(source_id:str,table_id:str,request:Request,auth:AuthContext=Depends(identity)):
    request.app.state.semantics.authorize(auth)
    return await read_schema(request.app.state.sources,auth,source_id,table_id)

@router.post('/drafts',response_model=DraftReceipt)
def create_draft(body:SemanticDraftInput,request:Request,auth:AuthContext=Depends(identity)):
    # Source ownership checked before retaining user authored drafts.
    request.app.state.sources.get(auth,body.source_id)
    return request.app.state.semantics.draft(auth,body)

@router.post('/drafts/{draft_id}/check',response_model=CheckReceipt)
async def check(draft_id:str,request:Request,auth:AuthContext=Depends(identity)):
    store=request.app.state.semantics;draft=store.get_draft(auth,draft_id)
    snapshot=await read_schema(request.app.state.sources,auth,draft.contract.source_id,draft.contract.table_id)
    result=check_contract(draft.contract,snapshot)
    with store.lock:
        if len(store.checks)>=200:raise PublicError(409,'SEMANTIC_CHECK_LIMIT','本轮校验已到上限，请重新创建会话；发布版本保留。')
        receipt=CheckReceipt(draft_id=draft_id,validation_id=str(uuid4()),result=result)
        store.checks[receipt.validation_id]=(store.owner(auth),receipt)
    return receipt

@router.post('/publish',response_model=PublishedSemantic)
async def publish(body:PublishInput,request:Request,auth:AuthContext=Depends(identity)):
    store=request.app.state.semantics;sources=request.app.state.sources
    cached=store.cached_publish(auth,body)
    if cached is not None:return cached # Read acknowledgement, never revalidates by querying/republishing.
    draft=store.get_draft(auth,body.draft_id);value=store.checks.get(body.validation_id)
    if not value or value[0]!=store.owner(auth) or value[1].draft_id!=body.draft_id:raise PublicError(409,'SEMANTIC_CHECK_EXPIRED','校验回执已失效或不属于该草稿，请重新校验。')
    result=value[1].result
    if not result.valid:raise PublicError(409,'SEMANTIC_NOT_VALID','存在字段/口径冲突，请修正并重新校验后批准。')
    snapshot=await read_schema(sources,auth,draft.contract.source_id,draft.contract.table_id)
    if snapshot.fingerprint!=result.schema_snapshot.fingerprint:raise PublicError(409,'SEMANTIC_MAPPING_STALE','实际字段或来源版本已改变，请重新校验；未发布。')
    # Freeze current source version while doing the bounded SQLite transaction. No awaits under thread locks.
    with sources.lock:
        row=sources.get(auth,draft.contract.source_id)
        if not row['enabled'] or row['version']!=snapshot.source_version:raise PublicError(409,'SEMANTIC_MAPPING_STALE','来源已变化，请重验。')
        return store.publish(auth,body,draft,snapshot)

@router.get('/versions/{version_id}',response_model=PublishedSemantic)
def version(version_id:str,request:Request,auth:AuthContext=Depends(identity)):
    return request.app.state.semantics.version(auth,version_id)

@router.post('/versions/{version_id}/resolve',response_model=ResolvedSemantic)
async def resolve(version_id:str,request:Request,auth:AuthContext=Depends(identity)):
    # Downstream must use this gate, not a stale browser-supplied schema/pack.
    value=request.app.state.semantics.version(auth,version_id)
    if value.state=='disabled':raise PublicError(409,'SEMANTIC_DISABLED','语义包已停用，不能消费；历史定义仍保留。')
    if value.state=='superseded':raise PublicError(409,'SEMANTIC_VERSION_STALE','该版本已被新版本替代，只可追溯，不能生成新执行计划。')
    snapshot=await read_schema(request.app.state.sources,auth,value.contract.source_id,value.contract.table_id)
    if snapshot.fingerprint!=value.schema_snapshot.fingerprint:raise PublicError(409,'SEMANTIC_MAPPING_STALE','发布版本的字段映射已变化，不能消费；请重新发布。')
    current=request.app.state.semantics.version(auth,version_id)
    if current.state!='published_recheck_required' or current.state_revision!=value.state_revision:
        raise PublicError(409,'SEMANTIC_VERSION_STALE','校验期间语义版本或启禁状态已变化，请重新选择。')
    return ResolvedSemantic(version=current)


@router.post('/packs/{pack_id}/state',response_model=PublishedSemantic)
async def toggle(pack_id:str,body:SemanticStateInput,request:Request,auth:AuthContext=Depends(identity)):
    store=request.app.state.semantics;sources=request.app.state.sources
    current=store.latest(auth,pack_id)
    if body.enabled:
        snapshot=await read_schema(sources,auth,current.contract.source_id,current.contract.table_id)
        if snapshot.fingerprint!=current.schema_snapshot.fingerprint:
            raise PublicError(409,'SEMANTIC_MAPPING_STALE','当前字段映射已变，不能启用；请编辑重验并发布新版本。')
        with sources.lock:
            source=sources.get(auth,current.contract.source_id)
            if not source['enabled'] or source['version']!=snapshot.source_version:raise PublicError(409,'SEMANTIC_MAPPING_STALE','来源变化，不能启用。')
            return store.toggle(auth,pack_id,body)
    return store.toggle(auth,pack_id,body)
