import type { Message } from './conversations';

/** Pure projection of current in-memory receipts. Never infer work from timers. */
export function workbenchEvidence(messages:Message[],busy=false){
 const last=messages.at(-1);
 const preview=messages.filter((m):m is Extract<Message,{kind:'preview'}>=>m.kind==='preview').at(-1);
 const validation=messages.filter((m):m is Extract<Message,{kind:'validation'}>=>m.kind==='validation').at(-1);
 const task=messages.filter((m):m is Extract<Message,{kind:'task'}>=>m.kind==='task').at(-1);
 const user=messages.filter((m):m is Extract<Message,{kind:'user'}>=>m.kind==='user').at(-1);
 // An earlier successful result is a separate receipt, NOT progress of a newer question.
 const current=last?.kind==='preview'?last:undefined;
 const state=busy?'等待真实回执':current?'只读预览已返回':last?.kind==='validation'?'仅结构校验通过':last?.kind==='error'?'请求未完成':last?.kind==='task'?'测试任务未执行':last?.kind==='unavailable'?'自然语言请求未执行':last?.kind==='attachment'?'附件目录已读取':'等待提问';
 return {state,user,preview,validation,task,current,steps:[
  {label:'口径确认',state:current?'开发模板，不是业务认证':last?.kind==='validation'?'结构通过，语义未确认':'等待确认'},
  {label:'数据检索',state:current?'真实MCP元数据':last?.kind==='attachment'?'附件实际目录已读取':'未访问'},
  {label:'SQL执行',state:busy?'等待回执':current?'已执行只读预览':'未执行'},
  {label:'结果校验',state:current?'预览返回，质量范围有限':'未运行'},
 ]};
}

export type SelectableModel={id:string;label:string;available:boolean;note?:string};
/** Downstream model catalog must supply actual availability, never aliases from host config. */
export function resolveModel(models:SelectableModel[],id:string){
 return models.find(model=>model.id===id&&model.available)??null;
}
