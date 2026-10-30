import {describe,it,expect} from 'vitest';
import {workbenchEvidence,resolveModel} from './workbench';
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
