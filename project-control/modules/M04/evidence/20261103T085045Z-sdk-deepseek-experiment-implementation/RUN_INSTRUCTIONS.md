# D072-D 运行说明（仅本机、用户操作）

> **2026-11-03 成功**：D073-A 单模型重跑已成功，`deepseek-v4.1-flash` 在 8 步内完成发布（11325，质量 PASS），Job 峰值 8≤10。该结果是非 Claude 兼容性实验，不关闭 `sdk-real-gateway`。当前不再需要运行本启动器；下一步等待用户决定是否做 Web 集成或等待 Claude 模型。成功报告见 `20261103T092622Z-sdk-deepseek-experiment/success-report.md`。

> **第一次运行后的更新（2026-11-03）**：第一次运行发现 runtime 在项目树内，CLI 会向上发现项目 `AGENTS.md`/`CLAUDE.md`，SDK init 列出非产品 Skill，且 Job 峰值进程超过上限。该次结果已标记为无效诊断。现在 runtime 改到系统临时目录并在运行后清理，失败时保存 `failure-diagnostics.json`。请按下面步骤**重新运行一次**，以生成干净证据。

## 干净重跑后的单模型验证

干净重跑已确认：

- `deepseek-v4-1-flash-261017` 被网关 400 拒绝（`This model is not currently supported`），**不再重试**。
- `deepseek-v4.1-flash` 能跑完整工具链，但在发布后多调了一次 `get_receipt`，8 步用尽触发 `error_max_turns`。
- 已加 Skill 1.0.1 的“发布后停止”指令；仍保持 8 模型步预算。

若批准 D073-A，只运行第一个名称：

```powershell
.\run-sdk-deepseek-experiment.cmd --model deepseek-v4.1-flash
```

启动器仍会隐藏输入 Key，并把新证据写到新的 `<UTC>-sdk-deepseek-experiment` 目录。

## 运行方式

在项目根目录双击 `run-sdk-deepseek-experiment.cmd`，或在项目根目录的普通终端运行：

```powershell
.\run-sdk-deepseek-experiment.cmd
```

启动器会：

1. 在终端隐藏输入一次 AIPlan 产品专用 Key（输入不回显、不保存、不写日志）；
2. 依次运行两个模型名：
   - `deepseek-v4.1-flash`
   - `deepseek-v4-1-flash-261017`
3. 每个模型一次固定非敏感问题，使用独立合成 150 行数据、受控 MCP、自动 QA 与回执发布；
4. 每个模型最多 8 模型步、10 次工具、100K tokens、300 秒；估算预留每次 2 USD，两次最多约 4 USD（D053 不重置）；
5. 把非秘密证据写到：

```text
project-control/modules/M04/evidence/<UTC时间>-sdk-deepseek-experiment/results.json
```

## 不要做什么

- 不要把 Key 贴到聊天、文档、截图或任何文件。
- 不要改成 `claude-*` 模型名；本实验只使用真实 DeepSeek 名。
- 不要换端点/供应商；失败就保留失败证据。
- 不要把本实验成功称为“Claude SDK 已验证”或关闭 `sdk-real-gateway`。

## 运行后

把终端最后打印的 evidence 路径告诉我，我读取 `results.json` 并保存检查点。若两个模型都失败，也把路径给我；失败点本身就是结论。
