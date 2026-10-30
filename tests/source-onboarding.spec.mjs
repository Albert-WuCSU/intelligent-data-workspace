import {test,expect} from '../apps/web/node_modules/@playwright/test/index.mjs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
import fs from 'node:fs';
let child,fixture;
test.beforeAll(async()=>{
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>['SYSTEMROOT','WINDIR','TEMP','TMP','PATH'].includes(k.toUpperCase())));env.PYTHONUTF8='1';
 child=spawn(path.resolve('services/api/.venv/Scripts/python.exe'),['scripts/remote_browser_fixture.py'],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
 fixture=await new Promise((resolve,reject)=>{let output='';const timeout=setTimeout(()=>reject(new Error('Owned source fixture did not start')),15000);child.stdout.on('data',data=>{output+=data;try{const value=JSON.parse(output.split('\n')[0]);clearTimeout(timeout);resolve(value);}catch{}});child.on('exit',()=>{clearTimeout(timeout);reject(new Error('Owned source fixture exited before ready'));});});
});
test.afterEach(async({page})=>{await page.unrouteAll({behavior:'wait'});});
test.afterAll(async()=>{if(child&&child.exitCode===null){const exited=once(child,'exit');child.stdin.end('stop\n');await exited;expect(child.exitCode).toBe(0);}});
const EVIDENCE=process.env.WORKSPACE_BROWSER_EVIDENCE||`project-control/modules/M02/evidence/sources-${Date.now()}`;
async function openSources(page){
 // Only address forwarding: all source responses/Worker/MCP execution are real,
 // using current product code and independent temporary data, not the old API.
 await page.route('**/api/v1/source-profiles**',async route=>{
  const request=route.request(),url=new URL(request.url()),bytes=request.postDataBuffer(),headers={...request.headers()};
  // Preserve binary multipart bytes instead of text conversion; reframe exact byte length.
  if(bytes)headers['content-length']=String(bytes.length);
  if(url.pathname.endsWith('/upload'))console.log('source-upload-frame',JSON.stringify({bytes:bytes?.length??null,declared:request.headers()['content-length']??null}));
  const response=await route.fetch({url:fixture.api_url+url.pathname+url.search,postData:bytes??undefined,headers});
  if(url.pathname.endsWith('/upload'))console.log('source-upload-status',response.status());
  await route.fulfill({response});
 });
 await page.goto('http://127.0.0.1:5173/#connectors');await expect(page.getByRole('region',{name:'数据源连接管理'})).toBeVisible();await expect(page.getByRole('button',{name:'新增数据源'})).toBeEnabled();}
async function openChat(page){
 await page.route('**/api/v1/source-profiles**',async route=>{
  const request=route.request(),url=new URL(request.url()),bytes=request.postDataBuffer(),headers={...request.headers()};
  if(bytes)headers['content-length']=String(bytes.length);
  const response=await route.fetch({url:fixture.api_url+url.pathname+url.search,postData:bytes??undefined,headers});await route.fulfill({response});
 });
 await page.goto('http://127.0.0.1:5173/#query');await expect(page.getByLabel('业务问题')).toBeEnabled();
}
async function addFile(page,name,buffer){
 await page.getByLabel('聊天数据文件').setInputFiles({name,mimeType:name.endsWith('.xlsx')?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'text/csv',buffer});
 await expect(page.getByRole('button',{name:'导入到本会话'})).toBeDisabled();
 await page.getByRole('checkbox',{name:'我有权使用文件并同意上述本机导入'}).check();
 const done=page.waitForResponse(r=>r.url().includes('/source-profiles/test')&&r.request().method()==='POST',{timeout:30000});
 await page.getByRole('button',{name:'导入到本会话'}).click();const response=await done;expect(response.status()).toBe(200);
 const card=page.getByRole('region',{name:`会话附件 ${name}`,exact:true});await expect(card).toBeVisible();return card;
}
test('chat CSV import uses actual MCP, preserves dates100 rows and never creates a saved connection',async({page})=>{
 await openChat(page);const before=await page.request.get(fixture.api_url+'/api/v1/source-profiles');const count=(await before.json()).profiles.length;
 const csv='code,created_at,shipped_on,amount\n'+Array.from({length:120},(_,i)=>`c${i},2025-01-01 12:00:00,2025-01-02,${i}\n`).join('');
 const card=await addFile(page,'chat-dates.csv',Buffer.from(csv));
 await expect(card).toContainText('未保存为连接');await card.getByRole('button',{name:'预览 main.data'}).click();
 const table=card.getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('shipped_on');await expect(table).toContainText('TIMESTAMP');await expect(table).toContainText('2025-01-01T12:00:00');
 expect((await (await page.request.get(fixture.api_url+'/api/v1/source-profiles')).json()).profiles.length).toBe(count);
 await expect(page.getByLabel('选择问数数据源')).toHaveCount(0);await expect(page.locator('input[type=date]')).toHaveCount(0);
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/chat-csv-light.png`,fullPage:true});
 const persisted=await page.evaluate(()=>JSON.stringify({...localStorage}));expect(persisted).not.toContain('chat-dates.csv');expect(persisted).not.toContain('2025-01-01T12:00:00');
 await page.reload();await expect(page.getByRole('region',{name:'会话附件 chat-dates.csv',exact:true})).toHaveCount(0);
});
test('connector only offers remote configuration and preserves failed imports without secrets',async({page})=>{
 await openSources(page);await page.getByRole('button',{name:'新增数据源',exact:true}).click();
 await expect(page.getByLabel('数据源类型').getByRole('option',{name:/本地文件/})).toHaveCount(0);await expect(page.getByLabel('选择数据文件')).toHaveCount(0);
 const config={schema_version:'1.0',profile:{kind:'postgresql',name:'导入数据库',host:'127.0.0.1',port:5432,database:'demo',username:'readonly',sslmode:'disable',secret_ref:'DEMO_PG',usage_authorized:true}};
 await page.getByLabel('连接配置文件').setInputFiles({name:'remote.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(config))});await expect(page.getByLabel('连接名称')).toHaveValue('导入数据库');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('TARGET_NOT_APPROVED');await expect(page.getByLabel('数据库名称')).toHaveValue('demo');
 await page.getByLabel('连接配置文件').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({...config,command:'powershell',password:'sentinel-never-reflect'}))});await expect(page.getByRole('alert')).toContainText('INVALID_CONFIG');await expect(page.getByRole('alert')).not.toContainText('sentinel-never-reflect');
});
test('mobile chat upload confirmation and right context do not overflow; visible themes remain',async({page})=>{
 await page.setViewportSize({width:390,height:844});await openChat(page);
 await page.getByLabel('聊天数据文件').setInputFiles({name:'mobile.csv',mimeType:'text/csv',buffer:Buffer.from('id,label\n1,Alpha\n')});
 await expect(page.getByRole('region',{name:'附件导入确认'})).toContainText('不向模型发送数据行');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');await page.screenshot({path:`${EVIDENCE}/chat-files-mobile.png`,fullPage:true});await page.getByRole('button',{name:'取消添加'}).click();
});
test('chat xlsx real multi-sheet navigation preserves original headers and dates with no filters',async({page})=>{
 await openChat(page);const card=await addFile(page,'chat-workbook.xlsx',fs.readFileSync(process.env.WORKSPACE_XLSX_FIXTURE));
 await expect(card).toContainText('2 张表');await card.getByRole('button',{name:'预览 workbook.订单表'}).click();
 let table=card.getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('发货日期');await expect(table).toContainText('2025-01-01T12:00:00');await expect(page.locator('input[type=date]')).toHaveCount(0);
 await card.getByRole('button',{name:'预览 workbook.字典表'}).click();await expect(card.getByRole('table')).toContainText('Alpha');await expect(card.getByRole('table').getByRole('row')).toHaveCount(2);await page.screenshot({path:`${EVIDENCE}/chat-xlsx-dark.png`,fullPage:true});
});
test('multiple conversation attachments and right multiple sources remain separate from real JOIN support',async({page})=>{
 const sourceIds=[];
 for(const name of ['remote-one','remote-two']){
  const response=await page.request.post(fixture.api_url+'/api/v1/source-profiles/test',{headers:{'X-Workspace-Request':'1'},data:{kind:'http_mcp',name,url:fixture.mcp_url,auth_mode:'bearer',secret_ref:fixture.secret_ref,usage_authorized:true}});expect(response.status()).toBe(200);
  const saved=await page.request.post(fixture.api_url+'/api/v1/source-profiles/save',{headers:{'X-Workspace-Request':'1'},data:{test_id:(await response.json()).test_id}});expect(saved.status()).toBe(200);sourceIds.push((await saved.json()).id);
 }
 await openChat(page);const panel=page.getByRole('complementary',{name:'会话摘要'});
 await panel.getByRole('checkbox',{name:'包含来源 remote-one',exact:true}).check();await panel.getByRole('checkbox',{name:'包含来源 remote-two',exact:true}).check();
 await expect(panel.getByRole('checkbox',{name:'包含来源 remote-one',exact:true})).toBeChecked();await expect(panel.getByRole('checkbox',{name:'包含来源 remote-two',exact:true})).toBeChecked();
 await addFile(page,'orders.csv',Buffer.from('id,amount\n1,10\n'));await addFile(page,'items.csv',Buffer.from('id,label\n1,fixture\n'));
 await expect(panel).toContainText('orders.csv');await expect(panel).toContainText('items.csv');await expect(panel).toContainText('跨源JOIN尚待受控实现');
 await page.getByRole('button',{name:'新建会话'}).click();await expect(panel.getByRole('checkbox',{name:'包含来源 remote-one',exact:true})).not.toBeChecked();await expect(panel).not.toContainText('orders.csv');
});
