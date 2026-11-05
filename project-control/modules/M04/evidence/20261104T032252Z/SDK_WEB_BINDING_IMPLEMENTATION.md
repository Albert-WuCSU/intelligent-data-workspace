# SDK runner / 默认 Web 模型绑定切片（2026-11-04）

决策依据：D-M04B-CLAUDE-SDK-070 主线、D-M04B-SDK-REAL-074 A（继续本机 Web 集成实验）、D-M04B-MODEL-PICKER-075（服务端目录→选择器→Agent/SDK 绑定）。  
需求：R-U30 / R-A07 / R-P26；M04-B 的 Skill 路由、确认、预算、幂等、自动 QA、回执发布与版本失效要求。

## 1. 实现范围

- **SDK runner `web_catalog` 模式**：只接受服务端生成的绑定配置（model ref、model/config version、semantic/source/schema 指纹、表/指标/粒度/时间、binding hash、幂等键）；不接受浏览器传入的端点、模型 ID 或 Key。只批准既有 AI Plan coding-plan 端点；loopback 仅限 `SDK_WEB_TEST=1` 的隔离测试。
- **真实用户确认桥**：runner 在 `AWAITING_CONFIRMATION` 写状态并等待 `confirmation.json`；API 只有在用户显式确认、且模型/语义/来源/实时 Schema 全部复核通过后才写确认文件。模型不能自行确认。
- **Web 任务服务**：`SdkWebAgentService` 负责服务端 catalog resolve、任务内存状态、SDK 子进程、状态轮询、结果/回执复核、取消与失效。浏览器只使用现有 `/api/v1/agent/tasks` 合同。
- **默认路由**：AI Plan 且 `anthropic_messages` 的 catalog 模型进入 SDK runner；个人 API / 非 AI Plan 模型保留既有 LangGraph 路径。`AgentTask.engine` 与 `AgentCapabilities.engines` 由服务端返回；UI 标签使用服务端 engine，不根据模型名推断。
- **失效**：`binding_hash` 绑定 owner/任务/model ref/config version/semantic version/state revision/source/version/schema 指纹；模型、语义、来源或 Schema 变化使旧计划/确认/回执失效；执行后若绑定变化，结果不发布。
- **预算**：任务开始前在既有估算账本预留 8 个 0.25 USD 单元（2 USD，D053 不 reset）；失败/取消不退款；账本仍为估算，不是供应商账单。
- **幂等/QA/回执**：执行使用服务端 `request_id` 作为 MCP 幂等键（模型仍须提交合法 UUID）；后端自动 QA；API 再次核验 `publication`、query/quality receipt、结果合同后才会把结果写入任务。
- **隔离**：最小环境、独立 cwd/HOME/config/temp、`setting_sources=[]`、受控 plugin Skill、专属 Windows Job；结果行不返回模型；运行目录在项目外并在任务结束后清理。

## 2. 主要文件

- `services/api/src/data_workspace/sdk_agent_backend.py`：`GovernedQueryBackend`、`SyntheticGovernedBackend`、`WebGovernedBackend`、工具服务器。
- `services/api/src/data_workspace/sdk_agent_runner.py`：`fixture` / `real_gateway_experiment` / `web_catalog` 三种模式及状态写入。
- `services/api/src/data_workspace/sdk_web_service.py`：Web 任务生命周期、确认桥、失效与最终核验。
- `services/api/src/data_workspace/agent_hybrid.py`：AI Plan→SDK，其他→既有 LangGraph；统一任务 API。
- `services/api/src/data_workspace/agent_contracts.py`、`agent_routes.py`、`agent_service.py`、`main.py`、`config.py`、`model_budget.py`。
- `services/api/src/data_workspace/sdk_skills/data-query/SKILL.md`：1.0.2，增加时间范围与“当前 Web 切片只支持已发布指标”的说明。
- `apps/web/src/AgentTaskCard.tsx`、`workbench.ts`：服务端 engine 标签与测试。
- `services/api/tests/test_sdk_web_agent.py`、`test_sdk_agent.py`、`test_agent.py`。

## 3. 实际验证

最终完整回归证据：[results.json](results.json)

- 613 后端通过（含 SDK Web API 端到端、模型/预算/目录/legacy Agent 回归）。
- 20 前端测试通过；types / build / pip check 退出 0。
- 44 浏览器测试通过（既有 LangGraph/模型/连接器/知识库/主题/窄屏路径未回归）。
- code fingerprint：`1fd8ffff644261a56caf5c6abcfa1b55895a9fa6d3b4c29a5a6952a282fcc628`。
- SDK Web 专项：`test_sdk_web_agent.py` 7 项通过；fake loopback Messages 网关 + 真实合成 MCP，150 行全输入 SUM=11325，质量 PASS，确认后执行，结果行不返回模型；模型变更在确认前使任务 EXPIRED 且不执行；取消等待不执行；预算不足在模型调用前拒绝；同 request_id 不重复预留；能力接口报告 SDK engine。
- 失败与修复历史：第一次浏览器回归 42/44，其中 legacy Agent 浏览器 fixture 因 AI Plan 测试模型被新路由进入 SDK 而失败；在 `scripts/remote_browser_fixture.py` 显式设置 `sdk_web_agent=False` 后，legacy 浏览器测试恢复，最终 44/44。该失败不是放宽断言，SDK 路径由独立 API 端到端测试覆盖。

## 4. 未完成 / 边界

- **真实 DeepSeek Web 调用 not_run**：需要用户在本机 Web 显式选择已测试/启用的 AI Plan `deepseek-v4.1-flash`、输入专用 Key、发送问题并确认；本轮未读取 Key、未调用真实网关、未收费。
- **Claude 官方支持 not_run**：`sdk-real-gateway`（Claude 模型）门禁未关闭；DeepSeek 仍是非 Claude/unsupported 实验证据。
- **个人 API / 非 AI Plan 模型的 SDK 绑定 not_run**：这些模型仍走既有 LangGraph 路径；SDK 只批准既有 AI Plan 端点，未新增端点/供应商。
- **SDK 浏览器路径未单独 browser 回归**：SDK 任务的 UI 复用同一任务卡，engine 标签有前端单测；真实用户路径由上述真实 DeepSeek Web 测试作为门禁。
- **网关自动发现/价格/上下文元数据**未实现，保持未知或隐藏。
- `SDK_INIT` 仍可能列出 CLI 自带非产品 Skill；实际 Skill 调用由后端 `governed:data-query` 门禁；`CanUseToolShadowedWarning` 保留残余风险。
- 真实模型行为有方差；首次真实 Web 测试不应自动重试或换模型/端点。
- SDK runner 不持有 API 进程内的模型配置锁；模型变更会使任务失效，但用户另行显式触发的模型测试可能与运行中的 SDK 任务并行；账本与门禁仍生效。生产前需重新评估。
- M05 持久任务、正式历史、多租户/生产认证、生产 SQL、部署与整体 MVP 验收仍未完成。

## 5. 复现命令

```powershell
services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_web_agent.py -q
services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_agent.py services/api/tests/test_agent.py -q
services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser
```

最后一条需要本机 5173/8000 服务；本轮服务由本轮启动并在完成后停止，5173/8000 无监听。
