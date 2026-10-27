"""Explicit local-source onboarding; no implicit business/date filters."""
import json
from fastapi import APIRouter,Depends,Request,UploadFile,File
from pydantic import ValidationError
from .auth import identity,PublicError
from .contracts import AuthContext
from .source_profiles import (SourceStore,ProfileDraft,SourceDraft,Profile,ProfileList,TestedDraft,SaveProfile,ToggleProfile,ConfigImport,FileReceipt,NavigationPreview,MAX_BYTES)

from .storage_inventory import StorageSummary,storage_summary

router=APIRouter(prefix='/api/v1/source-profiles')

@router.get('',response_model=ProfileList)
def profiles(request:Request,auth:AuthContext=Depends(identity)):
    return request.app.state.sources.profiles(auth)

@router.get('/storage',response_model=StorageSummary)
async def storage(request:Request,auth:AuthContext=Depends(identity)):
    import anyio
    return await anyio.to_thread.run_sync(lambda:storage_summary(request.app.state.sources,auth))

@router.post('/upload',response_model=FileReceipt)
async def upload(request:Request,file:UploadFile=File(...),auth:AuthContext=Depends(identity)):
    store=request.app.state.sources;store.authorize(auth)
    try:
        content=await file.read(MAX_BYTES+1)
        import anyio
        return await anyio.to_thread.run_sync(lambda:store.upload(auth,file.filename,content))
    finally:await file.close()

@router.post('/import-config',response_model=SourceDraft)
async def import_config(request:Request,file:UploadFile=File(...),auth:AuthContext=Depends(identity)):
    request.app.state.sources.authorize(auth)
    try:
        data=await file.read(65537)
        if len(data)>65536 or not (file.filename or '').lower().endswith('.json'):raise ValueError('invalid config')
        value=ConfigImport.model_validate(json.loads(data.decode('utf-8-sig')))
        return value.profile
    except (ValueError,ValidationError):raise PublicError(422,'INVALID_CONFIG','仅支持非秘密连接JSON配置；未知字段、命令、密码或协议均拒绝，不自动连接。') from None
    finally:await file.close()

@router.post('/test',response_model=TestedDraft)
async def test_source(body:SourceDraft,request:Request,auth:AuthContext=Depends(identity)):
    return await request.app.state.sources.test(auth,body)

@router.post('/save',response_model=Profile)
def save_source(body:SaveProfile,request:Request,auth:AuthContext=Depends(identity)):
    return request.app.state.sources.save(auth,body)

@router.post('/{id}/toggle',response_model=Profile)
def toggle_source(id:str,body:ToggleProfile,request:Request,auth:AuthContext=Depends(identity)):
    return request.app.state.sources.toggle(auth,id,body)

@router.get('/{id}/tables')
async def source_tables(id:str,request:Request,auth:AuthContext=Depends(identity)):
    return await request.app.state.sources.navigation(auth,id)

@router.get('/{id}/tables/{table}/preview',response_model=NavigationPreview)
async def preview_table(id:str,table:str,request:Request,auth:AuthContext=Depends(identity)):
    return await request.app.state.sources.preview(auth,id,table)
