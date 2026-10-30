import {useState} from 'react';
import {ApiError,request} from './api';
import type {ModelServiceStatus} from './api';
type Protocol='openai_responses'|'openai_chat_completions'|'anthropic_messages';
const presets={
 openai:{label:'OpenAI',protocol:'openai_responses',endpoint:'https://api.openai.com/v1/responses',model:'gpt-4.1-mini',auth:'bearer'},
 deepseek:{label:'DeepSeek 官方',protocol:'openai_chat_completions',endpoint:'https://api.deepseek.com/chat/completions',model:'deepseek-chat',auth:'bearer'},
 anthropic:{label:'Anthropic',protocol:'anthropic_messages',endpoint:'https://api.anthropic.com/v1/messages',model:'claude-haiku-4-5',auth:'x_api_key'},
 ai_plan:{label:'公司 AI Plan（已授权内网）',protocol:'anthropic_messages',endpoint:'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages',model:'deepseek-v4.1-flash',auth:'bearer'},
 custom:{label:'自定义兼容服务',protocol:'openai_chat_completions',endpoint:'',model:'',auth:'bearer'},
} as const;
export default function ModelConnectionForm({status,blocked,onChanged}:{status:ModelServiceStatus|null;blocked:boolean;onChanged:()=>Promise<void>}){
 const [vendor,setVendor]=useState<keyof typeof presets>('openai'),[protocol,setProtocol]=useState<Protocol>('openai_responses'),[endpoint,setEndpoint]=useState<string>(presets.openai.endpoint),[model,setModel]=useState<string>(presets.openai.model),[auth,setAuth]=useState('bearer'),[key,setKey]=useState(''),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const fixed=vendor==='ai_plan',disabled=blocked||busy;
 function choose(v:keyof typeof presets){const p=presets[v];setVendor(v);setProtocol(p.protocol);setEndpoint(p.endpoint);setModel(p.model);setAuth(p.auth);setKey('');setConsent(false);setNotice('');}
 async function save(e:React.FormEvent){e.preventDefault();if(!status||!key||!consent)return;setBusy(true);setNotice('');try{
  await request('/api/v1/model-service/connection',{preset:fixed?'ai_plan':'custom',protocol,endpoint,model_id:model,authentication:auth,api_key:key,execution_generation:status.execution_generation,accept_fixed_test_egress:true,accept_estimated_cost:true});
  setNotice('已保存到本次后端会话，未收费调用。请点击下方“测试模型连接”。');await onChanged();
 }catch(error){setNotice(error instanceof ApiError?`${error.code} · ${error.message}`:'连接配置未保存，请刷新状态后再试。');}finally{setKey('');setBusy(false);}}
 async function clear(){if(!status)return;setBusy(true);setKey('');try{await request('/api/v1/model-service/connection/clear',{execution_generation:status.execution_generation});setNotice('Key已清除，预算预留保留。');await onChanged();}catch(e){setNotice(e instanceof ApiError?e.message:'清除未完成，请刷新。');}finally{setBusy(false);}}
 return <section aria-label="快捷模型接入"><h3>连接自己的模型 API</h3><p>选择厂商预设或自定义标准协议；预设名称不代表你的账号已授权或模型已验证。无需终端输 Key。</p>{!status?.connection_management&&<p role="status">当前后端未加载快捷接入接口；更新服务后刷新，不要在旧页面提交 Key。</p>}
 <form onSubmit={e=>void save(e)} autoComplete="off"><label>厂商／服务<select aria-label="模型服务厂商" value={vendor} disabled={disabled} onChange={e=>choose(e.target.value as keyof typeof presets)}>{Object.entries(presets).map(([v,p])=><option value={v} key={v}>{p.label}</option>)}</select></label>
 <label>协议<select aria-label="模型 API 协议" value={protocol} disabled={disabled||fixed} onChange={e=>{const p=e.target.value as Protocol;setProtocol(p);setAuth(p==='anthropic_messages'?'x_api_key':'bearer');setConsent(false);}}><option value="openai_responses">OpenAI Responses</option><option value="openai_chat_completions">OpenAI-compatible Chat Completions</option><option value="anthropic_messages">Anthropic Messages</option></select></label>
 <label>完整 API 地址<input aria-label="模型 API 地址" type="url" required maxLength={512} value={endpoint} disabled={disabled||fixed} onChange={e=>{setEndpoint(e.target.value);setConsent(false);}} placeholder="https://你的域名/v1/chat/completions"/></label>
 <label>模型名称<input aria-label="模型名称" required maxLength={120} value={model} disabled={disabled||fixed} onChange={e=>setModel(e.target.value)} placeholder="供应商实际提供的 model ID"/></label>
 {protocol==='anthropic_messages'&&!fixed&&<label>认证方式<select aria-label="模型认证方式" value={auth} disabled={disabled} onChange={e=>setAuth(e.target.value)}><option value="x_api_key">x-api-key</option><option value="bearer">Bearer Token</option></select></label>}
 <label>专用 API Key<input aria-label="专用模型 API Key" type="password" autoComplete="new-password" spellCheck={false} required minLength={8} maxLength={4096} value={key} disabled={disabled||!status?.connection_management} onChange={e=>setKey(e.target.value)} placeholder="仅本次后端内存，不保存到浏览器"/></label>
 <label><input aria-label="同意模型测试外发和估算" type="checkbox" checked={consent} disabled={disabled} onChange={e=>setConsent(e.target.checked)}/>同意向此服务发送固定非敏感测试文本，并接受每次 $0.25 估算预留（非厂商单价或费用保证）；不发数据行、历史、截图</label>
 <p>自定义服务只允许 HTTPS 公网，私有协议需另适配。Key只通过本机请求发送给后端，提交后密码框清空；不进日志、历史或浏览器存储，后端重启需重输。共享电脑仍需注意隐私。</p>
 <button className="primary" type="submit" disabled={disabled||!status?.connection_management||!consent||!key||!endpoint||!model}>{busy?'保存中…':'保存连接（不调用模型）'}</button>
 <button className="secondary" type="button" disabled={disabled||!status?.connection_management||!status?.credential_configured} onClick={()=>void clear()}>清除会话 Key</button></form>{notice&&<p role="status">{notice}</p>}
 </section>;
}
