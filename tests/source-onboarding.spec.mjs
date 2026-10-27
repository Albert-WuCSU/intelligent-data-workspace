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
test('user adds a source, saves, reconnects after reload and browses dates with no date filter',async({page})=>{
 const name=`日期数据源-${Date.now()}`;
 const csv='code,created_at,shipped_on,amount\n'+Array.from({length:120},(_,i)=>`c${i},2025-01-01 12:00:00,2025-01-02,${i}\n`).join('');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await openSources(page);
 await expect(page.locator('input[type=date]')).toHaveCount(0);
 await page.getByRole('button',{name:'新增数据源'}).click();await page.getByLabel('连接名称').fill(name);await page.getByLabel('选择数据文件').setInputFiles({name:'dates.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();
 await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('真实 MCP 连接测试通过');await page.getByRole('button',{name:'保存连接'}).click();
 await page.reload();const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});await card.getByRole('button',{name:'连接并浏览'}).click();await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'main.data'}).click();
 const table=page.getByLabel('数据源前100行').getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('shipped_on');await expect(table).toContainText('2025-01-01T12:00:00');await expect(table).toContainText('TIMESTAMP');await expect(page.locator('input[type=date]')).toHaveCount(0);
 await page.screenshot({path:`${EVIDENCE}/source-navigation-dark.png`,fullPage:true});await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/source-navigation-light.png`,fullPage:true});
 await card.getByRole('button',{name:'禁用',exact:true}).click();await expect(card.getByRole('button',{name:'连接并浏览'})).toBeDisabled();await expect(page.getByRole('region',{name:'数据表导航'})).toHaveCount(0);expect(errors).toEqual([]);
});
test('nonsecret configuration import fills form but does not auto-connect; errors preserve input',async({page})=>{
 await openSources(page);const config={schema_version:'1.0',profile:{kind:'local_file',name:'导入的连接',path:'data/does-not-exist.csv',usage_authorized:true}};
 await page.getByLabel('连接配置文件').setInputFiles({name:'connection.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(config))});await expect(page.getByLabel('连接名称')).toHaveValue('导入的连接');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('INVALID_SOURCE');await expect(page.getByLabel('连接名称')).toHaveValue('导入的连接');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();
 await page.getByLabel('连接配置文件').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({...config,command:'powershell',password:'sentinel-never-reflect'}))});await expect(page.getByRole('alert')).toContainText('INVALID_CONFIG');await expect(page.getByRole('alert')).not.toContainText('sentinel-never-reflect');
});
test('mobile source navigation controls preserve visible themes without a time-filter input',async({page})=>{
 await page.setViewportSize({width:390,height:844});await openSources(page);await page.getByRole('button',{name:'新增数据源'}).click();await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');await expect(page.locator('input[type=date]')).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/source-config-mobile.png`,fullPage:true});
});


test('xlsx workbook upload, real multisheet navigation and date columns without time filters',async({page})=>{
 await openSources(page);await page.getByRole('button',{name:'新增数据源'}).click();
 const name=`Excel工作簿-${Date.now()}`;await page.getByLabel('连接名称').fill(name);
 await expect(page.getByLabel('选择数据文件')).toHaveAttribute('accept',/\.xlsx/);
 await page.getByLabel('选择数据文件').setInputFiles({name:'xlsx-fixture.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:fs.readFileSync(process.env.WORKSPACE_XLSX_FIXTURE)});
 await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();
 // Await the bounded real HTTP operation before the unchanged 5s DOM assertion.
 const uploaded=page.waitForResponse(r=>r.url().includes('/api/v1/source-profiles/upload')&&r.request().method()==='POST',{timeout:30000});
 await page.getByRole('button',{name:'测试连接',exact:true}).click();
 const uploadReceipt=await uploaded;expect(uploadReceipt.status()).toBe(200);
 const receipt=await page.waitForResponse(r=>r.url().includes('/api/v1/source-profiles/test')&&r.request().method()==='POST',{timeout:30000});expect(receipt.status()).toBe(200);expect((await receipt.json()).tables).toHaveLength(2);
 await expect(page.getByRole('status')).toContainText('2 张表');await page.getByRole('button',{name:'保存连接'}).click();
 const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});await card.getByRole('button',{name:'连接并浏览'}).click();
 await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'workbook.订单表'}).click();
 const table=page.getByLabel('数据源前100行').getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('发货日期');await expect(table).toContainText('2025-01-01T12:00:00');await expect(page.locator('input[type=date]')).toHaveCount(0);
 await page.screenshot({path:`${EVIDENCE}/xlsx-navigation.png`,fullPage:true});
 await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'workbook.字典表'}).click();await expect(table).toContainText('Alpha');await expect(table.getByRole('row')).toHaveCount(2);
 await card.getByRole('button',{name:'禁用',exact:true}).click();
});
