# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: source-onboarding.spec.mjs >> xlsx workbook upload, real multisheet navigation and date columns without time filters
- Location: tests\source-onboarding.spec.mjs:26:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('status')
Expected substring: "2 张表"
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toContainText" getByRole('status') with timeout 5000ms
  - waiting for getByRole('status')

```

```yaml
- complementary "工作空间侧栏":
  - link "数据工作台 DATA WORKSPACE":
    - /url: "#query"
  - button "新建会话 NEW" [disabled]
  - navigation "主导航":
    - button "取数工作台" [disabled]: 取数工作台 主干
    - button "连接器" [disabled]
    - button "知识库" [disabled]
    - button "数据资产" [disabled]
    - button "可视化看板" [disabled]
    - button "分析报告" [disabled]
  - text: 历史会话
  - button "会话存储说明"
  - text: 还没有会话 发送问题后会出现在这里
  - button "清除本地历史" [disabled]
  - text: API 已连接
  - button "刷新连接" [disabled]
  - text: D
  - strong: 本地开发者
  - text: 本地会话 · 不跨设备
  - button "切换浅色主题"
- main:
  - text: 工作空间 /
  - strong: 连接器
  - text: 本地开发
  - group "背景主题":
    - button "黑色主题" [pressed]: 黑色
    - button "白色主题": 白色
  - button "开发工具" [disabled]
  - text: WORKSPACE / CONNECTORS
  - heading "连接器" [level=1]
  - region "数据源连接管理":
    - heading "连接你的数据" [level=2]
    - paragraph: 配置连接后选择表，查看列头、类型与前 100 行；不设置时间或其他筛选条件。
    - button "新增数据源" [disabled]
    - button "导入连接配置" [disabled]
    - button "配置 MCP" [disabled]
    - button "存储与清理" [disabled]
    - group: 远程连接的权限与凭证说明
    - region "新增连接配置":
      - heading "新增数据源配置" [level=3]
      - paragraph: 配置保存于本机服务器，刷新后可复用；测试通过不等于正式身份、业务口径或质量认证。
      - text: 数据源类型
      - combobox "数据源类型" [disabled]:
        - option "本地文件（DuckDB / CSV / Parquet / Excel）" [selected]
        - option "PostgreSQL 数据库"
        - option "HTTP MCP 服务"
      - text: 连接名称
      - textbox "连接名称" [disabled]: Excel工作簿-1793086737053
      - paragraph: 文件复制到本机后端隔离目录，原文件不修改。
      - paragraph: 支持 .xlsx：每个可见工作表作为一张表，第一行作为列标题；不执行公式。日期列会保留。
      - text: 选择数据文件
      - button "选择数据文件" [disabled]
      - paragraph: 已选择：xlsx-fixture.xlsx · 4.3 KB
      - group: 或填写后端可访问的本机文件路径
      - checkbox "我有权使用此文件，同意复制到本机后端，仅用于只读连接和预览。" [checked] [disabled]
      - text: 我有权使用此文件，同意复制到本机后端，仅用于只读连接和预览。
      - button "实际连接处理中…" [disabled]
      - button "保存连接" [disabled]
      - button "取消配置" [disabled]
      - group: 非秘密配置文件格式
    - article:
      - heading "Excel工作簿-1793067919289" [level=3]
      - paragraph: 本地文件 · source.xlsx · 配置已保存，连接时重新校验
      - text: 最近真实测试：2026/10/27 10:25:21 · 版本 3
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "禁用" [disabled]
    - article:
      - heading "Excel工作簿-1793069002952" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 10:43:24 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793070670592" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 11:11:12 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793071026624" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 11:17:08 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793071194200" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 11:19:56 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793076174000" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 12:42:55 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793076452893" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 12:47:35 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793077529138" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 13:05:31 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793077849481" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 13:10:52 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793079094996" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 13:31:37 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793079507793" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 13:38:31 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793085373953" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 15:16:17 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "Excel工作簿-1793085773814" [level=3]
      - paragraph: 本地文件 · source.xlsx · 已禁用
      - text: 最近真实测试：2026/10/27 15:22:57 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793066829251" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 10:07:11 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793067105934" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 10:11:47 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793067911212" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 10:25:13 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793068996401" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 10:43:18 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793070663971" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 11:11:05 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793071019149" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 11:17:00 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793071186345" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 11:19:48 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793076166946" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 12:42:48 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793076444229" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 12:47:26 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793077519865" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 13:05:22 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793077839532" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 13:10:42 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793079084811" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 13:31:27 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793079498165" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 13:38:21 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793085363481" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 15:16:06 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793085762677" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 15:22:46 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - article:
      - heading "日期数据源-1793086724416" [level=3]
      - paragraph: 本地文件 · source.csv · 已禁用
      - text: 最近真实测试：2026/10/27 15:38:47 · 版本 2
      - button "连接并浏览" [disabled]
      - button "配置" [disabled]
      - button "启用" [disabled]
    - button "使用内置合成示例" [disabled]
```

# Test source

```ts
  1  | import {test,expect} from '../apps/web/node_modules/@playwright/test/index.mjs';
  2  | const EVIDENCE=process.env.WORKSPACE_BROWSER_EVIDENCE||`project-control/modules/M02/evidence/sources-${Date.now()}`;
  3  | async function openSources(page){await page.goto('http://127.0.0.1:5173/#connectors');await expect(page.getByRole('region',{name:'数据源连接管理'})).toBeVisible();await expect(page.getByRole('button',{name:'新增数据源'})).toBeEnabled();}
  4  | test('user adds a source, saves, reconnects after reload and browses dates with no date filter',async({page})=>{
  5  |  const name=`日期数据源-${Date.now()}`;
  6  |  const csv='code,created_at,shipped_on,amount\n'+Array.from({length:120},(_,i)=>`c${i},2025-01-01 12:00:00,2025-01-02,${i}\n`).join('');
  7  |  const errors=[];page.on('pageerror',e=>errors.push(e.message));await openSources(page);
  8  |  await expect(page.locator('input[type=date]')).toHaveCount(0);
  9  |  await page.getByRole('button',{name:'新增数据源'}).click();await page.getByLabel('连接名称').fill(name);await page.getByLabel('选择数据文件').setInputFiles({name:'dates.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();
  10 |  await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('status')).toContainText('真实 MCP 连接测试通过');await page.getByRole('button',{name:'保存连接'}).click();
  11 |  await page.reload();await openSources(page);const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});await card.getByRole('button',{name:'连接并浏览'}).click();await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'main.data'}).click();
  12 |  const table=page.getByLabel('数据源前100行').getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('shipped_on');await expect(table).toContainText('2025-01-01T12:00:00');await expect(table).toContainText('TIMESTAMP');await expect(page.locator('input[type=date]')).toHaveCount(0);
  13 |  await page.screenshot({path:`${EVIDENCE}/source-navigation-dark.png`,fullPage:true});await page.getByRole('button',{name:'白色主题'}).click();await page.screenshot({path:`${EVIDENCE}/source-navigation-light.png`,fullPage:true});
  14 |  await card.getByRole('button',{name:'禁用',exact:true}).click();await expect(card.getByRole('button',{name:'连接并浏览'})).toBeDisabled();await expect(page.getByRole('region',{name:'数据表导航'})).toHaveCount(0);expect(errors).toEqual([]);
  15 | });
  16 | test('nonsecret configuration import fills form but does not auto-connect; errors preserve input',async({page})=>{
  17 |  await openSources(page);const config={schema_version:'1.0',profile:{kind:'local_file',name:'导入的连接',path:'data/does-not-exist.csv',usage_authorized:true}};
  18 |  await page.getByLabel('连接配置文件').setInputFiles({name:'connection.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(config))});await expect(page.getByLabel('连接名称')).toHaveValue('导入的连接');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();await expect(page.getByRole('alert')).toContainText('INVALID_SOURCE');await expect(page.getByLabel('连接名称')).toHaveValue('导入的连接');await expect(page.getByRole('button',{name:'保存连接'})).toBeDisabled();
  19 |  await page.getByLabel('连接配置文件').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({...config,command:'powershell',password:'sentinel-never-reflect'}))});await expect(page.getByRole('alert')).toContainText('INVALID_CONFIG');await expect(page.getByRole('alert')).not.toContainText('sentinel-never-reflect');
  20 | });
  21 | test('mobile source navigation controls preserve visible themes without a time-filter input',async({page})=>{
  22 |  await page.setViewportSize({width:390,height:844});await openSources(page);await page.getByRole('button',{name:'新增数据源'}).click();await page.getByRole('button',{name:'白色主题'}).click();await expect(page.getByRole('button',{name:'白色主题'})).toHaveAttribute('aria-pressed','true');await expect(page.locator('input[type=date]')).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`${EVIDENCE}/source-config-mobile.png`,fullPage:true});
  23 | });
  24 | 
  25 | 
  26 | test('xlsx workbook upload, real multisheet navigation and date columns without time filters',async({page})=>{
  27 |  await openSources(page);await page.getByRole('button',{name:'新增数据源'}).click();
  28 |  const name=`Excel工作簿-${Date.now()}`;await page.getByLabel('连接名称').fill(name);
  29 |  await expect(page.getByLabel('选择数据文件')).toHaveAttribute('accept',/\.xlsx/);
  30 |  await page.getByLabel('选择数据文件').setInputFiles(process.env.WORKSPACE_XLSX_FIXTURE);
  31 |  await page.getByRole('checkbox',{name:'我有权使用此文件',exact:false}).check();await page.getByRole('button',{name:'测试连接',exact:true}).click();
> 32 |  await expect(page.getByRole('status')).toContainText('2 张表');await page.getByRole('button',{name:'保存连接'}).click();
     |                                         ^ Error: expect(locator).toContainText(expected) failed
  33 |  const card=page.getByRole('article').filter({has:page.getByRole('heading',{name,exact:true})});await card.getByRole('button',{name:'连接并浏览'}).click();
  34 |  await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'workbook.订单表'}).click();
  35 |  const table=page.getByLabel('数据源前100行').getByRole('table');await expect(table.getByRole('row')).toHaveCount(101);await expect(table).toContainText('created_at');await expect(table).toContainText('发货日期');await expect(table).toContainText('2025-01-01T12:00:00');await expect(page.locator('input[type=date]')).toHaveCount(0);
  36 |  await page.screenshot({path:`${EVIDENCE}/xlsx-navigation.png`,fullPage:true});
  37 |  await page.getByRole('region',{name:'数据表导航'}).getByRole('button',{name:'workbook.字典表'}).click();await expect(table).toContainText('Alpha');await expect(table.getByRole('row')).toHaveCount(2);
  38 |  await card.getByRole('button',{name:'禁用',exact:true}).click();
  39 | });
  40 | 
```