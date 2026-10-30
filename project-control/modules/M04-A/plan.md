> 2026-10-29 最新明确选择：默认模型改为 `deepseek-v4.1-flash`（按用户截图中的精确ID），不是Haiku。仍用 `start-workspace-claude.cmd` 的 Anthropic Messages/Bearer候选；网关是否支持该模型与此协议组合需实际测试，不自动改协议。已有预算保留，启动/刷新不收费。下方Haiku描述为历史。

# M04-A 最小模型 API 接入计划（M04-A-C01 DO，首切片）

2026-10-28；依赖 M02 有限本机交付审查及用户验收。路线固定为 M02 → M04-A → M03 → 原 M04=M04-B，不创建重复 Agent。PRD：project-control/prd/M04-A.md。

## 已批准，不重复询问
D-MVP-FAST-034：产品专用调用 http://ada-cli-golang.ctripcorp.com/coding-plan；HTTP 内网特例；只发送问题与必要字段信息，不发送数据行、全历史、截图；PG/生产验证后补但保持 required/not_run 发布门禁。
D-MODEL-REFERENCE-BUDGET-035：项目模型测试总额不超过 15 USD。D-LOCAL-MODEL-KEY-ENTRY-043 及本轮指令：先做好适配和本机安全 Key 输入，由用户自行输入应用专用 Key；不要求在聊天粘贴，不读取或复制 Claude/Codex 认证。
以上不是 M02 delivery，也不是已验证端点、价格、模型或秘密持久化授权。

## 用户任务与最短路径
接入管理员：模型服务非秘密配置 → 本机隐藏输入专用 Key → 固定非敏感测试 → 真实回执 → 启用。
业务用户：输入区选择服务端已授权、测试通过的模型 → 提问；不接触 Key/JSON/数仓配置。
保留聊天附件、右侧多来源、显式黑白主题、历史和顶部实际状态。模型文本生成不等于 SQL 执行，多源选择不等于 JOIN。首次只有一个实测模型时只提供一个，不编造第二个模型。

## 推荐安全输入切片（实现前检查）
- 复用 Python 标准库 getpass 的本机终端隐藏输入，入口由本项目启动器显式提供；检测交互终端，不能隐藏时拒绝，不降级回显。用户在自己的终端输入，助手不接收或读取该值。
- Key 仅存后端进程内存及专用 WORKSPACE_MODEL_* 命名空间；不写文件、命令参数、日志、URL、浏览器 storage、进度或 Git。关闭/重启后重新输入；不读取宿主环境中的 ANTHROPIC/OPENAI/Codex 凭证。不新增秘密持久化机制。
- 启动器将前后端环境严格分开，Key 不传给 Node/Vite/数据源 Worker。后端错误只返回固定分类/trace_id，不反射请求头、异常原文、供应商响应或 Key。退出释放自身拥有服务，不盲杀占用端口的进程。
- 模型服务页面只配置非秘密模型信息，显示“未配置凭证 / 待测试 / 已验证 / 已禁用”等真实状态，不提供浏览器密钥输入或掩码回读。

## 薄适配与固定合同
1. 复用已安装 httpx，不安装完整 SDK/LangChain/LangGraph。定义 ModelProvider.generate；流式/工具/结构化能力分别 unknown，未实测不开放。
2. 非秘密 ModelProfile：id/name/protocol/精确请求路径/model_id/version/enabled；批准目标由服务端确定，浏览器不可指定任意域、scope、价格或提高预算。网关 base path 和 Messages 协议只能作为候选，不猜拼 /v1/messages 宣称兼容。实际路径/模型/协议需非秘密接口资料或可验证配置。
3. 严格请求/响应字节、输入/输出 token、连接/总时限、最多并发和取消控制；禁止跳转、代理环境继承、任意工具执行及自动重试。认证拒绝/限流/超时/坏 JSON/空输出/部分或结果不明均有可行动状态，不换资源绕权限。
4. 测试使用固定非敏感短字符串；真实输出回执绑定配置版本和模型。编辑/禁用使旧测试与后续计划失效，不改既有历史。不在本模块执行 SQL。
5. 前端目录来自后端授权与实际测试，通过前不得出现可调用的模型选择。Pydantic/OpenAPI 为合同真源，生成 TypeScript，不手改生成文件。

## 15 USD 门禁
缺可靠网关费率/用量或可核实项目专用供应商硬限额时，适配和入口仍可开发、隔离测试可运行，但收费测试保持 not_run。未知费用显示 unknown，不能用用户声明的金额或官方别名价格伪装硬控。
优先核实专用 Key 的供应商硬限额 ≤15 USD；否则以完整计费上界和 Decimal 原子预留非秘密账本治理输入/输出/缓存/其他费用，跨重启不能清零绕限额。结果不明保留预留、禁止自动重提。配置/测试入口不默认发起收费请求。

## 验收矩阵与边界
- 单元/合同：目标/版本绑定、秘密隔离、环境白名单、非 TTY 拒绝、认证/403/429/超时/取消/坏 JSON/大小限制、无自动重试、未知 usage/cost、预算并发与恢复。
- 用户路径：配置 → 本机隐藏输入 → 真实最小测试 → 保存/刷新/编辑/禁用 → 授权模型选择；主题、历史、附件和多来源无回归。UI 状态无假成功，失败保留非秘密输入并解释下一步。
- 真实：应用专用凭证、有效精确协议/model、费用门禁齐备后用户触发一次最小请求；没有这三项不得标 verified。
- 流式和受 Schema 计划另有验收项，首个非流式切片完成不代表整个 PRD 通过。真实 SQL/JOIN 归 M03/M04-B，PG/正式身份/生产继续后补，不删除门禁。

## 实施顺序与回滚
M02 验收前仅做这份低风险相邻计划，不激活 M04-A。验收后先固定适配合同和隐藏输入启动切片，再隔离测试/生成合同/UI，最后等用户安全输入专用 Key 并补齐非秘密协议及费用证据后真实调用。
回滚禁用模型服务并停止自己拥有的后端，保留原件、保存配置、非秘密预算/回执证据与历史；不删除或复制宿主认证。当前 Key 入口和模型适配均未实现，不能把本计划称作可用入口。

## M04-A-C01 本轮切片准入（2026-10-28）
用户“是，继续推进吧”明确验收M02并进入上一轮所述模型适配/安全Key输入实现；仅将此已明确切片记录为PLAN批准，不扩大为费用验证、新安装或秘密持久化。第一切片：固定网关非秘密配置由后端专用命名空间提供，Messages为显式协议候选、无默认猜测path/model；本机getpass隐藏输入；一次受限非流式适配、只读安全状态。未知协议/model/费用时后端拒绝实际调用；隔离测试注入HTTP transport与预算许可（测试哨兵非网关费用证据）。网页接入说明显示后端实际状态并指导用户双击专用启动器，网页不接收Key、不提供可绕预算的测试按钮。持久预算/真实收费准入与目录启用、保存/编辑、流式和SQL/JOIN均未完成，后续逐项推进。


## 本轮实现状态
已编写薄Messages候选协议适配、专用getpass启动入口、只读后端状态和UI刷新。真实路径/model/认证和费用治理未核实，尚无生产BudgetPermit，因此真实收费请求拒绝；输入Key不表示调用成功。管理员非秘密配置/保存启禁、可用模型目录、真实最小生成、流式与结构化能力仍未完成。第一切片已跑完整后端322（含35模型隔离测试）、前端16及types/build/pip；浏览器最终结果见progress，不在计划里预写通过。


## Responses协议增量（2026-10-28）
用户“继续推进吧”继续上一轮明确的Codex脱敏wire_api=responses适配工作。复用httpx/受限传输/预算门禁，不引入新栈、不复制宿主认证。显式openai_responses协议，候选/coding-plan/v1/responses和model=gpt-6.1-sol[1M]仅来自已提取非秘密配置；Bearer产品专用Key认证为协议候选，实际网关兼容/模型映射未验证。请求仅model/input/max_output_tokens128/store=false/stream=false，拒绝工具/部分/模型不一致响应，reasoning不展示，未知usage/cost不编造。共享单并发/响应时限字节/拒绝未知费用/无自动重试；保留Messages合同和36项原专项。用户--model-key启动时可用静态非秘密候选默认（环境显式值优先），不再要求手写示例；默认不读取Codex配置/认证文件。收费许可实现未完成所以输入Key后仍budget_unverified。真实调用/目录/流式/SQL/JOINnot_run。


## 2026-10-29 用户明确接受近似费用（最高优先当前规则）
D-MODEL-ESTIMATE-BUDGET-053：“你自己估计费用，大体控制在10-20刀预算就行”。这是费用准入变更，不能继续要求供应商硬限额/费率证明作为调用先决条件。历史gpt61截图59.37USD/993次≈0.0598USD/次，但95percentcache，不套为新单价。先目标15USD/预算上限20USD，按每个受限请求估算预留0.25USD/最多60次、2kchars/128输出token/无重试；只是一套保守估算启发式，不是数学费用保证。费用/余额必须标estimated，截图历史费用不当本项目消费，未知结果保留预留，实际报告费用或估算阈值到达停止。
下一步直接实现非秘密跨重启estimatedledger及真实固定非敏感test/receipt入口，再由用户自己本机隐输专用Key触发。仍不复制Codex/Claude凭证，不外发行/历史/截图，不绕权限；真实model/SQL/JOIN未完成。之前“费率或硬限额证明否则永远拒绝”描述已被本次明确用户变更替代。


## 2026-10-29 估算预算与固定模型测试切片
按D-MODEL-ESTIMATE-BUDGET-053实现固定0.25USD/次预留、最多60次、15USD目标/20USD预算参考（非硬费用保证）的专用非秘密SQLite账本，Windowspinning/事务冻结/不退款或reset；跨重启保留未知预留，不写prompt/Key/输出行。用户--model-key启动加载已接受估算许可，不再要求供应商价目证明。
POST model-service/test只接受UUID、当前runtimegeneration/configversion和acceptestimatedcosttrue，固定非敏感文本，不收rows/history/Key。幂等回执内存保持同UUID只调用一次，重启generation变更拒绝旧请求；成功只验证最小模型，不执行SQL不启用问数目录。UI明确接受估算，固定测试按钮和回执token未知/估算、重复读取不重发。正式结果/队列持久化仍M05，SQL/JOIN未实现。
用户持Key旧进程只读核keyconfiguredtrue，未读值/命令行/环境，不停止或迁移Key。新代码测试后由用户自己CtrlC旧窗口、重启cmd并隐输；Agent只读取回执状态，不发送真实测试直到用户点击。新账本不入Git或历史。


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


## 2026-10-30 用户要求网页快捷Key输入（D059）
真实最小模型已succeeded，readonlyGET验证，仅连接文本不是SQL/JOIN。用户明确网页输入自己的Key即接入，替代终端必需：公司AIPlan固定已实测preset、密码框→POST专用Key仅后台memory→保存会话→显式固定test。浏览器瞬时field/requestbody授权仅本机loopback，不入storage/history/log/文件，密码字段不回显/保存后清空。用户可清除或替换，忙请求拒绝更换/清除，版本执行generation失效旧test，预算保留不reset。没有生产secret持久化或公开HTTP授权，需后续生产身份/TLS再开放远程。终端仅高级可选，不再让用户手改env/接口协议或重启来更换Key。


## 通用个人BYOK范围（D060，2026-10-30）
用户明确不能只选AIPlan，要个人自有API任意厂商目标。采用协议预设/自定义API地址/模型/Key表单，AIPlan仅可选预设。首标准协议Responses、OpenAI-compatible Chat Completions、AnthropicMessages；特殊私有协议需扩展适配，不能宣称任何URL兼容。公网默认HTTPS并服务端SSRF/DNSIP/禁跳转/秘密URL检查，不能为任意provider删除现有allowlist允许local/private访问；既有内网AIPlan作为明确已批准绑定单列。网页Key只瞬时password和后台sessionmemory，不保存history/storage/log/file；保存/test分开，改配置失效旧test，busy变更拒绝、预算不reset。
不同厂商费率/计费不能套AIPlan历史平均或0.25当真实价，提供明确估算和请求总上限，新的实际外发/费用依据逐项绑定，不自动把公司用途批准延伸到未知厂商。当前只是范围/计划，尚未实现通用webprovider，真实模型最小生成成功不等于通用BYOK或SQL/JOIN。


## 2026-10-30 通用BYOK首实现切片
D060/D059已准入口，实际实现三协议Responses/ChatCompletions/Messages，自定义HTTPSendpoint/model/passwordKey/固定AIPlan预设。POSTconnection SecretStr/8192body/CSRF和loopback身份、配置锁、改Key失效testgeneration不自动test，清除仅内存Key/验证不resetbudget。passwordsubmit无论成功失败清空，不进storage/history/log或文件，无费用保存/清除/刷新。
publiccustomHTTPSDNS解析所有IP为global后TCP固定校验IP，原Host/SNI保留certificatehostname验证、无proxyenv/redirect，禁止loopback/private/userinfo/queryURL，privateAIPlan仅exactpreset已授权原路径。特殊私有协议/真实厂商权限未测，不能宣称anyvendoralreadycompatible；fixeddevidentity仍非productionauth，公共真实Keys不自动外发，仅用户固定test目的接受。
182专项实跑过/fullpending，API/合同/前端generated Types真源生成。收到D061完成后安全scan/commit/push现有GitHub明确授权，Keys/uploads/runtime/toolconfig不上传，不算部署或模块验收。
