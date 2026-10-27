import { test, expect } from '../apps/web/node_modules/@playwright/test/index.mjs';
const URL='http://127.0.0.1:5173';
const EVIDENCE=process.env.WORKSPACE_BROWSER_EVIDENCE||`project-control/modules/M02/evidence/manual-browser-${Date.now()}`;
async function online(page){await page.goto(URL);await expect(page.getByLabel('业务问题')).toBeEnabled();}
async function openTools(page){await page.getByRole('button',{name:'开发工具',exact:true}).click();await expect(page.getByRole('dialog',{name:'接口与契约验证'})).toBeVisible();}

test('business-first layout, real output cards and preserved API checks',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await online(page);
 await expect(page.getByRole('heading',{name:'从问题到可用数据'})).toBeVisible();
 await expect(page.getByLabel('QuerySpec')).toHaveCount(0);
 const pipe=await page.getByRole('region',{name:'执行进度'}).boundingBox();
 const composer=await page.getByLabel('业务问题').boundingBox();expect(pipe.y).toBeLessThan(composer.y);
 await page.screenshot({path:`${EVIDENCE}/welcome-dark.png`,fullPage:true,animations:'disabled'});
 await page.getByLabel('业务问题').fill('上周各区域的订单转化率是多少？');await page.getByRole('button',{name:'发送问题'}).click();
 await expect(page.getByText('本地能力提示',{exact:true})).toBeVisible();
 await expect(page.getByText('没有查询结果，也没有生成 SQL',{exact:true})).toBeVisible();
 await expect(page.getByRole('region',{name:'执行进度'})).toContainText('未执行');
 await page.getByLabel('业务问题').fill('再按渠道拆分');await page.getByLabel('业务问题').press('Enter');
 await expect(page.getByRole('article',{name:'助手输出'})).toHaveCount(2);
 await page.screenshot({path:`${EVIDENCE}/conversation-dark.png`,fullPage:true,animations:'disabled'});
 await openTools(page);await page.getByRole('button',{name:'验证数据契约',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByText('结构通过',{exact:true})).toBeVisible();
 await expect(page.getByText('仅验证结构 · 未确认业务口径 · 未执行 SQL')).toBeVisible();
 await expect(page.getByText('2026-10-19 至 2026-10-26（不含结束日）')).toBeVisible();
 await page.getByRole('button',{name:'白色主题'}).click();
 await page.getByText('结构通过',{exact:true}).scrollIntoViewIfNeeded();
 await page.screenshot({path:`${EVIDENCE}/scope-output-light.png`,fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'黑色主题'}).click();
 await page.getByText('QuerySpec 与接口详情',{exact:true}).click();await expect(page.locator('pre')).toContainText('order_conversion_rate');await page.getByText('QuerySpec 与接口详情',{exact:true}).click();
 await openTools(page);await page.getByRole('button',{name:'登记测试任务'}).click();
 await expect(page.getByText('未执行 · FAILED',{exact:true})).toBeVisible();
 await page.getByText('任务编号与技术信息',{exact:true}).click();await expect(page.getByText('EXECUTOR_NOT_CONFIGURED',{exact:true})).toBeVisible();
 await page.getByText('任务编号与技术信息',{exact:true}).click();
 await page.getByText('未执行 · FAILED',{exact:true}).scrollIntoViewIfNeeded();
 await page.screenshot({path:`${EVIDENCE}/result-cards-dark.png`,fullPage:true,animations:'disabled'});
 await openTools(page);await page.getByRole('button',{name:'重新读取任务'}).click();
 await expect(page.locator('.last-task')).toContainText('FAILED');
 const editor=page.getByLabel('QuerySpec');const spec=JSON.parse(await editor.inputValue());spec.tenant_id='attacker';
 await editor.fill(JSON.stringify(spec));await page.getByRole('button',{name:'验证数据契约'}).click();await expect(page.getByRole('alert')).toContainText('INVALID_REQUEST');
 await editor.fill('{bad');await page.getByRole('button',{name:'验证数据契约'}).click();await expect(page.getByRole('alert')).toContainText('INVALID_JSON');
 await page.getByRole('button',{name:'恢复示例'}).click();await page.getByRole('button',{name:'查看实际 Schema'}).click();
 await expect(page.getByRole('status')).toContainText('当前显示 Schema');expect(JSON.parse(await editor.inputValue()).title).toBe('QuerySpec');
 await expect(page.getByRole('button',{name:'验证数据契约'})).toBeDisabled();await page.getByRole('button',{name:'恢复示例'}).click();
 await page.getByRole('button',{name:'关闭开发工具'}).click();
 for(const label of ['知识库','数据资产','可视化看板','分析报告']){
  await page.getByRole('navigation',{name:'主导航'}).getByRole('button',{name:label,exact:true}).click();
  await expect(page.getByRole('heading',{name:label+'尚未接入',exact:true})).toBeVisible();
 }
 await page.getByRole('button',{name:'返回取数工作台'}).click();expect(errors).toEqual([]);
});

test('black and white themes persist through reload',async({page})=>{
 await online(page);await expect(page.getByRole('group',{name:'背景主题'})).toBeVisible();await expect(page.getByRole('button',{name:'黑色主题'})).toHaveAttribute('aria-pressed','true');await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.screenshot({path:`${EVIDENCE}/welcome-light.png`,fullPage:true,animations:'disabled'});
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.getByRole('button',{name:'黑色主题'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});

test('history supports multi-turn, new conversations, switching, reload and deliberate deletion',async({page})=>{
 await online(page);await page.getByLabel('业务问题').fill('第一段分析');await page.getByRole('button',{name:'发送问题'}).click();
 await page.getByLabel('业务问题').fill('第一段的追问');await page.getByLabel('业务问题').press('Enter');
 await expect(page.locator('.user-message')).toHaveCount(2);
 await page.getByRole('button',{name:'新建会话'}).click();await page.getByLabel('业务问题').fill('第二段分析');await page.getByRole('button',{name:'发送问题'}).click();
 await page.locator('.history-select').filter({hasText:'第一段分析'}).click();await expect(page.locator('.user-message')).toHaveCount(2);
 await page.reload();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();
 await page.locator('.history-select').filter({hasText:'第一段分析'}).click();await expect(page.getByText('第一段的追问',{exact:true})).toBeVisible();
 await page.locator('.history-select').filter({hasText:'第二段分析'}).click();await expect(page.locator('.user-message')).toHaveCount(1);
 await page.getByRole('button',{name:'删除会话 第二段分析'}).click();await page.getByRole('button',{name:'取消',exact:true}).click();await expect(page.locator('.history-item')).toHaveCount(2);
 await page.getByRole('button',{name:'删除会话 第二段分析'}).click();await page.getByRole('button',{name:'确认删除'}).click();await expect(page.locator('.history-item')).toHaveCount(1);
 await page.getByRole('button',{name:'清除本地历史'}).click();await page.getByRole('button',{name:'确认删除'}).click();await expect(page.locator('.history-item')).toHaveCount(0);
 await page.reload();await expect(page.locator('.history-item')).toHaveCount(0);
});

test('API validation snapshots are not persisted as authentic results on reload',async({page})=>{
 await online(page);await page.getByLabel('业务问题').fill('结果保留边界');await page.getByLabel('业务问题').press('Enter');
 await openTools(page);await page.getByRole('button',{name:'验证数据契约'}).click();await expect(page.getByText('结构通过',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();await page.locator('.history-select').filter({hasText:'结果保留边界'}).click();
 await expect(page.getByText('结构通过',{exact:true})).toHaveCount(0);await expect(page.getByText('没有查询结果，也没有生成 SQL',{exact:true})).toBeVisible();
});

test('mobile themes, history access and tools have no overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await online(page);
 await page.getByLabel('业务问题').fill('手机端测试');await page.getByRole('button',{name:'发送问题'}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`${EVIDENCE}/mobile-dark.png`,fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/mobile-light.png`,fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'打开侧栏'}).click();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();await expect(page.locator('.history-select').filter({hasText:'手机端测试'})).toBeVisible();
 await page.getByRole('button',{name:'关闭侧栏'}).click();await openTools(page);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.getByRole('button',{name:'关闭开发工具'}).click();
});

test('unavailable API shows failure and disables input',async({page})=>{
 await page.route('**/api/v1/**',route=>route.abort('failed'));await page.goto(URL);
 await expect(page.getByRole('alert')).toContainText('无法连接后端服务');await expect(page.getByLabel('业务问题')).toBeDisabled();await expect(page.getByRole('button',{name:'开发工具'})).toBeDisabled();
 await page.screenshot({path:`${EVIDENCE}/offline.png`,fullPage:true,animations:'disabled'});
});

test('loading state is visible before API responds',async({page})=>{
 await page.route('**/api/v1/session',async route=>{await new Promise(r=>setTimeout(r,700));await route.continue();});await page.goto(URL);
 await expect(page.getByText('正在连接 API',{exact:true})).toBeVisible();await expect(page.getByLabel('业务问题')).toBeDisabled();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();
});

test('stored text is escaped rather than executed as HTML',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await online(page);const text='<img src=x onerror="window.pwned=true">';
 await page.getByLabel('业务问题').fill(text);await page.getByRole('button',{name:'发送问题'}).click();
 await expect(page.locator('.user-message p')).toHaveText(text);expect(await page.evaluate(()=>window.pwned)).toBeUndefined();
 await page.reload();await expect(page.getByText('API 已连接',{exact:true})).toBeVisible();await page.locator('.history-select').click();expect(await page.evaluate(()=>window.pwned)).toBeUndefined();expect(errors).toEqual([]);
});
