import {useEffect,useRef,useState} from 'react';
import {ApiError,request} from './api';
import type {ModelServiceStatus,StreamTestReceipt} from './api';
export default function ModelStreamTest({status,blocked,onBusy,onChanged}:{status:ModelServiceStatus|null;blocked:boolean;onBusy:(busy:boolean)=>void;onChanged:()=>Promise<void>}){
 const [receipt,setReceipt]=useState<StreamTestReceipt|null>(null),[busy,setBusy]=useState(false),[accepted,setAccepted]=useState(false),[error,setError]=useState('');
 const pending=useRef<{request_id:string;execution_generation:string;config_version:string;accept_estimated_cost:true}|null>(null),mounted=useRef(true);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{onBusy(busy);},[busy,onBusy]);
 useEffect(()=>{if(pending.current&&status&&pending.current.execution_generation!==status.execution_generation){pending.current=null;setReceipt(null);setAccepted(false);setError('');}},[status?.execution_generation]);
 async function readUntilDone(id:string){for(let i=0;i<45&&mounted.current;i++){const value=await request<StreamTestReceipt>(`/api/v1/model-service/stream-tests/${id}`);if(!mounted.current)return;setReceipt(value);if(value.status!=='running')return;await new Promise(resolve=>setTimeout(resolve,500));}throw new Error('unknown');}
 async function start(){if(!status||busy||blocked||!accepted||(!status.stream_available&&!pending.current))return;setBusy(true);setError('');
  if(!pending.current)pending.current={request_id:crypto.randomUUID(),execution_generation:status.execution_generation,config_version:status.config_version,accept_estimated_cost:true};
  try{const id=pending.current.request_id;if(!receipt)await request<StreamTestReceipt>('/api/v1/model-service/stream-test',pending.current);await readUntilDone(id);}catch(e){setError(e instanceof ApiError?`${e.code} · ${e.message}`:'流式通信未确认，预留或调用可能已发生；保留同一编号，可读取回执或取消，不自动重试。');}finally{await onChanged();if(mounted.current)setBusy(false);}
 }
 async function cancel(){if(!pending.current)return;try{const value=await request<StreamTestReceipt>(`/api/v1/model-service/stream-tests/${pending.current.request_id}/cancel`,{});setReceipt(value);}catch{setError('取消未确认，请读取同一回执；不会自动重新调用模型。');}}
 const text=(receipt?.events??[]).filter(e=>e.kind==='text_delta').map(e=>e.text).join('');
 return <section className="settings-card" aria-label="真实流式连接测试"><header><h3>流式测试</h3><p>验证逐步返回的固定测试文本，不是业务问题或 SQL 调用。</p></header>
 {!status?.stream_management?<p>当前后端未加载流式测试，请更新服务后刷新。</p>:!status.stream_available&&!pending.current?<p>{status.protocol==='anthropic_messages'?'先配置有效模型连接与预算。':'当前仅 Messages 协议支持流式测试，其他协议待适配，不自动切换。'}</p>:<><label className="settings-consent"><input type="checkbox" aria-label="同意固定文本流式测试" checked={accepted} disabled={busy||blocked} onChange={e=>setAccepted(e.target.checked)}/><span>仅发送固定非敏感文本，接受一次 $0.25 估算预留；取消/未知结果不退回预留。</span></label><div className="settings-actions"><button type="button" className="primary" disabled={!accepted||busy||blocked} onClick={()=>void start()}>{pending.current?'读取同一流式回执':'开始流式测试（估算 $0.25）'}</button>{pending.current&&<button type="button" className="secondary" disabled={receipt?.status!=='running'&&!busy} onClick={()=>void cancel()}>取消流式测试</button>}</div></>}
 <p className="settings-state">{busy?'等待真实上游事件…':status?.stream_verified?'当前配置流式已验证':'当前配置流式未验证'}</p>{error&&<p role="alert">{error}</p>}
 {receipt&&<div aria-label="流式测试回执"><p role="status">{receipt.status==='succeeded'?'流式完成已确认 · SQL未执行':receipt.status==='running'?'请求进行中；完成尚未确认':receipt.status==='partial'?`部分输出，未完成 · ${receipt.error_code??'结果未知'}`:`流式未完成 · ${receipt.error_code??'结果未知'}`}</p>{text&&<pre>{text}</pre>}{receipt.diagnostics&&<p aria-label="流式安全诊断">诊断：{receipt.diagnostics.reason}{receipt.diagnostics.upstream_status?` · HTTP ${receipt.diagnostics.upstream_status}`:''}。不显示远程错误正文、思考或Key；读取同一回执不会重新调用。</p>}<small>这是当前上游事件的只读快照；安全检查可能延迟释放短文本，不用动画伪造输出。</small><details className="settings-details"><summary>流式请求追踪</summary><code>{receipt.request_id}</code><p>估算而非实际费用；本次后端内存，重启丢失；不显示思考或工具内容。</p></details></div>}
 </section>;
}
