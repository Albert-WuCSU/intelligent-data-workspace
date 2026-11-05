# D072-D 第一次运行诊断（2026-11-03T08:57:55Z）

## 结论

这次运行**不能作为干净隔离证据**。虽然 `deepseek-v4.1-flash` 返回 `SUCCEEDED` 并发布 11325，但运行环境存在以下问题，必须用修正后的项目外临时目录重跑：

1. **运行目录在项目树内**：`runtime_root` 位于 `project-control/modules/M04/evidence/.../model-1/runtime`，SDK cwd 向上可发现项目 `AGENTS.md`/`CLAUDE.md`。
2. **SDK init 列出了大量非产品 Skill**：`deep-research`、`dataviz`、`update-config`、`verify`、`debug`、`code-review`、`simplify`、`batch`、`fewer-permission-prompts`、`doctor`、`loop`、`claude-api`、`workflow-authoring`、`run`、`run-skill-generator`、`plugin-authoring`，以及 `governed:data-query`。
3. **CLI 插件 store 出现 `claude-md-or-agents-md` 使用记录**：说明 CLI 执行了 CLAUDE.md/AGENTS.md 扫描路径。
4. **隔离 home 出现宿主工具痕迹**：`.git-ai/internal/...`、Windows Caches、`cwd/%SystemDrive%/...` 等；不是产品 Skill，也不是合成 fixture。
5. **Windows Job 进程峰值超限**：两次运行分别 `job_peak_processes=16` 和 `15`，而配置上限是 `10`。在查清并修正前，不能接受该运行作为隔离通过。

## 结果本身（仅诊断）

### deepseek-v4.1-flash

- `SUCCEEDED`
- 8 模型步、7 工具调用、1 次元数据；24,752 tokens
- 查询 `SUCCEEDED`，质量 `PASS`，发布 11325，150 行全输入
- `model_text` 明确表示不重述数字，让用户看结果卡
- usage key = `deepseek-v4.1-flash`；`costUSD=0.0545056` 是客户端估算，`costBasis=unknown`，不是账单
- 运行中第一次 `execute_approved_query` 因非 UUID 幂等键被拒绝，模型改用合法 UUID 后成功；这是治理门禁按预期工作
- `Skill` 调用最终被后端接受为 `governed:data-query`，否则运行会失败

### deepseek-v4-1-flash-261017

- `FAILED SDK_PUBLICATION_MISSING`
- 当时 runner 未保存失败事件/用量，无法判断是模型没调用 `publish_result`、turn 用尽，还是其他行为差异
- 本次已加失败诊断文件；干净重跑时会保留事件、模型文本、usage 和预算快照

## 其他观察

- `CanUseToolShadowedWarning`：`allowed_tools` 中的只读/提案工具会被自动批准，`can_use_tool` 不会对它们触发；执行/发布工具不在 `allowed_tools`，仍由后端与回调门禁。该警告与既有 S01/S02 结论一致，但应保留为残余风险。
- `[claude-code:unrecognized_model]` 对两个 DeepSeek 名都出现；这是 Claude Code 对非 Claude 模型名的预期提示，本身不是失败。
- `.claude.json` 只含隔离运行生成的 machineID/userID 等，不含认证字段；未发现 Key 写入证据文件。
- 第一次运行的 runtime/outer 目录已删除；保留 `results.json`、`config.json`、`output.json`、stdout/stderr 作为历史诊断。

## 重跑修正

- `runtime_root` 改用系统临时目录（项目树外），运行后清理。
- 失败时写入 `failure-diagnostics.json`，保留事件/模型文本/usage/预算。
- 重跑仍只允许既有 AIPlan coding-plan 端点与两个 DeepSeek 名；仍不伪装 Claude。
- 重跑后重新检查 `SDK_INIT` 的 Skill 列表和 `job_peak_processes`；若仍超限，停止真实运行并先修隔离。
