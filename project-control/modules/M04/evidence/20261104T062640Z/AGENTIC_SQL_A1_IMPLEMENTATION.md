# Agentic 单源 SQL A1 实现（2026-11-04）

决策：D-M04B-AGENT-EXPERIENCE-076 **A**（用户选择推荐方向：Agentic 单源 SQL + 澄清 + 自然语言回答 + 实际证据摘要）。  
本切片仍是**单来源、单表、已发布指标**，不是截图中的多源企业 Hive Agent；RAG、多表 JOIN、企业数据、导出/QA 报告未实现。

## 1. 已实现

- **受控筛选**：`AggregateRequest.filters` 支持 `eq / in / gte / lt`；最多 5 组、`in` 最多 200 个值；只允许授权表实际字段，按字段类型校验（数值/字符串/日期/时间戳），生成参数化 SQL；AST 白名单增加筛选节点；完整输入 MCP 执行与 QA 不变。
- **SDK 工具**：`propose_metric_query` 的 `filters` / `time_range` 改为可选字段（完整 JSON Schema），模型可基于 `read_authorized_metadata` 返回的真实字段筛选；Skill 升级到 **1.0.3**，明确只能使用授权字段、不得编造 ID/值、必要时澄清。
- **自然语言回答**：SDK runner 的最终 `model_text` 以 `AgentTask.answer` 返回（最多 4000 字符，包含 Key 时不返回）；结果卡上方显示模型解释，数值仍以结果卡/回执为准。
- **实际来源/进度**：任务事件包含实际表名、匹配指标、计划/确认/执行/QA/发布；右侧摘要显示实际 Agent 步骤、授权表/指标/分组/筛选；任务卡显示筛选条件。
- **终止式澄清**：新增 `request_clarification` 工具；模型可提出一个关键澄清问题，任务进入 `NEEDS_CLARIFICATION`，不执行 SQL；用户在输入区补充后发起新问题（同任务恢复留 A2）。
- **门禁保留**：服务端 catalog resolve、真实用户确认、2 USD 估算预留、幂等、自动 QA、执行/质量回执复核、模型/语义/来源/Schema 失效均未放宽。

## 2. 主要文件

- `services/api/src/data_workspace/warehouse/aggregate_contract.py`：`AggregateFilter`、参数化 WHERE、AST 白名单。
- `services/api/src/data_workspace/sdk_agent_backend.py`：筛选参数、澄清工具、路由/元数据事件。
- `services/api/src/data_workspace/sdk_agent_runner.py`：Skill 1.0.3、澄清输出、工具暴露。
- `services/api/src/data_workspace/sdk_web_service.py`：`answer`、澄清阶段、实际事件映射。
- `services/api/src/data_workspace/agent_contracts.py`：`AgentTask.answer`。
- `services/api/src/data_workspace/sdk_skills/data-query/SKILL.md`：1.0.3。
- `apps/web/src/AgentTaskCard.tsx`、`WorkbenchPanel.tsx`、`styles.css`：模型回答、筛选、实际步骤/来源。
- `services/api/tests/test_aggregate_filters.py`、`test_sdk_agent.py`、`test_sdk_web_agent.py`。

## 3. 实际验证

最终完整证据：[results.json](results.json)

- **617 后端 / 20 前端 / 44 浏览器 / types / build / pip 全部通过**。
- code fingerprint：`1850298d4ecc5fcb66ebb031d0ae03022bbaff32bdbc45de4a4dcd83d375e144`。
- 筛选专项 2 项：`eq/in/gte` + 时间组合、完整输入 150 行；`region=A` matched 75 / SUM 5625；`IN` 参数化；未知字段/类型/超限/伪造 SQL 拒绝。
- SDK Web 专项 9 项：筛选 E2E（region=A，matched 75，结果 5625）、澄清 E2E（`NEEDS_CLARIFICATION`、未执行 SQL、预算 8 单元）、自然语言回答、模型变更失效、取消、预算、幂等、能力、runner 门禁。
- Legacy Agent 33 项与既有 M04/M02/M03/M04-A 回归通过；浏览器 44 项通过（legacy LangGraph fixture 未走 SDK，未放宽断言）。
- 用户报告的真实 DeepSeek Web 窄切片成功：任务 `3764b186-dc7d-4e29-98d6-888672b857ad`，`SUCCEEDED` / `claude_agent_sdk_skills_v1` / `deepseek-v4.1-flash` / 120 行全输入 / 质量 PASS；结果行与聚合值未落盘，sdk-real-gateway（Claude）仍 `not_run`。

## 4. 边界与未完成

- **单来源/单表/已发布指标**：不执行任意自由 SQL；不支持多表 JOIN、跨来源、企业 Hive/公司数据。
- **RAG 未实现**：业务知识文档导入、切片、检索、引用属于 M03 下一批；需要文档来源/权限/存储/嵌入模型费用计划。
- **澄清是终止式**：任务不执行 SQL，用户补充后新问题；同任务恢复/多轮澄清留 A2。
- **截图仅交互参考**：未复制公司数据、SQL、水印对象；未接宿主 MCP/公司 Hive。
- 真实 Claude SDK 网关、个人 API 的 SDK 绑定、生产、M05–M08 与整体 MVP 仍 `not_run`。
- 结果行不返回模型；模型回答不替代结果卡/回执；不展示原始思维链。

## 5. 复现

```powershell
services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_aggregate_filters.py services/api/tests/test_sdk_web_agent.py -q
services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser
```
