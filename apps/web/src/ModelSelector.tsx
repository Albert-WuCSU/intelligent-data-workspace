import {useId} from 'react';
import type {SelectableModel} from './workbench';
import {resolveModel} from './workbench';

type Props={models:SelectableModel[];value:string;busy:boolean;onChange:(id:string)=>void;onConfigure:()=>void};
/** A real model catalog plugs in after onboarding. Unconfigured options stay unavailable. */
export default function ModelSelector({models,value,busy,onChange,onConfigure}:Props){
 const id=useId();const usable=models.filter(model=>model.available);
 const selected=resolveModel(models,value);
 return <div className="model-picker"><label htmlFor={id}>模型</label><select id={id} aria-label="切换模型" value={selected?.id??''} disabled={busy||!usable.length} onChange={e=>{if(resolveModel(models,e.target.value))onChange(e.target.value);}}>
  <option value="" disabled>未连接模型</option>
  {models.map(model=><option key={model.id} value={model.id} disabled={!model.available}>{model.label}{model.available?'':' · 未验证'}</option>)}
 </select><button className="model-service-link" type="button" onClick={onConfigure} disabled={busy}>模型服务</button><span className="model-readiness">{selected?'当前请求将使用所选模型':'待接入 · 不调用模型'}</span></div>;
}
