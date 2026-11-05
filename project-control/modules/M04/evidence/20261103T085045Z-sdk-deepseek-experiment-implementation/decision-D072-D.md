# D-M04B-SDK-REAL-072｜用户选择 D：DeepSeek SDK 兼容性实验

日期：2026-11-03  
决策：D（用户明确选择）  
状态：实验代码已实现并通过本地回归；第一次真实运行已完成但因隔离问题判定无效；等待项目外临时目录的干净重跑

> **2026-11-03 更新**：第一次运行（`20261103T085755Z-sdk-deepseek-experiment`）中 `deepseek-v4.1-flash` 返回 SUCCEEDED，但 runtime 位于项目树内，SDK init 列出非产品 Skill，CLI 出现 CLAUDE.md/AGENTS.md 扫描记录，且 Windows Job 峰值进程 16/15 超过上限 10。该次结果只作诊断，不作干净证据。已改为项目外系统临时目录、运行后清理，并新增失败诊断；完整后端 604 passed。等待用户重新运行启动器。

> **2026-11-03 干净重跑更新**：干净 runtime 下 Job 峰值 8/7 ≤10，项目树泄漏已修复。`deepseek-v4.1-flash` 执行了完整受控链（含 `publish_result`），但发布后多调一次 `get_receipt`，8 步用尽触发 `error_max_turns`。`deepseek-v4-1-flash-261017` 被网关明确 400 拒绝（`This model is not currently supported`），它是返回版本别名，不是可用请求名。已加 Skill 1.0.1“发布后停止”指令；SDK 专项 11、后端 604 通过。下一步仅申请一次 `deepseek-v4.1-flash` 单模型重跑（D073），不再重试错误名称。

> **2026-11-03 单模型重跑成功**：`deepseek-v4.1-flash` **SUCCEEDED**。Skill 1.0.1 生效，8 模型步/7 工具/1 元数据/23,080 tokens；查询 SUCCEEDED、质量 PASS、发布 11325（150 行全输入）；结果行未回传模型，模型文本未复述数字；Job 峰值 8≤10。该结果是非 Claude 兼容性实验，不关闭 `sdk-real-gateway`，也不等于官方 Claude SDK 验证。详见 `20261103T092622Z-sdk-deepseek-experiment/success-report.md`。

## 1. 用户原话

> 我觉得选择D选项，你试试能不能使用deepseek模型。另外aiplan网关里的deepseek模型名称可能叫这个，你两个名称都试试

截图给出的模型名：`deepseek-v4-1-flash-261017`。

## 2. 本次实验范围

- 端点：既有 AIPlan `http://ada-cli-golang.ctripcorp.com/coding-plan`，Bearer 认证（与已通过文本/流式的 DeepSeek 路由一致）。
- 模型名（依次各跑一次）：
  1. `deepseek-v4.1-flash`
  2. `deepseek-v4-1-flash-261017`
- 问题：固定非敏感 `What is total amount?`
- 数据：独立合成 150 行，全输入 SUM(amount)=11325；结果行不回传模型。
- 确认：沿用隔离 fixture 的显式模拟用户确认（`auto_confirm_fixture=True`），不是真实用户确认。
- 预算：每任务 ≤8 模型步、≤10 工具调用、≤3 元数据、≤100K tokens、≤300 秒、≤2 USD 估算预留；两次最多约 4 USD 估算预留，D053 campaign 不重置。
- 验证目标：真实 DeepSeek 能否驱动 SDK 的 Skill → 指标/受控 SQL → 确认 → 合成 MCP → 自动 QA → 回执发布循环；重点是 Messages、tool_use/tool_result、Skill、stream、usage。
- 明确不做：把 DeepSeek 改名/伪装成 `claude-*`；新端点/供应商；生产/业务 SQL；结果行回传模型；默认 Web 迁移；部署；commit/push。
- 密钥：只由用户在本机终端隐藏输入；不读取宿主 Key/settings/hooks；不写入磁盘/日志/聊天；仅传入子进程环境。

## 3. 结果解释

- 任一模型成功：只能证明“在该合成 fixture 中，SDK 循环可以经 AIPlan DeepSeek 完成一次工具循环”；**不能**关闭 `sdk-real-gateway`，不能称为官方支持的 Claude SDK 路径，也不能证明 Claude 模型可用。
- 失败：记录失败点（认证/模型名/协议/tool_use/stream/usage/模型行为），作为 DeepSeek 不兼容的证据；不自动换端点/供应商/模型，不回退 LangGraph。
- 无论成功或失败，真实 Claude 模型授权仍是独立门禁。

## 4. 实现与验证

- 新增默认关闭的 `real_gateway_experiment` 模式，只允许上述精确端点与两个模型名；默认 fixture 路径不变。
- 新增本机隐藏输入启动器 `run-sdk-deepseek-experiment.cmd` / `scripts/run_sdk_deepseek_experiment.py`。
- `test_sdk_agent.py` 新增精确门禁测试；SDK 专项 **10 passed**；完整后端 **603 passed**（266.81s）。
- 未重跑前端/浏览器/types/build：本次无 UI/契约改动；S02 的 602/17/44 全回归证据仍对应未变的前端。
- 真实网关：**not_run**，等待用户运行启动器并隐藏输入 Key。

## 5. 证据

- [results.json](results.json)
- [source-manifest.json](source-manifest.json)
- [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)
