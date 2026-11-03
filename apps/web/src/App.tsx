import { PreviewCard } from './ConnectorWorkspace';
import DataSourceWorkspace from './DataSourceWorkspace';
import WorkbenchPanel from './WorkbenchPanel';
import ModelSelector from './ModelSelector';
import SettingsWorkspace from './SettingsWorkspace';
import KnowledgeWorkspace from './KnowledgeWorkspace';
import AgentTaskCard,{AgentPipeline} from './AgentTaskCard';
import type {AgentTask,AgentTasks,AgentCapabilities,AgentRequest,SemanticList,PublishedSemantic} from './api';
import type {ModelCatalog} from './api';
import type {SelectableModel} from './workbench';
import {ChatFilePicker,ChatFileCard} from './ChatFiles';
import type { QueryPreview, PreviewReceipt } from './api';
import { useEffect, useRef, useState } from 'react';
import { ApiError, example, request, uploadFile } from './api';
import type { Capabilities, Session, Task, Validation, SourceProfileList, SourceProfile, FileReceipt, TestedDraft } from './api';
import { appendMessages, browserStorage, loadConversations, loadTheme, MAX_MESSAGES, MAX_TEXT, MAX_THREADS, messageBase, newConversation, saveConversations, storageKey, storeTheme } from './conversations';
import type { Conversation, Message, Theme } from './conversations';

const pages=[['query','取数工作台'],['connectors','连接器'],['knowledge','知识库'],['assets','数据资产'],['dashboards','可视化看板'],['reports','分析报告']] as const;
type Page=typeof pages[number][0]|'settings';
function Icon({name,size=19}:{name:string;size?:number}){
 const paths:Record<string,string>={settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3',query:'M4 4h16v12H9l-5 4V4zm4 5h8m-8 4h5',connectors:'M8 3v5m8-5v5M6 8h12v4a6 6 0 0 1-6 6v3m0-3a6 6 0 0 1-6-6',knowledge:'M4 4h6l2 2 2-2h6v15h-6l-2 2-2-2H4V4zm8 2v15',assets:'M4 6c0-4 16-4 16 0v12c0 4-16 4-16 0V6zm0 0c0 4 16 4 16 0M4 12c0 4 16 4 16 0',dashboards:'M4 4h7v7H4V4zm10 0h6v7h-6V4zM4 14h7v6H4v-6zm10 0h6v6h-6v-6',reports:'M6 3h9l4 4v14H6V3zm9 0v5h4M9 12h7m-7 4h5',plus:'M12 5v14M5 12h14',arrow:'M12 19V5m-5 5 5-5 5 5',check:'m5 12 4 4 10-10',refresh:'M20 6v5h-5M4 18v-5h5m11-2a8 8 0 0 0-14-5M4 13a8 8 0 0 0 14 5',shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3',sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm0-5v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17m10-10 1.4-1.4',moon:'M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z',close:'m6 6 12 12M6 18 18 6',trash:'M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6m4-6v6',tool:'m8 6-5 6 5 6m8-12 5 6-5 6M14 4l-4 16',menu:'M4 6h16M4 12h16M4 18h16',clock:'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm0 4v5l3 2',chevron:'m9 5 7 7-7 7'};
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]||paths.query}/></svg>;
}
function time(s:string){return new Date(s).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Shanghai'});}
function Pipeline({message,busy=false}:{message:Message|undefined;busy?:boolean}){
 const real=message?.kind==='preview';
 const attempted=message?.kind==='unavailable'||message?.kind==='task';
 const labels=['口径确认','数据检索','SQL 执行','结果校验'];
 return <section className="pipeline" aria-label="执行进度"><div className="pipeline-label"><span className="live-square"/>执行进度<small>CURRENT REQUEST</small></div><ol>{labels.map((label,i)=><li key={label} className={attempted&&i===0?'blocked':''}><span className="step-index">0{i+1}</span><div>{label}<small>{busy?['开发模板已确认','MCP 已连接','等待执行回执','尚未完成'][i]:real?['开发模板','真实元数据','SQL 已执行','预览已返回'][i]:attempted?(i===0?'待接入':'未执行'):'等待请求'}</small></div>{i<3&&<Icon name="chevron" size={13}/>}</li>)}</ol><span className="pipeline-note">{busy?'等待真实回执':real?'合成数据 · 非口径认证':message?.kind==='validation'?'结构已验证 · 不代表查询完成':'自然语言执行待接入'}</span></section>;
}
function ResultCard({message}:{message:Message}){
 if(message.kind==='user')return <div className="user-message"><div className="user-label">你 <time>{time(message.createdAt)}</time></div><p>{message.text}</p></div>;
 return <article className="assistant-message" aria-label="助手输出"><div className="assistant-avatar"><Icon name="assets"/></div><div className="assistant-body"><div className="assistant-meta"><strong>数据助手</strong><span>{message.kind==='unavailable'?'本地能力提示':message.kind==='error'?'接口反馈':'开发验证结果'}</span><time>{time(message.createdAt)}</time></div>
 {message.kind==='unavailable'&&<><p className="answer-intro">这条请求还不能执行，取数 Agent 尚未接入；本条自然语言请求未访问数据源。</p><div className="result-card"><div className="result-header"><span className="result-status amber">未执行</span><strong>没有查询结果，也没有生成 SQL</strong></div><p>{message.text}</p><div className="evidence-grid"><div><small>请求处理</small><span>仅保存到本地会话</span></div><div><small>数据来源</small><span>未访问数仓</span></div><div><small>质量检查</small><span>未运行</span></div></div><details><summary>能力边界与技术信息</summary><p>这是一条本地规则提示，不是模型回答。M02 接入元数据和执行服务，M04 接入理解、澄清及受控取数；当前不会自动把你的问题映射为指标或猜测字段。</p></details></div><p className="answer-next">下一步：可查看连接器的接入状态，或在开发工具中验证结构化接口。</p></>}
 {message.kind==='validation'&&<><p className="answer-intro">结构化请求通过了接口校验。业务口径、权限与执行结果尚未验证。</p><div className="result-card"><div className="result-header"><span className="result-status green">结构通过</span><strong>请求摘要</strong></div><div className="scope-list"><div><span>目标</span><strong>{message.spec.target.kind==='metric'?message.spec.target.metric_refs.map(m=>`${m.id} · ${m.version}`).join('、'):message.spec.target.full_table_name}</strong></div><div><span>时间</span><strong>{message.spec.time_range.start} 至 {message.spec.time_range.end_exclusive}（不含结束日）</strong></div><div><span>时区</span><strong>{message.spec.timezone}</strong></div><div><span>分组</span><strong>{message.spec.dimensions?.join('、')||'未指定'}</strong></div></div><div className="quality-strip"><Icon name="shield" size={16}/><span>仅验证结构 · 未确认业务口径 · 未执行 SQL</span></div><details><summary>QuerySpec 与接口详情</summary><pre>{JSON.stringify(message.spec,null,2)}</pre><p>{message.note}</p></details></div></>}
 {message.kind==='task'&&<><p className="answer-intro">测试任务已登记，但未配置执行器，因此没有执行查询。</p><div className="result-card"><div className="result-header"><span className="result-status amber">未执行 · {message.task.status}</span><strong>任务反馈</strong></div><p>{message.task.error?.safe_message}</p><div className="evidence-grid"><div><small>数据结果</small><span>未生成</span></div><div><small>质量检查</small><span>未运行</span></div><div><small>运行记录</small><span>API 内存仓储</span></div></div><details><summary>任务编号与技术信息</summary><dl><dt>任务编号</dt><dd>{message.task.task_id}</dd><dt>错误类型</dt><dd>{message.task.error?.code}</dd><dt>追踪编号</dt><dd>{message.task.trace_id}</dd></dl><p>任务记录重启丢失；会话中的开发验证输出仅在本次页面内保留。</p></details></div></>}
 {message.kind==='attachment'&&<ChatFileCard attachment={message}/> }
 {message.kind==='preview'&&<PreviewCard result={message.result} receipt={message.receipt}/>}
 {message.kind==='error'&&<div className="result-card"><div className="result-header"><span className="result-status amber">请求未完成</span><strong>请检查请求或连接</strong></div><p>{message.text}</p><details><summary>接口反馈详情</summary><p>{message.code}</p><p>{message.traceId}</p></details></div>}
 </div></article>;
}
export default function App(){
 const [page,setPage]=useState<Page>(()=>location.hash.slice(1)==='settings'||pages.some(p=>p[0]===location.hash.slice(1))?location.hash.slice(1) as Page:'query');
 const [theme,setTheme]=useState<Theme>(()=>loadTheme(browserStorage));
 const [session,setSession]=useState<Session|null>(null),[caps,setCaps]=useState<Capabilities|null>(null);
 const [connection,setConnection]=useState<'loading'|'online'|'error'>('loading'),[problem,setProblem]=useState<ApiError|null>(null);
 const [threads,setThreads]=useState<Conversation[]>([]),[activeId,setActiveId]=useState<string|null>(null),[key,setKey]=useState<string|null>(null);
 const [draft,setDraft]=useState(''),[notice,setNotice]=useState(''),[privacy,setPrivacy]=useState(false),[mobileNav,setMobileNav]=useState(false);
 const [toolOpen,setToolOpen]=useState(false),[editor,setEditor]=useState(JSON.stringify(example,null,2)),[toolBusy,setToolBusy]=useState(false),[schemaMode,setSchemaMode]=useState(false);
 const [toolError,setToolError]=useState<ApiError|null>(null),[lastTask,setLastTask]=useState<Task|null>(null);
 const [previewBusy,setPreviewBusy]=useState(false);
 const [summaryOpen,setSummaryOpen]=useState(()=>window.innerWidth>=1100);
 const [settingsBusy,setSettingsBusy]=useState(false),[semanticBusy,setSemanticBusy]=useState(false);
 const navigationState=useRef({page,busy:settingsBusy});navigationState.current={page,busy:settingsBusy||semanticBusy};
 const [sourceChoices,setSourceChoices]=useState<SourceProfile[]>([]),[contexts,setContexts]=useState<Record<string,string[]>>({}),[sourcesError,setSourcesError]=useState(false);
 const [attachmentBusy,setAttachmentBusy]=useState(false);
 const [agentAvailable,setAgentAvailable]=useState(false),[agentSubmitting,setAgentSubmitting]=useState(false),[agentTasks,setAgentTasks]=useState<AgentTask[]>([]),[semanticChoices,setSemanticChoices]=useState<PublishedSemantic[]>([]),[selectedSemantic,setSelectedSemantic]=useState(''),[agentConsent,setAgentConsent]=useState(false);
 const pendingAgent=useRef<AgentRequest|null>(null);
 const currentAgentTask=agentTasks.filter(t=>t.conversation_id===activeId).at(-1);
 const agentRunning=!!currentAgentTask&&['PLANNING','VALIDATING','EXECUTING','CHECKING'].includes(currentAgentTask.phase);
 const workBusy=previewBusy||attachmentBusy||settingsBusy||semanticBusy||agentSubmitting||agentRunning;
 // Only authenticated server catalog; host aliases never establish availability.
 const [selectedModel,setSelectedModel]=useState('');
 const [modelChoices,setModelChoices]=useState<SelectableModel[]>([]);
 useEffect(()=>{if(connection!=='online'){setModelChoices([]);setSelectedModel('');return;}let active=true,inFlight=false;
  async function refreshCatalog(){if(inFlight)return;inFlight=true;try{const value=await request<ModelCatalog>('/api/v1/model-service/catalog');if(active){const models=value.models.map(m=>({id:m.id,label:m.model_id,available:m.available,note:'仅模型连接；问数待接入'}));setModelChoices(models);setSelectedModel(old=>models.some(m=>m.id===old&&m.available)?old:'');}}catch{if(active){setModelChoices([]);setSelectedModel('');}}finally{inFlight=false;}}
  void refreshCatalog();const timer=window.setInterval(()=>void refreshCatalog(),2000);const changed=()=>void refreshCatalog();window.addEventListener('model-catalog-changed',changed);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('model-catalog-changed',changed);};
 },[connection]);
 useEffect(()=>{if(connection!=='online'){setAgentAvailable(false);setAgentTasks([]);return;}let active=true,inFlight=false;
  async function update(){if(inFlight)return;inFlight=true;try{const cap=await request<AgentCapabilities>('/api/v1/agent/capabilities');if(!active)return;setAgentAvailable(cap.available);if(cap.available){const [tasks,semantics]=await Promise.all([request<AgentTasks>('/api/v1/agent/tasks'),request<SemanticList>('/api/v1/semantics')]);if(active){setAgentTasks(tasks.tasks);setSemanticChoices(semantics.versions.filter(v=>v.state==='published_recheck_required'));}}}catch{if(active){setAgentAvailable(false);setAgentTasks([]);}}finally{inFlight=false;}}
  void update();const timer=window.setInterval(()=>void update(),800);return()=>{active=false;clearInterval(timer);};
 },[connection]);
 useEffect(()=>{setAgentConsent(false);},[selectedModel,selectedSemantic,activeId]);
 useEffect(()=>{if(connection!=='online')return;let active=true;
  request<SourceProfileList>('/api/v1/source-profiles').then(value=>{if(active){setSourceChoices(value.profiles);setSourcesError(false);setContexts(previous=>Object.fromEntries(Object.entries(previous).map(([id,refs])=>[id,refs.filter(ref=>value.profiles.some(profile=>profile.id===ref&&profile.enabled))])));}}).catch(()=>{if(active){setSourcesError(true);setSourceChoices([]);setContexts({});}});
  return()=>{active=false;};
 },[connection,page]);
 useEffect(()=>{setContexts({});setSelectedModel('');setSourceChoices([]);},[key]);
 const selectedSources=activeId?contexts[activeId]??[]:[];
 function toggleSource(id:string){const thread=ensureThread();if(!thread||!sourceChoices.some(source=>source.id===id&&source.enabled))return;setContexts(previous=>{const values=previous[thread]??[];return {...previous,[thread]:values.includes(id)?values.filter(value=>value!==id):[...values,id].slice(0,8)};});}
 async function importAttachment(file:File){
  if(attachmentBusy||toolBusy||workBusy)throw new Error('请等待当前操作结束。');
  if(file.size>20*1024*1024||!file.size)throw new Error('文件必须为20MB以内的非空数据文件。');
  const thread=ensureThread();if(!thread)throw new Error('无法创建会话。');
  const attached=threads.find(t=>t.id===thread)?.messages.filter(m=>m.kind==='attachment').length??0;
  if((threads.find(t=>t.id===thread)?.messages.length??0)>=MAX_MESSAGES-1)throw new Error('此会话已满，请新建会话。');
  if(attached>=4)throw new Error('本机MVP每会话最多4个附件；请新建会话。');
  setAttachmentBusy(true);
  try{const upload=await uploadFile<FileReceipt>('/api/v1/source-profiles/upload',file);const tested=await request<TestedDraft>('/api/v1/source-profiles/test',{kind:'local_file',name:file.name.slice(0,80),file_id:upload.file_id,usage_authorized:true},30000);add(thread,[{...messageBase(),kind:'attachment',filename:file.name.slice(0,120),receipt:tested}]);setSummaryOpen(true);}
  finally{setAttachmentBusy(false);}
 }

 const [confirmDelete,setConfirmDelete]=useState<'all'|string|null>(null);
 const scroller=useRef<HTMLDivElement>(null),input=useRef<HTMLTextAreaElement>(null),toolPanel=useRef<HTMLElement>(null),previousFocus=useRef<HTMLElement|null>(null);
 const loadedScope=useRef<string|null>(null),toolLock=useRef(false);
 const current=threads.find(t=>t.id===activeId);
 useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;storeTheme(browserStorage,theme);},[theme]);
 async function connect(){
  setConnection('loading');setProblem(null);
  try{
   const [s,c]=await Promise.all([request<Session>('/api/v1/session'),request<Capabilities>('/api/v1/capabilities')]);
   // Browser history is only enabled for the explicit development identity.
   const scoped=s.identity.mode==='development'?storageKey(s.identity.tenant_id,s.identity.principal_id):null;
   if(scoped!==loadedScope.current){
    setThreads(scoped?loadConversations(browserStorage,scoped):[]);setActiveId(null);setDraft('');setLastTask(null);loadedScope.current=scoped;
   }
   setSession(s);setCaps(c);setKey(scoped);setConnection('online');
  }catch(e){setSession(null);setCaps(null);setKey(null);setConnection('error');setProblem(e as ApiError);setThreads([]);setActiveId(null);loadedScope.current=null;}
 }
 useEffect(()=>{void connect();const f=()=>{const p=location.hash.slice(1)||'query',nav=navigationState.current;if(nav.busy&&p!==nav.page){history.replaceState(null,'',`#${nav.page}`);return;}if(p==='settings'||pages.some(x=>x[0]===p))setPage(p as Page);};window.addEventListener('hashchange',f);return()=>window.removeEventListener('hashchange',f);},[]);
 useEffect(()=>{if(key&&connection==='online'&&!saveConversations(browserStorage,key,threads))setNotice('浏览器无法保存历史，本次会话仍可使用。');},[threads,key,connection]);
 useEffect(()=>{scroller.current?.scrollTo({top:scroller.current.scrollHeight,behavior:'smooth'});},[activeId,current?.messages.length]);
 useEffect(()=>{
  if(!toolOpen)return;
  previousFocus.current=document.activeElement as HTMLElement;
  requestAnimationFrame(()=>toolPanel.current?.querySelector<HTMLElement>('button')?.focus());
  const keydown=(e:KeyboardEvent)=>{
   if(e.key==='Escape'&&!toolLock.current){setToolOpen(false);previousFocus.current?.focus();}
   if(e.key==='Tab'){
    const controls=toolPanel.current?.querySelectorAll<HTMLElement>('button:not([disabled]),textarea:not([disabled])');
    if(!controls?.length)return;const first=controls[0],last=controls[controls.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
   }
  };document.addEventListener('keydown',keydown);return()=>document.removeEventListener('keydown',keydown);
 },[toolOpen]);
 useEffect(()=>{
  if(!confirmDelete)return;
  const before=document.activeElement as HTMLElement;
  const panel=document.querySelector<HTMLElement>('.confirm-dialog');
  panel?.querySelector<HTMLElement>('button')?.focus();
  const listener=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){setConfirmDelete(null);before?.focus();}
   if(e.key==='Tab'){
    const controls=panel?.querySelectorAll<HTMLElement>('button');if(!controls?.length)return;
    const first=controls[0],last=controls[controls.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
   }
  };document.addEventListener('keydown',listener);return()=>document.removeEventListener('keydown',listener);
 },[confirmDelete]);
 function navigate(p:Page){if(settingsBusy||semanticBusy)return;location.hash=p;setPage(p);setMobileNav(false);setNotice('');}
 function selectThread(id:string){setActiveId(id);setDraft('');navigate('query');}
 function startNew(){setActiveId(null);setDraft('');setNotice('');navigate('query');input.current?.focus();}
 function ensureThread():string|null{
  if(activeId&&threads.some(t=>t.id===activeId))return activeId;
  if(threads.length>=MAX_THREADS){setNotice(`已达到 ${MAX_THREADS} 个会话上限，请先删除不需要的会话。`);return null;}
  const thread=newConversation();setThreads(prev=>[thread,...prev]);setActiveId(thread.id);return thread.id;
 }
 function add(id:string,messages:Message[]){setThreads(prev=>appendMessages(prev,id,messages));}
 async function send(){
  const text=draft.trim();if(!text||connection!=='online'||toolBusy||workBusy)return;
  if((current?.messages.length||0)>MAX_MESSAGES-2){setNotice('此会话已达到消息上限，请新建会话；原记录不会被自动删除。');return;}
  if(agentAvailable&&!selectedSemantic){setNotice('请先选择已发布、启用的问数口径；可在知识库维护定义。未调用模型或执行SQL。');return;}
  const id=ensureThread();if(!id)return;
  if(agentAvailable&&selectedSemantic){
   const semantic=semanticChoices.find(v=>v.id===selectedSemantic);
   if(!semantic||!selectedModel||!agentConsent){setNotice('请选择启用模型与语义口径，并明确同意发送问题和必要字段；未调用模型。');return;}
   const refs=contexts[id]??[];
   if(!refs.includes(semantic.contract.source_id)){setNotice('请在右侧来源范围中勾选语义定义对应数据源；不会自动扩大本次来源。');setSummaryOpen(true);return;}
   setAgentSubmitting(true);setNotice('');
   if(!pendingAgent.current||pendingAgent.current.question!==text||pendingAgent.current.conversation_id!==id||pendingAgent.current.model_ref!==selectedModel||pendingAgent.current.semantic_version_id!==selectedSemantic)
    pendingAgent.current={conversation_id:id,request_id:crypto.randomUUID(),question:text,model_ref:selectedModel,semantic_version_id:selectedSemantic,selected_source_refs:refs,accept_model_egress:true};
   try{const task=await request<AgentTask>('/api/v1/agent/tasks',pendingAgent.current,12000);setAgentTasks(old=>old.some(v=>v.id===task.id)?old.map(v=>v.id===task.id?task:v):[...old,task]);add(id,[{...messageBase(),kind:'user',text}]);setDraft('');pendingAgent.current=null;setAgentConsent(false);}
   catch(e){setNotice(e instanceof ApiError?`${e.code} · ${e.message}`:'任务通信不明，保留同一请求编号；请读取状态，不自动重复调用。');}
   finally{setAgentSubmitting(false);}return;
  }
  add(id,[{...messageBase(),kind:'user',text},{...messageBase(),kind:'unavailable',text:'你可以继续补充目标或查看接入状态；这些文字仅保存为本地会话，不会被当作已确认指标口径，也不会提交到数仓。'}]);
  setDraft('');setNotice('');
 }
 async function toolAction(kind:'validate'|'create'|'reload'|'schema'){
  if(toolLock.current)return;toolLock.current=true;setToolBusy(true);setToolError(null);
  try{
   if(kind==='schema'){const s=await request<Record<string,unknown>>('/api/v1/contracts/QuerySpec');setEditor(JSON.stringify(s,null,2));setSchemaMode(true);return;}
   if(kind==='reload'&&lastTask){const task=await request<Task>(`/api/v1/tasks/${lastTask.task_id}`);setLastTask(task);return;}
   let body:unknown;try{body=JSON.parse(editor);}catch{throw new ApiError('INVALID_JSON','请输入有效 JSON。','');}
   if((current?.messages.length||0)>MAX_MESSAGES-1)throw new ApiError('LOCAL_LIMIT','请新建会话后再验证。','');
   const id=ensureThread();if(!id)return;
   if(kind==='validate'){
    const output=await request<Validation>('/api/v1/query-spec/validate',body);
    add(id,[{...messageBase(),kind:'validation',spec:output.query_spec,note:output.note}]);
   }else{
    const task=await request<Task>('/api/v1/tasks',body);setLastTask(task);add(id,[{...messageBase(),kind:'task',task}]);
   }
   navigate('query');setToolOpen(false);requestAnimationFrame(()=>input.current?.focus());
  }catch(e){setToolError(e as ApiError);}finally{toolLock.current=false;setToolBusy(false);}
 }
 function removeThreads(){
  if(confirmDelete==='all'){setThreads([]);setActiveId(null);}
  else{setThreads(prev=>prev.filter(t=>t.id!==confirmDelete));if(activeId===confirmDelete)setActiveId(null);}
  setConfirmDelete(null);setDraft('');
 }
 const last=current?.messages.at(-1);
 return <div className="app-shell">
  <aside className={`sidebar ${mobileNav?'is-open':''}`} aria-label="工作空间侧栏"><a href="#query" className="brand" onClick={e=>{e.preventDefault();navigate('query');}}><span className="brand-mark"><Icon name="assets" size={23}/></span><span>数据工作台<small>DATA WORKSPACE</small></span></a>
   <button className="new-thread" onClick={startNew} disabled={toolBusy||workBusy||connection!=='online'}><Icon name="plus" size={18}/>新建会话<span>NEW</span></button>
   <nav aria-label="主导航">{pages.map(([id,label])=><button key={id} aria-label={label} title={label} className={`nav-item ${page===id?'active':''}`} disabled={workBusy} onClick={()=>navigate(id)}><Icon name={id}/><span>{label}</span>{id==='query'&&<span className="nav-pill">主干</span>}</button>)}</nav>
   <div className="history-heading"><span>历史会话</span><button aria-label="会话存储说明" onClick={()=>setPrivacy(!privacy)}><Icon name="shield" size={14}/></button></div>
   {privacy&&<p className="privacy-note">仅此浏览器 · 开发身份隔离。不要输入敏感数据；正式历史将由服务端授权管理。</p>}
   <div className="history-list">{threads.length?threads.map(t=><div className={`history-item ${activeId===t.id?'selected':''}`} key={t.id}><button className="history-select" title={t.title} disabled={toolBusy||workBusy} onClick={()=>selectThread(t.id)}><Icon name="query" size={14}/><span>{t.title}</span></button><button className="history-delete" aria-label={`删除会话 ${t.title}`} disabled={toolBusy||workBusy} onClick={()=>setConfirmDelete(t.id)}><Icon name="close" size={12}/></button></div>):<div className="history-empty"><Icon name="clock" size={17}/><span>还没有会话<br/><small>发送问题后会出现在这里</small></span></div>}</div>
   <div className="sidebar-bottom"><button className={`nav-item settings-entry ${page==='settings'?'active':''}`} aria-label="设置" aria-current={page==='settings'?'page':undefined} disabled={toolBusy||workBusy} onClick={()=>navigate('settings')}><Icon name="settings" size={18}/><span>设置</span></button><button className="clear-history" disabled={!threads.length||toolBusy||workBusy} onClick={()=>setConfirmDelete('all')}><Icon name="trash" size={13}/>清除本地历史</button><div className="environment"><span className={`status-dot ${connection==='online'?'green':''}`}/><span>{connection==='online'?'API 已连接':connection==='loading'?'正在连接 API':'API 未连接'}</span><button aria-label="刷新连接" disabled={toolBusy||workBusy||connection==='loading'} onClick={()=>void connect()}><Icon name="refresh" size={15}/></button></div><div className="profile"><span className="avatar">D</span><div><strong>{session?'本地开发者':'等待身份连接'}</strong><small>本地会话 · 不跨设备</small></div><button className="theme-button" aria-label={theme==='dark'?'切换浅色主题':'切换深色主题'} title={theme==='dark'?'切换浅色主题':'切换深色主题'} onClick={()=>setTheme(theme==='dark'?'light':'dark')}><Icon name={theme==='dark'?'sun':'moon'} size={18}/></button></div></div>
  </aside>
  {mobileNav&&<button className="nav-scrim" aria-label="关闭侧栏" onClick={()=>setMobileNav(false)}/>}
  <main><header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="打开侧栏" onClick={()=>setMobileNav(true)}><Icon name="menu"/></button><span>工作空间</span><span className="slash">/</span><strong>{page==='settings'?'设置':pages.find(p=>p[0]===page)?.[1]}</strong>{page==='query'&&current&&<><span className="slash">/</span><span className="thread-crumb">{current.title}</span></>}</div><div className="top-actions">{page==='query'&&<button className="tool-button summary-toggle" aria-label="会话摘要" aria-expanded={summaryOpen} onClick={()=>setSummaryOpen(!summaryOpen)}><Icon name="assets" size={16}/><span>摘要</span></button>}<span className="local-tag">本地开发</span><div className="theme-selector" role="group" aria-label="背景主题"><button aria-label="黑色主题" aria-pressed={theme==='dark'} onClick={()=>setTheme('dark')}><Icon name="moon" size={14}/><span>黑色</span></button><button aria-label="白色主题" aria-pressed={theme==='light'} onClick={()=>setTheme('light')}><Icon name="sun" size={14}/><span>白色</span></button></div><button className="tool-button" aria-label="开发工具" title="开发工具" disabled={connection!=='online'||toolBusy||workBusy} onClick={()=>{setToolError(null);setToolOpen(true);}}><Icon name="tool" size={16}/><span>开发工具</span></button></div></header>
   {page==='query'?<div className={`workbench-layout ${summaryOpen?'summary-expanded':''}`}><div className="conversation-workspace">{currentAgentTask?<AgentPipeline task={currentAgentTask}/>:<Pipeline message={last} busy={previewBusy}/>}{attachmentBusy&&<p className="local-notice" role="status">附件安全预检/目录读取中；尚未执行问数。</p>}<div className="capability-banner"><span className="status-dot"/><span>{agentAvailable?'已接入受控单表指标问数：选择授权口径与模型，规划后确认执行；JOIN尚未支持。':caps?.modules.some(m=>m.id==='connectors'&&m.available)?'自然语言问数Agent待接入；模型API可在设置验证，数据源可真实预览。':'自然语言问数Agent待接入；模型连接状态请查看设置，当前问题不会执行SQL。'}</span><button onClick={()=>navigate('connectors')}>查看接入状态<Icon name="chevron" size={13}/></button></div>
    {problem&&<div className="error-banner" role="alert"><strong>{problem.code}</strong> {problem.message}<button onClick={()=>void connect()}>重新连接</button></div>}
    <div className="messages-scroll" ref={scroller}><div className="messages-content">
     {!current?.messages.length?<section className="welcome"><div className="welcome-eyebrow">DATA WORKSPACE / QUERY</div><h1>从问题到可用数据</h1><p>直接添加本地数据文件或描述问题；多来源与执行证据在右侧管理。<br className="desktop-break"/>{agentAvailable?'选择已发布口径和启用模型，明确外发同意后规划；SQL执行另需确认。':'先在知识库维护口径；自然语言问数Agent仍待接入。'}</p><div className="welcome-prompts">{['上周各区域的订单转化率是多少？','本月销售额相比上月有什么变化？','按渠道拆分最近 30 天的新增用户'].map((s,i)=><button key={s} disabled={connection!=='online'} onClick={()=>{setDraft(s);input.current?.focus();}}><span>0{i+1}</span><strong>{s}</strong><Icon name="chevron" size={14}/></button>)}</div><div className="welcome-footnote"><Icon name="shield" size={14}/>示例仅填入问题，不自动执行或匹配指标。</div></section>:<div className="message-list" aria-live="polite">{current.messages.map(m=><ResultCard key={m.id} message={m}/>)}{agentTasks.filter(t=>t.conversation_id===activeId).map(task=><AgentTaskCard key={task.id} task={task} onChanged={updated=>setAgentTasks(old=>old.map(t=>t.id===updated.id?updated:t))}/>)}</div>}
    </div></div>
    <div className="composer-area">{notice&&<p className="local-notice" role="status">{notice}</p>}<div className="composer"><textarea ref={input} aria-label="业务问题" maxLength={MAX_TEXT} rows={2} placeholder={current?.messages.length?'继续补充或追问…':'输入你想了解的业务问题…'} value={draft} disabled={connection!=='online'||toolBusy||workBusy} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();send();}}}/><div className="composer-context"><ChatFilePicker busy={toolBusy||workBusy||connection!=='online'} onImport={importAttachment}/><ModelSelector queryReady={agentAvailable} models={modelChoices} value={selectedModel} busy={toolBusy||workBusy} onChange={setSelectedModel} onConfigure={()=>navigate('settings')}/></div>{agentAvailable&&<div className="agent-context"><label>问数口径<select aria-label="选择问数语义版本" value={selectedSemantic} disabled={workBusy} onChange={e=>{setSelectedSemantic(e.target.value);pendingAgent.current=null;}}><option value="">选择已发布、启用的口径</option>{semanticChoices.map(v=><option key={v.id} value={v.id}>{v.contract.name} · v{v.version}</option>)}</select></label><label className="agent-consent"><input aria-label="同意问数模型外发和估算" type="checkbox" checked={agentConsent} disabled={workBusy||!selectedSemantic||!selectedModel} onChange={e=>setAgentConsent(e.target.checked)}/><span>发送本次问题及必要字段给所选模型，接受 $0.25 估算预留；不发数据行或历史。查询另行确认。</span></label></div>}
<div className="composer-toolbar"><span><Icon name="shield" size={13}/>{selectedSemantic&&agentConsent?'显式模型规划 · SQL另需确认':'仅本地会话 · 未向模型外发'}</span><button className="send-button" aria-label="发送问题" disabled={!draft.trim()||connection!=='online'||toolBusy||workBusy} onClick={send}><Icon name="arrow" size={18}/></button></div></div><div className="composer-footnote"><span>Enter 发送 · Shift + Enter 换行</span><span>本地保存文字；接口验证输出不跨刷新保留</span></div></div>
   </div>{summaryOpen&&<WorkbenchPanel agentTask={currentAgentTask} messages={current?.messages??[]} busy={workBusy} sources={sourceChoices} selectedSources={selectedSources} sourcesError={sourcesError} attachments={(current?.messages??[]).filter((m):m is Extract<Message,{kind:'attachment'}>=>m.kind==='attachment')} onToggleSource={toggleSource} onClose={()=>setSummaryOpen(false)} onConnect={()=>navigate('connectors')}/>}</div>:page==='settings'?<SettingsWorkspace busy={settingsBusy} onBack={()=>{navigate('query');requestAnimationFrame(()=>input.current?.focus());}} onBusy={setSettingsBusy}/>:<div className="module-workspace"><div className="module-title"><span className="welcome-eyebrow">WORKSPACE / {page.toUpperCase()}</span><h1>{pages.find(p=>p[0]===page)?.[1]}</h1></div>{page==='knowledge'?<KnowledgeWorkspace onBusy={setSemanticBusy}/>:page==='connectors'?<DataSourceWorkspace onBusy={setPreviewBusy} onVerified={(generation)=>{if(generation)setThreads(previous=>previous.map(thread=>({...thread,messages:thread.messages.map(message=>message.kind==='preview'&&message.receipt.execution_generation&&message.receipt.execution_generation!==generation?{...messageBase(),id:message.id,createdAt:message.createdAt,kind:'error' as const,code:'RESULT_CONTEXT_EXPIRED',text:'SQL 曾完成，但 MCP 执行上下文已失效，旧预览不再可用。请重新验证并确认新预览；不会自动重复查询。',traceId:message.receipt.trace_id}:message)})));void connect();}} onResult={(result:QueryPreview,receipt:PreviewReceipt)=>{const id=ensureThread();if(id)add(id,[{...messageBase(),kind:'preview',result,receipt}]);}}/>:<section className="empty-panel"><Icon name={page} size={36}/><h2>{pages.find(p=>p[0]===page)?.[1]}尚未接入</h2><p>{caps?.modules.find(m=>m.id===page)?.milestone||'后续模块'} 将接入真实服务。当前没有配置、业务数据或已发布结果。</p><button className="primary" onClick={()=>navigate('query')}>返回取数工作台</button></section>}</div>}
  </main>
  {toolOpen&&<div className="dialog-scrim" onClick={e=>{if(e.target===e.currentTarget&&!toolBusy)setToolOpen(false);}}><section ref={toolPanel} className="tool-drawer" role="dialog" aria-modal="true" aria-labelledby="tool-title"><header><div><span className="welcome-eyebrow">DEVELOPER TOOLS</span><h2 id="tool-title">接口与契约验证</h2></div><button className="icon-button" disabled={toolBusy||attachmentBusy} aria-label="关闭开发工具" onClick={()=>{setToolOpen(false);previousFocus.current?.focus();}}><Icon name="close"/></button></header><p className="tool-description">业务用户不需要编辑这些内容。这里用于验证工程接口，结果会以卡片出现在当前会话，不代表取数成功。</p>{toolError&&<div className="error-banner" role="alert"><strong>{toolError.code}</strong> {toolError.message}{toolError.traceId&&<small>{toolError.traceId}</small>}</div>}<label className="editor-label" htmlFor="query-spec">QuerySpec<span>示例不是已认证指标</span></label><textarea id="query-spec" className="json-editor" spellCheck={false} value={editor} disabled={toolBusy||attachmentBusy} onChange={e=>{setEditor(e.target.value);setSchemaMode(false);}}/><div className="editor-actions"><button className="secondary" disabled={toolBusy||attachmentBusy} onClick={()=>{setEditor(JSON.stringify(example,null,2));setSchemaMode(false);setToolError(null);}}>恢复示例</button><button className="secondary" disabled={toolBusy||attachmentBusy} onClick={()=>void toolAction('schema')}>查看实际 Schema</button></div>{schemaMode&&<p className="local-notice" role="status">当前显示 Schema，恢复示例后再验证。</p>}<div className="tool-boundary"><Icon name="shield" size={17}/><p>身份来自服务器；客户端不能自报租户。任务记录仅存 API 内存，重启丢失；不会执行 SQL。</p></div><div className="tool-submit"><button className="secondary" disabled={toolBusy||schemaMode} onClick={()=>void toolAction('create')}>登记测试任务</button><button className="primary" disabled={toolBusy||schemaMode} onClick={()=>void toolAction('validate')}>{toolBusy?'验证中…':'验证数据契约'}<Icon name="check" size={15}/></button></div>{lastTask&&<div className="last-task"><strong>最近接口任务 · {lastTask.status}</strong><code>{lastTask.task_id}</code><span>{lastTask.error?.code}</span><button className="secondary" disabled={toolBusy||attachmentBusy} onClick={()=>void toolAction('reload')}>重新读取任务</button></div>}</section></div>}
  {confirmDelete&&<div className="dialog-scrim"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title"><h2 id="delete-title">{confirmDelete==='all'?'清除本地历史？':'删除这段会话？'}</h2><p>只删除此浏览器的会话文字，无法恢复。不影响 API 任务记录或数据源。</p><div><button className="secondary" onClick={()=>setConfirmDelete(null)}>取消</button><button className="danger-button" onClick={removeThreads}>确认删除</button></div></section></div>}
 </div>;
}
