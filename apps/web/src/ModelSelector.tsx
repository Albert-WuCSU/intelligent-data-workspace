import {useEffect,useId,useMemo,useRef,useState} from 'react';
import type {SelectableModel} from './workbench';
import {filterModels,groupModels,resolveModel} from './workbench';

type Props={queryReady?:boolean;models:SelectableModel[];value:string;busy:boolean;onChange:(id:string)=>void;onConfigure:()=>void};
const sourceLabel:Record<string,string>={personal_api:'个人 API',ai_plan:'企业 AI Plan'};

function statusLabel(model:SelectableModel){
 if(model.available)return '可用';
 if(!model.enabled)return '未启用';
 if(!model.generationVerified)return '未验证';
 return '暂不可用';
}

/** Server-catalog-only model picker. Selection never invokes a model. */
export default function ModelSelector({models,value,busy,onChange,onConfigure,queryReady=false}:Props){
 const id=useId();
 const root=useRef<HTMLDivElement>(null);
 const trigger=useRef<HTMLButtonElement>(null);
 const search=useRef<HTMLInputElement>(null);
 const [open,setOpen]=useState(false);
 const [query,setQuery]=useState('');
 const [active,setActive]=useState(-1);
 const selected=resolveModel(models,value);
 const usable=models.filter(model=>model.available);
 const filtered=useMemo(()=>filterModels(models,query),[models,query]);
 const groups=groupModels(filtered);
 const flat=groups.flatMap(group=>group.models);

 useEffect(()=>{
  if(!open)return;
  const listener=(event:PointerEvent)=>{if(root.current&&!root.current.contains(event.target as Node))setOpen(false);};
  document.addEventListener('pointerdown',listener);
  requestAnimationFrame(()=>search.current?.focus());
  return()=>document.removeEventListener('pointerdown',listener);
 },[open]);

 useEffect(()=>{setActive(-1);},[query,open]);

 function choose(model:SelectableModel){
  if(!model.available||busy)return;
  onChange(model.id);
  setOpen(false);setQuery('');trigger.current?.focus();
 }
 function onKeyDown(event:React.KeyboardEvent){
  if(event.key==='Escape'){setOpen(false);trigger.current?.focus();return;}
  if(event.key==='ArrowDown'){event.preventDefault();setActive(current=>Math.min(current+1,flat.length-1));return;}
  if(event.key==='ArrowUp'){event.preventDefault();setActive(current=>Math.max(current-1,0));return;}
  if(event.key==='Enter'&&active>=0&&flat[active]){event.preventDefault();choose(flat[active]);}
 }
 return <div className="model-picker" ref={root}>
  <button ref={trigger} type="button" className="model-picker-trigger" aria-label="切换模型" aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} disabled={busy||!usable.length} onClick={()=>setOpen(current=>!current)} onKeyDown={event=>{if(event.key==='ArrowDown'){event.preventDefault();setOpen(true);}}}>
   <span className="model-picker-name">{selected?selected.label:(usable.length?'选择模型':'未连接模型')}</span>
   {selected&&<span className={`model-picker-status ${selected.available?'ok':''}`}>{statusLabel(selected)}</span>}
   <span className="model-picker-chevron" aria-hidden="true">▾</span>
  </button>
  {open&&<div className="model-picker-popover" onKeyDown={onKeyDown}>
   <div className="model-picker-head"><span>选择模型</span><small>只显示服务端目录；选择不调用模型</small></div>
   <label className="model-picker-search"><span className="sr-only">搜索模型</span><input ref={search} aria-label="搜索模型" placeholder="搜索模型名称…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
   <div id={`${id}-list`} role="listbox" aria-label="可用模型" className="model-picker-list">
    {!flat.length&&<p className="model-picker-empty">没有匹配的模型。请先在“模型服务”中添加并测试模型。</p>}
    {groups.map(group=><section key={group.source} className="model-picker-group" aria-label={sourceLabel[group.source]}>
     <h4>{sourceLabel[group.source]}</h4>
     {group.models.map(model=>{
      const index=flat.indexOf(model);
      const disabled=!model.available||busy;
      return <button key={model.id} type="button" role="option" aria-selected={model.id===selected?.id} aria-disabled={disabled} className={`model-option ${model.id===selected?.id?'selected':''} ${index===active?'active':''}`} disabled={disabled} onMouseEnter={()=>setActive(index)} onClick={()=>choose(model)}>
       <span className="model-option-main"><span className="model-option-label">{model.label}</span>{model.default&&<span className="model-badge">默认</span>}<span className={`model-option-status ${model.available?'ok':''}`}>{statusLabel(model)}</span></span>
       <span className="model-option-meta"><span>{model.modelId??model.label}</span><span>{model.contextWindow?`${Math.round(model.contextWindow/1000)}K 上下文`:'上下文未知'}</span><span>{model.priceNote??'价格未知'}</span></span>
       {model.note&&<span className="model-option-note">{model.note}</span>}
      </button>;
     })}
    </section>)}
   </div>
   <div className="model-picker-foot"><button type="button" className="model-service-link" onClick={onConfigure} disabled={busy}>管理模型服务</button><span>{selected?queryReady?'已选模型 · 显式同意后规划':'已选模型 · 问数尚未接入，不调用':'选择模型不调用模型'}</span></div>
  </div>}
  <button className="model-service-link" type="button" onClick={onConfigure} disabled={busy}>模型服务</button>
  <span className="model-readiness">{selected?queryReady?'已选实测模型 · 显式同意后规划':'已选实测模型 · 问数尚未接入，不调用':'待接入 · 不调用模型'}</span>
 </div>;
}
