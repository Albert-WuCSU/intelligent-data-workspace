# M04-C02-SDK｜S02 离线实现与验证

日期：2026-11-03  
状态：离线 SDK/CLI + 合成 MCP fixture 已通过；真实网关、生产与 MVP 仍 `not_run`

## 1. 已安装与锁定

- Python SDK `0.2.177`，从已核 SHA 的 Windows wheel 离线安装到项目 venv，无旧包替换。
- 捆绑 Claude Code CLI `2.1.317`，隔离 `claude.exe --version` 实际返回 `2.1.317 (Claude Code)`。
- wheel SHA256：`7997db488354a539c08b5b6b16717d99ae67903ae7351da43d51b68b80097fad`。
- CLI SHA256：`26b01ec22df2c17ac7f5703aa547d36706e8d58412136ced0344a8ced4d86038`。
- 安装证据：[install-verification.json](evidence/20261103T060255Z-sdk-install-plan/install-verification.json)。

## 2. 最小真实垂直切片

实现文件：

- [sdk_agent_backend.py](../../../services/api/src/data_workspace/sdk_agent_backend.py)：受治理工具、确认、幂等、真实 MCP 执行、自动 QA、回执发布与预算。
- [sdk_agent_runner.py](../../../services/api/src/data_workspace/sdk_agent_runner.py)：受控 plugin Skill、最小 SDK 配置、事件与用量核验。
- [sdk_process.py](../../../services/api/src/data_workspace/sdk_process.py)：最小父环境与专属 Windows Job 生命周期。
- [sdk_runner_entry.py](../../../services/api/src/data_workspace/sdk_runner_entry.py)：固定子进程入口。
- [data-query/SKILL.md](../../../services/api/src/data_workspace/sdk_skills/data-query/SKILL.md)：版本化产品 Skill。
- [test_sdk_agent.py](../../../services/api/tests/test_sdk_agent.py)：治理单测、loopback 假 Messages 网关与真实 SDK/CLI 端到端 fixture。

实际流程：Skill 加载 → 语义/路由回执 → 授权元数据 → 已发布指标计划 → 显式模拟用户确认 → 真实合成 MCP 执行 → 自动 QA → QueryReceipt + QualityReceipt → 后端结果卡发布。

受控 SQL 路径接受结构化 `AggregateRequest`，经确定性编译与 AST/字段/Schema 校验；有已匹配指标时禁止绕过指标引擎。当前不是自由 SQL 或 JOIN 实现。

## 3. 实测结果

- SDK 专项 **9/9 通过**，命令：`./services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_agent.py -q`。覆盖路由变化使旧计划/确认失效、原始异常不回显、墙钟边界及真实端到端fixture。
- 中间非浏览器回归：**599 后端、17 前端、types/build/pip 全部退出 0**，证据：[20261103T072251Z/results.json](evidence/20261103T072251Z/results.json)。
- 最终完整回归：**602 后端、17 前端、44 浏览器及 types/build/pip 全部退出 0**，证据：[20261103T074400Z/results.json](evidence/20261103T074400Z/results.json)。首轮43/44的capability fixture隔离失败已修复并保留记录。
- 离线 fixture 完成 **8 模型步、7 工具调用、2 元数据调用、48 个流事件**。
- 真实合成输入 150 行，全输入 SUM(amount)=**11325**，质量 `PASS`，并非前 100 行估算。
- 结果只由后端发布；`model_generated_numbers=false`，结果行未进入后续模型请求。
- SDK `total_cost_usd=0.0024` 是客户端价格表估算，不是实际费用或假网关账单。
- Windows Job 实测峰值 8 进程、约 531 MiB；进程上限 10、Job 内存上限 2 GiB，另有进程内存、CPU 和墙钟限制。

主证据：[results.json](evidence/20261103T071717Z-sdk-s02/results.json)、[result.json](evidence/20261103T071717Z-sdk-s02/result.json)、[process-diagnostics.json](evidence/20261103T071717Z-sdk-s02/process-diagnostics.json)、[source-manifest.json](evidence/20261103T071717Z-sdk-s02/source-manifest.json)。

## 4. 实际发现的隔离问题与修复

1. 原生 Windows 下仅设置 HOME/config 仍出现宿主全局 `CLAUDE.md`。改为 **`setting_sources=[]` + 只有受控 Skill/清单的本地 plugin**，以 `governed:data-query` 精确加载；最终请求不再包含该宿主指令。
2. `PreToolUse` 可对同一 MCP 调用重复触发。预算不再依赖 hook 次数：内置工具由 hook 计数，MCP 工具由实际后端调用计数。
3. 初版在 SDK 外层 Job 内再次创建聚合 MCP 内层 Job。此 fixture 改为 MCP 继承外层 Job 的资源限制与后代清理；其他既有 stdio 默认路径保持原样并通过全后端回归。
4. 原生配额失败后，运行中采样测得峰值 6 进程超过原上限 4。调整为有证据的有限上限，成功路径峰值 8，最终上限 10；没有改成无限进程或取消隔离。
5. 幂等键必须满足既有 UUID 合同；后端在提交前验证，失败不会转成重复执行。

失败及修复历史：[failure-history.json](evidence/20261103T071717Z-sdk-s02/failure-history.json) 及同目录保留的诊断文件。

## 5. 当前安全边界

- `tools=["Skill"]`，MCP 仅项目 governed server；不暴露 Bash/PowerShell/Write/Edit/任意 Read/Web/Agent 等内置工具。
- `setting_sources=[]`，不加载 user/project/local 设置；独立 cwd/config/HOME/temp、禁 auto memory、connectors、非必要流量和外部 trace。
- `permission_mode=default`，执行与发布不在自动允许列表；`can_use_tool` 默认拒绝，且后端再次独立核验。
- 确认只来自显式 fixture 用户动作，模型不能自行确认。重复执行、缺少确认、缺少 QA 或质量 UNKNOWN/FAIL 均拒绝发布。
- 模型只收到回执 ID/状态，不收到结果行或完整业务结果；后端直接生成真实结果卡。
- SDK init 可列出内置 Skills，但实际模型上下文与工具调用只批准 `governed:data-query`，不把 init 列表当作全部启用或安全证明。

## 6. 不能据此声称完成的事项

- 模型是 loopback 脚本化假网关；没有真实模型理解、真实 AIPlan、真实费用或供应商 SLA 证据。
- 当前 DeepSeek 不属于官方支持的 Claude Code 网关模型路径；真实 SDK 测试须先确认获授权 Claude 模型及 base URL/auth，再由用户显式执行。
- 尚未接入默认业务 Web 工作台，未做真实用户研究；本切片是可复现的开发 fixture。
- 没有生产认证、多租户、生产持久任务、跨重启恢复、正式网络/文件沙箱或部署。
- L2/L3/L4、JOIN、M05–M08 与整个 MVP 未完成；旧 LangGraph 分支只保留作比较基线。

## 7. 下一门禁

先完成全量浏览器与文档回归并保存检查点。之后只在用户明确进行真实 SDK 网关测试时，核授权 Claude 模型和完整 Messages/tool_use/Skill/stream/usage；不自动改模型、端点、供应商或回退 LangGraph，不把旧单次 128-token 合同当成多轮预算。
