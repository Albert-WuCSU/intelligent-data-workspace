> 2026-10-29 最新明确选择：默认模型改为 `deepseek-v4.1-flash`（按用户截图中的精确ID），不是Haiku。仍用 `start-workspace-claude.cmd` 的 Anthropic Messages/Bearer候选；网关是否支持该模型与此协议组合需实际测试，不自动改协议。已有预算保留，启动/刷新不收费。下方Haiku描述为历史。

> 2026-10-28 最新：M02有限本机已验收，M04-A-C01正在DO。getpass本机隐藏专用Key、后台内存隔离和薄Messages候选适配/只读状态首切片已编写，真实协议/model/费用门禁尚未验证，收费请求拒绝。下方“未实现/相邻PLAN/待确认许可”均为历史；网关/15USD/问题及必要字段外发/PG生产后补已回答，不重复问。专用Key只能用户自己在本机输入，不含在非秘密文档示例。

> 2026-10-28 恢复校正：下方“接入前待确认”第1—3项属于历史，D-MVP-FAST-034已回答，不再重复要求许可。专用Key由用户通过拟本机隐藏终端入口输入，当前入口尚未实现；不读取宿主认证，不做秘密持久化。真实调用仍需精确协议/model及可核实计价或供应商专用硬限额。相邻PLAN已更新为内存凭证/前后端环境隔离方案，M02验收前不进入DO。
> 2026-10-28 最新授权：D-MVP-FAST-034已确认产品专用调用该公司HTTP网关，仅问题/必要字段信息外发，不发表行/全历史/截图。PG与生产后補明确。认证不得复用ClaudeToken；项目专用密钥当前未配。入口/openapi无认证探测404，不代表model生成通过，协议/实际模型/费率或15USD供应商硬限额待补，已批准许可不重问。

# Claude Code非秘密供应商盘点与模型接入边界

2026-10-28；用户授权只读参考本机Claude Code供应商/文档/模型信息。只解析已知settings JSON中的非秘密字段，不输出或复制认证值，不读取其MCP配置/项目历史/hooks，不调用内网模型接口。

## 观察到的配置（配置不等于协议/权限/价目实证）
- Base URL：`http://ada-cli-golang.ctripcorp.com/coding-plan`。HTTP公司内部网关，包含自定义路径；不是已验证的官方HTTPS模型接口。
- Claude Code顶层model：`claude-kr-claude-opus-5.5[1M]`。
- Sonnet/Opus/Haiku默认映射均为`claude-haiku-4-5`。这些值不一致/可能是网关别名，不能从名称推导真实模型、上下文、价格或可切换权限。
- 存在认证配置字段，但认证值未输出/复制/配置到本产品。Claude Code已有权限不自动成为产品API权限。
- 本地JSON不含已核实接口文档/价格/应用调用授权；接口可能类似Anthropic Messages，但`/coding-plan`路由映射需网关负责人文档确认，不能直接拼`/v1/messages`宣称兼容。

## 15美元是什么
用户明确给出**本项目MVP测试调用总预算上限15 USD**。是模型服务调用费用，不是Python/本机SQL执行费用，也不统计用户在Claude Code或其他客户端的消费。

费用必须以该网关的实际计价规则/可核验用量为准；官方Anthropic价格不能自动套用网关别名。未知费率或用量时UI显示未知，不虚构已消费/余额；15美元不等于无限请求许可。

优先给项目专用API Key设供应商硬限额15美元。若支持计量费率，再以各模型输入/输出/缓存/其他计费项的明确上界做服务端原子预算预留，有限输入/输出token/请求数/重试总额；费用结果不明保留预留、不自动重提，跨重启保护账本。缺可靠单价/计量及供应商限额不能承诺硬费用控制。

## 接入前待确认
1. 今天是否按有限本机MVP验收并将PG真实/生产后补（保留not_run发布门禁），M02不自动closed。
2. 公司网关是否允许本产品独立调用、使用HTTP在当前网络发送应用专用认证头；TLS/驻留限制由管理员明确，不静默降级证书检查。未核实则不请求该网关。
3. 外发仅本轮问题+选中表必要字段名/类型+批准语义，**不发数据行、全历史/全库Schema、其他源、截图或公司表内容**。这是待批准范围，不由参考配置推导。
4. 一个或多个**真实授权**model ID、请求路径/协议/错误与用量字段及15美元实际价格/专用硬限额。
5. 应用专用密钥由用户在安全渠道配置至专用后端命名空间；不要发聊天或复制`ANTHROPIC_AUTH_TOKEN`/Claude Code/Codex凭证。本轮未读取认证值用于执行。

## 前端模型切换
已请求在取数工作台输入区提供模型选择，下游只展示服务端已配置/已授权的模型项，未验证项不成为可用项。更换模型/源使后续旧查询计划失效，不悄悄重提SQL；每次任务回执绑定模型ID/配置版本，已有历史文字不被改写。M04-A真实目录/调用尚未实现，当前入口明确显示“未连接模型”，不能把本机别名伪装为已接通模型。

## 当前完成与实现顺序
现有数据源API/MCP和只读预览真实可用；本轮先落已批准的界面（左历史/中对话/右摘要/底部模型及数据源选择）。供应商发现属只读准备，不是M04-A代码完成、模型测试成功或M02验收。M04-A薄适配PLAN将在M02有限范围/模块验收后执行；ModelProvider测试成功也不冒充受控问数已完成。保持M02→M04-A→M03→原M04=M04-B顺序，LangGraph版本/安装另核验。


## Codex脱敏网关参考（2026-10-28）
用户授权查自己的Codex API配置以免手写调用示例。本轮解析已知D:/Users/luqianwu/.codex/config.toml，仅输出model/model_provider及providers的name/base_url/wire_api/requires_openai_auth，URL移除userinfo/query/fragment；不复制原文件、auth值、Key/令牌、HTTPheaders/MCP配置，不读auth.json或执行凭证命令。
实际配置：provider=ctrip，base_url=http://ada-cli-golang.ctripcorp.com/coding-plan/v1，wire_api=responses，model=gpt-6.1-sol[1M]，requires_openai_auth=true。脱敏参考CODEX_GATEWAY_REFERENCE.json。官方config-reference已只读获取确认wire_api含义。候选POST /coding-plan/v1/responses由base_url和协议推导，未经真实调用验证；model别名/运行时override/产品专用授权及计价未知。
这与产品现有anthropic_messages候选适配不同；不能拿/v1/messages发Responses对象或将宿主认证复制到产品。下一步可直接用这份非秘密参考实现显式Responses薄适配和隔离测试，不要求用户手写网关示例；专用Key仍用户本机隐藏输入，费用证据仍未知且真实调用拒绝。


## Responses实现增量
显式Responses薄适配和用户--model-key启动的静态非秘密候选已编写；不用用户手写请求示例。厂商请求以store=false/stream=false/max_output_tokens128和Bearer专用Key隔离Messages。候选真实协议/模型映射/费用尚未实证，未安装SDK/调用网关/读取宿主Key。生产预算仍未实现，收费拒绝；最终测试以progress为准。


## 2026-10-29 用户明确接受近似费用（最高优先当前规则）
D-MODEL-ESTIMATE-BUDGET-053：“你自己估计费用，大体控制在10-20刀预算就行”。这是费用准入变更，不能继续要求供应商硬限额/费率证明作为调用先决条件。历史gpt61截图59.37USD/993次≈0.0598USD/次，但95percentcache，不套为新单价。先目标15USD/预算上限20USD，按每个受限请求估算预留0.25USD/最多60次、2kchars/128输出token/无重试；只是一套保守估算启发式，不是数学费用保证。费用/余额必须标estimated，截图历史费用不当本项目消费，未知结果保留预留，实际报告费用或估算阈值到达停止。
下一步直接实现非秘密跨重启estimatedledger及真实固定非敏感test/receipt入口，再由用户自己本机隐输专用Key触发。仍不复制Codex/Claude凭证，不外发行/历史/截图，不绕权限；真实model/SQL/JOIN未完成。之前“费率或硬限额证明否则永远拒绝”描述已被本次明确用户变更替代。


## 隐藏输入真实状态与估算治理实现中
用户本机隐藏Key后，GETstatus实际credential_configured=true、Responses候选且预算尚未加载，未读Key值/环境，不搬运秘密。新版EstimatedBudget和固定POSTtest/回执已写，0.25USD估算/60次/15USD目标/20USD参考，用户明确接受近似成本后显式点击才调用；完整回归进行中不预写通过。用户旧进程保持，不停；验证后用户自行CtrlC/newcmd/reinput，首次网关回执仍待实测，不能用fixture称成功。


## 2026-10-29 用户明确Claude风格重配置
D-MODEL-CLAUDE-PRESET-054：用户签发平台ada-config，主动怀疑Anthropic格式并要求如ClaudeCode/允许从截图挑默认model。新增独立start-workspace-claude.cmd，显式套餐anthropic_messages、候选coding-plan/v1/messages、Bearer产品专用Key、claude-haiku-4-5；与之前非秘密Claude配置ANTHROPIC_AUTH_TOKEN风格一致，但具体网关认证/路径及Key权限不保证。传统Messagesx-api-key和Responses仍保留，authmode绑定configversion。不读宿主Key/控制台秘密页面，不因拒绝自动fallback/换账号，预算跨套餐同一账本不清零。
401/403新增安全HTTPstatus诊断，不输出remote正文/秘密。用户本人CtrlC旧窗口/newclaudecmd隐藏重输，并在页面显式测试才收费；新真实调用尚未跑，旧gpt61真实拒绝证据不删除。


## 2026-10-30 用户SDK示例修正（当前最高优先接入合同）
用户明确AnthropicSDK baseURL=http://ada-cli-golang.ctripcorp.com，apiKey占位符ada_xxxxxxxx；对应请求候选/v1/messages、x-api-key，而不是此前coding-plan/v1/messages/Bearer。已修start-workspace-claude.cmd所用preset，defaultdeepseek-v4.1-flash保留，预算共用不清零。根网络例外仅精确/v1/messages+Messages+xapikey，不放任意接口或其他域，不安装SDK/读宿主Key/重启用户进程/网关POST。108模型专项通过（含5新root合同范围测试），未重跑完整backend/browser，不称整体通过。
用户先前实测DeepSeekMessagesBearerHTTP403已failed，旧路由认证合并错误由示例明确修正，但不保证此为唯一拒绝原因；新rootxapikey实际test仍not_run。用户本人CtrlC/Y旧窗口、新start-workspace-claude.cmd重新隐输后页面确认authx_api_key再显式test。不能自动重提/尝试别的账号或头，不索要Key。


## 2026-10-30 当前架构及AIPlan连接（覆盖旧引擎提案）
用户明确保留原LangGraph＋项目治理Harness，D-CLAUDE-ENGINE-058已答，不实施ClaudeCodeCLI/AgentSDK引擎、不安装新Agent栈。M02已验收→M04-A真实模型接入→M03→原M04=M04-B LangGraph顺序不变。公司ClaudeCLI配置仅作模型API非秘密合同：coding-plan baseURL/AUTH_TOKEN风格Bearer，当前明确套餐coding-plan/v1/messages/anthropic_messages/bearer/deepseek-v4.1-flash。用户确认AIPlan支持DeepSeek，记录userconfirmed而非应用integrationpassed；不自动替换为claude-前缀别名、不安装CLI、不执行hooks或继承令牌/无限超时。
start-workspace-claude.cmd只是历史命名的模型API启动器，不等于工作台底层ClaudeCode。用户本人重启隐藏Key并显式test才调用，预算不reset，旧拒绝failed保留；109模型专项过（14套餐+95原专项），本轮preset/tests仅改，provider/UI/ledger未改，不称全backend/browser再过。最新网关实测未运行，收到新回执继续排查，不自动遍历认证/协议。


## 2026-10-30 响应无效诊断
用户最新实际MODEL_RESPONSE_INVALID，读取本机安全status仅确认Messages/Bearer/DeepSeek/verifiedfalse/估算1.50USD6次，不读Key或网关正文，不自动POST。旧统一错误不能判根因，新增ModelResponseDiagnostics只固定reason、modelmatches布尔、白名单stopreason/contenttypes与有界token；不放宽model匹配/完成输出/128tokens或工具禁用，不展示思考/正文/远程任意字符串。新diagnostic需要更新服务后用户一次显式test才获得，不把可能别名/截断当已证实。
诊断分别invalid_json/envelope_mismatch/model_mismatch/incomplete_output/unsupported_content/usage_invalid等。重复读取同UUID只取缓存回执，不再次网络；API重启旧generation拒绝不重提。保留预算预留，LangGraph+Harness路线不变，真实生成仍failed，完整回归待progress结果。


## 2026-10-30 诊断过窄修复与只读回执
用户第二次other_or_unreported证明先前3别名白名单不足，不再追加猜测名单或让用户反复截图。新增returned_model_identifier只允许<=120受限model-family字符、Key及secret-marker排除，值仅作诊断，不能自动变授权模型或接受映射；旧未知字符串仍不全量输出。模型正常endturn/thinkingtext/11tokens，非128截断。标准thinking块需要thinking/signature字符串，redactedthinking需要data字符串，校验后不展示/保存思考或签名，最终只text；仍拒绝工具/仅思考/不完整/模型不符。
新增GET /api/v1/model-service/tests/{request_id}/diagnostics，只读已存在回执的安全diagnostic，不返回generation正文、不创建任务/预算或调用网络，API重启没记录返回404不重提。旧response没有存model原值，无法回溯，用户更新后需一次显式请求收字段，之后Agent可只读GET获取无需截图。不请求Key或读取进程秘密、不偷偷POST，LangGraph和预算保持。


## 2026-10-30 实测网关版本别名绑定
用户授权只读回执d94d4bec-d45d-4519-a3c5-530f6ab5a686实际GET200，返回model deepseek-v4-1-flash-261017/end_turn/thinkingtext/input49/output16。请求deepseek-v4.1-flash的网关返回版本化名称，精确添加Observed mapping仅codingplan/v1/messages/anthropic_messages/bearer和该请求名对应此返回ID。不是所有DeepSeekfamily/前缀/日期都接受，也不扩到其他地址/auth/模型。configurationversion纳入映射，成功receipt双ID+observed_gateway_alias，不把后端返回名伪装请求名；旧失败回执保留不改成功。
思考块按合同形状检查后丢弃，最终仅text输出，tool/partial/空文本/超budget/其他alias继续拒绝。测试150专项passed、全回归待最终记录；本轮没有新真实网关POST或Key读取/用户服务停止，下一步用户一次显式更新验证，不再以诊断猜model。LangGraph和预算保持。


## 2026-10-30 网关thinking封装兼容修复
用户实际只读回执32a14cea：unsupported_content，精确DeepSeek版本别名/end_turn/thinkingtext/17tokens；名称modelmatchesfalse不表示绑定未通过，代码已经走入content检查。原signedClaudeNative thinking字段要求过严，不回放/执行/展示网关思考时不必校验签名。仅已观察alias完整tuple允许thinking/redactedthinking块为opaque元数据直接丢弃，保留整个响应64KB/块数16上限，最终text非空/大小/类型/秘密/usage/outputbudget校验不变；工具/未知模型/partial仍拒绝，原非gateway原生thinking规则仍保持。
不保留原思考字段，不能证明原sig缺失，仅修不必要的依赖。diagnostic新增model_binding exact/observed_gateway_alias/unmatched，避免把词面false误当映射失败。157专项passed/fullpending，无Key读取/真实POST/服务停止，LangGraph与预算保留。
