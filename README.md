# 智能问数 · Intelligent Data Workspace

面向业务用户的智能数据分析工作台，也是一个以**真实 Web 应用**交付的 AI 产品经理作品项目。

项目将「提出问题 → 明确口径 → 授权取数 → 查看证据 → 复用结果」作为产品主线，强调用户任务、渐进披露、可行动的失败状态和可核验的测试证据，而非用模拟结果包装尚未接入的能力。

> **当前是持续开发中的本机版本，不是完整智能问数产品或生产系统。** M01 已验收；M02 数据接入正在收尾，尚未验收。自然语言 Agent 和模型 API 尚未接入；真实 PostgreSQL 实例、默认自动清理周期、正式认证与生产部署仍未验证。

## 当前可以做什么

- **业务会话工作台**：显式黑色/白色主题、浏览器本地历史、多轮消息、顶部实际状态、结构化结果卡；SQL/Schema 验证放在开发工具中。
- **本地数据接入**：DuckDB、CSV、Parquet、`.xlsx` 文件上传或受控后端路径；真实测试 → 保存 → 刷新复用 → 编辑重测 → 启用/禁用。
- **表导航**：展示原始列头、数据类型和最多前 100 行；**不增加时间或其他筛选，不删除日期列，不猜测业务含义**。
- **受治理 MCP/SQL 底座**：真实 stdio MCP 与只读 DuckDB；HTTP MCP 仅支持受审定的适配合同和后端授权目标，已通过独立本机认证服务验证。
- **安全与恢复**：Windows Job Object 资源限额、固定 Worker 入口、上传安全预检、代际失效、未知结果不自动重提、显式重新连接。
- **保留安全底座**：24 小时测试草稿失效、来源标记、引用保护、原生句柄逐项回收及跨重启幂等恢复、只读清理回执。**回收执行仅在独立新建测试副本上验证，默认自动回收尚未启用。**

### 能力边界

| 能力 | 当前状态 |
| --- | --- |
| 本机 Web 工作台、主题和开发历史 | 已验收；历史不是正式服务器持久化 |
| 本地文件 / Excel → API → MCP → 只读预览 | 本机真实链路已测 |
| 授权 HTTP MCP 配置、测试、保存和导航 | 独立本机真实服务已测；不代表任意服务兼容 |
| PostgreSQL | 适配器和配置流程已有；真实实例验证 `not_run` |
| 临时副本安全回收 | 内部独立测试通过；默认自动周期/启用 `not_run` |
| 模型 API / 自然语言受控问数 | 规划待实施，不会伪造经营数字或执行成功 |
| 企业登录、跨租户权限、持久任务、生产部署 | 未交付 / `not_run` |

## 界面预览

以下为本机开发自测截图，**不是用户研究或真实企业经营数据**。回执截图中的维护计数来自独立测试实例，不代表默认存储状态。

![白色主题与只读保留回执](project-control/modules/M02/evidence/20261027T071957Z/browser/retention-receipt-light.png)

![黑色主题与明确的草稿重测反馈](project-control/modules/M02/evidence/20261027T071957Z/browser/retention-draft-retested-dark.png)

## 技术架构

```text
React + TypeScript + Vite
          │  本机 HTTP / 服务端身份与输入校验
          ▼
FastAPI + Pydantic ── OpenAPI ── 自动生成前端类型
          │
          ├─ 来源配置 / SQLite 非秘密配置与引用
          ├─ 固定 Worker + Windows Job Object
          └─ 受治理 MCP / 只读执行适配
                    ├─ 本地 DuckDB 快照
                    ├─ 审定 HTTP MCP
                    └─ PostgreSQL（待真实实例补验）
```

模型服务与数据源连接分别授权；模型、编排框架和提示词不能代替服务端的权限、SQL、资源及文件网络安全门禁。

## 本机运行

当前主要验证环境为 **Windows + Python 3.12 + Node.js 22.12 以上**。Worker/存储保护使用 Windows 原生机制；不承诺其他平台已验证。需要预先安装 Python、Node.js 和 pnpm，依赖安装会联网，请先审阅锁文件与相关许可。

在项目根目录打开 PowerShell：

```powershell
py -3.12 -m venv services/api/.venv

./services/api/.venv/Scripts/python.exe -m pip install -r services/api/requirements.lock.txt -r services/api/requirements.warehouse.lock.txt -r services/api/requirements.excel.lock.txt
./services/api/.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e services/api
./services/api/.venv/Scripts/python.exe -m pip check

pnpm --dir apps/web install --frozen-lockfile
./services/api/.venv/Scripts/python.exe scripts/dev.py
```

打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)，API 为 [http://127.0.0.1:8000](http://127.0.0.1:8000)，健康检查为 `/health/live`。也可双击 `start-workspace.cmd`。启动器检查端口占用，**不会替你终止其他服务**；Ctrl+C 仅停止本次启动器拥有的进程。

此模式仅用于隔离本机开发，**不要绑定 `0.0.0.0` 或公开部署开发身份**。程序不会自动读取 `.env.example`，它仅说明变量；实际授权配置由管理员安全提供。

仓库附带 `data/demo/synthetic-v1` 和 `data/warehouse/synthetic-v1`：数据由项目独立合成，使用 `TEST` 单位，不包含真实公司数据。已有仓库目录不要重复初始化或覆盖。可核验：

```powershell
./services/api/.venv/Scripts/python.exe -m data_workspace.warehouse.verify
```

PostgreSQL 可选驱动另见 `services/api/requirements.postgres.lock.txt` 与 [接入说明](CONNECTORS.md)。安装驱动不代表数据库已连通；不要把公司数据库或宿主工具凭证当作演示资源。

## 测试与合同生成

```powershell
# 修改后端合同后重新导出，不手改生成的 TypeScript
./services/api/.venv/Scripts/python.exe -m data_workspace.export_contracts
pnpm --dir apps/web run contracts

# 后端、依赖、类型、构建、前端检查
./services/api/.venv/Scripts/python.exe scripts/check.py --module M02

# 先启动本机服务，再运行浏览器检查；使用已安装 Chrome
./services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser

# 保留 / 原生执行专项：仅独立临时测试副本
./services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_retention.py services/api/tests/test_retention_execution.py -q
```

截至本次同步前，已保存的证据为 **55 项保留专项、261 项后端、10 项前端检查通过，最终 23 项浏览器复跑通过**，类型、构建与依赖检查通过。部分检查在后续仅修改浏览器测试后按相关源码字节一致复用，保留原命令和指纹；**不是本次写 README 后重新跑出的结果，也不代表全部真实集成或生产门禁通过**。

- [最新检查与复用边界](project-control/modules/M02/evidence/20261027T0841324874169Z-browser-final/results-final.json)
- [复用核查](project-control/modules/M02/evidence/20261027T0841324874169Z-browser-final/reuse.json)
- [局部自审与失败记录](project-control/modules/M02/evidence/20261027T0841324874169Z-browser-final/retention-review-final.md)

## 项目结构

```text
apps/web/         Web 会话与连接器界面
services/api/     API、合同、安全边界、Worker、MCP 和测试
contracts/        后端导出的 JSON Schema / OpenAPI
scripts/          本机启动、检查及独立测试服务
tests/           浏览器端到端测试
data/demo/       明确标注的独立合成种子
data/warehouse/  对应合成数仓与 Parquet 快照
project-control/  PRD、路线、PDCA 进度、决策和测试证据
output/           产品策划材料；早期图示不是实现证明
skills/           本项目维护的 project-pdca 工作流
```

## 路线与产品决策

**M02 收尾验收 → M04-A 模型 API 接入 → M03 语义知识库 → M04-B LangGraph 受控问数**。原进度 ID `M04` 保留为 M04-B。之后推进资产/任务、可视化、报告和 MVP 验收。

- [模块 PRD 入口](project-control/prd/README.md)
- [批准路线](project-control/ROADMAP.md)
- [用户体验原则](project-control/PRODUCT_UX_PRINCIPLES.md)
- [当前交接](project-control/HANDOFF.md)
- [开发说明](DEVELOPMENT.md) · [数据源接入](CONNECTORS.md) · [合成数仓](WAREHOUSE.md)

新依赖、模型供应商/端点、费用、数据外发及生产部署需要独立确认；推送代码**不等于部署、模块验收或新能力授权**。

## 数据与仓库安全

本仓库只提交源码、规划、合成测试数据与证据。`.gitignore` 排除用户上传和配置副本 `data/connections/`、凭证/本地工具配置、依赖、构建输出、临时目录和下载的依赖轮子；没有删除这些本地文件。历史证据中的本机路径和时点是可复现开发记录，不是运行配置。

请勿提交密码、令牌、真实企业数据或浏览器私有历史；凭证仅通过专用后端安全配置提供，不写在 URL、聊天、README 或进度中。查看只读候选不会执行清理，禁用连接不会删除数据。

本项目尚未指定开源许可证；第三方依赖遵循各自许可证。
