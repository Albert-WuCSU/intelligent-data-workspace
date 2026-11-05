# M04-C02-SDK｜真实网关前置只读复核（D-M04B-SDK-REAL-072）

日期：2026-11-03T08:14:13Z  
状态：只读复核完成；AIPlan 产品专用凭证的 Claude 授权**未确认**；真实 SDK 网关仍 `not_run`

## 1. 本轮范围与安全边界

- 只读现有非秘密项目档案：MODEL_PROVIDER_NOTES、M04-A 认证合同记录、CLAUDE_ENGINE_PROPOSAL、BACKLOG、S01/S02 与最终证据。
- **没有**读取宿主 Key/settings/hooks；没有访问网关；没有真实模型/SDK/SQL 调用；费用 0。
- 没有修改产品代码、默认模型、端点、供应商或 LangGraph 基线。

## 2. 只读发现

### 2.1 有记录的宿主 Claude Code 非秘密别名

2026-10-28 的项目记录曾观察宿主 Claude Code 配置：

- Base URL：`http://ada-cli-golang.ctripcorp.com/coding-plan`
- 顶层 model：`claude-kr-claude-opus-5.5[1M]`
- 默认映射：`claude-haiku-4-5`
- 存在认证字段；认证值未记录/未复制。

这只能证明宿主 Claude Code 曾配置这些别名，**不能证明产品专用 AIPlan Key 有 Claude 权限**，也不能证明网关支持 SDK 的 tool_use/Skill/stream/usage。

### 2.2 用户提供的另一候选合同

2026-10-30 用户提供的 Anthropic SDK 示例为：

- Base URL：`http://ada-cli-golang.ctripcorp.com`
- 候选路径：`/v1/messages`
- 候选认证：`x-api-key`

该合同未实际测试；产品默认仍为 AIPlan `coding-plan/v1/messages` + Bearer + `deepseek-v4.1-flash`。不能自动把两套 base URL/auth 互换或逐个试。

### 2.3 产品实际证据

- 已验证：DeepSeek 固定非敏感文本生成、固定文本流式。
- 未验证：Claude 模型身份/授权、SDK Messages/tool_use、Skill 加载、SDK stream 完整事件、SDK usage/model_usage。
- 官方明确：不支持通过网关把 Claude Code 路由到非 Claude 模型；宿主 Claude Code 权限不自动成为产品 API 权限。

### 2.4 能力矩阵（真实网关）

| 能力 | 结论 |
| --- | --- |
| Claude 模型授权 | 未确认 |
| Messages | `not_run`（SDK 请求形状/完整事件） |
| tool_use / tool_result | `not_run` |
| Skill | `not_run` |
| stream | `not_run`（SDK 工具流） |
| usage | `not_run`（SDK model_usage） |

## 3. 结论

现有非秘密项目记录不足以确认 AIPlan 为产品专用凭证提供了账号授权的 Claude 模型。`sdk-real-gateway` 保持 `not_run`，不得用宿主 Claude Code 别名或 DeepSeek 文本成功替代。不自动换模型、端点、供应商，不回退 LangGraph。

## 4. D-M04B-SDK-REAL-072 最小真实测试许可（待用户选择）

仅在用户能确认以下三项后，才可执行一次最小真实 SDK 工具循环：

1. 精确的授权 Claude model ID；
2. 对应 base URL；
3. 认证模式（Bearer 或 x-api-key）及产品专用 Key 的 Claude 权限。

**测试范围（A）**：现有受控 runner + 本地合成 MCP；固定非敏感问题；≤8 模型步、≤10 工具调用、≤3 次元数据、≤1 次执行、≤1 次发布、≤100K tokens、≤300 秒、≤2 USD 估算预留（D053 不重置）；不重试/不 fallback；结果行不回传模型；不执行生产 SQL；不迁移默认 Web；不新端点/供应商；不部署。

**可验证**：真实 Claude 模型身份与 alias 绑定、Messages/stream 完成、tool_use 往返、受控 Skill 加载、SDK usage/model_usage。

**不包含**：宿主 Key/settings/hooks 读取、聊天提供 Key、生产/业务数据、结果行外发、默认 Web 迁移、部署、commit/push。

**选项**：

- **A（推荐，前提是你能确认授权）**：确认授权 Claude 模型并批准上述一次最小真实测试。
- **B**：AIPlan 只有 DeepSeek；真实 SDK 保持 `not_run`，记录 `blocked_by_model_compatibility/authorization`，不收费。
- **C**：暂缓，先向网关管理员确认授权、base URL/auth 与协议能力；不改配置、不调用。

## 5. 证据

- 本文件：[review.md](review.md)
- 机器可读：[review.json](review.json)
- 来源及 SHA256 见 review.json 的 `sources`。
