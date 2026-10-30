import type { components } from './api.generated';
export type ConnectorSummary = components['schemas']['ConnectorSummary'];
export type ConnectorMetadata = components['schemas']['ConnectorMetadata'];
export type PreviewReceipt = components['schemas']['PreviewReceipt'];
export type PreviewResult = components['schemas']['PreviewResult'];
export type QueryPreview = components['schemas']['QueryPreview'];
export type PreviewRequest = components['schemas']['PreviewRequest'];
export type QuerySpec = components['schemas']['QuerySpec'];
export type Task = components['schemas']['Task'];
export type Session = components['schemas']['SessionResponse'];
export type Capabilities = components['schemas']['CapabilitiesResponse'];
export type Validation = components['schemas']['ValidationResponse'];
export class ApiError extends Error {
  constructor(public code:string, message:string, public traceId:string){super(message);}
}
export async function request<T>(path:string, body?:unknown, timeoutMs=8000):Promise<T>{
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const response=await fetch(path,{method:body === undefined?'GET':'POST',
      headers:body === undefined?{}:{'Content-Type':'application/json','X-Workspace-Request':'1'},
      body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
    const data=await response.json();
    if(!response.ok)throw new ApiError(data.code||'SERVICE_ERROR',data.safe_message||'服务请求失败。',data.trace_id||'');
    return data as T;
  }catch(e){
    if(e instanceof ApiError)throw e;
    throw new ApiError('CONNECTION_ERROR','无法连接后端服务，请确认 API 已启动。','');
  }finally{clearTimeout(timer);}
}
export const example:QuerySpec={schema_version:'1.0',target:{kind:'metric',metric_refs:[{id:'order_conversion_rate',version:'1.0.0'}]},
  time_range:{start:'2026-10-19',end_exclusive:'2026-10-26'},timezone:'Asia/Shanghai',dimensions:['region'],filters:[]};

export type SourceProfile = components['schemas']['Profile'];
export type SourceProfileList = components['schemas']['ProfileList'];
export type ProfileDraft = components['schemas']['ProfileDraft'];
export type TestedDraft = components['schemas']['TestedDraft'];
export type FileReceipt = components['schemas']['FileReceipt'];
export type NavigationPreview = components['schemas']['NavigationPreview'];
export async function uploadFile<T>(path:string,file:File):Promise<T>{
 const body=new FormData();body.append('file',file);
 try{
  const response=await fetch(path,{method:'POST',headers:{'X-Workspace-Request':'1'},body});
  const data=await response.json();
  if(!response.ok)throw new ApiError(data.code||'UPLOAD_FAILED',data.safe_message||'上传失败，请检查文件格式与大小。',data.trace_id||'');
  return data as T;
 }catch(error){if(error instanceof ApiError)throw error;throw new ApiError('UPLOAD_FAILED','文件上传未完成，请检查连接。','');}
}

export type HTTPMCPDraft = components['schemas']['HTTPMCPDraft'];
export type PostgresDraft = components['schemas']['PostgresDraft'];
export type ConnectionDraft = ProfileDraft | HTTPMCPDraft | PostgresDraft;

export type StorageSummary = components['schemas']['StorageSummary'];

export type RetentionStatus = components['schemas']['RetentionStatus'];

export type DraftPreview = components['schemas']['DraftPreview'];

export type ModelServiceStatus = components['schemas']['ModelReadiness'];
export type ModelTestReceipt = components['schemas']['ModelTestReceipt'];
