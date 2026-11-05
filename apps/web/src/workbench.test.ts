import {describe,it,expect} from 'vitest';
import {workbenchEvidence,resolveModel,defaultModel,filterModels,groupModels,engineLabel} from './workbench';
import type {Message} from './conversations';
const base={id:'message',createdAt:'2026-10-28T00:00:00Z'};
const preview={...base,kind:'preview',receipt:{},result:{source:'independently_generated_synthetic',returned_row_count:3}} as Message;
describe('workbench evidence remains receipt-driven',()=>{
 it('empty and unanswered questions never imply SQL or data access',()=>{
  expect(workbenchEvidence([]).state).toBe('等待提问');
  const value=workbenchEvidence([{...base,kind:'user',text:'查订单'},{...base,kind:'unavailable',text:'未接入'}]);
  expect(value.state).toBe('自然语言请求未执行');expect(value.steps[1].state).toBe('未访问');expect(value.steps[2].state).toBe('未执行');
 });
 it('a previous preview is evidence, not progress for the newer request',()=>{
  const value=workbenchEvidence([preview,{...base,kind:'user',text:'再看看'},{...base,kind:'unavailable',text:'待接入'}]);
  expect(value.preview).toBe(preview);expect(value.current).toBeUndefined();expect(value.steps[2].state).toBe('未执行');
 });
 it('actual preview is differentiated from business certification',()=>{
  const value=workbenchEvidence([preview]);expect(value.current).toBe(preview);expect(value.steps[2].state).toContain('已执行');expect(value.steps[0].state).toContain('不是业务认证');
 });
 it('loading does not infer model/warehouse progress',()=>{
  const value=workbenchEvidence([],true);expect(value.state).toBe('等待真实回执');expect(value.steps[1].state).toBe('未访问');
 });
});
it('only actually available catalog models can be resolved for switching',()=>{
 const models=[{id:'one',label:'fixture-one',available:true},{id:'two',label:'fixture-two',available:true},{id:'denied',label:'fixture-unverified',available:false}];
 expect(resolveModel(models,'one')?.id).toBe('one');expect(resolveModel(models,'two')?.id).toBe('two');expect(resolveModel(models,'denied')).toBeNull();expect(resolveModel([],'one')).toBeNull();
});
it('default model is server-declared and only selected when available',()=>{
 const models=[
  {id:'one',label:'Default',available:false,default:true,modelId:'deepseek-v4.1-flash',source:'ai_plan' as const},
  {id:'two',label:'Fallback',available:true,modelId:'other-model',source:'personal_api' as const},
 ];
 expect(defaultModel(models)?.id).toBe('two');
 expect(defaultModel([{...models[0],available:true}])?.id).toBe('one');
 expect(defaultModel([])).toBeNull();
});
it('task engine label is server-reported, never inferred from a model name',()=>{
 expect(engineLabel('claude_agent_sdk_skills_v1')).toBe('Claude Agent SDK');
 expect(engineLabel('langgraph_governed_single_table_v1')).toBe('LangGraph');
 expect(engineLabel(undefined)).toBe('LangGraph');
});
it('model search and grouping use server catalog fields',()=>{
 const models=[
  {id:'one',label:'DeepSeek',available:true,modelId:'deepseek-v4.1-flash',source:'ai_plan' as const},
  {id:'two',label:'My API',available:true,modelId:'my-model',source:'personal_api' as const},
  {id:'denied',label:'Untested',available:false,modelId:'untested-model',source:'personal_api' as const},
 ];
 expect(filterModels(models,'deepseek').map(model=>model.id)).toEqual(['one']);
 expect(filterModels(models,'my-model').map(model=>model.id)).toEqual(['two']);
 expect(filterModels(models,'  ').length).toBe(3);
 const groups=groupModels(models);
 expect(groups.map(group=>group.source)).toEqual(['personal_api','ai_plan']);
 expect(groups[0].models.map(model=>model.id)).toEqual(['two','denied']);
 expect(groups[1].models.map(model=>model.id)).toEqual(['one']);
});
