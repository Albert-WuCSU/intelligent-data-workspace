import {useId} from 'react';
import type {SelectableModel} from './workbench';
import {resolveModel} from './workbench';

type Props={queryReady?:boolean;models:SelectableModel[];value:string;busy:boolean;onChange:(id:string)=>void;onConfigure:()=>void};
/** A real model catalog plugs in after onboarding. Unconfigured options stay unavailable. */
export default function ModelSelector({models,value,busy,onChange,onConfigure,queryReady=false}:Props){
 const id=useId();const usable=models.filter(model=>model.available);
 const selected=resolveModel(models,value);
 return <div className="model-picker"><label htmlFor={id}>模型</label><select id={id} aria-label="切换模型" value={selected?.id??''} disabled={busy||!usable.length} onChange={e=>{if(resolveModel(models,e.target.value))onChange(e.target.value);}}>
  <option value="" disabled>{usable.length?'请选择已启用模型':'未连接模型'}</option>
  {models.map(model=><option key={model.id} value={model.id} disabled={!model.available}>{model.label}{model.available?'':' · 不可选择'}</option>)}
 </select><button className="model-service-link" type="button" onClick={onConfigure} disabled={busy}>模型服务</button><span className="model-readiness">{selected?queryReady?'已选实测模型 · 显式同意后规划':'已选实测模型 · 问数尚未接入，不调用':'待接入 · 不调用模型'}</span></div>;
}
