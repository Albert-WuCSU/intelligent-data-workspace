# 2026-11-03 当前主线：Claude Agent SDK＋Skills＋治理Harness
D-M04B-CLAUDE-SDK-070明确替代D058/D069的LangGraph主线方向；顺序M02→M04-A→M03→M04（M04-B）不变。M01/M02/M04-A/M03有限本机验收保持，当前M04-C02-SDK PLAN、SDK运行not_run。先Skill路由/加载、动态探索/澄清，指标优先或SQL，取数必QA并校验回执；安全不是Prompt约定。LangGraph C01保留codex/langgraph-baseline-20261103（92d0b03），历史593/17/44测试不当SDK证据。具体迁移见M04 plan/PRD、SDK Skill reference。版本/安装/网关/新费用/数据外发尚需核验，不重问已批准总预算/PG延期。

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
