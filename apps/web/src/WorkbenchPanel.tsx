import ModelServiceReadiness from './ModelServiceReadiness';
import {useEffect,useRef} from 'react';
import type {SourceProfile} from './api';
import type {ConversationAttachment} from './ChatFiles';
import type {Message} from './conversations';
import {workbenchEvidence} from './workbench';

type Props={messages:Message[];busy:boolean;sources:SourceProfile[];selectedSources:string[];sourcesError:boolean;attachments:ConversationAttachment[];onToggleSource:(id:string)=>void;showModelInfo:boolean;onClose:()=>void;onCloseModelInfo:()=>void;onConnect:()=>void};
export default function WorkbenchPanel({messages,busy,sources,selectedSources,sourcesError,attachments,onToggleSource,showModelInfo,onClose,onCloseModelInfo,onConnect}:Props){
 const evidence=workbenchEvidence(messages,busy);
 const modelInfo=useRef<HTMLElement>(null);
 useEffect(()=>{if(showModelInfo)modelInfo.current?.scrollIntoView({block:'nearest'});},[showModelInfo]);
 return <aside className="workbench-panel" aria-label="会话摘要"><header><div><span>CONVERSATION CONTEXT</span><h2>会话摘要</h2></div><button type="button" aria-label="收起会话摘要" onClick={onClose}>×</button></header>
  <section><h3>当前目标</h3><p className="summary-goal">{evidence.user?.text??'添加数据文件或描述问题，允许多个来源参与。'}</p><small>来源范围在右侧管理；选择多个来源不代表JOIN已执行。</small></section>
  <section><div className="summary-heading"><h3>任务进度</h3><span>{evidence.state}</span></div><ol className="summary-steps">{evidence.steps.map((step,i)=><li key={step.label}><span className="summary-step-number">{i+1}</span><div><strong>{step.label}</strong><small>{step.state}</small></div></li>)}</ol></section>
  <section aria-label="多来源上下文"><h3>来源与附件</h3><p>可选多个已接入来源；真正取数还需确认表及关联键，跨源JOIN尚待受控实现。</p>{sourcesError?<p>来源目录读取失败，请重新连接API。</p>:!sources.length?<p>尚无已保存数据库或MCP来源。</p>:<div className="context-source-list">{sources.map(source=><label key={source.id}><input type="checkbox" aria-label={`包含来源 ${source.name}`} checked={selectedSources.includes(source.id)} disabled={busy||!source.enabled} onChange={()=>onToggleSource(source.id)}/><span>{source.name}<small>{source.enabled?source.kind:'已禁用，不能加入'}</small></span></label>)}</div>}{attachments.length>0&&<ul className="context-attachment-list">{attachments.map(file=><li key={file.receipt.test_id}>{file.filename}<small>{file.receipt.tables.length}张表 · 本会话临时附件</small></li>)}</ul>}</section><section><h3>来源与证据</h3>{evidence.preview?<><p>本会话已收到真实只读预览回执。</p><dl><dt>数据来源</dt><dd>{evidence.preview.result.source==='independently_generated_synthetic'?'独立合成测试仓 · TEST':'实际来源'}</dd><dt>返回记录</dt><dd>{evidence.preview.result.returned_row_count} 行，最多100行预览</dd></dl><p>这是已有回执，不表示新问题已执行；预览不是完整数据资产。</p></>:<p>暂无查询来源回执；选择数据源不等于已经取数。</p>}
   {evidence.validation&&<details><summary>结构校验记录</summary><p>请求结构通过；业务语义和SQL执行未验证。</p></details>}
   {evidence.task&&<details><summary>测试任务记录</summary><p>{evidence.task.task.status} · {evidence.task.task.error?.code??'暂无执行器回执'}</p></details>}
  </section>
  <section><h3>结果与文件</h3><p>未生成可下载文件。会话文字只保存在此浏览器，API回执不跨刷新保留。</p></section>
  {showModelInfo&&<section ref={modelInfo} className="model-onboarding-info" aria-label="模型接入说明"><div className="summary-heading"><h3>模型服务与连接测试</h3><button type="button" aria-label="关闭模型接入说明" onClick={onCloseModelInfo}>×</button></div><p>应用尚无已验证、已授权的模型目录；下方最小生成测试不代表已取数。不会读取Claude Code或其他宿主工具的密钥。可在下方选择厂商、输入自己的Key。</p><p>使用本机专用Key和所选协议/模型候选（Claude或Responses入口），先完成最小生成测试；业务问数模型目录仍待接入。</p><p>本次估算预算目标为15美元、参考上限20美元。按每次0.25美元保守预留，最多60次；不是实际账单或硬费用保证。</p><p>仅显式点击测试才发送固定非敏感文本；不发送表行、全历史或截图。输入Key和刷新状态不会自动收费。</p><ModelServiceReadiness/></section>}
  <footer><button type="button" className="secondary" onClick={onConnect} disabled={busy}>管理数据源</button><small>只读摘要 · 不执行查询</small></footer>
 </aside>;
}
