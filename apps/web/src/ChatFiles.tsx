import {useState} from 'react';
import {ApiError,request} from './api';
import type {DraftPreview,TestedDraft} from './api';

export type ConversationAttachment={filename:string;receipt:TestedDraft};
export function ChatFilePicker({busy,onImport}:{busy:boolean;onImport:(file:File)=>Promise<void>}){
 const [file,setFile]=useState<File|null>(null),[authorized,setAuthorized]=useState(false),[error,setError]=useState('');
 async function upload(){if(!file||!authorized)return;setError('');try{await onImport(file);setFile(null);setAuthorized(false);}catch(error){setError(error instanceof Error?error.message:'导入未完成，请重试');}}
 return <div className="chat-file-composer"><label className="attachment-button">＋ 添加数据文件<input aria-label="聊天数据文件" type="file" accept=".csv,.parquet,.xlsx,.duckdb" disabled={busy} onChange={event=>{setFile(event.target.files?.[0]??null);setAuthorized(false);setError('');event.target.value='';}}/></label>
 {file&&<section className="chat-import-confirm" aria-label="附件导入确认"><strong>{file.name}</strong><p>复制到本机隔离目录，草稿最多24小时；不保存为连接，不修改原件、不向模型发送数据行。</p><label><input type="checkbox" disabled={busy} checked={authorized} onChange={e=>setAuthorized(e.target.checked)}/>我有权使用文件并同意上述本机导入</label><div><button type="button" className="primary" disabled={busy||!authorized} onClick={()=>void upload()}>{busy?'实际导入中…':'导入到本会话'}</button><button type="button" className="secondary" disabled={busy} onClick={()=>{setFile(null);setError('');}}>取消添加</button></div>{error&&<p role="alert">{error}</p>}</section>}
 </div>;
}
export function ChatFileCard({attachment}:{attachment:ConversationAttachment}){
 const [data,setData]=useState<DraftPreview|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const {filename,receipt}=attachment;const expired=!!receipt.expires_at&&Date.parse(receipt.expires_at)<=Date.now();
 async function preview(table:string){if(busy)return;setBusy(true);setError('');setData(null);try{setData(await request<DraftPreview>(`/api/v1/source-profiles/drafts/${receipt.test_id}/tables/${encodeURIComponent(table)}/preview`,undefined,30000));}catch(error){setError(error instanceof ApiError?`${error.code} · ${error.message}`:'预览失败');}finally{setBusy(false);}}
 const columns=(data?.preview.columns??[]) as {name:string;type:string}[],rows=(data?.preview.rows??[]) as unknown[][];
 return <section className="result-card chat-file-card" aria-label={`会话附件 ${filename}`}><div className="result-header"><span className="result-status green">本机目录已读取</span><strong>{filename}</strong></div><p>{receipt.tables.length} 张表 · 临时附件，未保存为连接 · 24小时后需重新导入。多份附件属于本会话上下文，不代表已执行JOIN。</p><div className="connector-actions">{receipt.tables.map(table=><button type="button" className="secondary" key={String(table.id)} disabled={busy||expired} onClick={()=>void preview(String(table.id))}>预览 {String(table.name)}</button>)}</div>
 {busy&&<p role="status">正在读取真实列头与前100行…</p>}{expired&&<p role="alert">附件已过期，请重新添加文件。</p>}{error&&<p role="alert">{error}</p>}
 {data&&<><p>真实MCP只读结果 · {rows.length} 行 · 原类型/日期保留，无筛选；业务口径尚未认证。</p><div className="preview-table-scroll" tabIndex={0} aria-label={`附件预览 ${filename}`}><table><thead><tr>{columns.map(column=><th key={column.name}>{column.name}<small>{column.type}</small></th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell==null?'—':String(cell)}</td>)}</tr>)}</tbody></table>{!rows.length&&<p>没有返回行，原列头仍保留。</p>}</div></>}
 </section>;
}
