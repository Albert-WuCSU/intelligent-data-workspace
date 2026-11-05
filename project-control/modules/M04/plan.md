# M04-B PLAN｜Claude Agent SDK＋Skills＋治理 Harness
2026-11-03 · M04-C02-SDK · 主线方向变更 D-M04B-CLAUDE-SDK-070 · 当前 DO / not_verified

## 1. 用户任务与选择理由
业务用户可能只知道经营问题，不知道数据/口径/表名。通过连续对话理解意图、按需读取Skills并探索授权元数据，补齐关键口径后取数，不要求先选metric_id或把思考拆成审批步骤。模型选择路线；真正执行仍有必要的人类确认。保留已验收黑白主题、历史、左设置/知识库、右来源摘要、真实pipeline和结构卡，SQL/Schema/工具日志折叠。用户选择SDK以获得更灵活工具编排，这是设计假设，不宣称Claude比LangGraph更准确。

## 2. 已批准与本轮边界
用户明确决定Claude SDK主线，更新规划/Skill/PRD/更新日志并上传GitHub，LangGraph另留分支。保留M04原ID、M01/M02/M04-A/M03验收、预算D053与PG/生产后补，旧方向D058/D069原记录不删，D070替代编排方向，不撤销历史安装许可。
D071已批准固定SHA wheel项目venv离线安装＋离线/合成fixture S02，不含真实模型收费、生产SQL、新模型端点、结果行外发、WSL/container安装、部署或push。版本锁和安装已完成；真实SDK网关与生产仍按后续独立门禁，已选SDK方向不再重复询问。

## 3. 目标架构（不是已实现）
业务问题→产品Skill选择/加载→模型澄清与授权元数据探索→指标优先或SQL申请→治理工具检查授权/版本/预算/确认→MCP真实执行→自动质量检查→回执校验→结果发布/解释/下一步。
- Claude Agent SDK承担模型/tool_use循环；产品Skills是任务知识，不是project-pdca，也不继承当前助手Skill/MCP/Bash/凭证。
- 产品托管版本化Skills候选：问题理解/取数路由、指标查询、SQL查询、质量解释；QA执行是后端必经步骤，不靠模型记得调用QA Skill。
- 模型可自行选择检索/澄清顺序；代码不规定全部推理路径，仅守危险动作和输出证据。未知诉求先探索，不反复问已明确槽位。
- 最小工具候选：load_skill/resolve_route、search_semantics、read_authorized_metadata、propose_metric_query、propose_sql_query、request_confirmation、execute_approved_query、get_receipt、publish_result。名称是项目合同候选，非保证SDK原生同名接口；优先受治理MCP适配，模型不传tenant/路径/任意权限。
- 执行请求绑定已加载Skill/version与RouteTrace（指标匹配/SQL理由）、语义/来源/schema/model/plan hash。RouteTrace可审计但不证明内部推理或绝对最佳选型；无证据/版本失效拒绝，缺口径澄清。
- 匹配已批准指标则确定性指标引擎；复杂SQL仍服务端AST/方言/真实字段/扫描预算/只读权限，JOIN需M03明确关系/keys/cardinality/grain和独立批准，不根据同名字段猜。拒绝不换账号/源/引擎绕路。
- 取数工具内部执行QA，发布入口核QueryReceipt＋QualityReceipt＋当前owner/版本。质量FAIL/超限/UNKNOWN不能包装验证通过；空集、WARN、部分结果明确限制与修复建议。没有下载资产不造按钮。

## 4. SDK安全与适配核验（迁移阻断条件）
S01已完成公开release、官方文档与固定wheel只读核验：候选为Python SDK 0.2.177＋捆绑CLI 2.1.317；Windows wheel SHA256=7997db488354a539c08b5b6b16717d99ae67903ae7351da43d51b68b80097fad，离线dry-run仅新增SDK且无旧包替换。安装/CLI执行/真实网关仍not_run。完整法律、隔离、预算与工具合同见[SDK_S01_INSTALL_PLAN.md](SDK_S01_INSTALL_PLAN.md)。
1. 已核确切SDK＋内置CLI版本/哈希/包大小/依赖/Python3.12-Windows wheel及许可/CommercialTerms；安装与部署分发仍按独立批准，不把SDK包的MIT标记覆盖到所有运行条款。
2. 官方不支持通过网关路由Claude Code到非Claude模型；现有AIPlan/DeepSeek文本与固定流式成功不属于受支持SDK路径。须先确认授权Claude模型与对应base URL/auth，再实测Messages/tool_use/Skill/stream/usage；不得自动换模型、端点或供应商。
3. 独立runner进程最小环境、独立cwd/config/HOME/temp和资源限额。SDK env={}不阻断继承，禁宿主Claude/Codex登录/keys/user settings/hooks/plugin自动加载。原生Windows实测宿主全局CLAUDE.md可泄漏后，改为setting_sources=[]＋仅含受控Skill/清单的本地plugin，精确加载governed:data-query；不给任意文件Read权限，禁未知MCP/hooks。
4. 明确tools暴露/disallowed工具/权限回调/hooks优先级，禁bypassPermissions；不靠allowed_tools或hook保证工具安全。执行/发布工具的后端鉴权是最终门禁。Bash/Write/任意Read/WebFetch/子Agent等默认不暴露；后续代码分析按明确沙箱新方案，不为灵活性放开主机。
5. 关闭不必要遥测/外部trace/缓存外发，核SDK启动/退出和进程树/WindowsJob；挂起确认不能占无限runner。真实状态事件映射现有任务卡，不显示模型思考链/Key。

## 5. 预算、恢复与复用
D053整体campaign不重置。旧一次generate/128输出token/2000输入字符路径是LangGraph首切片上限，不能直接扩成SDK多轮工具预算；需形成每任务turn/tool/token/墙钟与费用预留子合同，SDK max_budget_usd不是第三方网关实际账单硬保证。未知收费保留预留、不静默repair/fallback，新付费测试用户明确进行。
复用既有MCP/Worker/SQLAST/semantic/version/receipt/QA逻辑，迁移不重写底座。SDK resume不等于SQL exactly-once；确认绑定版本，提交前tombstone、未知ACK同键读取不重提；M05前不宣称生产持久任务。结果进入模型上下文须另审最小数据用途，既有只问题/必要字段授权不自动扩大至行/全历史。

## 6. 切片与下一步
S00（本轮）：保存LangGraph分支/归档，记录D070，更新需求和Skill，文档审计/Git推送。没有运行SDK。
S01（已完成）：只读官方release/许可与网关适配调查，已列确切依赖/隔离/预算/工具合同及D-M04B-SDK-INSTALL-071安装授权点；详见[SDK_S01_INSTALL_PLAN.md](SDK_S01_INSTALL_PLAN.md)。AIPlan当前DeepSeek不属于官方支持的Claude Code网关模型路径，真实网关仍需授权Claude模型与实测；不暗换路线。
S02（离线fixture已通过）：D071固定wheel安装后，SDK/CLI真实Windows子进程＋本地假Messages＋真实合成MCP验证load Skill→指标/受控SQL→明确确认→执行自动QA→回执发布；6项专项通过，150行聚合11325且结果行不回传模型。实现capability明确区分legacy和SDK，尚未迁移默认业务API/UI。详见[SDK_S02_OFFLINE_FIXTURE.md](SDK_S02_OFFLINE_FIXTURE.md)。
S02-MODEL-CATALOG（2026-11-03新增，D-M04B-MODEL-PICKER-075）：在M04-A单模型连接之上实现服务端多模型目录与工作台选择器。同一授权连接可注册多个model ID；每个模型独立测试/验证/启用；catalog绑定generation/config/model，模型变化使旧计划/确认失效；工作台选择器支持搜索/来源分组/状态，MVP默认`deepseek-v4.1-flash`；本轮不自动发现网关模型、不复制宿主Token、不生产。先完成目录/选择器基础，再把选中模型绑定到Agent/SDK runner。
  - 2026-11-03首切片已实现并通过本机回归：catalog多条目/独立测试启用/Agent provider按catalog引用解析/富选择器/设置页模型目录管理；606后端/19前端/44浏览器/types/build/pip通过，证据`project-control/modules/M04/evidence/20261103T101648Z/results.json`与`MODEL_PICKER_IMPLEMENTATION.md`。真实网关Web调用、SDK runner接入与网关自动发现仍not_run。
  - 2026-11-04 SDK/Web绑定切片已实现并通过本机回归：AI Plan且`anthropic_messages`的catalog模型经服务端绑定进入SDK runner的`web_catalog`模式；其余模型保留既有LangGraph路径。新增真实用户确认桥、任务级2 USD估算预留（8×0.25，D053不reset）、模型/语义/来源/Schema绑定失效、API层结果与质量回执复核、服务端engine标识与UI标签。最终613后端/20前端/44浏览器/types/build/pip通过，证据`project-control/modules/M04/evidence/20261104T032252Z/results.json`与`SDK_WEB_BINDING_IMPLEMENTATION.md`。真实DeepSeek Web、Claude官方支持、个人API的SDK绑定与生产仍not_run；未新增端点/供应商、未自动发现网关模型。
  - 2026-11-04 D-M04B-AGENT-EXPERIENCE-076 A / A1 已实现并通过本机回归：单源单表已发布指标增加受控筛选`eq/in/gte/lt`（最多5组、in最多200值、按字段类型参数化、AST白名单）、SDK工具可选filters/time_range、Skill 1.0.3、`AgentTask.answer`自然语言回答、实际表/指标/事件右侧摘要、终止式`request_clarification`（不执行SQL，补充后新问题）。最终617后端/20前端/44浏览器/types/build/pip通过，证据`project-control/modules/M04/evidence/20261104T062640Z/results.json`与`AGENTIC_SQL_A1_IMPLEMENTATION.md`。RAG、多表JOIN、企业Hive、导出/QA报告未实现；截图公司数据/SQL未复制。
S03：用户网页显式实际网关调用/取数、故障/版本/恢复/预算/安全测试；L2/L3/L4与JOIN按依赖逐项实施。M05–M08才形成MVP完整交付。

2026-11-04 D-M04B-AGENT-EXPERIENCE-077（用户明确要求连续对话 Agent + L1–L4 编排 + 业务知识 RAG）：A1 卡片式/终止式澄清被真实使用否定；下一阶段按 [AGENTIC_CONVERSATION_L1L4_PLAN.md](AGENTIC_CONVERSATION_L1L4_PLAN.md) 重做。A2 先修可靠性（发布后 max_turns 不丢结果、后端自动发布、16步/20工具/600秒预算）、连续对话 UI、可恢复澄清、报告；A3 做 L2 主题 Skill + L3 元数据/受控 SQL；B 做 M03 RAG；C 做公司 Hive/多源/导出/QA（需新授权）。只使用治理工具，不开放宿主 Bash/Read/Write/Key；截图仅交互参考，不复制公司数据/SQL。当前可靠性修复仅专项23通过，完整回归待新窗口。

## 7. CHECK/ACT验收与回滚
需实测：含糊问题能提出关键澄清；加载错误/恶意Skill无法扩权；指标匹配优先、无指标有依据转SQL；不支持adapter拒绝；无路由/无确认/跨owner/旧schema不能执行；每次取数必QA；无质量回执不能发布。涵盖超时/429/预算/取消/失联/重复确认/恢复，Prompt注入、Bash/文件/环境/网络旁路，黑白主题/键盘/窄屏/历史和真事件。
本轮最终602backend/17frontend/44browser/types/build/pip实际通过，包含9项SDK离线专项；旧593/17/44仅LangGraph baseline，未复用为本轮证据。真实模型/AIPlan、生产与整体验收not_run保持。self_review非独立审计，无用户验收不closed。
回滚使用codex/langgraph-baseline-20261103（92d0b03），旧方案见LANGGRAPH_C01_PLAN_ARCHIVE.md和LANGGRAPH_C01_PRD_ARCHIVE.md。不要删除数据/Key/历史/旧锁或强制重置Git。SDK与图未来比较同任务/工具/口径/质量/预算，记录正确性/澄清/成本/耗时/违规，不伪造基准结果。

## 2026-11-04 A2 连续对话与可恢复澄清（实现中，未验收）

- 对话按原问题→澄清问答→Agent回答/报告→嵌入结果证据排列；SQL/版本回执折叠，右侧只展示实际工具/字段/来源。短暂状态轮询失败保留已收到的结果，不把网络错误当成查询失败。
- 新增 POST /api/v1/agent/tasks/{id}/clarify：同一正在运行的SDK调用等待回答，不新建任务、不调用SDK resume、不新增费用预留。回答必须属于当前owner/generation/clarification_id/绑定，并明确同意问题外发；响应幂等，已答口径冲突拒绝。
- 最多两轮、每答1600字符，仍共享既有16步/20工具/6元数据/200K tokens/600秒模型与1260秒进程墙钟；等待不会自动延长整体预算或重置D053。回答不等于SQL授权，旧plan/confirmation失效，新plan hash包含澄清轮次；执行前另需显式确认和实时Schema重核。
- 澄清等待状态原子带ID/问题/计划失效；待答/超时不能规划/确认/执行。取消、版本变化、超时、已结束任务拒绝恢复；API复核前后重新核任务/计划，避免异步状态变化接受旧确认。
- 产品Skill 1.0.4；仅治理工具，无宿主Bash/Read/Write/Key权限，无公司数据/SQL或完整历史外发。只保留本机后台内存对话/任务，不是M05生产持久化；新的独立问题不自动继承历史筛选或查询结果。
- 本机合成SDK/MCP与UI专项正在验证，完整A2回归与真实DeepSeek复测待补。可靠性修复前置完整检查618后端/20前端/44浏览器/types/build/pip通过（20261104T074457Z）；此旧指纹不是A2整片证据。
- A3 L2/L3、B M03业务RAG、C公司多源/导出/Python QA未实施；真实Claude/生产/整体MVP仍not_run，M04仍DO/not_verified，无commit/push。

## 2026-11-04 A2 本机检查完成（真实复测/验收待补）
627后端/20前端/45浏览器/types/build/pip及源稳定检查通过；证据`project-control/modules/M04/evidence/20261104T082927Z/results.json`与`A2_CHECK_REPORT.md`，fingerprint `ddf9d400751aed4b4ca065da80447e1d481110318205052152e597413fbd451b`。同任务澄清/计划失效/幂等/取消与异步重核、连续消息/报告/实际工具进度、发布与有效usage门禁均已实现。服务已在最终检查后安全重启，Key缺失需用户重输；原授权来源/语义/估算账本保留49/60，余额2.75USD只够一次完整SDK复测，三项需补充授权而非reset。本轮真实DeepSeek/Claude/生产/MVP not_run；M04仍DO/not_verified，A3/B/C未实施、无commit/push。

## M04-B-AC05 / R-U31：常规 Agent 式连续交互（2026-11-04，D078）

用户再次明确：遵循L1–L4之外，收到问题后的交互必须像常规Agent，而不是纯卡片结果。此前D077/AC01–03仅笼统写连续对话，A2“短句＋大卡片”不构成本项验收。

1. 主聊天按实际发生顺序呈现**执行说明→发现/限制→必要澄清→用户回答→继续执行→最终正文报告**；旧过程说明保留，不被最终结果替换。模型公开回答与服务端工具事实说明区分，不展示原始thinking/思维链。
2. 实际Skill/元数据/计划/确认/执行/QA工具事件以紧凑标签/折叠详情穿插在过程说明中；只显示真实成功/等待/失败，不从截图复制工具、不用动画编排，不展示原始工具参数/路径/Key。
3. 一次问答可原任务恢复，回答后说明采用何种已确认口径；不可重新开卡片任务或重复已答槽位。SQL仍独立确认，预算与版本/权限门禁不变。
4. 最终主要输出是可阅读的正文报告（结论、口径、来源、质量与限制、下一步），支持安全标题/列表/强调；表格内嵌正文，卡片仅辅助证据，技术回执/SQL默认折叠。精确数字必须来自后端已发布结果，不让模型猜数；无结果不展示业务结论、文件或下载。
5. 当前无需把结果行送模型：后台事实说明+模型最终解释+后端确定性数值正文。逐条模型中间公开说明的流式脱敏/存储仍需后续受控实现；不拿固定模板冒充模型思考。
6. 可观察验收：从提交到结束至少出现已发生的工具事实说明，澄清与回答位于正确顺序；最终没有强制展开的大型成功任务壳，只读正文即可理解结果/限制；工具详情折叠；黑白主题/窄屏/刷新/失败保留正确。
7. 用户截图仅说明交互结构，不复制公司数据/SQL/文档/水印；截图中的Bash/Read/Write/http_request不授权产品宿主权限。L2/L3/RAG/下载/PythonQA需真实能力与授权，不提前伪造。

实施切片A2.1：治理事件生成顺序化公开说明/工具标签、原任务澄清穿插、安全正文渲染和内嵌结果表；不安装依赖，不调用真实模型、不扩大数据外发。完整本机检查和真实体验验收分开记录。

## 2026-11-04 R-U31 / AC05 A2.1本机CHECK完成，默认服务待手动加载
631后端/23前端/45浏览器/types/build/pip及源稳定全通过，证据`project-control/modules/M04/evidence/20261104T092140Z/results.json`和`A21_CHECK_REPORT.md`，fingerprint `dcbf6753a9f16844c1eccf1baaa19ff595b77af682993b84f17f30303a8b9dfd`。治理事件公开执行说明/实际工具标签/澄清问答按序、正文报告/后端数值/内嵌表格/技术折叠、Skill1.0.5已实现；不展示原始思维链，模型中间公开消息流仍待受控实现。重启命令被执行环境拦截，旧默认API尚未加载新字段，需用户手动重启本项目；真实体验验收not_run。D053余额2.75USD/49单位不变，无真实调用/公司数据复制/宿主权限/安装/commit/push；A3/B/C后续，M04仍DO/not_verified。

## 2026-11-04 A3-M1 已批准范围内的本机切片（实现/检查中）
业务目标：用户不知道字段名时，可检索本任务绑定的真实授权表/字段；L1未命中时，在已有批准口径内选择单表模板，再确认执行。不是开放整个数仓或让模型自行定义企业口径。

- 治理工具 list_authorized_tables/search_authorized_fields：只暴露当前source+semantic绑定的单表与实际字段，无结果行；本机快照分区未暴露，返回unknown/不可用不猜。
- load_topic_sql_template / propose_topic_query：L1先检索；有匹配拒绝L2，没匹配可加载已有canonical metric派生的版本1.0.0模板，含字段/粒度/时间/筛选合同与绑定回执。模板失效/错任务/错Skill/schema/澄清变化拒绝。
- 参数提案复用参数化聚合/AST/字段/预算/显式确认/MCP/自动QA与回执发布；自由SQL/新metric/多表JOIN/未选来源仍禁。不是完整企业主题Skill库，L3仅授权元数据发现基础，不代表任意SQL或跨表能力完成。
- 发现安全缺口：原_set_plan只比较metric ID，现改完整canonical定义比较，禁止同ID换字段/单位/算子；提交后禁止再规划。query_path从真实计划与发布回执产生，L1/L2在正文展示，路径标签与质量独立。
- Skill1.0.6指导已批准口径派生模板，新增元数据工具共享原6次预算，不增加token/turn/时间/费用；截图数据/公司凭证/宿主Read/Write/Bash/Key不开放。
- 当前仅代码/合成测试，完整CHECK、默认运行加载与用户真实复测分别登记；D05349/60/2.75USD估算不reset。A3完整L3无语义/自由SQL、多表、B RAG、C公司多源/导出/QA后续，M04未验收。

## 2026-11-04 A3-M1本机CHECK完成（非完整A3验收）
642后端/23前端/45浏览器/types/build/pip/源稳定全部通过，证据`project-control/modules/M04/evidence/20261104T101013Z/results.json`与`A3_M1_CHECK_REPORT.md`，fingerprint `4d39b9b48bd499383292b6526d9bea41d009dc71025e85928b2371555f1a7f0d`。已实现任务绑定单表/字段metadata发现、L1未命中时canonical批准口径派生L2模板与参数提案、模板回执/版本/预算/确认/MCP/QA发布、完整metric定义比较与提交后禁再规划、实际L1/L2路径和工具标签。Skill1.0.6/工具1.0.1/模板1.0.0，不开放自由SQL/新metric/JOIN/公司数据/host工具。用户已重启A2.1（新8000/5173监听18:01:32），A3改动在其后默认API尚未重载；本轮不打断用户服务，真实A3/Claude/生产/MVP not_run。D05349/60/2.75USD不变，未真实调用/安装/commit/push。完整L2业务Skill/L3/RAG/context/模型中间公开流等后续，M04未验收。
