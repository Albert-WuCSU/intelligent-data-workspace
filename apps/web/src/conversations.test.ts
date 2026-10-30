import { describe, expect, it } from 'vitest';
import { appendMessages, loadConversations, loadTheme, newConversation, saveConversations, storageKey, storeTheme } from './conversations';
import type { Message } from './conversations';
import { example } from './api';
function memory(){const values=new Map<string,string>();return {getItem:(k:string)=>values.get(k)||null,setItem:(k:string,v:string)=>{values.set(k,v);}};}
describe('local development conversation storage',()=>{
 it('separates tenants and principals',()=>{expect(storageKey('a','user')).not.toBe(storageKey('b','user'));expect(storageKey('a','user')).not.toBe(storageKey('a','other'));});
 it('persists only local text, never API result snapshots',()=>{
  const store=memory(),thread={...newConversation(),title:'分析请求'};
  thread.messages=[{id:'1',createdAt:'2026-10-26',kind:'user',text:'查订单'}, {id:'2',createdAt:'2026-10-26',kind:'validation',spec:example,note:'validation'}];
  expect(saveConversations(store,'scope',[thread])).toBe(true);
  const loaded=loadConversations(store,'scope');expect(loaded[0].messages).toHaveLength(1);expect(loaded[0].messages[0].kind).toBe('user');
  expect(loadConversations(store,'other')).toEqual([]);
 });
 it('never persists MCP preview rows or receipts',()=>{
  const store=memory(),thread=newConversation();
  thread.messages=[{id:'user',createdAt:'2026-10-26',kind:'user',text:'开发测试'},
    {id:'preview',createdAt:'2026-10-26',kind:'preview',receipt:{task_id:'test-task',status:'SUCCEEDED',created_at:'2026-10-26',trace_id:'test-trace'},result:{source:'independently_generated_synthetic',dataset_version:'test',sql_dialect:'duckdb',columns:[{name:'test_column',type:'VARCHAR'}],rows:[['synthetic-snapshot-sentinel']],returned_row_count:1,reported_total_rows:null,truncated:false,retrieved_at:'2026-10-26',currency:'TEST',quality:{status:'WARN',limitations:['fixture only']}}}];
  expect(saveConversations(store,'scope',[thread])).toBe(true);
  expect(store.getItem('scope')).not.toContain('synthetic-snapshot-sentinel');
  expect(store.getItem('scope')).not.toContain('test-task');
  expect(loadConversations(store,'scope')[0].messages).toHaveLength(1);
 });
 it('handles corrupt, unknown version and malicious stored message kinds',()=>{
  const store=memory();for(const raw of ['not json','{"version":2,"conversations":[]}','{"version":1,"conversations":[{"id":"1","title":"bad","updatedAt":"x","messages":[{"id":"1","createdAt":"x","kind":"html","text":"<script>"}]}]}']){store.setItem('scope',raw);expect(loadConversations(store,'scope')).toEqual([]);}
 });
 it('handles quota or disabled browser storage safely',()=>{
  const broken={getItem:()=>{throw new Error('disabled');},setItem:()=>{throw new Error('quota');}};
  expect(loadConversations(broken,'scope')).toEqual([]);expect(saveConversations(broken,'scope',[newConversation()])).toBe(false);expect(loadTheme(broken)).toBe('dark');expect(()=>storeTheme(broken,'light')).not.toThrow();
 });
 it('append preserves old messages and titles only the target thread',()=>{
  const a=newConversation(),b=newConversation();const message:Message={id:'1',createdAt:'2026-10-26',kind:'user',text:'第一条请求'};
  const out=appendMessages([a,b],a.id,[message]);expect(out.find(t=>t.id===a.id)?.title).toBe('第一条请求');expect(out.find(t=>t.id===b.id)?.messages).toEqual([]);
  const updated=appendMessages(out,a.id,[{...message,id:'2',text:'继续追问'}]);expect(updated.find(t=>t.id===a.id)?.messages).toHaveLength(2);expect(updated.find(t=>t.id===a.id)?.title).toBe('第一条请求');
 });
 it('theme persists and rejects unknown theme',()=>{const store=memory();storeTheme(store,'light');expect(loadTheme(store)).toBe('light');store.setItem('data-workspace:theme','evil');expect(loadTheme(store)).toBe('dark');});
});


it('chat attachment receipts and rows are never persisted as reusable context',()=>{
 const thread={id:'attachment-thread',title:'files',updatedAt:'2026-10-28T00:00:00Z',messages:[{id:'one',createdAt:'2026-10-28T00:00:00Z',kind:'attachment' as const,filename:'sensitive-name.csv',receipt:{test_id:'private-draft-id',name:'private',source_label:'local',tables:[],note:'unit attachment'}}]};
 let saved='';saveConversations({setItem:(_key:string,value:string)=>{saved=value;}},'test',[thread]);
 expect(saved).not.toContain('private-draft-id');expect(saved).not.toContain('sensitive-name');
});
