import {test,expect} from '../apps/web/node_modules/@playwright/test/index.mjs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
const EVIDENCE=process.env.WORKSPACE_BROWSER_EVIDENCE;
let child,fixture,fixtureErrors='';
test.beforeAll(async()=>{
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>['SYSTEMROOT','WINDIR','TEMP','TMP','PATH'].includes(k.toUpperCase())));env.PYTHONUTF8='1';
 child=spawn(path.resolve('services/api/.venv/Scripts/python.exe'),['scripts/remote_browser_fixture.py'],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
 child.stderr.on('data',data=>{fixtureErrors+=data.toString();});
 fixture=await new Promise((resolve,reject)=>{let output='';const timeout=setTimeout(()=>reject(new Error('Owned real HTTP fixture did not start')),15000);child.stdout.on('data',data=>{output+=data;const line=output.split('\n')[0];try{const value=JSON.parse(line);clearTimeout(timeout);resolve(value);}catch{}});child.on('exit',()=>{clearTimeout(timeout);reject(new Error('Owned fixture exited before ready'));});});
});
test.beforeEach(async({page})=>{await page.route('**/api/v1/agent/capabilities',route=>route.fulfill({status:404,json:{code:'HTTP_ERROR',safe_message:'unconfigured Agent layout fixture'}}));});
test.afterEach(async({page})=>{await page.unrouteAll({behavior:'wait'});});
test.afterAll(async()=>{if(child&&child.exitCode===null){const exited=once(child,'exit');child.stdin.end('stop\n');await exited;expect(child.exitCode,fixtureErrors).toBe(0);}});
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


test('real default-cadence automatic worker cycle reports success while disabled saved data stays protected',async({page})=>{
 for(const pattern of ['**/api/v1/source-profiles**'])await page.route(pattern,async route=>{const url=new URL(route.request().url());const response=await route.fetch({url:fixture.automatic_api_url+url.pathname+url.search});await route.fulfill({response});});
 await expect.poll(async()=>{const value=await page.request.get(fixture.automatic_api_url+'/api/v1/source-profiles/retention');return (await value.json()).cycle_state;},{timeout:15000}).toBe('SUCCEEDED');
 await page.goto('http://127.0.0.1:5173/#connectors');await page.getByRole('button',{name:'存储与清理',exact:true}).click();
 const panel=page.getByRole('region',{name:'存储与清理盘点'});await expect(panel).toContainText('自动回收已启用');await expect(panel).toContainText('最近自动周期：SUCCEEDED');await expect(panel).toContainText('间隔 600 秒');await expect(panel).toContainText('本周期回收 1 个目录');
 const status=await page.request.get(fixture.automatic_api_url+'/api/v1/source-profiles/storage');const value=await status.json();expect(value.saved_profiles).toBe(1);expect(value.uploads.referenced_folders).toBe(1);expect(value.snapshots.referenced_folders).toBe(1);expect(value.retention.completed_cleanup_folders).toBe(1);
 await expect(panel.getByRole('button',{name:/删除|立即清理/})).toHaveCount(0);await page.getByText(/历史本地来源.*保留已有配置/).click();await expect(page.getByRole('article').filter({hasText:'protected isolated source'})).toContainText('已禁用');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/automatic-retention-light.png`,fullPage:true});
});


test('model readiness comes from actual isolated API with empty password and no automatic generation',async({page})=>{
 await page.route('**/api/v1/model-service/status',async route=>{const response=await route.fetch({url:fixture.api_url+'/api/v1/model-service/status'});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();
 const status=page.getByLabel('模型服务实际状态');await expect(status).toContainText('尚未配置');
 await expect(status).toContainText('未验证');await expect(status).toContainText('在模型服务中填写专用Key并保存');await expect(page.getByLabel('设置页面')).toContainText('保存配置不会调用模型');
 await expect(status.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(status.getByLabel('专用模型 API Key')).toHaveValue('');
 await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await status.getByRole('button',{name:'刷新模型状态'}).click();await expect(status).toContainText('尚未配置');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/model-readiness-light.png`,fullPage:true});
});


test('Responses candidate is disclosed from real isolated status without enabling generation',async({page})=>{
 await page.route('**/api/v1/model-service/status',async route=>{const response=await route.fetch({url:fixture.automatic_api_url+'/api/v1/model-service/status'});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();
 const status=page.getByLabel('模型服务实际状态');await expect(status).toContainText('缺少专用Key');
 await expect(status).toContainText('openai_responses');await expect(status).toContainText('gpt-6.1-sol[1M]');
 await expect(status).toContainText('尚未实测');await expect(status).toContainText('未验证');
 await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await expect(status.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(status.getByLabel('专用模型 API Key')).toHaveValue('');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/responses-candidate-light.png`,fullPage:true});
});


test('estimated model test uses real product route and preserves same receipt without a second reservation',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await expect(panel).toContainText('目标 $15');const button=panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true});
 await expect(button).toBeDisabled();await panel.getByLabel('接受估算费用进行最小模型测试').check();await button.click();
 const receipt=panel.getByLabel('模型测试回执');await expect(receipt).toContainText('最小模型生成已成功，不代表已取数');await expect(receipt).toContainText('isolated fixture OK');
 await expect(panel).toContainText('估算预留 $0.25');await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(panel.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(panel.getByLabel('专用模型 API Key')).toHaveValue('');await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/estimated-model-test-light.png`,fullPage:true});
});


test('explicit Claude preset shows bearer Haiku and safe 401 refusal without protocol fallback',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-claude-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await expect(panel).toContainText('anthropic_messages');await expect(panel).toContainText('bearer');await expect(panel).toContainText('claude-haiku-4-5');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 await expect(panel.getByLabel('模型测试回执')).toContainText('MODEL_ACCESS_DENIED（网关HTTP 401）');
 await expect(panel).not.toContainText('fixture-only raw auth body');await expect(panel).toContainText('未验证');
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(page.getByLabel('切换模型')).toHaveCount(0);await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/claude-preset-denied-light.png`,fullPage:true});
});


test('invalid model response shows safe categories without exposing partial output or retrying',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-diagnostics',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 const diagnostic=panel.getByLabel('模型响应安全诊断');await expect(diagnostic).toContainText('incomplete_output');await expect(diagnostic).toContainText('max_tokens');
 await expect(diagnostic).toContainText('128');await expect(panel).not.toContainText('fixture partial output is not verified');
 await expect(panel).toContainText('MODEL_RESPONSE_INVALID');await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await page.getByRole('button',{name:'白色主题'}).click();const rid=await panel.getByLabel('模型测试回执').locator('code').textContent();
 const read=await page.request.get(fixture.api_url+'/api/v1/model-service/tests/'+rid+'/diagnostics');
 expect(read.ok()).toBeTruthy();const readBody=await read.json();expect(readBody.diagnostics.reason).toBe('incomplete_output');expect(readBody.generation).toBeUndefined();
 await page.screenshot({path:`${EVIDENCE}/model-response-diagnostics-light.png`,fullPage:true});
});


test('observed gateway alias preserves both model identities and never exposes reasoning',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-observed-model-alias',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 const receipt=panel.getByLabel('模型测试回执');await expect(receipt).toContainText('最小模型生成已成功');
 await expect(receipt).toContainText('deepseek-v4.1-flash');await expect(receipt).toContainText('deepseek-v4-1-flash-261017');
 await expect(receipt).toContainText('observed_gateway_alias');await expect(receipt.locator('pre')).toHaveText('OK');
 await expect(panel).not.toContainText('fixture hidden reasoning');await expect(panel).not.toContainText('fixture signature');
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(page.getByLabel('切换模型')).toHaveCount(0);await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/observed-model-alias-light.png`,fullPage:true});
});


test('generic personal BYOK config saves session key without restart or browser persistence and tests explicitly',async({page})=>{
 const initialized=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(initialized.ok()).toBeTruthy();
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 let rejectEnableOnce=true;
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const options={url:fixture.api_url+u.pathname+u.search};if(u.pathname.endsWith('/connection/enabled')&&rejectEnableOnce){rejectEnableOnce=false;options.postData=JSON.stringify({...route.request().postDataJSON(),config_version:'expired-fixture-version'});}const response=await route.fetch(options);await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();
 const baseline=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;
 const form=page.getByLabel('快捷模型接入');await form.getByLabel('模型服务厂商').selectOption('custom');
 await form.getByLabel('模型 API 协议').selectOption('openai_chat_completions');await form.getByLabel('模型 API 地址').fill('https://api.example.com/v1/chat/completions');await form.getByLabel('模型名称',{exact:true}).fill('fixture-model');
 const key=form.getByLabel('专用模型 API Key');await expect(key).toHaveAttribute('type','password');await key.fill('fixture-only-personal-key');await form.getByLabel('同意模型测试外发和估算').check();
 await form.getByRole('button',{name:'保存连接（不调用模型）'}).click();await expect(form).toContainText('已保存到本次后端会话');await expect(key).toHaveValue('');
 let status=await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json();expect(status.budget.reserved_requests).toBe(baseline);expect(status.generation_verified).toBe(false);
 const browserStorage=await page.evaluate(()=>JSON.stringify({local:{...localStorage},session:{...sessionStorage}}));expect(browserStorage).not.toContain('fixture-only-personal-key');
 // Test fixture explicitly injects a transport after saving, real product route handles every call.
 const inject=await page.request.post(fixture.api_url+'/fixture-only/inject-personal-chat-transport',{headers:{'X-Workspace-Request':'1'}});expect(inject.ok()).toBeTruthy();
 const panel=page.getByLabel('模型服务实际状态');await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 await expect(panel.getByLabel('模型测试回执')).toContainText('最小模型生成已成功');await expect(panel.getByLabel('模型测试回执')).toContainText('personal fixture OK');
 await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await panel.getByRole('button',{name:'启用已实测模型',exact:true}).click();
 await expect(panel).toContainText('MODEL_TEST_CONTEXT_EXPIRED');await expect(page.getByLabel('切换模型')).toHaveCount(0);
 await panel.getByRole('button',{name:'启用已实测模型',exact:true}).click();
 await page.getByRole('button',{name:'返回工作台',exact:true}).click();await expect(page.getByLabel('切换模型')).toBeEnabled();
 const catalog=await (await page.request.get(fixture.api_url+'/api/v1/model-service/catalog')).json();
 expect(catalog.models).toHaveLength(1);expect(catalog.models[0].query_available).toBe(false);
 await page.getByLabel('切换模型').selectOption(catalog.models[0].id);
 await expect(page.getByText('已选实测模型 · 问数尚未接入，不调用',{exact:true})).toBeVisible();
 expect((await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests).toBe(baseline+1);
 await page.reload();await expect(page.getByLabel('切换模型')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();await expect(page.getByLabel('设置页面')).toBeVisible();await page.getByText('协议、能力与会话限制',{exact:true}).click();
 await panel.getByRole('button',{name:'禁用模型（旧测试失效）',exact:true}).click();
 await expect(page.getByLabel('切换模型')).toHaveCount(0);await expect(panel.getByRole('button',{name:'启用已实测模型',exact:true})).toBeDisabled();
 await form.getByRole('button',{name:'清除会话 Key'}).click();await expect(form).toContainText('Key已清除');
 status=await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json();expect(status.credential_configured).toBe(false);expect(status.budget.reserved_requests).toBe(baseline+1);expect(status.generation_verified).toBe(false);
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/generic-byok-mobile.png`,fullPage:true});
});

test('left settings keeps conversation clean, model IDs are free for every preset and secrets are cleared on leave',async({page})=>{
 const initialized=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(initialized.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 const summary=page.getByRole('complementary',{name:'会话摘要'});await expect(summary.locator('input[type=password]')).toHaveCount(0);await expect(summary).not.toContainText('模型服务与连接测试');
 await page.getByLabel('业务问题').fill('保留这段未发送问题');
 const sidebar=page.getByRole('complementary',{name:'工作空间侧栏'});await sidebar.getByRole('button',{name:'设置',exact:true}).click();
 const settings=page.getByLabel('设置页面');await expect(settings).toBeVisible();await expect(page.getByLabel('业务问题')).toHaveCount(0);await expect(summary).toHaveCount(0);
 const form=page.getByLabel('快捷模型接入');const model=form.getByLabel('模型名称',{exact:true});
 for(const preset of ['openai','deepseek','anthropic','ai_plan','custom']){
  await form.getByLabel('模型服务厂商').selectOption(preset);await expect(model).toBeEnabled();await expect(model).toHaveValue('');await model.fill('my-account-model');await expect(model).toHaveValue('my-account-model');
 }
 await form.getByLabel('模型服务厂商').selectOption('ai_plan');await model.fill('claude-user-selected-model');
 await expect(form.getByLabel('模型 API 地址')).toBeDisabled();await expect(form.getByLabel('模型 API 协议')).toBeDisabled();
 await form.getByLabel('专用模型 API Key').fill('fixture-only-settings-key');await form.getByLabel('同意模型测试外发和估算').check();
 const before=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;
 await form.getByRole('button',{name:'保存连接（不调用模型）'}).click();await expect(form).toContainText('已保存到本次后端会话');
 const state=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json());expect(state.model_id).toBe('claude-user-selected-model');expect(state.generation_verified).toBe(false);expect(state.budget.reserved_requests).toBe(before);
 await form.getByLabel('模型名称',{exact:true}).fill('a-new-model');await expect(form.getByLabel('同意模型测试外发和估算')).not.toBeChecked();
 await form.getByLabel('专用模型 API Key').fill('fixture-only-unsaved-key');
 await page.getByRole('button',{name:'返回工作台',exact:true}).click();await expect(page.getByLabel('业务问题')).toHaveValue('保留这段未发送问题');
 await sidebar.getByRole('button',{name:'设置',exact:true}).click();await expect(form.getByLabel('专用模型 API Key')).toHaveValue('');await expect(model).toHaveValue('claude-user-selected-model');
 const stored=await page.evaluate(()=>JSON.stringify({local:{...localStorage},session:{...sessionStorage}}));expect(stored).not.toContain('fixture-only-settings-key');expect(stored).not.toContain('fixture-only-unsaved-key');
 await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');await page.screenshot({path:`${EVIDENCE}/settings-models-light.png`,fullPage:true});
 await page.getByRole('button',{name:'黑色主题'}).click();await page.screenshot({path:`${EVIDENCE}/settings-models-dark.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/settings-models-mobile.png`,fullPage:true});
 await page.reload();await expect(settings).toBeVisible();await expect(model).toHaveValue('claude-user-selected-model');await expect(form.getByLabel('专用模型 API Key')).toHaveValue('');
 expect((await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests).toBe(before);
});

test('settings refuses silent legacy model lock and prevents leaving an in-flight save',async({page})=>{
 const initialized=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(initialized.ok()).toBeTruthy();
 let legacy=true,releaseSave;
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());
  if(u.pathname.endsWith('/connection')&&route.request().method()==='POST')await new Promise(resolve=>{releaseSave=resolve;});
  const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});
  if(u.pathname.endsWith('/status')&&legacy){const value=await response.json();delete value.model_name_editable;await route.fulfill({response,json:value});}else await route.fulfill({response});
 });
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();await page.getByRole('button',{name:'设置',exact:true}).click();const form=page.getByLabel('快捷模型接入');
 await expect(form.getByLabel('模型服务厂商')).toBeEnabled();await form.getByLabel('模型服务厂商').selectOption('ai_plan');await form.getByLabel('模型名称',{exact:true}).fill('a-user-chosen-model');
 await expect(form).toContainText('当前后端仍是固定模型版本');
 await form.getByLabel('专用模型 API Key').fill('fixture-only-legacy-key');await form.getByLabel('同意模型测试外发和估算').check();await expect(form.getByRole('button',{name:'保存连接（不调用模型）'})).toBeDisabled();
 legacy=false;await page.getByRole('button',{name:'刷新模型状态'}).click();await expect(form).not.toContainText('当前后端仍是固定模型版本');
 await form.getByLabel('模型服务厂商').selectOption('custom');await form.getByLabel('模型 API 地址').fill('https://api.example.com/v1/chat/completions');await form.getByLabel('模型名称',{exact:true}).fill('fixture-model');await form.getByLabel('专用模型 API Key').fill('fixture-only-save-key');await form.getByLabel('同意模型测试外发和估算').check();
 await form.getByRole('button',{name:'保存连接（不调用模型）'}).click();
 try{await expect.poll(()=>typeof releaseSave).toBe('function');await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeDisabled();await expect(page.getByRole('navigation',{name:'主导航'}).getByRole('button',{name:'取数工作台',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'设置',exact:true})).toBeDisabled();await page.goBack();await expect(page.getByLabel('设置页面')).toBeVisible();await expect(page).toHaveURL(/#settings$/);}finally{releaseSave?.();}
 await expect(form).toContainText('已保存到本次后端会话');await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'返回工作台',exact:true}).click();await expect(page.getByLabel('业务问题')).toBeEnabled();
});

test('real Messages stream snapshots complete or cancel without retrying, thought leakage or fake SQL',async({page})=>{
 const enable=async mode=>{const r=await page.request.post(fixture.api_url+'/fixture-only/enable-stream-test',{headers:{'X-Workspace-Request':'1'},data:{mode}});expect(r.ok()).toBeTruthy();};
 await enable('complete');
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/#settings');const panel=page.getByLabel('真实流式连接测试');
 await expect(panel.getByRole('button',{name:'开始流式测试（估算 $0.25）',exact:true})).toBeDisabled();
 const baseline=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;
 await panel.getByLabel('同意固定文本流式测试').check();await panel.getByRole('button',{name:'开始流式测试（估算 $0.25）',exact:true}).click();
 await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeDisabled();
 await expect(panel.getByLabel('流式测试回执')).toContainText('流式完成已确认 · SQL未执行');await expect(panel).toContainText('Live fixture text safe.');
 await panel.getByRole('button',{name:'读取同一流式回执',exact:true}).click();await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeEnabled();
 let status=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json());expect(status.stream_verified).toBe(true);expect(status.budget.reserved_requests).toBe(baseline+1);
 await panel.scrollIntoViewIfNeeded();await page.screenshot({path:`${EVIDENCE}/stream-complete-settings.png`,fullPage:true});
 await enable('cancel');await page.reload();await panel.getByLabel('同意固定文本流式测试').check();await panel.getByRole('button',{name:'开始流式测试（估算 $0.25）',exact:true}).click();
 await expect(panel.getByLabel('流式测试回执')).toContainText('Live fixture text safe.');
 await panel.getByRole('button',{name:'取消流式测试',exact:true}).click();await expect(panel.getByLabel('流式测试回执')).toContainText('部分输出，未完成 · MODEL_STREAM_CANCELLED');await expect(panel.getByLabel('流式安全诊断')).toContainText('cancelled');
 await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeEnabled();
 status=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json());expect(status.stream_verified).toBe(false);expect(status.generation_verified).toBe(false);expect(status.budget.reserved_requests).toBe(baseline+2);
 expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('fixture-only-stream-key');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await panel.scrollIntoViewIfNeeded();expect(await panel.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/stream-cancel-mobile.png`,fullPage:true});
});

test('stream auth refusal shows safe category and same receipt read never bills again',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-stream-test',{headers:{'X-Workspace-Request':'1'},data:{mode:'denied'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/#settings');const panel=page.getByLabel('真实流式连接测试');
 const before=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;
 await panel.getByLabel('同意固定文本流式测试').check();await panel.getByRole('button',{name:'开始流式测试（估算 $0.25）',exact:true}).click();
 await expect(panel.getByLabel('流式测试回执')).toContainText('MODEL_ACCESS_DENIED');await expect(panel.getByLabel('流式安全诊断')).toContainText('upstream_refused · HTTP 403');
 await expect(panel).not.toContainText('fixture-private-error');await expect(panel).not.toContainText('fixture-only-stream-key');
 await panel.getByRole('button',{name:'读取同一流式回执',exact:true}).click();await expect(page.getByRole('button',{name:'返回工作台',exact:true})).toBeEnabled();
 const after=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget;
 expect(after.reserved_requests).toBe(before+1);await page.screenshot({path:`${EVIDENCE}/stream-safe-refusal.png`,fullPage:true});
});

test('semantic metadata draft conflict repair human publish immutable version and restart use real MCP without row query',async({page})=>{
 const created=await page.request.post(fixture.api_url+'/fixture-only/semantic-source',{headers:{'X-Workspace-Request':'1'},data:{}});expect(created.ok()).toBeTruthy();const source=(await created.json()).id;
 for(const pattern of ['**/api/v1/semantics**','**/api/v1/source-profiles**'])await page.route(pattern,async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 const rowCalls=[];page.on('request',r=>{if(r.url().includes('/preview')||r.url().includes('/execution-previews'))rowCalls.push(r.url());});
 await page.goto('http://127.0.0.1:5173/#knowledge');const panel=page.getByLabel('企业语义知识库');await expect(panel).toBeVisible();
 await panel.getByLabel('语义数据源').selectOption(source);await panel.getByLabel('语义数据表').selectOption('t0');await expect(panel).toContainText('真实字段（仅元数据，未读取行）');await expect(panel).toContainText('created_at');
 await panel.getByLabel('语义包名称').fill('测试订单口径');await panel.getByLabel('业务域代号').fill('fixture_orders');await panel.getByLabel('口径负责人说明').fill('开发走查，不是用户研究');await panel.getByLabel('粒度字段 id',{exact:true}).check();await panel.getByLabel('粒度含义').fill('每条记录为一个声明ID，唯一性未统计验证');
 const first=panel.getByLabel('指标定义 1',{exact:true});await first.getByLabel('指标名称',{exact:true}).fill('记录数量');await first.getByLabel('指标代号',{exact:true}).fill('row_count');await first.getByLabel('指标单位',{exact:true}).fill('条');await first.getByLabel('指标别名',{exact:true}).fill('数量');
 await panel.getByRole('button',{name:'添加指标',exact:true}).click();const second=panel.getByLabel('指标定义 2',{exact:true});await second.getByLabel('指标名称',{exact:true}).fill('同名数量');await second.getByLabel('指标代号',{exact:true}).fill('row_total');await second.getByLabel('指标单位',{exact:true}).fill('条');await second.getByLabel('指标别名',{exact:true}).fill('数量');
 await panel.getByRole('button',{name:'校验实际字段与口径',exact:true}).click();await expect(panel.getByLabel('语义校验结果')).toContainText('ALIAS_CONFLICT');await expect(panel.getByRole('button',{name:'发布语义版本',exact:true})).toHaveCount(0);
 await second.getByLabel('指标别名',{exact:true}).fill('独立数量');await panel.getByRole('button',{name:'校验实际字段与口径',exact:true}).click();await expect(panel.getByLabel('语义校验结果')).toContainText('字段与结构校验通过，尚未批准');
 await expect(panel.getByRole('button',{name:'发布语义版本',exact:true})).toBeDisabled();await panel.getByLabel('批准并发布语义定义').check();await panel.getByRole('button',{name:'发布语义版本',exact:true}).click();await expect(panel).toContainText('已发布版本 v1');
 let versions=(await (await page.request.get(fixture.api_url+'/api/v1/semantics')).json()).versions;expect(versions).toHaveLength(1);expect(versions[0].schema_snapshot.rows_read).toBe(false);expect(versions[0].execution_available).toBe(false);
 const card=panel.getByLabel('已发布语义版本').getByRole('article').filter({hasText:'测试订单口径 · v1'});await card.getByRole('button',{name:'核验版本映射',exact:true}).click();await expect(panel).toContainText('当前字段映射核验通过');
 await card.getByRole('button',{name:'编辑为新版本',exact:true}).click();await panel.getByLabel('语义包名称').fill('测试口径修订');await panel.getByRole('button',{name:'校验实际字段与口径',exact:true}).click();await panel.getByLabel('批准并发布语义定义').check();await panel.getByRole('button',{name:'发布语义版本',exact:true}).click();await expect(panel).toContainText('已发布版本 v2');
 versions=(await (await page.request.get(fixture.api_url+'/api/v1/semantics')).json()).versions;expect(versions.map(v=>v.version)).toEqual([2,1]);expect(versions[1].contract.name).toBe('测试订单口径');
 const latestCard=panel.getByLabel('已发布语义版本').getByRole('article').filter({hasText:'测试口径修订 · v2'});
 await latestCard.getByRole('button',{name:'停用语义包',exact:true}).click();await expect(panel).toContainText('语义包已停用');await expect(latestCard.getByRole('button',{name:'核验版本映射',exact:true})).toBeDisabled();
 const denied=await page.request.post(fixture.api_url+`/api/v1/semantics/versions/${versions[0].id}/resolve`,{headers:{'X-Workspace-Request':'1'},data:{}});expect(denied.status()).toBe(409);expect((await denied.json()).code).toBe('SEMANTIC_DISABLED');
 await latestCard.getByRole('button',{name:'重验并启用语义包',exact:true}).click();await expect(panel).toContainText('语义包已重新核验启用');await expect(latestCard.getByRole('button',{name:'核验版本映射',exact:true})).toBeEnabled();await expect(card.getByRole('button',{name:'核验版本映射',exact:true})).toBeDisabled();
 const restart=await page.request.post(fixture.api_url+'/fixture-only/semantic-restart',{headers:{'X-Workspace-Request':'1'},data:{}});expect(restart.ok()).toBeTruthy();await page.reload();await expect(panel.getByLabel('已发布语义版本')).toContainText('测试口径修订 · v2');
 expect(rowCalls).toEqual([]);await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/semantics-published-light.png`,fullPage:true});await page.getByRole('button',{name:'黑色主题'}).click();await page.screenshot({path:`${EVIDENCE}/semantics-published-dark.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await panel.getByLabel('已发布语义版本').scrollIntoViewIfNeeded();await page.screenshot({path:`${EVIDENCE}/semantics-published-mobile.png`,fullPage:true});
});

test('semantic JSON import remains draft, typed ratio aliases edit correctly and disabled source rejects resolve',async({page})=>{
 const r=await page.request.post(fixture.api_url+'/fixture-only/semantic-source',{headers:{'X-Workspace-Request':'1'},data:{}});expect(r.ok()).toBeTruthy();const source=(await r.json()).id;
 for(const pattern of ['**/api/v1/semantics**','**/api/v1/source-profiles**'])await page.route(pattern,async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/#knowledge');const panel=page.getByLabel('企业语义知识库');await panel.getByText('导入结构化定义（可选）',{exact:true}).click();
 const body={domain:'import_fixture',name:'导入成本占比',owner_note:'fixture local review',source_id:source,table_id:'t0',grain:['id'],grain_note:'declared order id, uniqueness not inferred',metrics:[{id:'cost_ratio',name:'成本占比',operator:'ratio',numerator:'cost',denominator:'amount',unit:'比率',additive:false}]};
 const importFile=async value=>{await panel.getByLabel('导入语义定义JSON').setInputFiles({name:'definition.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});};
 await importFile({...body,api_key:'never-store-fixture-key'});await expect(panel.getByRole('alert')).toContainText('INVALID_REQUEST');expect((await (await page.request.get(fixture.api_url+'/api/v1/semantics')).json()).versions.some(v=>v.contract.domain==='import_fixture')).toBe(false);
 await importFile(body);await expect(panel).toContainText('定义已导入为草稿，尚未校验或发布');await expect(panel.getByLabel('语义校验结果')).toHaveCount(0);await expect(panel.getByRole('button',{name:'发布语义版本',exact:true})).toHaveCount(0);
 const metric=panel.getByLabel('指标定义 1',{exact:true});await expect(metric.getByLabel('分子字段')).toHaveValue('cost');await expect(metric.getByLabel('分母字段')).toHaveValue('amount');await expect(metric).toContainText('分母为零时结果为空');
 await metric.getByLabel('指标别名').fill('');await metric.getByLabel('指标别名').pressSequentially('ratio,cost share');await expect(metric.getByLabel('指标别名')).toHaveValue('ratio,cost share');
 await panel.getByRole('button',{name:'校验实际字段与口径',exact:true}).click();await expect(panel.getByLabel('语义校验结果')).toContainText('尚未批准');await panel.getByLabel('批准并发布语义定义').check();await panel.getByRole('button',{name:'发布语义版本',exact:true}).click();await expect(panel).toContainText('已发布版本 v1');
 const versions=(await (await page.request.get(fixture.api_url+'/api/v1/semantics')).json()).versions;const version=versions.find(v=>v.contract.domain==='import_fixture');expect(version.contract.metrics[0].aliases).toEqual(['ratio','cost share']);expect(version.contract.time).toBeNull();expect(version.contract.metrics[0].denominator_zero).toBe('null');
 const disable=await page.request.post(fixture.api_url+`/api/v1/source-profiles/${source}/toggle`,{headers:{'X-Workspace-Request':'1'},data:{enabled:false,expected_version:1}});expect(disable.ok()).toBeTruthy();
 const card=panel.getByLabel('已发布语义版本').getByRole('article').filter({hasText:'导入成本占比 · v1'});await card.getByRole('button',{name:'核验版本映射',exact:true}).click();await expect(panel.getByRole('alert')).toContainText('SOURCE_DISABLED');
 expect((await (await page.request.get(fixture.api_url+`/api/v1/semantics/versions/${version.id}`)).json()).id).toBe(version.id);
});

test('LangGraph workbench uses approved metric, human confirms full150rowMCP query and refresh never repeats',async({page})=>{
 const r=await page.request.post(fixture.api_url+'/fixture-only/agent-ready',{headers:{'X-Workspace-Request':'1'},data:{}});expect(r.ok()).toBeTruthy();const ready=await r.json();
 for(const pattern of ['**/api/v1/agent/**','**/api/v1/model-service/**','**/api/v1/semantics**','**/api/v1/source-profiles**'])await page.route(pattern,async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'新建会话',exact:false}).click();await expect(page.getByLabel('选择问数语义版本')).toBeVisible();
 await page.getByLabel('业务问题').fill('尚未选定口径的问题');await page.getByRole('button',{name:'发送问题',exact:true}).click();await expect(page.getByText('请先选择已发布、启用的问数口径；可在知识库维护定义。未调用模型或执行SQL。',{exact:true})).toBeVisible();expect((await (await page.request.get(fixture.api_url+'/api/v1/agent/tasks')).json()).tasks).toHaveLength(0);
await page.getByLabel('选择问数语义版本').selectOption(ready.semantic_version_id);await page.getByLabel('切换模型').selectOption(ready.model_ref);
 await page.getByLabel(`包含来源 ${ready.source_name}`).check();await page.getByLabel('同意问数模型外发和估算').check();await page.getByLabel('业务问题').fill('请计算总金额，全部数据');await page.getByRole('button',{name:'发送问题',exact:true}).click();
 const card=page.getByLabel('受控问数任务');await expect(card).toContainText('等待确认执行');await expect(card).toContainText('全表，无时间筛选');await expect(card.getByRole('button',{name:'确认执行查询'})).toBeDisabled();
 let tasks=(await (await page.request.get(fixture.api_url+'/api/v1/agent/tasks')).json()).tasks;expect(tasks).toHaveLength(1);expect(tasks[0].sql_executed).toBe(false);
 const before=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;expect(before).toBe(1);
 await page.reload();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();await page.locator('.history-select').filter({hasText:'请计算总金额'}).click();await expect(card).toContainText('等待确认执行');
 await card.getByLabel('确认本次口径与查询执行').check();await card.getByRole('button',{name:'确认执行查询',exact:true}).click();await expect(card).toContainText('查询完成',{timeout:20000});await expect(card.getByRole('table',{name:'受控查询完整聚合结果'})).toContainText('11325');await expect(card).toContainText('输入 150 行 · 匹配 150 行');await expect(page.getByRole('region',{name:'执行进度'})).toContainText('SQL已执行');await expect(page.getByRole('complementary',{name:'会话摘要'})).toContainText('已收到实际执行成功回执');
 tasks=(await (await page.request.get(fixture.api_url+'/api/v1/agent/tasks')).json()).tasks;const t=tasks[0];expect(t.result.rows).toEqual([[11325]]);const execution=t.execution_receipt.task.id;
 const repeated=await page.request.post(fixture.api_url+`/api/v1/agent/tasks/${t.id}/confirm`,{headers:{'X-Workspace-Request':'1'},data:{plan_hash:t.plan_hash,execution_generation:t.execution_generation,confirm_execute:true}});expect((await repeated.json()).execution_receipt.task.id).toBe(execution);
 expect((await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests).toBe(before);
 expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('11325');expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('fake-fixture-agent-key');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/agent-whole-input-result-light.png`,fullPage:true});await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await card.scrollIntoViewIfNeeded();await page.screenshot({path:`${EVIDENCE}/agent-result-mobile.png`,fullPage:true});
});

test('Agent incomplete model output gives safe read-only diagnostic without SQL or extra retry',async({page})=>{
 const r=await page.request.post(fixture.api_url+'/fixture-only/agent-ready',{headers:{'X-Workspace-Request':'1'},data:{mode:'incomplete'}});expect(r.ok()).toBeTruthy();const ready=await r.json();
 for(const pattern of ['**/api/v1/agent/**','**/api/v1/model-service/**','**/api/v1/semantics**','**/api/v1/source-profiles**'])await page.route(pattern,async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await page.getByRole('button',{name:'新建会话',exact:false}).click();await page.getByLabel('选择问数语义版本').selectOption(ready.semantic_version_id);await page.getByLabel('切换模型').selectOption(ready.model_ref);await page.getByLabel(`包含来源 ${ready.source_name}`).check();await page.getByLabel('同意问数模型外发和估算').check();await page.getByLabel('业务问题').fill('请统计总金额');
 const before=(await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests;
 await page.getByRole('button',{name:'发送问题',exact:true}).click();const card=page.getByLabel('受控问数任务');await expect(card).toContainText('MODEL_RESPONSE_INVALID');await expect(card.getByLabel('问数模型安全诊断')).toContainText('incomplete_output');await expect(card).not.toContainText('fake-fixture-agent-key');await expect(card.getByRole('button',{name:'确认执行查询'})).toHaveCount(0);
 const tasks=(await (await page.request.get(fixture.api_url+'/api/v1/agent/tasks')).json()).tasks;const current=tasks.find(t=>t.model_ref===ready.model_ref&&t.phase==='FAILED');expect(current.sql_executed).toBe(false);expect(current.execution_receipt).toBeNull();expect(current.result).toBeNull();
 await page.request.get(fixture.api_url+`/api/v1/agent/tasks/${current.id}`);expect((await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json()).budget.reserved_requests).toBe(before+1);
 await page.screenshot({path:`${EVIDENCE}/agent-incomplete-model-diagnostic.png`,fullPage:true});
});
