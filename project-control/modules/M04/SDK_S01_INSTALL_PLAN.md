# M04-C02-SDK｜S01 安装前核验与许可点

日期：2026-11-03  
状态：S01 调查完成；SDK 安装、运行、真实网关与 MVP 仍 `not_run`  
主线：D-M04B-CLAUDE-SDK-070，不重选框架，不改变 D053 总预算或 PG/生产延期

## 1. 结论

1. 可将 **Python SDK 0.2.177 + 捆绑 Claude Code CLI 2.1.317** 作为待批准安装候选。Windows x64 wheel 哈希、包内容、Python/AMD64 兼容和离线依赖解析均已核实。
2. **现有 AIPlan/DeepSeek 不能登记为 SDK 兼容。** 官方明确不支持通过网关把 Claude Code 路由到非 Claude 模型；当前仅有 DeepSeek 固定文本和固定文本流式成功，没有 Claude 模型、工具循环、Skills 或 SDK usage 证据。
3. SDK 代码包标记 MIT，但 SDK/CLI 使用受 Anthropic Commercial Terms 约束。嵌入产品不得修改二进制或移除/禁用/限制内置认证；对外终端用户的认证与计费必须满足官方条件。
4. 原生 Windows 没有官方命令沙箱。首切片可用“去除内置工具 + 独立 runner/目录/环境 + 服务端工具门禁”做有限本机验证，但不能称文件/网络沙箱或生产隔离。WSL2 状态命令退出 50，当前没有可用 WSL2 证明。
5. 建议只申请 ** pinned wheel 安装 + 离线/合成 fixture** 许可；真实 Claude 模型、AIPlan SDK 工具循环、结果行回传模型、生产 SQL 和部署不在该许可内。

## 2. 已锁定发布物

| 项目 | 实测/官方值 |
| --- | --- |
| Python SDK | `0.2.177` |
| 捆绑 CLI | `2.1.317`，GitHub release 与 wheel 内 `_cli_version.py` 一致 |
| Release 时间 | `2026-11-03T02:17:57Z` |
| Windows wheel | `claude_agent_sdk-0.2.177-py3-none-win_amd64.whl` |
| 大小 | `149800822` bytes |
| SHA256 | `7997db488354a539c08b5b6b16717d99ae67903ae7351da43d51b68b80097fad` |
| wheel 内 CLI | `claude_agent_sdk/_bundled/claude.exe`，解压大小 `338187936` bytes |
| Python | `>=3.10`；项目实际 `3.12.14` / AMD64 |
| wheel 检查 | SHA 与 PyPI 一致、33 个条目、CRC 全通过；未执行其中二进制 |
| 离线 pip dry-run | 退出 0，仅 `Would install claude-agent-sdk-0.2.177`，无旧包替换 |
| 当前依赖 | anyio 4.15.1、jsonschema 4.26.0、mcp 1.30.0、sniffio 1.3.1 已满足 |
| 当前环境 | SDK 未安装；`pip check` 退出 0 |

全部平台 artifact 哈希和原始命令见 [package-verification.json](evidence/20261103T060255Z-sdk-install-plan/package-verification.json)，wheel 内源码摘录见 [wheel-inspection.json](evidence/20261103T060255Z-sdk-install-plan/wheel-inspection.json)。

建议安装时再次核对同一 SHA，然后从已审 wheel 离线安装；不另装 CLI/npm/Node，不改全局环境。

## 3. 许可与法律边界

官方 [Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance) 与 wheel METADATA 均指向 [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms)。当前 Commercial Terms 页面标示生效日期为 2025-06-17。

- SDK Python 包自身保留 MIT LICENSE；这不是把整个 Claude Code 运行能力当作无约束 MIT 组件使用。
- 预装/运行 Claude Code 于产品中，须使用 Anthropic 发布的原二进制，不修改它，也不移除、禁用或限制其内置认证方法。隔离宿主凭据不等于删除认证能力。
- 不得代终端用户支付、转售或中介化 Claude 使用。终端用户应使用自己的 Anthropic API key、Claude 订阅或受支持第三方推理提供方凭证，并由 key/凭证所有者按协议承担费用。
- 当前仅单用户、本机、组合 portfolio 验证；多租户、对外托管、共享 key 给终端客户或商业分发必须另做条款审查，不能从本机安装许可外推。
- 可以用纯文本准确说明运行 Claude Code，不得借名称/Logo 暗示 Anthropic 背书或合作。

## 4. AIPlan 兼容矩阵

当前项目真实证据只覆盖：

- `coding-plan/v1/messages` + Messages + Bearer + `deepseek-v4.1-flash` 固定文本成功；返回版本别名另行绑定。
- 同一 DeepSeek 配置的固定文本流式完成，`stream_verified=true`；SQL 未执行。
- 详见 [real-stream.json](../M04-A/evidence/20261102T065830543311Z-actual-stream-acceptance/real-stream.json)。这不是 SDK 证据。

| 能力 | 官方要求/事实 | 当前结论 |
| --- | --- | --- |
| 模型 | 官方不支持经网关路由 Claude Code 到非 Claude 模型 | **不兼容受支持路径**：当前 DeepSeek；AIPlan 是否提供授权 Claude 模型未知 |
| Messages | `ANTHROPIC_BASE_URL` 对应 Anthropic Messages，`POST /v1/messages?beta=true` | 普通 DeepSeek Messages 曾通过；SDK 请求形状未测 |
| tool_use/tool_result | 标准工具块、schema 与后续 tool_result 必须完整往返 | `not_run` |
| Skills | CLI 从本地文件发现并调用 Skill；无独立网关 Skills API | SDK 支持；AIPlan 端到端 `not_run`，需承载 Skill 工具调用及上下文 |
| Streaming | 有序完整 SSE 至 `message_delta`/`message_stop`，不能被整段缓冲；ping/idle 也要保留 | 固定文本 SSE 成功；SDK 工具流与完整事件序列 `not_run` |
| usage | SDK 从 result 读取 usage/model_usage；output token 以 result 为准 | 固定测试 token 字段不等于 SDK model_usage，`not_run` |
| cost | `total_cost_usd/costUSD` 是客户端价格表估算，不是账单；未知模型可无法定价 | 不用于真实费用保证；D053 估算账本继续独立执行 |
| 高级字段 | beta headers、thinking、effort、context_management、cache_control、mid-conversation system 等按版本发送 | 全部 `not_run`；不得靠关闭字段隐瞒兼容差距 |
| 认证/base URL | `ANTHROPIC_AUTH_TOKEN`→Bearer，`ANTHROPIC_API_KEY`→x-api-key；base URL 后由 CLI 组路径 | 不自动把现有完整 endpoint 改写成 root/coding-plan base；配置与实测均未做 |
| 模型目录 | 可选 `/v1/models`，默认关闭；目录不代表账号授权或生成成功 | 保持 BACKLOG，不猜接口、不批量试模型 |

官方同时说明：Skills 的文件发现、命令和 init 列表是本地 CLI 行为，但 `skills=[]` 只是上下文过滤，不是文件系统沙箱。技能文本、工具定义和结果都会进入模型上下文，仍受外发合同约束。

## 5. Windows runner 与工具隔离

### 5.1 已核事实

- SDK 启动并监管 `claude` 子进程；每个 session 一个进程，默认继承 cwd、写本地 transcript，不是无状态 HTTP wrapper。
- Python `env={...}` 是在父环境上合并。wheel 源码明确为 `inherited_env + options.env`，所以 `env={}` 不能隔离宿主 Key/代理/OTEL。
- `setting_sources` 缺省会读 user/project/local；设置 `skills` 而未显式设置来源时，0.2.177 会自动补 `['user','project']`。
- `setting_sources=[]` 也不覆盖 managed policy、`~/.claude.json`、auto memory、claude.ai connectors 等所有输入。
- 官方沙箱支持 macOS、Linux、WSL2；**原生 Windows 上命令不被官方沙箱隔离**。Windows Job Object 可继续做资源/进程限制，但不是文件或网络边界。
- `allowed_tools` 是自动批准，不是可用工具白名单；`can_use_tool` 可被先前的 allow/mode 跳过。`bypassPermissions` 禁止用于本项目。
- `tools` 控制内置工具可用性；`tools=['Skill']` 可只保留 Skill 内置工具，MCP 工具另由 `mcp_servers` 显式提供。

### 5.2 首切片强制配置（安装后验证，不是现已实现）

1. 用单独 launcher 以**最小父环境**启动 runner，不能仅在 SDK options 里覆盖 env。清除宿主认证、代理、OTEL、调度、插件和其他非必要变量，只传本任务明确需要项。
2. 每任务独立 `cwd`、`CLAUDE_CONFIG_DIR`、HOME/USERPROFILE 对应目录和临时目录；`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`、`ENABLE_CLAUDEAI_MCP_SERVERS=false`。
3. `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` 并关闭遥测，不配置外部 trace；网络仅允许批准的模型网关与受治理工具适配，不开放 WebFetch/WebSearch。
4. 为 Skills 使用独立、受版本审计的 cwd，仅放托管 `.claude/skills/<name>/SKILL.md`，不放 settings/hooks/MCP/CLAUDE.md，不使用 add_dirs/plugins。显式 `setting_sources=['project']`、`skills=[精确名称]`；禁止 user/local。
5. `tools=['Skill']`，只注册项目 governed MCP；不暴露 Bash/PowerShell/Write/Edit/任意 Read/Glob/Grep/Web/Agent/Task 等内置工具。
6. `permission_mode='default'`，`fallback_model=None`，禁 `bypassPermissions/acceptEdits/auto`。`can_use_tool` 默认拒绝；仅只读/提案工具可自动批准，执行与发布绝不放入 allowed_tools。
7. 外层 Windows Job 限制内存、CPU、进程数和墙钟，并回收整棵新建进程树；不继承旧 PID，不盲杀。官方托管建议起步资源为每 agent 1 GiB RAM、5 GiB disk、1 CPU，实际限制需安装后测量，不能当已验证容量。
8. 原生 Windows 文件/网络强隔离、WSL2/container/VM、多租户与生产部署继续保留独立门禁。

## 6. 有限多轮预算子合同（建议随 S02 实施）

以下是一个业务任务从提问、澄清、确认到发布的**总上限**，不是单次 128-token 旧合同，也不重置 D053 campaign：

| 维度 | 初始上限与强制方式 |
| --- | --- |
| 模型步 | SDK `max_turns=8`，Harness 跨澄清/确认累计也不超过 8；最终文本也占一步 |
| 工具调用 | 每任务最多 10 次；元数据/语义检索最多 3 次，执行最多 1 次、发布最多 1 次，禁止执行重试 |
| Token | `CLAUDE_CODE_MAX_OUTPUT_TOKENS=4096`；Harness 按 result `model_usage` 累计输入、cache 与输出，总量达到 100000 停止，不自动 compact/resume |
| 墙钟 | 每任务 300 秒外层硬截止；API header 60 秒、流空闲 30 秒；超时不重提未知执行 |
| 重试/后台 | `CLAUDE_CODE_MAX_RETRIES=0`、禁 nonstreaming fallback、无 fallback model、无子 Agent/后台任务/定时任务；capability retry 仍须计入实际调用 |
| 估算费用 | 8 个模型步 × 既有 $0.25 启发式 = **每任务 $2 预留**；SDK `max_budget_usd=1.75` 仅辅助并留余量 |
| 计费真相 | SDK 成本字段不是第三方网关账单；余额不足不启动，未知/失败保留预留，真实费用不虚构、不重置 campaign |

`task_budget` beta 存在，但当前网关支持和耗尽语义未验证，不能作为唯一 token 安全边界。`max_turns` 在新用户消息/reset 场景可能重新计数，所以 Harness 必须独立累计。

## 7. 治理工具合同

模型只收到最小必要参数；owner、tenant、真实路径、权限、密钥由服务端绑定，不接受模型传入提升权限。

| 工具 | 作用 | 服务端硬门禁/返回 |
| --- | --- | --- |
| Skill（内置） + `resolve_route` | 先加载指定产品 Skill，再登记路由 | Harness 观察实际 Skill 调用并核 SKILL.md SHA/version；无实际加载或版本不符，不发 `SkillRouteReceipt` |
| `search_semantics` | 查已发布指标/口径 | owner、来源、发布状态、版本；只返回必要语义，不返回行 |
| `read_authorized_metadata` | 读授权表/字段 | 真实 MCP/schema、source version；只元数据，无任意路径/SQL |
| `propose_metric_query` | 生成指标计划 | 指标匹配优先，绑定 route/语义/schema/model/plan hash；不执行 |
| `propose_sql_query` | 无匹配指标时申请 SQL | AST、方言、字段、只读、grain/JOIN/扫描预算；无明确关系不猜 JOIN |
| `request_confirmation` | 产生用户可理解确认单 | 只创建确认请求，不执行；包含口径、来源、范围、预算和外发说明 |
| `execute_approved_query` | 受治理 MCP 取数并**自动 QA** | 有效 confirmation、route/skill/version/owner、预算、tombstone/idempotency 全部通过才可一次提交；返回 QueryReceipt + QualityReceipt |
| `get_receipt` | 查询已有执行/质量回执 | owner 与 generation 校验；只读，不重提 |
| `publish_result` | 发布结构化结果卡 | 必须同时核 QueryReceipt + QualityReceipt + 当前版本/owner；FAIL/UNKNOWN 不可包装成功 |

默认执行工具只向模型返回回执 ID、状态和最小质量元数据，**不回传业务行/完整结果**。后端可直接生成真实结果卡；若后续需要模型解释数值或把行/完整结果送回网关，须另审数据外发子合同。

SDK 事件只映射真实任务状态：Skill/工具开始结束、等待澄清、等待确认、执行、QA、发布/失败。思考链、宿主日志和 Key 不进入业务 UI。

## 8. 明确安装许可点：D-M04B-SDK-INSTALL-071

推荐批准范围：

1. 对上述固定 SHA 的 `claude-agent-sdk==0.2.177` Windows wheel 做项目 venv 内离线安装；不升级/替换其他包，不另装 CLI。
2. 安装后仅做 import/版本、CLI version probe、最小环境/目录、启动退出、Windows Job 和独立合成 fake gateway/MCP fixture 验证。
3. 实现 S02 最小 runner、版本化产品 Skills、上述工具与预算门禁；保留 legacy/SDK capability 区分，完整回归仍须重跑。
4. 不包含真实 AIPlan/其他模型调用、收费、生产 SQL、新模型/端点、结果行外发、WSL/container 安装、部署或 Git push。

真实 SDK 网关测试前另需：用户确认 AIPlan 上**获授权 Claude 模型**及对应 base URL/auth，并按上述矩阵做用户显式最小工具循环。若只有 DeepSeek，则保持 `sdk-real-gateway=not_run/blocked_by_model_compatibility`，不自动换供应商或回退 LangGraph。

备选：暂不安装，仅保留本次调查报告；SDK 方向不变。

## 9. 本轮实际执行与未执行

实际通过：

- `progress.py validate/show`：revision 165 合法；后续包检查点保存为 revision 166。
- PyPI/GitHub 官方 release 读取与固定 wheel 下载/SHA/CRC/内容检查。
- 离线 `pip install --dry-run --no-index --no-cache-dir <wheel>` 退出 0，仅新增 SDK。
- `pip check` 退出 0。
- 官方法律、网关、权限、Skills、hosting、成本和 Windows 沙箱文档只读归档。

明确未做：SDK 安装/import/CLI 执行、真实模型或 AIPlan POST、任何生产查询、宿主 Key/settings/hooks 读取、服务重启、WSL/container 安装、部署和子 Agent。`wsl --status` 退出 50，不据此声称 WSL2 可用。

## 10. 官方来源

- [PyPI package metadata](https://pypi.org/pypi/claude-agent-sdk/json)
- [SDK v0.2.177 release](https://github.com/anthropics/claude-agent-sdk-python/releases/tag/v0.2.177)
- [Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- [Other LLM gateways](https://code.claude.com/docs/en/llm-gateway)
- [Gateway compatibility guide](https://code.claude.com/docs/en/llm-gateway-protocol)
- [Connect to a gateway](https://code.claude.com/docs/en/llm-gateway-connect)
- [Hosting](https://code.claude.com/docs/en/agent-sdk/hosting)
- [Secure deployment](https://code.claude.com/docs/en/agent-sdk/secure-deployment)
- [Permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- [Skills](https://code.claude.com/docs/en/agent-sdk/skills)
- [Cost and usage](https://code.claude.com/docs/en/agent-sdk/cost-tracking)
- [Claude Code features / setting sources](https://code.claude.com/docs/en/agent-sdk/claude-code-features)
- [Custom tools](https://code.claude.com/docs/en/agent-sdk/custom-tools)
- [Agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)
- [Sandboxing](https://code.claude.com/docs/en/sandboxing)
- [Environment variables](https://code.claude.com/docs/en/env-vars)

下载原文的逐文件 SHA 见 [source-manifest.json](evidence/20261103T060255Z-sdk-install-plan/source-manifest.json)。旧 LangGraph 分支与 593/17/44 结果只保留作历史比较基线。
