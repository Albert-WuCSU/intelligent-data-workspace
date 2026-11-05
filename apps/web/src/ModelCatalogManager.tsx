import {useEffect,useState} from 'react';
import {ApiError,request} from './api';
import type {ModelCatalog,ModelCatalogEntry,ModelServiceStatus,ModelTestReceipt} from './api';

type Props={status:ModelServiceStatus|null;blocked:boolean;onBusy:(busy:boolean)=>void;onChanged:()=>Promise<void>};

const sourceLabel:Record<string,string>={personal_api:'个人 API',ai_plan:'企业 AI Plan'};

/** Add/test/enable additional models on the current connection. No key is accepted here. */
export default function ModelCatalogManager({status,blocked,onBusy,onChanged}:Props){
 const [models,setModels]=useState<ModelCatalogEntry[]>([]);
 const [modelId,setModelId]=useState('');
 const [busy,setBusy]=useState(false);
 const [accepted,setAccepted]=useState(false);
 const [notice,setNotice]=useState('');
 useEffect(()=>{onBusy(busy);},[busy,onBusy]);
 async function refresh(){
  if(!status?.credential_configured){setModels([]);return;}
  try{const value=await request<ModelCatalog>('/api/v1/model-service/catalog');setModels(value.models);}catch{setModels([]);}
 }
 useEffect(()=>{void refresh();},[status?.execution_generation,status?.config_version,status?.credential_configured]);
 async function add(event:React.FormEvent){
  event.preventDefault();
  if(!status?.execution_generation||!status.config_version||!modelId.trim()||busy)return;
  setBusy(true);setNotice('');
  try{
   await request('/api/v1/model-service/connection/models',{execution_generation:status.execution_generation,config_version:status.config_version,model_id:modelId.trim()});
   setModelId('');setNotice('模型已加入目录；请显式测试后再启用。');await refresh();await onChanged();
  }catch(error){setNotice(error instanceof ApiError?`${error.code} · ${error.message}`:'模型未加入，请刷新后重试。');}
  finally{setBusy(false);}
 }
 async function test(model:ModelCatalogEntry){
  if(!status?.execution_generation||busy||!accepted)return;
  setBusy(true);setNotice('');
  try{
   const receipt=await request<ModelTestReceipt>('/api/v1/model-service/models/test',{model_id:model.model_id,request_id:crypto.randomUUID(),execution_generation:status.execution_generation,config_version:model.config_version,accept_estimated_cost:true},25000);
   setNotice(receipt.status==='succeeded'?'模型连接测试成功；请显式启用。':`测试未完成：${receipt.error_code??'结果未知'}；不自动重试。`);
   await refresh();await onChanged();
  }catch{setNotice('测试通信失败，费用或结果可能已产生；不自动重试。');await refresh();}
  finally{setBusy(false);}
 }
 async function toggle(model:ModelCatalogEntry){
  if(!status?.execution_generation||busy)return;
  setBusy(true);setNotice('');
  try{
   await request('/api/v1/model-service/models/enabled',{model_id:model.model_id,execution_generation:status.execution_generation,config_version:model.config_version,enabled:!model.enabled});
   setNotice(model.enabled?'已禁用该模型；旧测试/选择失效。':'已启用该模型；选择不调用、不执行SQL。');await refresh();await onChanged();
  }catch(error){setNotice(error instanceof ApiError?`${error.code} · ${error.message}`:'模型状态未更新，请刷新后重试。');}
  finally{setBusy(false);}
 }
 async function remove(model:ModelCatalogEntry){
  if(!status?.execution_generation||!status.config_version||busy)return;
  setBusy(true);setNotice('');
  try{
   await request('/api/v1/model-service/connection/models/remove',{model_id:model.model_id,execution_generation:status.execution_generation,config_version:status.config_version});
   setNotice('已移除该模型；主模型不变。');await refresh();await onChanged();
  }catch(error){setNotice(error instanceof ApiError?`${error.code} · ${error.message}`:'模型未移除，请刷新后重试。');}
  finally{setBusy(false);}
 }
 const additional=models.filter(model=>!model.default);
 const disabled=blocked||busy||!status?.credential_configured;
 return <section className="settings-card" aria-label="多模型目录">
  <header><h3>模型目录</h3><p>同一连接可添加多个模型；每个模型独立测试/启用。输入区只显示已启用模型。</p></header>
  {!status?.credential_configured?<p className="settings-warning" role="status">请先完成左侧连接配置并保存；添加模型不需要再次输入Key。</p>:<>
   <form className="settings-form-grid" onSubmit={e=>void add(e)}><label className="settings-span">添加模型<input aria-label="添加模型ID" required maxLength={120} value={modelId} disabled={disabled} onChange={e=>setModelId(e.target.value)} placeholder="输入你的账号可用的 model ID"/><small>只加入目录，不调用模型；测试通过后显式启用。</small></label><div className="settings-span settings-actions"><button className="secondary" type="submit" disabled={disabled||!modelId.trim()}>添加模型</button><span className="model-readiness">MVP 默认：{models.find(m=>m.default)?.model_id??'deepseek-v4.1-flash'}</span></div></form>
   <label className="settings-consent"><input type="checkbox" checked={accepted} disabled={disabled} onChange={e=>setAccepted(e.target.checked)}/><span>接受每次 $0.25 估算预留，测试仅发送固定非敏感文本；不发送表行、历史或截图。</span></label>
   {additional.length===0?<p className="settings-notice" role="status">当前只有主模型。添加第二个模型后，可在这里独立测试/启用。</p>:<ul className="model-catalog-list">{additional.map(model=><li key={model.id} className="model-catalog-row">
    <div><strong>{model.label||model.model_id}</strong><span className={`model-option-status ${model.available?'ok':''}`}>{model.available?'可用':model.enabled?'未验证':'未启用'}</span><small>{model.model_id} · {sourceLabel[model.source]??model.source} · {model.price_note} · {model.context_window?`${Math.round(model.context_window/1000)}K 上下文`:'上下文未知'}</small></div>
    <div className="settings-actions"><button className="secondary" type="button" disabled={disabled||!accepted} onClick={()=>void test(model)}>测试（估算 $0.25）</button><button className="secondary" type="button" disabled={disabled||(!model.enabled&&!model.generation_verified)} onClick={()=>void toggle(model)}>{model.enabled?'禁用':'启用'}</button><button className="settings-text-button" type="button" disabled={disabled} onClick={()=>void remove(model)}>移除</button></div>
   </li>)}</ul>}
   {notice&&<p className="settings-notice" role="status">{notice}</p>}
  </>}
  <details className="settings-details"><summary>目录、选择与费用</summary><p>目录只来自当前后端连接的实际配置与测试状态，不自动枚举网关模型，不显示未经验证的价格或上下文。Key只在后端内存。</p><p>选择模型不调用模型；模型变更使旧计划/确认失效。测试/启用不代表工具、SQL或业务问数已验证。</p></details>
 </section>;
}
