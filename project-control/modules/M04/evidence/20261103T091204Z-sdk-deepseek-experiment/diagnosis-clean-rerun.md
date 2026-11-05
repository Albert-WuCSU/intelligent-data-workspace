# D072-D 干净重跑诊断（2026-11-03T09:12:04Z）

## 结论

这次 runtime 已在项目外系统临时目录，运行后清理；Windows Job 峰值 **8/7**，低于上限 **10**，项目树上下文泄漏已消除。两个模型名仍都未成功，但原因已经明确：

1. `deepseek-v4.1-flash`：**可用的请求名**。干净运行执行了 Skill → search_semantics → propose_metric_query → request_confirmation → execute_approved_query（两次）→ publish_result → **get_receipt**，在 8 步用尽时返回 `error_max_turns`。发布后多调一次 `get_receipt` 是失败直接原因；不是协议不兼容。
2. `deepseek-v4-1-flash-261017`：**不是可用的请求名**。网关返回 400：
   `This model is not currently supported (deepseek-v4-1-flash-261017). Please check the recommended models at: http://aicoding.console.ctripcorp.com/admin/modelList`
   截图中的这个名字是网关返回的版本别名，不能当作请求 model ID 使用。

## 干净重跑数据

### deepseek-v4.1-flash

- `FAILED SDK_RUN_FAILED` / `result_status=error_max_turns`
- 8 模型步、8 工具调用、1 元数据；22,702 tokens
- usage key = `deepseek-v4.1-flash`；`costUSD=0.0424752` 是客户端估算，`costBasis=unknown`
- 事件顺序：SDK_INIT → Skill → search_semantics → propose_metric_query → request_confirmation → AWAITING_CONFIRMATION → execute_approved_query → execute_approved_query → publish_result → get_receipt
- 发布前工具链完整；失败发生在发布后的额外回执读取
- Job 峰值 8 / 上限 10；内存约 548 MiB / 2 GiB

### deepseek-v4-1-flash-261017

- 网关 400：`This model is not currently supported (deepseek-v4-1-flash-261017)`
- SDK 把错误文本当作 assistant 文本返回，`result_status=success` 但 `usage={}`、无工具调用；runner 因此报 `SDK_PUBLICATION_MISSING`
- 这是**模型名不被支持**，不是 SDK 工具循环缺陷；不要再使用该名字请求

## 隔离观察

- 项目树 context 泄漏已修复：runtime 在 `%TEMP%`，Job 峰值 8/7 ≤10。
- `SDK_INIT` 仍列出非产品 Skill（`deep-research`、`dataviz`、`claude-api` 等）。干净 runtime 下仍出现，说明它们是 CLI 自带/宿主 PATH 可发现的 Skill 列表，不是项目 `AGENTS.md` 直接导致。实际 `Skill` 调用必须被后端接受为 `governed:data-query`，否则运行失败；本次事件中的 Skill 调用通过了治理门禁。该 init 列表仍是残余风险，不能当作“已启用全部 Skill”的证据。
- `CanUseToolShadowedWarning` 仍存在：`allowed_tools` 中的只读/提案工具会被自动批准；执行/发布仍由后端与回调门禁。与既有结论一致。

## 已实施的修正

- Skill 版本 **1.0.1**：明确“`publish_result` 返回 `PUBLISHED` 后停止调用工具、给简短最终回复、不要再调 `get_receipt`”。
- system prompt 同步加入发布后停止指令。
- `publish_result` 返回值增加 `instruction: "Result published. Stop calling tools and give a brief final response."`
- SDK 专项 11 passed；完整后端 604 passed。
- 未提高 max_turns；仍保持每任务 8 模型步预算。

## 待决策

是否批准一次**仅 `deepseek-v4.1-flash`** 的真实重跑，验证 Skill 1.0.1 是否能在 8 步内完成发布并返回最终文本。`deepseek-v4-1-flash-261017` 已被网关拒绝，不再重试。
