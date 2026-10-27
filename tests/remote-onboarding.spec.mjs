import {test,expect} from '../apps/web/node_modules/@playwright/test/index.mjs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
const EVIDENCE=process.env.WORKSPACE_BROWSER_EVIDENCE;
let child,fixture;
test.beforeAll(async()=>{
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>['SYSTEMROOT','WINDIR','TEMP','TMP','PATH'].includes(k.toUpperCase())));env.PYTHONUTF8='1';
 child=spawn(path.resolve('services/api/.venv/Scripts/python.exe'),['scripts/remote_browser_fixture.py'],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
 fixture=await new Promise((resolve,reject)=>{let output='';const timeout=setTimeout(()=>reject(new Error('Owned real HTTP fixture did not start')),15000);child.stdout.on('data',data=>{output+=data;const line=output.split('\n')[0];try{const value=JSON.parse(line);clearTimeout(timeout);resolve(value);}catch{}});child.on('exit',()=>{clearTimeout(timeout);reject(new Error('Owned fixture exited before ready'));});});
});
test.afterEach(async({page})=>{await page.unrouteAll({behavior:'wait'});});
test.afterAll(async()=>{if(child&&child.exitCode===null){const exited=once(child,'exit');child.stdin.end('stop\n');await exited;expect(child.exitCode).toBe(0);}});
async function open(page){
 // Routing only changes the network address; every response comes from real product API.
 await page.route('**/api/v1/source-profiles**',async route=>{const url=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+url.pathname+url.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/#connectors');await expect(page.getByRole('button',{name:'配置 MCP',exact:true})).toBeEnabled();
}
test('real authenticated HTTP MCP form, save, reload, dates and disable without browser credentials',async({page})=>{
 await open(page);await page.getByRole('button',{name:'配置 MCP',exact:true}).click();
 const name=`HTTP连接-${Date.now()}`;await page.getByLabel('连接名称').fill(name);await page.getByLabel('MCP 服务地址').fill(fixture.mcp_url);await page.getByLabel('后台凭证引用').fill(fixture.secret_ref);
 await expect(page.locator('input[type=password],input[type=date]')).toHaveCount(0);
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();
 await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('真实 MCP 连接测试通过');
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).uncheck();await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('真实 MCP 连接测试通过');await page.getByRole('button',{name:'保存连接'}).click();await page.reload();
 const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});await expect(card).toContainText('HTTP MCP');await card.getByRole('button',{name:'连接并浏览'}).click();
 await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'main.data'}).click();const table=page.getByLabel('数据源前100行').getByRole('table');
 await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('shipped_on');await expect(table).toContainText('2025-01-01T12:00:00');
 await page.screenshot({path:`${EVIDENCE}/http-mcp-navigation.png`,fullPage:true});
 const persisted=await page.evaluate(()=>JSON.stringify({...localStorage}));expect(persisted).not.toContain('test-only-browser-credential');expect(persisted).not.toContain('BROWSER_MCP');
 await card.getByRole('button',{name:'配置',exact:true}).click();await expect(page.getByLabel('MCP 服务地址')).toHaveValue(fixture.mcp_url);await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('button',{name:'取消配置'}).click();
 await card.getByRole('button',{name:'禁用',exact:true}).click();await expect(card.getByRole('button',{name:'连接并浏览'})).toBeDisabled();
});
test('PG configuration and unapproved HTTP fail actionably with preserved fields and visible mobile themes',async({page})=>{
 await page.setViewportSize({width:390,height:844});await open(page);await page.getByRole('button',{name:'新增数据源',exact:true}).click();await page.getByLabel('数据源类型').selectOption('postgresql');
 await page.getByLabel('连接名称').fill('PG待授权');await page.getByLabel('数据库主机').fill('127.0.0.1');await page.getByLabel('数据库名称').fill('demo');await page.getByLabel('数据库账号').fill('readonly');await page.getByLabel('后台凭证引用').fill('DEMO_PG');await page.getByLabel('TLS 安全模式').selectOption('disable');
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('TARGET_NOT_APPROVED');await expect(page.getByLabel('数据库名称')).toHaveValue('demo');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();
 await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');await expect(page.locator('input[type=password],input[type=date]')).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`${EVIDENCE}/postgres-config-mobile.png`,fullPage:true});
 await page.getByLabel('数据源类型').selectOption('http_mcp');await page.getByLabel('MCP 服务地址').fill('http://127.0.0.1:1/mcp');await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('TARGET_NOT_APPROVED');await expect(page.getByLabel('MCP 服务地址')).toHaveValue('http://127.0.0.1:1/mcp');
});

test('real credential-loss failure preserves profile, exposes retest state and recovers only after manual connect',async({page})=>{
 await open(page);await page.getByRole('button',{name:'配置 MCP',exact:true}).click();
 const name=`恢复测试-${Date.now()}`;await page.getByLabel('连接名称').fill(name);await page.getByLabel('MCP 服务地址').fill(fixture.mcp_url);await page.getByLabel('后台凭证引用').fill(fixture.secret_ref);await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();
 await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('真实 MCP 连接测试通过');await page.getByRole('button',{name:'保存连接'}).click();
 const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});
 const control=async enabled=>{const response=await page.request.post(fixture.api_url+'/fixture-only/credential',{headers:{'X-Workspace-Request':'1'},data:{enabled}});expect(response.status()).toBe(200);};
 await control(false);
 try{
  await card.getByRole('button',{name:'连接并浏览'}).click();await expect(page.getByRole('alert')).toContainText('CREDENTIAL_NOT_CONFIGURED');await expect(card).toContainText('上次读取失败，请重新连接');await expect(page.getByRole('region',{name:'数据表导航'})).toHaveCount(0);
  await control(true);await expect(page.getByRole('region',{name:'数据表导航'})).toHaveCount(0);await card.getByRole('button',{name:'连接并浏览'}).click();await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'main.data'}).click();await expect(page.getByLabel('数据源前100行').getByRole('table')).toContainText('2025-01-01T12:00:00');
  await expect(card).not.toContainText('上次读取失败');await page.screenshot({path:`${EVIDENCE}/worker-manual-recovery.png`,fullPage:true});await card.getByRole('button',{name:'禁用',exact:true}).click();
 }finally{await control(true);}
});

test('real stdio job loss expires old results, manual verify rebuilds and new preview succeeds',async({page})=>{
 await open(page);
 for(const pattern of ['**/api/v1/connectors/owned-synthetic**','**/api/v1/execution-previews**'])await page.route(pattern,async route=>{const url=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+url.pathname+url.search});await route.fulfill({response});});
 await page.getByRole('button',{name:'使用内置合成示例'}).click();await page.getByRole('button',{name:'验证数据源连接'}).click();await expect(page.getByText('已从真实 MCP 读取：',{exact:false})).toBeVisible();await page.getByRole('button',{name:'浏览数据表'}).click();
 await page.getByRole('button',{name:'查看前 100 行'}).click();await expect(page.getByText('SQL 已执行 · SUCCEEDED',{exact:true})).toBeVisible();
 const oldSummary=await (await page.request.get(fixture.api_url+'/api/v1/connectors/owned-synthetic')).json();
 const fault=await page.request.post(fixture.api_url+'/fixture-only/stdio-fault',{headers:{'X-Workspace-Request':'1'},data:{}});expect(fault.status()).toBe(200);
 await expect(page.getByText('连接失败',{exact:true})).toBeVisible({timeout:7000});await expect(page.getByLabel('只读预览数据')).toHaveCount(0);await expect(page.getByRole('button',{name:'查看前 100 行'})).toHaveCount(0);
 await page.getByRole('button',{name:'验证数据源连接'}).click();await expect(page.getByText('已从真实 MCP 读取：',{exact:false})).toBeVisible();
 const fresh=await (await page.request.get(fixture.api_url+'/api/v1/connectors/owned-synthetic')).json();expect(fresh.execution_generation).not.toBe(oldSummary.execution_generation);
 await page.getByRole('navigation',{name:'主导航'}).getByRole('button',{name:'取数工作台',exact:true}).click();await expect(page.getByText('SQL 曾完成，但 MCP 执行上下文已失效，旧预览不再可用。',{exact:false})).toBeVisible();await expect(page.getByText('SQL 已执行 · SUCCEEDED',{exact:true})).toHaveCount(0);
 await page.getByRole('navigation',{name:'主导航'}).getByRole('button',{name:'连接器',exact:true}).click();await page.getByRole('button',{name:'使用内置合成示例'}).click();await page.getByRole('button',{name:'验证数据源连接'}).click();await expect(page.getByText('已从真实 MCP 读取：',{exact:false})).toBeVisible();await page.getByRole('button',{name:'浏览数据表'}).click();await page.getByRole('button',{name:'查看前 100 行'}).click();await expect(page.getByText('SQL 已执行 · SUCCEEDED',{exact:true})).toBeVisible();await expect(page.getByRole('table')).toContainText('paid_amount_cents');
 await page.screenshot({path:`${EVIDENCE}/stdio-manual-recovery.png`,fullPage:true});
});

test('storage inventory is read-only, protects disabled saved data and has no delete action',async({page})=>{
 await page.setViewportSize({width:390,height:844});await open(page);
 await page.getByRole('button',{name:'存储与清理',exact:true}).click();const panel=page.getByRole('region',{name:'存储与清理盘点'});
 await expect(panel).toContainText('不执行删除');await expect(panel).toContainText('方案 A 已批准');await expect(panel).toContainText('自动回收尚未启用');await expect(panel.getByRole('button',{name:/删除|清空|立即清理/})).toHaveCount(0);
 await expect(page.locator('input[type=date]')).toHaveCount(0);await page.getByRole('button',{name:'白色主题'}).click();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/storage-inventory-mobile.png`,fullPage:true});await panel.getByRole('button',{name:'收起盘点'}).click();await expect(panel).toHaveCount(0);
});


test('real isolated cleanup receipt appears without enabling automatic cleanup',async({page})=>{
 await open(page);
 const result=await page.request.post(fixture.api_url+'/fixture-only/retention-example',{headers:{'X-Workspace-Request':'1'}});
 expect(result.status()).toBe(200);expect((await result.json()).state).toBe('DONE');
 await page.getByRole('button',{name:'存储与清理',exact:true}).click();
 const panel=page.getByRole('region',{name:'存储与清理盘点'});
 await expect(panel).toContainText('自动回收尚未启用');await expect(panel).toContainText('已完成 1 个目录');await expect(panel).toContainText('最近记录已完成');
 await expect(panel.getByRole('button',{name:/删除|立即清理/})).toHaveCount(0);
 await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');
 await page.screenshot({path:`${EVIDENCE}/retention-receipt-light.png`,fullPage:true});
});

test('expired draft refuses save, keeps fields and explicitly requires retest',async({page})=>{
 await open(page);await page.getByRole('button',{name:'配置 MCP',exact:true}).click();
 await page.getByLabel('连接名称').fill('过期演示');await page.getByLabel('MCP 服务地址').fill(fixture.mcp_url);await page.getByLabel('后台凭证引用').fill(fixture.secret_ref);
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('草稿有效 24 小时');
 const result=await page.request.post(fixture.api_url+'/fixture-only/retention-expire-tests',{headers:{'X-Workspace-Request':'1'}});expect(result.status()).toBe(200);
 await page.getByRole('button',{name:'保存连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('TEST_EXPIRED');await expect(page.getByRole('button',{name:'保存连接',exact:true})).toBeDisabled();
 await expect(page.getByLabel('连接名称')).toHaveValue('过期演示');await expect(page.getByLabel('MCP 服务地址')).toHaveValue(fixture.mcp_url);
 await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('草稿有效 24 小时');await expect(page.getByRole('button',{name:'保存连接',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'黑色主题'}).click();await expect(page.getByRole('button',{name:'黑色主题'})).toHaveAttribute('aria-pressed','true');
 await page.screenshot({path:`${EVIDENCE}/retention-draft-retested-dark.png`,fullPage:true});
});


test('legacy API expiry metadata omission is not advertised as active expiry support',async({page})=>{
 await open(page);
 // This one is an explicit compatibility-response fixture, not proof of live API capability.
 await page.route('**/api/v1/source-profiles/test',async route=>{
  const response=await route.fetch({url:fixture.api_url+'/api/v1/source-profiles/test'});
  const body=await response.json();delete body.expires_at;
  await route.fulfill({response,json:body});
 });
 await page.getByRole('button',{name:'配置 MCP',exact:true}).click();await page.getByLabel('连接名称').fill('旧API能力边界');await page.getByLabel('MCP 服务地址').fill(fixture.mcp_url);await page.getByLabel('后台凭证引用').fill(fixture.secret_ref);
 await page.getByRole('checkbox',{name:'我有权连接此数据源',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('当前运行 API 未报告草稿过期能力');await expect(page.getByRole('status')).not.toContainText('草稿有效 24 小时');
});
