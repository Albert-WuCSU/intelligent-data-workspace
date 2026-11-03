import {useEffect,useRef} from 'react';
import ModelServiceReadiness from './ModelServiceReadiness';

export default function SettingsWorkspace({onBack,onBusy,busy}:{onBack:()=>void;busy:boolean;onBusy:(busy:boolean)=>void}){
 const heading=useRef<HTMLHeadingElement>(null);useEffect(()=>{heading.current?.focus();},[]);
 return <section className="settings-workspace" aria-label="设置页面">
  <div className="settings-layout">
   <aside className="settings-navigation" aria-label="设置分类"><span className="settings-eyebrow">PREFERENCES</span><h1>设置</h1><div className="settings-category" aria-current="page"><span aria-hidden="true">◈</span>模型服务</div><p>配置你的模型连接，<br/>工作台只保留模型选择。</p></aside>
   <div className="settings-content"><header className="settings-header"><div><h2 ref={heading} tabIndex={-1}>模型服务</h2><p>连接自己的 API，自由填写模型名称。</p></div><button className="secondary" type="button" disabled={busy} onClick={onBack}>返回工作台</button></header>
    <div className="settings-boundary">保存配置不会调用模型。测试通过并启用后，可在对话输入区选择；业务问数仍未接入。</div>
    <ModelServiceReadiness onBusy={onBusy}/>
   </div>
  </div>
 </section>;
}
