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


test('model readiness comes from actual isolated API and never accepts browser keys or claims generation',async({page})=>{
 await page.route('**/api/v1/model-service/status',async route=>{const response=await route.fetch({url:fixture.api_url+'/api/v1/model-service/status'});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();
 const status=page.getByLabel('模型服务实际状态');await expect(status).toContainText('尚未配置');
 await expect(status).toContainText('未验证');await expect(status).toContainText('start-workspace-model.cmd');
 await expect(status.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(status.getByLabel('专用模型 API Key')).toHaveValue('');
 await expect(page.getByLabel('切换模型')).toBeDisabled();
 await status.getByRole('button',{name:'刷新模型状态'}).click();await expect(status).toContainText('尚未配置');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/model-readiness-light.png`,fullPage:true});
});


test('Responses candidate is disclosed from real isolated status without enabling generation',async({page})=>{
 await page.route('**/api/v1/model-service/status',async route=>{const response=await route.fetch({url:fixture.automatic_api_url+'/api/v1/model-service/status'});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();
 const status=page.getByLabel('模型服务实际状态');await expect(status).toContainText('缺少专用Key');
 await expect(status).toContainText('openai_responses');await expect(status).toContainText('gpt-6.1-sol[1M]');
 await expect(status).toContainText('尚未实测');await expect(status).toContainText('未验证');
 await expect(page.getByLabel('切换模型')).toBeDisabled();
 await expect(status.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(status.getByLabel('专用模型 API Key')).toHaveValue('');
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/responses-candidate-light.png`,fullPage:true});
});


test('estimated model test uses real product route and preserves same receipt without a second reservation',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await expect(panel).toContainText('目标 $15');const button=panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true});
 await expect(button).toBeDisabled();await panel.getByLabel('接受估算费用进行最小模型测试').check();await button.click();
 const receipt=panel.getByLabel('模型测试回执');await expect(receipt).toContainText('最小模型生成已成功，不代表已取数');await expect(receipt).toContainText('isolated fixture OK');
 await expect(panel).toContainText('估算预留 $0.25');await expect(page.getByLabel('切换模型')).toBeDisabled();
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(panel.getByLabel('专用模型 API Key')).toHaveAttribute('type','password');await expect(panel.getByLabel('专用模型 API Key')).toHaveValue('');await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/estimated-model-test-light.png`,fullPage:true});
});


test('explicit Claude preset shows bearer Haiku and safe 401 refusal without protocol fallback',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-claude-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await expect(panel).toContainText('anthropic_messages');await expect(panel).toContainText('bearer');await expect(panel).toContainText('claude-haiku-4-5');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 await expect(panel.getByLabel('模型测试回执')).toContainText('MODEL_ACCESS_DENIED（网关HTTP 401）');
 await expect(panel).not.toContainText('fixture-only raw auth body');await expect(panel).toContainText('未验证');
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(page.getByLabel('切换模型')).toBeDisabled();await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/claude-preset-denied-light.png`,fullPage:true});
});


test('invalid model response shows safe categories without exposing partial output or retrying',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-diagnostics',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();
 await page.getByRole('button',{name:'模型服务',exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 const diagnostic=panel.getByLabel('模型响应安全诊断');await expect(diagnostic).toContainText('incomplete_output');await expect(diagnostic).toContainText('max_tokens');
 await expect(diagnostic).toContainText('128');await expect(panel).not.toContainText('fixture partial output is not verified');
 await expect(panel).toContainText('MODEL_RESPONSE_INVALID');await expect(page.getByLabel('切换模型')).toBeDisabled();
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
 await page.getByRole('button',{name:'模型服务',exact:true}).click();const panel=page.getByLabel('模型服务实际状态');
 await panel.getByLabel('接受估算费用进行最小模型测试').check();await panel.getByRole('button',{name:'测试模型连接（估算 $0.25）',exact:true}).click();
 const receipt=panel.getByLabel('模型测试回执');await expect(receipt).toContainText('最小模型生成已成功');
 await expect(receipt).toContainText('deepseek-v4.1-flash');await expect(receipt).toContainText('deepseek-v4-1-flash-261017');
 await expect(receipt).toContainText('observed_gateway_alias');await expect(receipt.locator('pre')).toHaveText('OK');
 await expect(panel).not.toContainText('fixture hidden reasoning');await expect(panel).not.toContainText('fixture signature');
 await panel.getByRole('button',{name:'读取同一测试请求'}).click();await expect(panel).toContainText('已预留 1/60 次');
 await expect(page.getByLabel('切换模型')).toBeDisabled();await page.getByRole('button',{name:'白色主题'}).click();
 await page.screenshot({path:`${EVIDENCE}/observed-model-alias-light.png`,fullPage:true});
});


test('generic personal BYOK config saves session key without restart or browser persistence and tests explicitly',async({page})=>{
 const enabled=await page.request.post(fixture.api_url+'/fixture-only/enable-model-budget-test',{headers:{'X-Workspace-Request':'1'}});expect(enabled.ok()).toBeTruthy();
 await page.route('**/api/v1/model-service/**',async route=>{const u=new URL(route.request().url());const response=await route.fetch({url:fixture.api_url+u.pathname+u.search});await route.fulfill({response});});
 await page.goto('http://127.0.0.1:5173/');await expect(page.getByLabel('业务问题')).toBeEnabled();await page.getByRole('button',{name:'模型服务',exact:true}).click();
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
 await form.getByRole('button',{name:'清除会话 Key'}).click();await expect(form).toContainText('Key已清除');
 status=await (await page.request.get(fixture.api_url+'/api/v1/model-service/status')).json();expect(status.credential_configured).toBe(false);expect(status.budget.reserved_requests).toBe(baseline+1);expect(status.generation_verified).toBe(false);
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/generic-byok-mobile.png`,fullPage:true});
});
