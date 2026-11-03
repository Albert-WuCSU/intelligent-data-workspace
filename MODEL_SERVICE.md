# 最新：Messages流式连接测试与模型目录待办（2026-11-02）

当前用户已完成 GLM 模型修改；只读运行状态确认 `glm-5.3` 非流式生成已验证并启用。不会为此再索要Key或重复收费。网关所有支持模型目录、工作台切换复用Key已列入 `project-control/BACKLOG.md`，接口/账号scope未核实前不伪造清单、不试探目录地址。

新开发的流式入口在 **设置 → 流式测试**：只支持 Messages 首切片，固定非敏感文本、单次0.25USD估算，点击“开始流式测试”。上游SSE真实事件由后台有界任务解析，网页只读快照显示部分文本/完成；可取消，失败或未知保留估算，同一编号读取不重复调用。安全检查可延迟释放短文本，不模拟打字，不执行SQL/JOIN。Responses/Chat流式尚未适配，明确不自动换协议。

需要后台实际加载本轮stream_management能力才可使用。当前运行服务未自动重启；如入口提示未加载，请用户本人在原启动器停止并加载新版一次，Key仍由用户在安全网页输入，本助手不读取/搬运。跨重启免输Key的秘密持久化是另一个待决策能力，不用热更新/宿主令牌绕过。

真实网关流式尚未验证；隔离SSE/API/browser与实际loopbackHTTP测试不等于企业网关或公网TLS。M04-A整体仍DO，审查/人工验收后才M03语义→M04-B LangGraph＋治理Harness真实模型规划与取数。以下历史记录不覆盖上述边界。

---

# 当前模型设置入口（2026-11-02）

在左侧底部点击 **设置 → 模型服务**。模型接入不再占右侧会话摘要；输入区“模型服务”也会跳转到同一设置页，返回工作台时保留未发送问题。

1. 选择厂商或自定义协议，填写完整 API 地址。预设只提供地址/协议，不自动填写或锁定模型名称。
2. 输入你账号可用的 **model ID** 与专用 Key。AI Plan 也可填写其他模型名称；内网地址/协议/认证仍固定在已授权目标，不代表其他模型已获供应商权限。
3. 明确同意固定非敏感文本与估算后，保存连接（不调用模型）。Key 提交即清空，仅当前后端内存。
4. 单独显式测试，通过后启用。返回工作台，在输入区选择实测、启用的模型；选择不会收费、不会执行 SQL/JOIN。
5. 修改模型/地址/Key 要保存并重测；禁用/清除使旧目录选择和测试失效，预算保留。当前只维护一个后端会话配置，不是多供应商永久Profile，也不自动拉取厂商完整模型清单。

费用/协议/秘密说明在设置内折叠查看。测试/保存中禁止离开页面；设置/返回/刷新不自动调用模型，退出丢弃未提交Key。

若选择AI Plan时显示“后端仍是固定模型版本”，由用户本人在原启动器停止并重新运行普通 `start-workspace.cmd` 加载新版一次。不要重复开第二个启动器，不要在聊天提供Key；运行中的旧Key不会被开发者读取/搬运。Key切换此后不需重启。

下面旧条目为阶段性历史，不能覆盖上述入口和当前progress状态。流式、真实公网TLS/账号、真实用户设置完整路径及SQL/JOIN仍有未完成门禁。

---

# 推荐入口：网页连接自己的模型API

新版模型服务提供“连接自己的模型 API”表单，不再要求终端输Key。选择厂商预设或自定义协议，填写完整接口地址、model ID、passwordKey，勾选固定非敏感测试用途/估算费用后点“保存连接（不调用模型）”，再点击下方最小测试。Key提交后字段清空，后台本次memory保存；“清除会话Key”不清预算。后端重启才需重新输入。

支持标准Responses/OpenAI-compatibleChatCompletions/AnthropicMessages，不承诺任意私有协议；公网仅HTTPS，不接受任意内网/localhost。公司AIPlan是明确已授权内网预设，不是唯一厂商。Key不得出现在聊天/截图/浏览器storage/history/log/文件中；自定义地址需用户有权使用且测试固定文本不会含行数据/历史。

供应商名称和预设模型不是账号权限/实际兼容承诺，测试按真实回执显示；$0.25预留只是本轮估算启发式不是各厂商真实单价，目标$15/参考$20不硬保证，换Key或厂商不reset累计。普通聊天取数/授权模型目录/stream/SQLJOIN仍后续模块，最小测试成功不代表查询成功。

当前仍loopback固定开发身份，不可暴露公网或用于生产多人秘密管理；只有首次加载新后端需要本人CtrlC/Y重启服务，新保存/换Key/清除均不用重启。原终端入口保留可选高级方式。以下为历史诊断/入口说明，已由上方推荐流程替代。

# 网关思考块兼容修复（2026-10-30）

已观察回执为unsupported_content，而非再次模型映射失败。model_matches=false只是请求/返回名称不相同；新diagnostic另显示model_binding=observed_gateway_alias。
仅对已绑定DeepSeek网关版本，将thinking/redactedthinking当作不需要解释/回放的元数据丢弃，不读取/输出/持久化思考或签名。最终text仍严格校验，工具、未知模型、partial和预算上限不变。旧非网关原生签名规则保留。

旧持Key进程不热加载，完整回归通过后需本人CtrlC/Y、新start-workspace-claude.cmd隐藏输入一次；再显式点击最小模型test。只读回执GET不重新收费，旧失败不改success，不保证下一次成功；若仍失败只反馈诊断链接，禁止复制Key/思考正文。

# 已定位：网关版本别名（2026-10-30）

实际安全回执返回deepseek-v4-1-flash-261017，而请求是deepseek-v4.1-flash。当前修复只为已观察codingplan/Messages/Bearer组合添加精确绑定，保留双模型ID；未知别名不自动允许。合法thinking块不显示，最终只text。旧失败回执不会被改成成功，新代码仍需用户一次显式测试确认。

更新步骤保持：本人CtrlC/Y旧窗口，start-workspace-claude.cmd重新隐输Key，网页刷新后接受估算并测试一次。若成功应显示请求模型、返回模型和observed_gateway_alias；这是最小生成不代表SQL/JOIN。可读诊断链接仍纯GET，不重复收费；预算累计不退不reset。

# 响应标识诊断更新（2026-10-30）

模型不匹配时，“other_or_unreported”旧白名单不能定位真实名称。新版增加“返回模型标识（仅诊断，不表示已授权）”，只返回经过长度/字符/model-family/Key泄漏检查的标识；不能直接接受任意上游模型映射。合法思考块与最终文本分层，思考和签名不展示/保存。

回执“测试追踪”里有“查看只读安全诊断（不再次调用）”链接，GET只读当前UUID回执，不返回模型正文或发网关请求。旧回执没有原始模型信息不能回溯，需用户更新入口隐输后一次显式test，之后只读链接可直接给助手检查，避免反复截图。API重启旧UUID返回404而非重复调用。Key始终不提供聊天或截图；不reset预算。

# 响应诊断入口（2026-10-30）

当前公司AIPlan入口仍start-workspace-claude.cmd的coding-plan/v1/messages、Bearer、deepseek-v4.1-flash，不运行ClaudeCode，LangGraph路线保持。
出现MODEL_RESPONSE_INVALID时不要重复点击或自动更换协议/模型。新版会显示“模型响应安全诊断”：reason、模型名匹配是/否、结束原因、内容类型、输出token。它不显示远程文本、模型思考或Key，失败不自动扩大输出/放宽别名。
加载新版后本人CtrlC/Y旧窗口、新cmd隐输一次，再显式点击测试；将安全diagnostic分类发给助手即可。旧回执不具备诊断字段，重读不会重新调用，所以首次获取需本人一次新请求；已有估算预留不退/不reset。未确认根因前不盲目重试。



## 2026-10-30 当前架构及AIPlan连接（覆盖旧引擎提案）
用户明确保留原LangGraph＋项目治理Harness，D-CLAUDE-ENGINE-058已答，不实施ClaudeCodeCLI/AgentSDK引擎、不安装新Agent栈。M02已验收→M04-A真实模型接入→M03→原M04=M04-B LangGraph顺序不变。公司ClaudeCLI配置仅作模型API非秘密合同：coding-plan baseURL/AUTH_TOKEN风格Bearer，当前明确套餐coding-plan/v1/messages/anthropic_messages/bearer/deepseek-v4.1-flash。用户确认AIPlan支持DeepSeek，记录userconfirmed而非应用integrationpassed；不自动替换为claude-前缀别名、不安装CLI、不执行hooks或继承令牌/无限超时。
start-workspace-claude.cmd只是历史命名的模型API启动器，不等于工作台底层ClaudeCode。用户本人重启隐藏Key并显式test才调用，预算不reset，旧拒绝failed保留；109模型专项过（14套餐+95原专项），本轮preset/tests仅改，provider/UI/ledger未改，不称全backend/browser再过。最新网关实测未运行，收到新回执继续排查，不自动遍历认证/协议。



## 2026-10-30 用户SDK示例修正（当前最高优先接入合同）
用户明确AnthropicSDK baseURL=http://ada-cli-golang.ctripcorp.com，apiKey占位符ada_xxxxxxxx；对应请求候选/v1/messages、x-api-key，而不是此前coding-plan/v1/messages/Bearer。已修start-workspace-claude.cmd所用preset，defaultdeepseek-v4.1-flash保留，预算共用不清零。根网络例外仅精确/v1/messages+Messages+xapikey，不放任意接口或其他域，不安装SDK/读宿主Key/重启用户进程/网关POST。108模型专项通过（含5新root合同范围测试），未重跑完整backend/browser，不称整体通过。
用户先前实测DeepSeekMessagesBearerHTTP403已failed，旧路由认证合并错误由示例明确修正，但不保证此为唯一拒绝原因；新rootxapikey实际test仍not_run。用户本人CtrlC/Y旧窗口、新start-workspace-claude.cmd重新隐输后页面确认authx_api_key再显式test。不能自动重提/尝试别的账号或头，不索要Key。

> 2026-10-29 最新明确选择：默认模型改为 `deepseek-v4.1-flash`（按用户截图中的精确ID），不是Haiku。仍用 `start-workspace-claude.cmd` 的 Anthropic Messages/Bearer候选；网关是否支持该模型与此协议组合需实际测试，不自动改协议。已有预算保留，启动/刷新不收费。下方Haiku描述为历史。

# Claude Code风格入口（2026-10-29）

你的Key由ada-config签发且你明确选择Anthropic接入，新增独立 `start-workspace-claude.cmd`，默认 **claude-haiku-4-5**。它绑定候选Messages路径和Bearer认证（ClaudeCode ANTHROPIC_AUTH_TOKEN风格），不读取或复制ClaudeCode配置/认证，仍需你自行隐藏输入专用Key。Key字符串不能单凭外形确定协议；成功需实际测试，不会自动协议fallback。

1. 在你当前启动窗口按 Ctrl+C，有“终止批处理(Y/N)”则输入Y回车。
2. 双击 **start-workspace-claude.cmd**，确认提示anthropic_messages / claude-haiku-4-5，隐藏输入你的产品专用Key。
3. 保持窗口开启，刷新网页→模型服务→刷新模型状态，应显示协议anthropic_messages、认证bearer、模型claude-haiku-4-5。
4. 勾选接受估算费用，显式点击最小模型测试。若仍拒绝，回执会区分网关HTTP401/403，不复制/发送Key；不要重复请求或换账号绕拒绝。

原 `start-workspace-model.cmd` 仍为Responses入口。两入口共享同一个预算账本，不因切换协议或model重置 $0.50 等已有估算预留。新入口只是用户主动重配置，不代表绕过权限或已验证；Messages/Bearer具体公司网关兼容性仍待本次真实回执证明。模型目录、SQL/JOIN仍未完成。

以下历史入口说明供参考，当前Anthropic用户优先上述独立入口；输入Key与启动/刷新均不自动收费。

# 当前可操作入口：估算预算与最小模型测试（2026-10-29）

你已完成本机隐藏输入，后端只读确认Key配置为true；不是网关认证成功。新版代码需要在你自己的旧启动窗口按Ctrl+C，再双击start-workspace-model.cmd重新隐藏输入一次。不要将Key发聊天或截图。测试完成前请保持窗口开启，普通启动和刷新模型状态不收费。

打开工作台→模型服务→刷新模型状态；新版应显示“可进行最小模型测试”和“估算预留 $0.00 / 目标 $15”（已有试用预留则显示实际账本估算）。勾选“接受估算费用进行最小模型测试”，再点击“测试模型连接（估算 $0.25）”。这一次才通过后端用专用Key发固定非敏感短测试，不发送表行/历史/截图或执行SQL。

结果卡区分最小生成成功、失败或结果未知，显示实际token或未知；费用标为估算，不是实际账单。首次响应可能因网关模型别名/协议/128output限制不兼容而拒绝验证；没有自动重试/换账号/协议fallback。通信异常保留同一requestid，点击“读取同一测试请求”不会自动重复调用；API重启旧generation拒绝而不是重发。

预算按用户已接受近似10-20USD：每受限请求预留0.25USD，累计估算15USD或60次停止。20USD仅预算参考非供应商硬限制；新请求缓存/模型实际费率可能不同。跨重启SQLite账本保留预留，超时/失败不退款以免低估，真实费用从网关看账单。账本位于data/model-runtime，只有UUID/时间/结果类别/token用量，不含Key/问题/模型输出，不入Git；不提供删除/reset按钮，请勿删账本绕限制。

当前Key保留在进程内存，关闭/重启须自己重输；OS同用户/管理员可检查进程内存，不是生产秘密仓库。测试验证模型文本生成，不启用自然语言SQL/JOIN；授权目录保存启禁、业务计划和流式仍后续实现。

下方硬费率/永久阻断或无test端点描述为旧切片，已由D-MODEL-ESTIMATE-BUDGET-053替代；当前以此说明和progress为准。

# Responses适配增量（2026-10-28）

已根据脱敏Codex参考增加显式 `openai_responses` 薄适配。用户使用 `start-workspace-model.cmd` 隐藏输入专用Key时，默认候选为 `http://ada-cli-golang.ctripcorp.com/coding-plan/v1/responses`、`gpt-6.1-sol[1M]`；不再需要手写调用示例。专用环境中的显式配置优先，不读取宿主Codex/Claude配置或认证文件。

候选来源是已观察的base_url/wire_api/model，不是网关已验证协议或模型授权证据。Responses使用专用Key的Bearer协议候选，与Messages的x-api-key隔离；无自动协议回退/换账号/重试。请求明确store=false/stream=false，不发全历史/表行/工具。完成文本、reasoning和不完整/工具/拒绝响应严格区分。

**仍无真实网关调用与生产费用许可**：输入Key后的正确状态是“费用控制待核实”，不是“已连接”。需可核实专用供应商15USD硬限额或实际完整计价/用量，以实现费用治理和真实最小测试入口。不复制宿主令牌，不要求聊天Key。默认服务本轮没有重载；本人在所属旧启动终端CtrlC后使用新启动器。

以下首切片说明的“待精确路径/协议/没有默认model”是历史，现在有脱敏候选但未实测。

# 模型服务本机安全输入（M04-A 第一切片）

模型适配及本机隐藏输入已实现；**真实网关调用、模型目录启用、流式、自然语言SQL及JOIN尚未验证/未完成**。当前没有收费测试HTTP端点，未核实费用门禁前调用拒绝。

## 用户自行输入专用Key
1. 在原来启动本项目的终端按 Ctrl+C，仅停止自己启动的服务。不在聊天贴密钥，不从Claude/Codex复制令牌。
2. 双击项目根目录 `start-workspace-model.cmd`，或在本机PowerShell运行 `services/api/.venv/Scripts/python.exe scripts/dev.py --model-key`。
3. 本机终端隐藏输入产品专用Key并回车；不显示字符，不写文件/日志/浏览器/Git。窗口保持开启，Ctrl+C结束后需重新输入。端口被占用则启动器拒绝，不杀其他进程。非交互终端/无法隐藏时拒绝，不回退回显。
4. 打开工作台的“模型服务”，点“刷新模型状态”。只显示是否配置，不显示Key或掩码。Key仅在launcher/backend进程内存中，使用专用后端命名空间，Node/Vite和数据源Worker不继承。

操作系统/本机同用户或管理员可检查进程内存/初始后端环境；这是有限本机隔离，不是安全硬件密钥仓库或生产身份。没有新增凭证持久化机制，不通过浏览器输入Key。

## 非秘密协议资料与费用门禁
网关授权、15USD测试总预算、仅问题及必要字段外发已确认，不重问。仍需要网关实际**精确Messages路径、协议、授权model ID、实际计价或产品专用Key供应商硬限额证明**。不要把官方价格套网关别名。

非秘密配置使用后端专用变量 `WORKSPACE_MODEL_ENDPOINT`、`WORKSPACE_MODEL_PROTOCOL`、`WORKSPACE_MODEL_ID`。Messages适配显式协议为 `anthropic_messages`；精确路径必须来自实际资料，代码不会从base URL猜路径、不会读取Claude配置。没有默认可用model。

只允许已批准的内网主机与coding-plan路径；禁止重定向、代理环境继承、任意域/工具/SDK插件、自动重试。协议与模型配置不表示已验证；目前尚无生产BudgetPermit，因此即使Key和非秘密配置齐备，也会显示“费用控制待核实”并拒绝收费调用。这不是再次索要预算金额，而是尚未完成真实计费治理。

下一切片：核实供应商限额/计价、接入真实最小测试回执及管理员非秘密配置/保存/启禁与授权模型目录。流式/结构化另测；SQL权限和JOIN由M03及原M04=M04-B治理，不能对100行预览算总体。

## 复现与回滚
专项：`services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_model_provider.py -q`，HTTP仅隔离fixture、Key仅测试哨兵，不调用网关。
回滚使用原 `start-workspace.cmd`（不读/继承模型Key），停自己拥有服务并重启，保留原数据、配置和证据。不要删除用户数据或宿主认证。


## 2026-10-29 用户明确接受近似费用（最高优先当前规则）
D-MODEL-ESTIMATE-BUDGET-053：“你自己估计费用，大体控制在10-20刀预算就行”。这是费用准入变更，不能继续要求供应商硬限额/费率证明作为调用先决条件。历史gpt61截图59.37USD/993次≈0.0598USD/次，但95percentcache，不套为新单价。先目标15USD/预算上限20USD，按每个受限请求估算预留0.25USD/最多60次、2kchars/128输出token/无重试；只是一套保守估算启发式，不是数学费用保证。费用/余额必须标estimated，截图历史费用不当本项目消费，未知结果保留预留，实际报告费用或估算阈值到达停止。
下一步直接实现非秘密跨重启estimatedledger及真实固定非敏感test/receipt入口，再由用户自己本机隐输专用Key触发。仍不复制Codex/Claude凭证，不外发行/历史/截图，不绕权限；真实model/SQL/JOIN未完成。之前“费率或硬限额证明否则永远拒绝”描述已被本次明确用户变更替代。


## 2026-11-02 会话模型目录切片（非模块验收）
- 本机旧API经只读归属核查仍缺 `connection_management`，不修改其Key或自动重启。测试使用独立fixture，新版默认服务须用户本人更新启动器加载一次。
- 当前本机开发身份的模型目录仅来自后端实际配置，最小测试成功后须显式启用；不拉取/猜测供应商所有模型、不自动授权第二个模型。目录ID绑定执行代际和配置版本，服务端复核下游选择；选择模型不调用、不执行SQL。
- 保存/替换Key或模型、禁用、清除使旧测试/目录选择失效，忙时拒绝变更；禁用保留后台内存Key但重新启用须重测，预算跨所有操作保留。刷新网页可复用后端会话，重启丢失，未引入秘密持久化/生产身份/永久Profile。
- 能力分开标记：最小文本实测、显式启用与可选目录；流式/工具/结构化输出/业务问数均未验证。输入区文案明确已选模型不意味着本轮问题会送给模型。
- AC01仅会话配置/测试/刷新/编辑启禁局部验证；真实用户网页Key输入、公网供应商TLS、AC02流式及完整模块验收仍待补，历史失败/not_run和PG/生产发布门禁原样保留。
