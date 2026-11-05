import {useEffect,useRef,useState} from 'react';
import {ApiError,request} from './api';
import type {ModelServiceStatus} from './api';
type Protocol='openai_responses'|'openai_chat_completions'|'anthropic_messages';
const presets={
 openai:{label:'OpenAI',protocol:'openai_responses',endpoint:'https://api.openai.com/v1/responses',auth:'bearer'},
 deepseek:{label:'DeepSeek 官方',protocol:'openai_chat_completions',endpoint:'https://api.deepseek.com/chat/completions',auth:'bearer'},
 anthropic:{label:'Anthropic',protocol:'anthropic_messages',endpoint:'https://api.anthropic.com/v1/messages',auth:'x_api_key'},
 ai_plan:{label:'公司 AI Plan（已授权内网）',protocol:'anthropic_messages',endpoint:'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',auth:'bearer'},
 custom:{label:'自定义兼容服务',protocol:'openai_chat_completions',endpoint:'',auth:'bearer'},
} as const;
export default function ModelConnectionForm({status,blocked,onChanged,onBusy}:{status:ModelServiceStatus|null;blocked:boolean;onChanged:()=>Promise<void>;onBusy:(busy:boolean)=>void}){
 const [vendor,setVendor]=useState<keyof typeof presets>('openai'),[protocol,setProtocol]=useState<Protocol>('openai_responses'),[endpoint,setEndpoint]=useState<string>(presets.openai.endpoint),[model,setModel]=useState(''),[auth,setAuth]=useState('bearer'),[key,setKey]=useState(''),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const initialized=useRef(false);
 useEffect(()=>{if(!status||initialized.current)return;initialized.current=true;
  if(status.credential_configured&&status.endpoint&&status.protocol){
   const entry=Object.entries(presets).find(([,p])=>p.endpoint===status.endpoint&&p.protocol===status.protocol&&p.auth===status.authentication);
   setVendor(entry?entry[0] as keyof typeof presets:'custom');setEndpoint(status.endpoint);setProtocol(status.protocol as Protocol);setAuth(status.authentication??'bearer');setModel(status.model_id??'');
  }
 },[status]);
 useEffect(()=>{onBusy(busy);},[busy,onBusy]);
 const fixed=vendor==='ai_plan',disabled=blocked||busy;
 const legacyModelLock=fixed&&!status?.model_name_editable;
 function choose(v:keyof typeof presets){initialized.current=true;const p=presets[v];setVendor(v);setProtocol(p.protocol);setEndpoint(p.endpoint);setModel(v==='ai_plan'?'deepseek-v4.1-flash':'');setAuth(p.auth);setKey('');setConsent(false);setNotice('');}
 async function save(e:React.FormEvent){e.preventDefault();if(!status||!key||!consent||legacyModelLock)return;setBusy(true);setNotice('');try{
  await request('/api/v1/model-service/connection',{preset:fixed?'ai_plan':'custom',protocol,endpoint,model_id:model,authentication:auth,api_key:key,execution_generation:status.execution_generation,accept_fixed_test_egress:true,accept_estimated_cost:true});
  setNotice('已保存到本次后端会话，未收费调用。请点击“测试模型连接”。');await onChanged();
 }catch(error){setNotice(error instanceof ApiError?`${error.code} · ${error.message}`:'连接配置未保存，请刷新状态后再试。');}finally{setKey('');setBusy(false);}}
 async function clear(){if(!status)return;setBusy(true);setKey('');try{await request('/api/v1/model-service/connection/clear',{execution_generation:status.execution_generation});setNotice('Key已清除，预算预留保留。');await onChanged();}catch(e){setNotice(e instanceof ApiError?e.message:'清除未完成，请刷新。');}finally{setBusy(false);}}
 return <section className="settings-card connection-settings" aria-label="快捷模型接入"><header><h3>连接配置</h3><p>预设只填入地址和协议，不限定模型名称。</p></header>{!status?.connection_management&&<p className="settings-warning" role="status">当前后端未加载快捷接入接口；更新服务后刷新，不要在旧页面提交 Key。</p>}
 {legacyModelLock&&<p className="settings-warning" role="status">当前后端仍是固定模型版本，加载新版后可保存 AI Plan 自选模型；不用在聊天提供 Key。</p>}
 <form onSubmit={e=>void save(e)} autoComplete="off"><div className="settings-form-grid">
 <label>厂商／服务<select aria-label="模型服务厂商" value={vendor} disabled={disabled} onChange={e=>choose(e.target.value as keyof typeof presets)}>{Object.entries(presets).map(([v,p])=><option value={v} key={v}>{p.label}</option>)}</select></label>
 <label>协议<select aria-label="模型 API 协议" value={protocol} disabled={disabled||fixed} onChange={e=>{initialized.current=true;const p=e.target.value as Protocol;setProtocol(p);setAuth(p==='anthropic_messages'?'x_api_key':'bearer');setConsent(false);}}><option value="openai_responses">OpenAI Responses</option><option value="openai_chat_completions">OpenAI-compatible Chat Completions</option><option value="anthropic_messages">Anthropic Messages</option></select></label>
 <label className="settings-span">完整 API 地址<input aria-label="模型 API 地址" type="url" required maxLength={512} value={endpoint} disabled={disabled||fixed} onChange={e=>{initialized.current=true;setEndpoint(e.target.value);setConsent(false);}} placeholder="https://你的域名/v1/chat/completions"/></label>
 <label className="settings-span">模型名称<input aria-label="模型名称" required maxLength={120} value={model} disabled={disabled} onChange={e=>{initialized.current=true;setModel(e.target.value);setConsent(false);}} placeholder="输入你的账号可用的 model ID"/><small>由你填写，任何预设都不锁定名称；保存、测试并启用后可在输入区选择。</small></label>
 {protocol==='anthropic_messages'&&!fixed&&<label className="settings-span">认证方式<select aria-label="模型认证方式" value={auth} disabled={disabled} onChange={e=>{initialized.current=true;setAuth(e.target.value);setConsent(false);}}><option value="x_api_key">x-api-key</option><option value="bearer">Bearer Token</option></select></label>}
 <label className="settings-span">专用 API Key<input aria-label="专用模型 API Key" type="password" autoComplete="new-password" spellCheck={false} required minLength={8} maxLength={4096} value={key} disabled={disabled||!status?.connection_management} onChange={e=>{initialized.current=true;setKey(e.target.value);}} placeholder={status?.credential_configured?'已在后端配置；修改连接时重新输入':'输入专用 Key，仅本次后端内存'}/><small>提交后清空，不保存到浏览器。修改模型或连接需要重新测试。</small></label>
 </div><label className="settings-consent"><input aria-label="同意模型测试外发和估算" type="checkbox" checked={consent} disabled={disabled} onChange={e=>setConsent(e.target.checked)}/><span>同意向此服务发送固定非敏感测试文本，并接受每次 $0.25 估算预留（非实际单价）；不发送表行、历史或截图。</span></label>
 <div className="settings-actions"><button className="primary" type="submit" disabled={disabled||legacyModelLock||!status?.connection_management||!consent||!key||!endpoint||!model}>{busy?'保存中…':'保存连接（不调用模型）'}</button><button className="secondary" type="button" disabled={disabled||!status?.connection_management||!status?.credential_configured} onClick={()=>void clear()}>清除会话 Key</button></div></form>{notice&&<p className="settings-notice" role="status">{notice}</p>}
 <details className="settings-details"><summary>连接与凭证安全</summary><p>自定义地址只允许 HTTPS 公网；公司内网仅使用已授权的固定预设地址。支持三种标准协议，不保证任意私有 API 兼容。</p><p>Key仅在当前后端内存，不进日志、历史或浏览器存储；重启需重新输入。共享电脑仍有隐私风险，不复制宿主工具的认证。</p></details>
 </section>;
}
