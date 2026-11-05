# D072-D 干净单模型成功报告（2026-11-03T09:26:22Z）

## 结果

`deepseek-v4.1-flash` **SUCCEEDED**。这是非 Claude 兼容性实验，不是 Anthropic 官方支持的 Claude SDK 路径。

- SDK/CLI：0.2.177 / 2.1.317
- Skill：`data-query` **1.0.1**，SHA256 `bcc683ea15044db85741f5fb27f79fcf2ef88bb415877cf717a13033e37bc580`
- 端点：`http://ada-cli-golang.ctripcorp.com/coding-plan`，Bearer
- 模型请求名：`deepseek-v4.1-flash`
- 问题：`What is total amount?`
- 数据：独立合成 150 行

## 预算与过程

- 8 模型步、7 工具调用、1 次元数据；23,080 tokens
- 每任务上限 8 步/10 工具/100K tokens/300 秒；估算预留 2 USD（D053 不 reset）
- usage：input 4,014 / output 1,146 / cache read 17,920；`costUSD=0.04256` 是客户端估算，`costBasis=unknown`，不是账单
- 事件：SDK_INIT → Skill → search_semantics → propose_metric_query → request_confirmation → AWAITING_CONFIRMATION → execute_approved_query → execute_approved_query → publish_result
- 执行两次是因为第一次幂等键不合法被拒绝，模型改用合法 UUID 后成功；这是治理门禁按预期工作
- 发布后没有额外的 `get_receipt`，Skill 1.0.1 的停止指令生效

## 结果与安全

- 查询 `SUCCEEDED`；质量 `PASS`（schema/unit/full_input/row_count/grain/limitations）
- 发布 `11325`，150 行全输入；`model_generated_numbers=false`
- `result_rows_returned_to_model=false`；模型文本没有复述 11325，只让用户看结果卡
- 流事件 661
- Windows Job 峰值 8 / 上限 10；内存约 540 MiB / 2 GiB
- 证据中未发现 Authorization/Bearer/Key 标记；Key 只在本机隐藏输入并经子进程环境传递

## 残余风险与边界

1. **官方不支持**：Anthropic 明确不支持把 Claude Code 路由到非 Claude 模型。本结果只证明“在该合成 fixture 中可运行”，不能关闭 `sdk-real-gateway`（Claude 模型门禁）。
2. `SDK_INIT` 仍列出 CLI 自带/可发现的非产品 Skill。实际 `Skill` 调用必须被后端接受为 `governed:data-query`；init 列表不是“全部已加载/可用”的证明。
3. `CanUseToolShadowedWarning`：`allowed_tools` 中的只读/提案工具会被自动批准；执行/发布仍由后端与回调门禁。该警告应保留为残余风险。
4. `[claude-code:unrecognized_model]` 对 DeepSeek 是预期提示，不是失败。
5. 版本别名 `deepseek-v4-1-flash-261017` 被网关 400 拒绝，不能作为请求名。
6. 未验证：默认 Web 工作台迁移、真实用户路径、生产/业务 SQL、多租户、持久任务、部署、费用账单。
7. 模型行为有方差：第一次污染运行 8 步成功；干净运行在 Skill 1.0.1 前因额外 `get_receipt` 触发 max_turns；本成功运行是 Skill 1.0.1 后的单次结果，不能承诺每次稳定。

## 结论

`deepseek-v4.1-flash` 可以在受控合成 fixture 中驱动 Claude Agent SDK 的 Skill/工具/确认/执行/QA/发布循环。它可作为一个明确标注的**非 Claude 兼容性实验路径**，但不等同于官方 Claude SDK 验证。是否把它用于 Web 集成或产品主线，需要单独决策。
