# 2026-11-04 D078：常规Agent式交互是验收要求
R-U31/M04-B-AC05要求问题后连续公开执行说明/真实工具标签/发现限制/原任务澄清问答/最终正文报告与内嵌表格，不以短句加大卡片算完成。A2.1在当前M04做此体验修正，不改变D070 SDK主线、L1–L4路线和A3→B RAG→C新公司数据授权的顺序。过程说明不等于原始思维链，截图不授权宿主Bash/Read/Write或公司数据；本机测试与真实体验验收分开。

# 2026-11-03 当前主线：Claude Agent SDK＋Skills＋治理Harness
D-M04B-CLAUDE-SDK-070明确替代D058/D069的LangGraph主线方向；顺序M02→M04-A→M03→M04（M04-B）不变。M01/M02/M04-A/M03有限本机验收保持，当前M04-C02-SDK DO。S01已锁定SDK 0.2.177＋CLI 2.1.317及Windows wheel hash，D071固定离线安装已完成；S02离线fixture 9项及602后端/17前端/44浏览器全回归通过，受控plugin Skill→指标/受控SQL→确认→真实合成MCP→自动QA→回执发布，详见M04 SDK_S02_OFFLINE_FIXTURE。真实AIPlan/生产仍not_run。官方不支持Claude Code经网关使用非Claude模型，现有DeepSeek文本/流式不是SDK兼容证据。先Skill路由/加载、动态探索/澄清，指标优先或SQL，取数必QA并校验回执；安全不是Prompt约定。LangGraph C01保留codex/langgraph-baseline-20261103（92d0b03），历史593/17/44不当SDK证据。D053总预算与PG/生产延期不变。D-M04B-MODEL-PICKER-075新增：产品需兼容个人API/企业AI Plan网关，工作台提供多模型选择；研发按“服务端多模型目录→选择器→SDK/Agent绑定”分期，MVP开发测试默认deepseek-v4.1-flash；不复制宿主Token/截图模型或价格，不自动枚举网关模型。

以下为历史路线与职责资料；旧“优先LangGraph/禁止SDK”选择仅历史，不能覆盖D070。

# 项目执行路线与模块边界

> 2026-10-27 当前事实：D-M02-RETENTION-013 A已批准，旧“待选择”叙述为历史。M02-C03仍DO；本机A自动清理已启用验证，PG真实及完整模块验收仍not_run，路线与逐模块验收不变。
更新2026-10-27；D-ROADMAP-MODEL-014记录本轮用户明确要求。它批准模块PRD和以下优先级/架构方向，不等于全部详细PLAN、LangGraph版本/安装、付费模型/外部目标/生产发布批准。

## 1. 当前状态与优先级

M01已经人工验收，M02-C03还在DO。D-M02-RETENTION-013 A已批准，内部安全执行已在独立副本通过；本机默认自动周期已验证；PG真实实例与模块审计验收尚未完成，不得通过写规划提前closed。

**M01已验收 → M02收尾 → M04-A 模型API接入 → M03 企业语义知识库 → M04-B SDK＋Skills受治理问数 → M05资产/任务/正式历史 → M06可视化 → M07报告 → M08MVP验收。**

M09归因、M10建模、M11实验保留MVP后范围；M12企业嵌入/完整发布。若首个客户需要SSO或私有模型/数据面前置，需要新变更审批，不自动跨验收。

## 2. 模块编号兼容与依赖

| 进度ID | 产品交付名称 | 硬依赖 |
| --- | --- | --- |
| M01 | 工程底座/业务会话工作台 | 无 |
| M02 | 数据源接入/MCP/执行底座 | M01 |
| M04-A | 模型服务接入 | M02 |
| M03 | 企业语义知识库 | M01、M02、M04-A |
| M04 | M04-B受控问数Agent/Harness | M02、M03、M04-A |
| M05 | 数据资产/任务/服务端历史 | M01、M04 |
| M06 | 可视化工作台 | M05 |
| M07 | 证据报告 | M05、M06 |
| M08 | MVP集成验收 | M02、M03、M04、M05、M06、M07 |
| M09/M10/M11 | 分析增强 | M08 |
| M12 | 企业化 | M09、M10、M11 |

原M04 ID不删除，其delivery_slice=M04-B；新增M04-A为独立验收节点，M05/M08原引用继续有效。M03新增对M04-A依赖表示交付先后，不是知识库结构校验必须依赖模型。当前active_module仍M02，其cycle及plan批准不重置。

## 3. 模型接入和编排方向

M04-A作为独立产品能力：“设置→模型服务”，配置供应商/受支持协议/base URL/模型名/后台凭证引用/授权域及预算，真实最小生成/流式/工具/结构化能力分别测试，不让业务每次填写API Key。官方SDK或严格受治理协议通过ModelProvider薄接口隔离，先不为一个API请求引入全套LangChain。选择供应商/模型/端点、数据外发内容/地域/处理条款、费用、版本与秘密方式需要模块PLAN和授权，缺服务凭证就not_run；数据源连接不自动允许把表行/Schema/历史发往模型。

M03维护版本化结构语义/批准口径，模型可辅助理解但不能自动认证。M04-B优先LangGraph实现显式状态/节点/分支/人类确认interrupt/可观测事件，混合确定性安全检查和受限模型步骤。实际版本、许可、传递依赖、现有Windows栈兼容与目标环境在PLAN核验后按运行权限安装；不重写已经通过的MCP/Worker，不同时安装多套框架。LangChain只在具体适配有价值时选组件；不默认接LangSmith/外部追踪/付费云。

权限、SQL/预算/文件网络边界由服务端执行，不交给模型Prompt或图框架。图checkpoint不是SQL恰好一次保证；使用已有回执、幂等键/不明状态/代际和将来M05持久记录。M04-A可验证真实文本调用但不能伪称问数完成；只有M04-B+M02+M03实际链路和结果质检后才是智能问数。

## 4. 文档职责、范围与门禁

- `project-control/prd/README.md`：13个交付PRD（原12模块加M04-A）。`REQUIREMENTS.md`及requirements.json覆盖可追踪用户反馈/原规划目标；来源和实现边界分开。
- `project-control/modules/<id>/plan.md`：当前详细方案与验收合同，未来PRD不是自动详细plan批准。M02原方案历史保留，新增引用和后继动作。
- `progress.json`：当前事实/审批/阻断/真实测试；HANDOFF由安全checkpoint生成，旧文档时程与建议不可覆盖。
- 项目Skill及个人安装副本按相同条件读取本项目路线；规则条件化，不把本项目ID顺序强加给其他项目，不更新无关Skill。
- M01仍已验收；M02清理/PG真实门禁保留。不能默默选择清理A/B、取消required、标production或提前进入新模块。
- M09/M10/M11/M12只记录目标/非目标/依赖/验证条件，不预批复杂统计方法、代码沙箱、SSO或生产部署，不虚构用户研究。

## 5. 当前项目下一步

D-M02-RETENTION-013 A本机周期已启用并完成75专项/281后端/24网页及原数据保护核查；接下来审查完整M02验收覆盖与真实PG补验条件，不能以本地周期替代PG或生产验证。真实PG要用户单独授权独立实例，不暗装服务或使用公司平台。M02审计与delivery后进入M04-A PLAN，先选择供应商、受支持协议、授权端点/凭证引用、预算/外发范围，再实现真实调用。之后M03 PLAN及M04-B LangGraph PLAN逐一审批验收，不因排期调整自动提前进入DO。


## 2026-10-28 验收后推进
D-M02-DELIVERY-049用户“是，继续推进吧”明确验收M02有限本机范围，依赖正常关闭；PG真实和生产验证门禁/责任人条件保留。当前原有M04-A-C01首DO：薄httpx Messages候选协议、本机隐藏Key输入和状态入口，不安装新包、不复制宿主认证、不自动收费。之后真实生成及目录/流式验收完成才M03→原M04=M04-B，当前SQL/JOIN尚未完成。


## 2026-10-30 当前架构及AIPlan连接（覆盖旧引擎提案）
用户明确保留原LangGraph＋项目治理Harness，D-CLAUDE-ENGINE-058已答，不实施ClaudeCodeCLI/AgentSDK引擎、不安装新Agent栈。M02已验收→M04-A真实模型接入→M03→原M04=M04-B LangGraph顺序不变。公司ClaudeCLI配置仅作模型API非秘密合同：coding-plan baseURL/AUTH_TOKEN风格Bearer，当前明确套餐coding-plan/v1/messages/anthropic_messages/bearer/deepseek-v4.1-flash。用户确认AIPlan支持DeepSeek，记录userconfirmed而非应用integrationpassed；不自动替换为claude-前缀别名、不安装CLI、不执行hooks或继承令牌/无限超时。
start-workspace-claude.cmd只是历史命名的模型API启动器，不等于工作台底层ClaudeCode。用户本人重启隐藏Key并显式test才调用，预算不reset，旧拒绝failed保留；109模型专项过（14套餐+95原专项），本轮preset/tests仅改，provider/UI/ledger未改，不称全backend/browser再过。最新网关实测未运行，收到新回执继续排查，不自动遍历认证/协议。

## 2026-11-04 R-U31 / AC05 A2.1本机CHECK完成，默认服务待手动加载
631后端/23前端/45浏览器/types/build/pip及源稳定全通过，证据`project-control/modules/M04/evidence/20261104T092140Z/results.json`和`A21_CHECK_REPORT.md`，fingerprint `dcbf6753a9f16844c1eccf1baaa19ff595b77af682993b84f17f30303a8b9dfd`。治理事件公开执行说明/实际工具标签/澄清问答按序、正文报告/后端数值/内嵌表格/技术折叠、Skill1.0.5已实现；不展示原始思维链，模型中间公开消息流仍待受控实现。重启命令被执行环境拦截，旧默认API尚未加载新字段，需用户手动重启本项目；真实体验验收not_run。D053余额2.75USD/49单位不变，无真实调用/公司数据复制/宿主权限/安装/commit/push；A3/B/C后续，M04仍DO/not_verified。

## 2026-11-04 A3-M1本机CHECK完成（非完整A3验收）
642后端/23前端/45浏览器/types/build/pip/源稳定全部通过，证据`project-control/modules/M04/evidence/20261104T101013Z/results.json`与`A3_M1_CHECK_REPORT.md`，fingerprint `4d39b9b48bd499383292b6526d9bea41d009dc71025e85928b2371555f1a7f0d`。已实现任务绑定单表/字段metadata发现、L1未命中时canonical批准口径派生L2模板与参数提案、模板回执/版本/预算/确认/MCP/QA发布、完整metric定义比较与提交后禁再规划、实际L1/L2路径和工具标签。Skill1.0.6/工具1.0.1/模板1.0.0，不开放自由SQL/新metric/JOIN/公司数据/host工具。用户已重启A2.1（新8000/5173监听18:01:32），A3改动在其后默认API尚未重载；本轮不打断用户服务，真实A3/Claude/生产/MVP not_run。D05349/60/2.75USD不变，未真实调用/安装/commit/push。完整L2业务Skill/L3/RAG/context/模型中间公开流等后续，M04未验收。

## 2026-11-05 A2.2当前本机CHECK完成，GitHub同步
669后端/23前端/45浏览器/types/build/pip/源稳定全通过，证据`project-control/modules/M04/evidence/20261105T024331Z/results.json`/`A22_CHECK_REPORT.md`，fingerprint `5affed8ff4be07d2e1e5086a81be2233cd41060ec98399140554458213495543`。完整工具伴随TextBlock有界未来意图、同ID拆块组合/unsafe消息毒化、双层门禁/4条500字、modelpublicintent来源标注已实现；不展示thinking/原始token流，unsafe中间原文不进失败diagnostic，无新请求/工具/费用或结果行历史外发。原MCP/QA/receipt/预算确认门禁不变。首次失败/重跑保留；默认服务与实模型尚未加载/验证，账本49/60估算2.75USD不变。此前基线702cabe已按D079非forcepush，最新增量推送另记真实receipt，未生产/未模块验收。
