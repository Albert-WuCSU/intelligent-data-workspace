# 项目续接档案

状态版本 revision 199，更新时间 2026-11-05T02:21:10.151261+00:00 UTC。

先校验 progress.json 并核对实际文件；本档案由脚本生成，主进度为唯一状态真源。

- 项目：通用企业智能数据分析平台
- 当前：M04 取数Agent与Harness（M04-B Claude Agent SDK＋Skills主线） / do
- 状态：in_progress
- 下一步：将D079批准的当前main源码/文档/合成测试证据提交并非force推既有origin；核远端SHA与baseline未变。完成后按D077/D078推进公开模型消息安全生命周期合同/实现与合成测试，不调用真实模型或扩大预算/外发/权限。

## 优先读取
- project-control/modules/M04/evidence/20261104T101013Z/A3_M1_CHECK_REPORT.md
- project-control/modules/M04/evidence/20261104T101013Z/NEXT_LOCAL_WORK.md
- project-control/HANDOFF_DETAILS.md
- project-control/modules/M04/AGENTIC_CONVERSATION_L1L4_PLAN.md
- project-control/modules/M04/plan.md
- project-control/prd/M04-B.md

## 工作状态
- 2026-11-03用户要求新窗口：已整理最终HANDOFF_DETAILS/STATUS/NEW_WINDOW_PROMPT；revision172仅交接和session更新，未重跑测试。S02 9项专项及602/17/44证据不变，真实AIPlan/Claude/生产/MVP仍not_run。
- 2026-11-03 S02最终：9项SDK离线专项与602后端/17前端/44浏览器/types/build/pip全部通过；S02指纹55ac27ed0c3db2caafd80ad7c3f07cdfe2ac93b36c35345c80704f098998f732，全回归指纹c4ec9676aa3f038e97e114345a26c6a6ca59d0c6f7337593227ef13988cbb370。宿主上下文/结果行隔离、路由失效、异常脱敏、usage与Windows Job上限均实测；真实AIPlan/Claude/生产仍not_run，M04未整体验收。
- 2026-11-03 S02离线fixture通过：SDK0.2.177/CLI2.1.317，6项专项，8模型步/7工具/2元数据，真实合成150行聚合11325，自动QA与回执发布；结果行未回传模型，宿主全局CLAUDE.md已隔离。Windows Job峰值8/上限10、内存约531MiB/2GiB；源码指纹17689c9a015122eac9a3ce8e8c310559a82bf6d7cd98fa0810830390684feee5。失败历史保留，真实网关仍not_run。
- 2026-11-03 D071安装检查点：固定SHA wheel离线安装成功，SDK0.2.177 import、CLI2.1.317 (Claude Code)隔离version probe退出0，CLI SHA256=26b01ec22df2c17ac7f5703aa547d36706e8d58412136ced0344a8ced4d86038，pip check通过。未真实模型/AIPlan调用；下一步本地假网关＋合成MCP fixture。
- 2026-11-03用户已明确批准D071 A：固定SHA wheel项目venv离线安装＋离线/合成fixture S02。许可不含真实AIPlan/收费/生产SQL/新端点/结果行外发/WSL/container/部署/push；开始DO，M04仍not_verified。
- 2026-11-03 S01完成：SDK0.2.177/CLI2.1.317包与Windows hash/许可/协议/隔离/预算/工具合同已归档；45项证据自审、PRD13模块60需求、31tests+9subtests通过，安装副本一致。AIPlan/DeepSeek非官方支持Claude Code模型路径，真实SDK需授权Claude模型。当前D071待用户批准仅离线安装+fixture；SDK安装/运行/真实网关仍not_run，未改产品源码/未push，MVP未完成。
- 2026-11-03 S01包核验：官方SDK0.2.177/捆绑CLI2.1.317；win_amd64 wheel 149800822字节SHA7997db48...与PyPI一致，CRC通过且包含claude.exe；Python3.12.14/AMD64匹配，离线dry-run仅新增SDK且无旧包替换，pip check通过。未安装/执行binary/真实模型调用；WSL status exit50，Windows沙箱可用性未证实。
- D070用户明确改Claude Agent SDK＋产品Skills＋治理Harness主线，旧D058/D069选择历史不删。M04原ID/M04-C02-SDK PLAN；已验收M01/M02/M04-A/M03、预算D053及PG/生产门禁保留。
- LangGraph完整C01源码/测试/证据/交接已commit92d0b03于codex/langgraph-baseline-20261103，main快进继承以复用底座。主线仅文档迁移，当前运行代码仍旧C01，不称SDK已实现；旧593/17/44为历史基线。
- M04SDK plan/PRD/Skill及对应安装副本、需求和日志已更新，SDK安装/运行/网关兼容not_run；官方docs403，officialPythonREADME/types调研成功，未锁release。
- 本轮未重启/核实时服务、读Key、实模型收费或productionSQL，未installSDK/新CLI，未授权子Agent。用户授权GitHub推送main及保留分支；main ce14cd4及LangGraphbaseline92d0b03已正常atomicpush；ls-remote同SHA证实。
- SDK方向文档self_review通过：PRD覆盖/引用/顺序、31测试+9subtests及3Skillfiles安装同步过；产品源SHA仍5be4b137...不变，旧C01未重跑。源代码/文档diffcheck过，原始evidence stdout空白保留。正常atomicpush和ls-remote实核通过，无force；后续收尾记录单独commit/push，续接以实际Git refs为准。
- GitHub main ce14cd4已承载SDK方案；codex/langgraph-baseline-20261103=92d0b03完整保留。官方PRD最终文档audit13模块/60需求通过，当前SDK所有runtime testsnot_run、M04-C02-SDK PLAN。下一步仅SDK兼容/锁版/隔离/安装计划，不复问选型、不自动实调用。
- 2026-11-03最终换窗口交接：GitHub main收尾6697c4e、LangGraph比较分支92d0b03已push/ls-remote核一致，当前源码工作区干净；本次仅交接更新，不新增SDK安装/调用/重跑产品测试。后续交接提交SHA以gitrefs为准。
- 2026-11-03 SDK真实网关门禁只读复核：现有非秘密档案仅记录宿主Claude Code曾配置claude-kr-claude-opus-5.5[1M]/claude-haiku-4-5与coding-plan地址，未证明产品专用Key的Claude授权；产品实际成功仍仅DeepSeek；Messages/tool_use/Skill/stream/usage真实SDK均not_run。未读宿主Key/settings/hooks、未调用网关、未收费/执行SQL。证据project-control/modules/M04/evidence/20261103T081413Z-sdk-real-gateway-prereq/review.json。
- 已登记D-M04B-SDK-REAL-072待用户选择；A为确认授权Claude模型后一次最小真实SDK工具循环（合成MCP/≤8步/≤10工具/≤100K tokens/≤300秒/≤2USD估算预留，D053不reset），B为仅DeepSeek保持not_run，C为暂缓待网关管理员确认。
- 2026-11-03用户明确选择D072-D：用真实DeepSeek模型名做非Claude SDK兼容性实验，两个名称都试；不伪装claude、不换端点/供应商、不读宿主Key。已实现默认关闭real_gateway_experiment模式，仅允许AIPlan coding-plan端点与deepseek-v4.1-flash/deepseek-v4-1-flash-261017。SDK专项10 passed、完整后端603 passed；真实网关not_run，等待用户本机隐藏输入Key。
- D072-D证据：project-control/modules/M04/evidence/20261103T085045Z-sdk-deepseek-experiment-implementation/。未重跑前端/浏览器/types/build（无UI/契约改动）；未commit/push；D053预算不reset，两次实验最多约4USD估算预留。
- 2026-11-03 D072-D第一次真实运行：deepseek-v4.1-flash SUCCEEDED（8步/7工具/1元数据/24752 tokens，发布11325 PASS，usage key=deepseek-v4.1-flash，cost estimate 0.0545 USD unknown basis），但runtime在项目树内，SDK init列出非产品Skill，CLI插件store出现CLAUDE.md/AGENTS.md扫描，Job峰值16/15>上限10；判为无效诊断，不作干净证据。deepseek-v4-1-flash-261017 FAILED SDK_PUBLICATION_MISSING，当时无失败事件/usage。证据project-control/modules/M04/evidence/20261103T085755Z-sdk-deepseek-experiment/results.json与diagnosis-first-run.md。
- 2026-11-03 D072-D修正：runtime改为项目外系统临时目录并在运行后清理；失败时写failure-diagnostics.json保留events/model_text/usage/budget；新增失败诊断测试。SDK专项11 passed、完整后端604 passed。第一次运行runtime/outer目录已清理；等待用户干净重跑。
- 2026-11-03 D072-D干净重跑：runtime在项目外临时目录，Job峰值8/7≤10，项目树上下文泄漏已修复；SDK_INIT仍列非产品内置Skill（实际Skill调用受governed门禁）。deepseek-v4.1-flash执行Skill→search→propose→confirm→execute×2→publish→get_receipt，8步用尽error_max_turns；usage 22702 tokens，cost estimate 0.0425 USD unknown basis。deepseek-v4-1-flash-261017被网关400拒绝（This model is not currently supported），它是返回版本别名，不是可用请求名。证据project-control/modules/M04/evidence/20261103T091204Z-sdk-deepseek-experiment/results.json与diagnosis-clean-rerun.md。
- 2026-11-03 D072-D修正：Skill 1.0.1明确publish_result PUBLISHED后停止、不再调get_receipt；system prompt和publish_result instruction同步；未提高8步预算。SDK专项11 passed、完整后端604 passed。已登记D073，等待用户批准仅deepseek-v4.1-flash的单模型重跑。
- 2026-11-03 D073-A单模型重跑成功：deepseek-v4.1-flash SUCCEEDED；Skill1.0.1；8模型步/7工具/1元数据/23080 tokens；查询SUCCEEDED、质量PASS、发布11325（150行全输入）；结果行未回传模型，model_generated_numbers=false，模型文本未复述数字；Job峰值8≤10；usage input4014/output1146/cacheRead17920，cost estimate0.04256 USD unknown basis。证据project-control/modules/M04/evidence/20261103T092622Z-sdk-deepseek-experiment/results.json与success-report.md。
- 该成功是非Claude兼容性实验，Anthropic官方不支持；不关闭sdk-real-gateway，不等同Claude模型验证，也未做默认Web迁移/生产/真实用户。deepseek-v4-1-flash-261017已被网关400拒绝，仅deepseek-v4.1-flash是可用请求名。SDK_INIT仍列CLI自带非产品Skill，实际Skill调用受后端governed门禁；CanUseToolShadowedWarning保留残余风险。
- 2026-11-03用户明确产品需求：兼容个人API/企业AI Plan网关，工作台像Claude Code选择模型，MVP开发测试用deepseek-v4.1-flash；实现方案由研发决定。已记录D074(A,继续)与D075(scope)，更新M04-A/M04-B PRD、REQUIREMENTS/requirements.json/index/modules、M04 plan、ROADMAP、PRODUCT_UX_PRINCIPLES、CHANGELOG；新增R-U30/R-A07/R-P26。
- 模型选择采用服务端多模型目录+工作台选择器分期：本轮先做目录/独立测试/启用与富选择器，不自动发现网关模型、不复制宿主Token/截图模型或价格；下一轮绑定Agent/SDK。MVP默认deepseek-v4.1-flash；真实DeepSeek实验仍是非Claude/unsupported，sdk-real-gateway(Claude)仍not_run。
- 2026-11-03 D075首切片实现：M04-A连接层保留单连接/单Key；新增同连接多模型registry、独立测试/启用、catalog多条目、Agent按catalog引用解析provider；工作台选择器改为可搜索/分组弹层；设置页新增模型目录添加/测试/启用/移除；MVP默认AI Plan预填deepseek-v4.1-flash。未自动枚举网关模型、未复制截图模型/价格/Effort、未接入SDK runner/Web默认业务。
- 2026-11-03 多模型选择证据：project-control/modules/M04/evidence/20261103T101648Z/results.json（606后端/19前端/44浏览器/types/build/pip全部通过，code fingerprint aebfe103dee3537d5214e67cf73e9ee954c19e71ed4b54e0c0cfb29b3fe36e7b）；浏览器remote-onboarding已改用新选择器helper，未放宽断言。开发服务由本轮启动并已停止，5173/8000无监听；未commit/push。
- 2026-11-04新窗口交接：用户要求写好交接/进度并开新窗口。已更新HANDOFF_DETAILS/STATUS/NEW_WINDOW_PROMPT；当前revision180，M04-C02-SDK仍DO/in_progress/not_verified。模型选择器首切片完成（606/19/44/types/build/pip，证据20261103T101648Z），下一步SDK/Web模型绑定。本轮未重跑测试；开发服务已停止，5173/8000无监听；未commit/push。
- 2026-11-04 SDK/Web绑定切片：AI Plan catalog模型经服务端引用进入SDK runner web_catalog；真实确认桥、2USD任务预留、模型/语义/来源/Schema失效、API层回执复核、engine标签；613后端/20前端/44浏览器/types/build/pip通过（fingerprint 1fd8ffff644261a56caf5c6abcfa1b55895a9fa6d3b4c29a5a6952a282fcc628，证据20261104T032252Z）；真实DeepSeek Web、Claude官方支持、个人API的SDK绑定与生产not_run；服务已停止，5173/8000无监听；未commit/push。
- 2026-11-04 真实测试准备：本机服务已启动并保持运行（5173/8000 loopback 200；启动器PID记录在tmp/dev.pid）；默认库1个启用Excel订单表来源（c0ea94d5-d9e0-406d-8037-6b018f7ff871，t0，编号/created_at/发货日期/金额），0个已发布语义；演示语义草稿DEMO_SEMANTIC_DRAFT.json已通过实际源校验valid:true/rows_read:false但未发布；估算账本15/60单元；等待用户网页输入Key并测试/启用模型、在知识库批准发布演示口径、发送并确认问数。未自动调用真实网关/未收费/未commit/push。
- 2026-11-04 真实 DeepSeek Web 测试用户报告成功：只读API任务3764b186-dc7d-4e29-98d6-888672b857ad phase SUCCEEDED、engine claude_agent_sdk_skills_v1、model deepseek-v4.1-flash、SQL已执行、质量PASS、input 120/matched 120/1组；结果行与聚合值未写入项目证据（本轮未落盘），sdk-real-gateway(Claude)仍not_run。用户指出效果与期望差距大：希望像参考截图中的正常Agent一样探索数据源/元数据、执行SQL、必要澄清、自然语言作答，右侧摘要显示实际数据源/任务进度；知识库除指标口径外需企业业务知识文档+RAG。已登记D-M04B-AGENT-EXPERIENCE-076待选择A/B/C；截图仅作交互参考，未复制公司数据/SQL；不自动接宿主MCP/公司Hive；未commit/push。
- 2026-11-04 用户选择 D-M04B-AGENT-EXPERIENCE-076 A：Agentic单源SQL（推荐）；已登记决策，开始A1切片：受控筛选/分组/时间SQL、SDK工具/Skill、自然语言回答、右侧实际来源/进度；不做RAG/多表/企业Hive/导出QA；截图仅参考不复制公司数据/SQL。
- 2026-11-04 D076 A/A1实现完成：受控筛选eq/in/gte/lt、SDK工具/Skill1.0.3、AgentTask.answer自然语言回答、实际表/指标/事件右侧摘要、终止式request_clarification；617后端/20前端/44浏览器/types/build/pip通过（fingerprint 1850298d4ecc5fcb66ebb031d0ae03022bbaff32bdbc45de4a4dcd83d375e144，证据20261104T062640Z）。本机服务已重启加载A1（新PID 4956），已发布语义/来源/预算保留，模型Key需用户重新输入；真实A1 Web测试待用户显式执行；RAG/多表/企业Hive/导出QA未实现；截图公司数据/SQL未复制；未commit/push。
- 2026-11-04 用户真实使用A1失败并否定卡片式交互：两个筛选/分组任务(task 15fd86fb..., 9d659f76...)显示AGENT_RESULT_UNKNOWN；只读诊断确认后端已执行/QA/发布，但SDK循环在发布后撞8步max_turns，runner判失败、API丢弃已发布结果；第三个含糊问题(task 113e56ce...)进入终止式NEEDS_CLARIFICATION。已在工作树做可靠性修复（publication存在且usage有效时成功、后端自动发布、Web预算16步/20工具/6元数据/200K/600秒、max_turns回归测试），专项23 passed/fingerprint64c7ed98...；完整回归/浏览器/types/build和真实复测未跑。用户明确新方向D077：连续对话Agent+L1指标引擎→L2主题SQL Skill→L3元数据/受控SQL→L4知识/RAG、可恢复澄清、QA/来源/报告；参考截图仅交互参考，不复制公司数据/SQL，不开放宿主Bash/Read/Write/Key。已写AGENTIC_CONVERSATION_L1L4_PLAN.md；本机服务仍在A1进程（可靠性修复未加载），新窗口需完整回归后重启，模型Key需重输；未commit/push。
- 2026-11-04 revision186续接完整检查：618后端/20前端/44浏览器/types/build/pip通过，证据20261104T074457Z。归属核对API31844/Vite31644均属项目dev33624；未重启/未调用真实模型/未读Key/未commit/push；进入已批准A2实现。
- 2026-11-04 A2 implemented; intermediate SDK/backend27passed and UI-only1passed, earlier fixture/version and atomic clarification-ID failures retained. Added final async confirmation/cancel rechecks and two tests after that intermediate run; final full regression pending. Source/semantic/ledger untouched; no Key/model/company query/commit/push.
- 2026-11-04 A2 full first626 backend/20frontend/types/build/pip pass, browser44/45 failed on initial-unconfigured Agent notice; evidence20261104T080447Z kept. Fixed notice only for existing received tasks, disclosed SDK2USD reservation in composer, made UI fixture awaiting-clarification plan empty, latched clarification-round cap to stop further execution; final full rerun active. Read-only old D05349/60 units, remaining2.75USD estimated: one task plus model retest fits, not three. No budget reset/real calls.
- 2026-11-04 A2 complete core regression626/20/45/types/build/pip passed(081413Z). Safety audit added explicit nonempty measured input/output/cache usage gate and one regression test; fresh final full check(082927Z) ongoing. Owned old tree4956 safely stopped after exact venv/script/listener recheck, started hidden dev27956; API31024/Web32176 both loopback200. Clarify invalid-contractPOST422/no task/model execution; publicOpenAPI404 disabled. Original authorized source enabled, published semantic1, existing profiles29 preserved. Provider unconfigured/Key absent. Read-onlySQLite campaign49/60 unchanged, estimate2.75USD remaining. No real models/commit/push.
- 2026-11-04 A2最终627后端/20前端/45浏览器/types/build/pip与源稳定通过，fingerprint ddf9d400751aed4b4ca065da80447e1d481110318205052152e597413fbd451b，证据20261104T082927Z。结果/usage、同任务澄清/预算/幂等/版本/schema/取消/异步确认、对话报告与保留结果均有检查。最终核归属后仅停止自己的20164前身树，隐藏启动launcher20164；API/Web loopback200，新路由invalidcontract422，没有模型/任务执行。Key未配置，原来源启用、语义1、账本49/60余额2.75USD不变。只够重测+一个SDK复测；三项需补授权，不reset。Claude/生产/MVP及本轮三项真实not_run，A3/B/C未实施，未commit/push。
- 2026-11-04 D078/R-U31新增：原PRD连续对话原则过于笼统，A2不视为本项体验验收；A2.1低风险实现进行中，真实模型不自动调用。
- 2026-11-04 D078/R-U31/AC05与PRD/索引/需求追踪已补；A2.1公开治理事件对话/工具标签/澄清穿插/安全正文/后端数值与内嵌表格已实现。19专项/23前端/tsc/browser1实测通过，完整当前源检查进行中。过程说明不冒充模型思维链，未复制公司截图数据SQL，未读Key/真实调用/commit/push，预算不reset。
- 2026-11-04 A2.1首次全检查631/23/45/types/build/pip通过，但末审升级产品Skill1.0.5/最终报告prompt及多TextBlock保留时源发生变化，source-stability失败；091236Z保留stale，不当最终证据。已启动干净完整复跑，不放宽源稳定断言。当前模型unconfigured/0任务；未真实调用/扩预算/复制公司截图数据SQL/commit/push。
- 2026-11-04 A2.1最终631后端/23前端/45浏览器/types/build/pip/源稳定全通过，fingerprint dcbf6753a9f16844c1eccf1baaa19ff595b77af682993b84f17f30303a8b9dfd，092140Z。D078/R-U31/AC05/PRD索引与追踪已补；公开治理对话/工具标签/同任务问答/正文报告/后端数值及表格/安全渲染/Skill1.0.5已实现。重启命令被环境拦截，未停止/重启/绕过，旧launcher20164仍200/模型unconfigured/0任务，默认新增字段未加载；需要用户手动重启。原来源启用/账本49/60余额2.75USD不变，未真实模型/新增费用/公司数据SQL复制/宿主权限/安装/commit/push。模型中间公开流/跨任务语义继承、A3/B/C、Claude/生产/MVP仍后续/not_run，M04未验收。
- 2026-11-04 用户报告手动重启并授权继续无需人工的工作；默认API200、模型unconfigured/0任务，未调用真实模型。继续D077 A3-M1：单源单表授权元数据发现+已有批准指标派生L2模板与参数化查询，不新增业务语义或自由SQL/公司数据/权限/费用；用户验收与真实门禁不变。
- 2026-11-04 A3-M1代码已实现，26初始专项passed/浏览器1与types通过；末审增加绑定/schema/unloaded/freeSQL拒绝与L2工具标签测试后，全量当前源检查进行中。L2仅已有批准口径派生单表模板，L3仅metadata基础，不开放自由SQL/新metric/多表/公司数据，原预算/确认/QA/receipt不变，未真实模型/commit/push。用户已重启A2.1且监听PID已变化；A3当前运行尚未加载。
- 2026-11-04 下班后自主A3-M1当前642后端/23前端/45浏览器/types/build/pip/源稳定全通过，fingerprint 4d39b9b48bd499383292b6526d9bea41d009dc71025e85928b2371555f1a7f0d，101013Z。单源单表metadata+批准canonical口径派生L2模板/参数提案、完整metric比对/提交后禁改计划、实际路径UI与Skill1.0.6完成。真实合成SDK/MCP9步/150输入/51匹配/2组/6375为独立测试金标准，无企业数据。用户重启A2.1新监听32324/30252于18:01:32，200/模型unconfigured/0任务；A3在其后修改default未加载，本轮不打断用户服务/不绕之前环境拒绝。账本49/60余额2.75USD不变，无Key/真实收费/公司截图SQL/host权限/安装/子Agent/commit/push。完整L2/L3/公开模型消息/context/RAG/多源/导出/QA及Claude/生产/MVP门禁保留，M04未验收。
- 2026-11-05 D079用户批准当前最新main更新GitHub后继续；当前源匹配642/23/45最终证据。预推检查1120候选文件未见规则匹配秘密，忽略runtime/key/上传/语义/账本/venv/临时draft；保留独立合成fixture/失败证据。无部署workflow确认后非force推既有main，baseline保留；推送结果待记录。

## 阻碍

## 上下文建议
在模块边界保存后按需切换。

在同一项目目录使用 $project-pdca，读取 project-control/progress.json 和 HANDOFF.md，核对实际文件后继续推进；遵守已登记决策，不重建项目。
