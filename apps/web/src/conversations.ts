import type { QuerySpec, Task, PreviewReceipt, QueryPreview, TestedDraft } from './api';
export type Theme = 'dark' | 'light';
export type Message = {id:string; createdAt:string} & (
  {kind:'user'; text:string} |
  {kind:'attachment'; filename:string; receipt:TestedDraft} |
  {kind:'unavailable'; text:string} |
  {kind:'validation'; spec:QuerySpec; note:string} |
  {kind:'task'; task:Task} |
  {kind:'preview'; receipt:PreviewReceipt; result:QueryPreview} |
  {kind:'error'; code:string; text:string; traceId:string}
);
export type Conversation={id:string; title:string; updatedAt:string; messages:Message[]};
export const MAX_THREADS=30, MAX_MESSAGES=80, MAX_TEXT=4000;
export const browserStorage={getItem:(key:string)=>window.localStorage.getItem(key),setItem:(key:string,value:string)=>window.localStorage.setItem(key,value)};
const PREFIX='data-workspace:local-conversations:v1:';
export function storageKey(tenant:string,principal:string){return PREFIX+encodeURIComponent(tenant)+':'+encodeURIComponent(principal);}
export function newConversation():Conversation{return {id:crypto.randomUUID(),title:'新会话',updatedAt:new Date().toISOString(),messages:[]};}
export function messageBase(){return {id:crypto.randomUUID(),createdAt:new Date().toISOString()};}
function record(v:unknown):v is Record<string,unknown>{return !!v&&typeof v==='object'&&!Array.isArray(v);}
function validMessage(v:unknown):v is Message{
 if(!record(v)||typeof v.id!=='string'||typeof v.createdAt!=='string')return false;
 if(v.kind==='user'||v.kind==='unavailable')return typeof v.text==='string'&&v.text.length<=MAX_TEXT;
 if(v.kind==='error')return typeof v.code==='string'&&typeof v.text==='string'&&typeof v.traceId==='string';
 // Persist only local user text and static capability feedback, not server responses or data snapshots.
 return false;
}
export function loadConversations(storage:Pick<Storage,'getItem'>,key:string):Conversation[]{
 try{
  const raw=storage.getItem(key);if(!raw||raw.length>2_000_000)return [];
  const data:unknown=JSON.parse(raw);
  if(!record(data)||data.version!==1||!Array.isArray(data.conversations))return [];
  return data.conversations.filter((v):v is Conversation=>record(v)&&typeof v.id==='string'&&typeof v.title==='string'&&v.title.length<=80&&typeof v.updatedAt==='string'&&Array.isArray(v.messages)&&v.messages.length<=MAX_MESSAGES&&v.messages.every(validMessage)).slice(0,MAX_THREADS);
 }catch{return [];}
}
export function saveConversations(storage:Pick<Storage,'setItem'>,key:string,threads:Conversation[]):boolean{
 try{
  const safe=threads.slice(0,MAX_THREADS).map(t=>({...t,messages:t.messages.filter(m=>m.kind==='user'||m.kind==='unavailable').slice(-MAX_MESSAGES)})).filter(t=>t.messages.length>0);
  const text=JSON.stringify({version:1,conversations:safe});if(text.length>2_000_000)return false;
  storage.setItem(key,text);return true;
 }catch{return false;}
}
export function appendMessages(threads:Conversation[],id:string,messages:Message[]):Conversation[]{
 return threads.map(t=>{
  if(t.id!==id)return t;
  const first=messages.find(m=>m.kind==='user');
  const title=t.title==='新会话'&&first?.kind==='user'?first.text.trim().slice(0,30):t.title;
  return {...t,title,messages:[...t.messages,...messages].slice(-MAX_MESSAGES),updatedAt:new Date().toISOString()};
 }).sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt));
}
export function loadTheme(storage:Pick<Storage,'getItem'>):Theme{try{return storage.getItem('data-workspace:theme')==='light'?'light':'dark';}catch{return 'dark';}}
export function storeTheme(storage:Pick<Storage,'setItem'>,theme:Theme){try{storage.setItem('data-workspace:theme',theme);}catch{/* theme still changes for this page */}}
