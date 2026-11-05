# 2026-11-04 当前验收重点：R-U31 / M04-B-AC05
M04仍SDK主线DO/not_verified；原PRD“连续对话”过于笼统，D078明确常规Agent式交互：按实际事件公开说明→工具标签→发现/限制→同任务澄清问答→正文报告/内嵌结果，不能以短句加大卡片算完成。详见[M04-B](M04-B.md)末节、requirements.json/index.json及当前M04 plan。A2.1在本机检查中，真实模型体验未验收；SDK已固定离线安装且合成运行有证据，下面2026-11-03及更早not_run表格仅历史，不覆盖progress。无公司数据/宿主权限/新增费用授权。

# 2026-11-03 当前主线：Claude Agent SDK＋Skills＋治理Harness
D-M04B-CLAUDE-SDK-070明确替代D058/D069的LangGraph主线方向；顺序M02→M04-A→M03→M04（M04-B）不变。M01/M02/M04-A/M03有限本机验收保持，当前M04-C02-SDK PLAN、SDK运行not_run。先Skill路由/加载、动态探索/澄清，指标优先或SQL，取数必QA并校验回执；安全不是Prompt约定。LangGraph C01保留codex/langgraph-baseline-20261103（92d0b03），历史593/17/44测试不当SDK证据。具体迁移见M04 plan/PRD、SDK Skill reference。版本/安装/网关/新费用/数据外发尚需核验，不重问已批准总预算/PG延期。

以下为历史路线与职责资料；旧“优先LangGraph/禁止SDK”选择仅历史，不能覆盖D070。

> 2026-10-28 最新：M02有限本机local_ready已人工验收；PG/生产required/not_run仍保留，M04-A-C01正在DO，实现薄适配/隐藏Key/状态首切片，真实生成/流式/SQL/JOIN未完成。历史状态快照以下保留，当前以progress为准。

# 产品PRD总入口

> 2026-10-27 当前事实：D-M02-RETENTION-013 A已批准，旧“待选择”叙述为历史。M02-C03仍DO；保留安全底座实现中，实际清理执行及PG真实仍not_run，路线与逐模块验收不变。
版本V1.0 · 2026-10-27。按用户要求整理现存需求；未来模块PRD是需求和验收规划，不是已实现功能、模块PLAN或delivery批准。

## 已批准路线
**M02 收尾 → M04-A 模型 API 接入 → M03 语义知识库 → M04-B LangGraph 编排的受控问数**。M01已经验收，保持原交互和证据；之后M05→M06→M07→M08，M09/M10/M11是后续增强，M12企业化。
- 为兼容历史：新增进度节点`M04-A`；`M04-B`的进度ID仍为`M04`，不删除旧ID或创建重复Agent。
- M03对模型服务的硬依赖表示本轮批准的交付排序；结构化语义库本身可以先读设计，并非基础校验必须靠LLM。
- D-M02-RETENTION-013 A已批准，本机A周期已启用验证，PG真实和模块验收门禁仍not_run，M02未验收不得提前跳转；新模型/网络/秘密/付费/安装要按独立门禁。

## 模块PRD
| 进度模块ID | 产品名称与PRD | 优先级 / 依赖 | 实现状态 |
| --- | --- | --- | --- |
| M01 | [工程底座与业务会话工作台](M01.md) | MVP基础；保持不重建；无依赖 | 已验收（local_ready）；生产认证及持久历史不在此验收范围 |
| M02 | [授权数据源接入与真实执行底座](M02.md) | 当前MVP收尾，结束才启动M04-A；M01 | DO / not_verified；多个本地切片通过，完整模块未验收 |
| M04-A | [用户模型API与模型服务管理](M04-A.md) | MVP：M02验收后先于M03；M02 | 规划待实施 / not_run；本轮批准前置顺序和薄适配方向，不是详细PLAN或凭证调用批准 |
| M03 | [企业语义知识库与口径治理](M03.md) | MVP：M04-A后、M04-B前；M01, M02, M04-A | 规划待实施 / not_run |
| M04 | [M04-B Claude Agent SDK＋Skills的受治理问数](M04-B.md) | MVP：M02→M04-A→M03之后；M02, M03, M04-A | 规划待实施 / not_run；原模块ID=M04，交付切片=M04-B |
| M05 | [数据资产生命周期、持久任务与服务端历史](M05.md) | MVP：受控问数后；M01, M04 | 规划待实施 / not_run |
| M06 | [可视化工作台与可发布看板](M06.md) | MVP：资产层后；M05 | 规划待实施 / not_run |
| M07 | [证据化分析报告与审阅发布](M07.md) | MVP：资产与图表之后；M05, M06 | 规划待实施 / not_run |
| M08 | [MVP端到端评测、运维与交付审计](M08.md) | MVP集成交付门禁；M02, M03, M04, M05, M06, M07 | 规划待实施 / not_run |
| M09 | [指标变化归因与可复现分析](M09.md) | MVP验收后分析增强；M08 | 后续规划目标 / not_run |
| M10 | [建模工作台与受控Notebook](M10.md) | MVP验收后分析增强；M08 | 后续规划目标 / not_run |
| M11 | [历史AB与DID实验分析](M11.md) | MVP验收后实验增强；M08 | 后续规划目标 / not_run |
| M12 | [企业SaaS嵌入、模型驻留与正式发布](M12.md) | 企业化扩展及完整交付；M09, M10, M11 | 后续规划目标 / not_run；必要的SSO/私有部署可按明确客户需求前置另批 |

## 如何维护和使用
- [需求追踪表](REQUIREMENTS.md)及机器真源`requirements.json`，`index.json`提供模块/PRD/依赖映射。
- 全项目执行顺序和决策边界：[路线图](../ROADMAP.md)。PRD回答“为谁/做什么/如何验收”，模块plan回答“当前获批如何实施”，progress只记录“事实/审批/下一步”。
- 实施前读取当前PRD、PLAN、最近证据和用户原则；新增长期决策先询问，不把文档编写当用户研究或功能验证。
- `services/api/.venv/Scripts/python.exe project-control/prd/validate.py --root .`检查模块/需求覆盖、原M04别名、依赖图、源文件和批准方向。它不是产品运行/集成测试。
- 模型与数据源接入分离：M04-A“设置→模型服务”采用薄适配，M04-B采用Claude Agent SDK＋Skills编排（D070；旧LangGraph为历史比较分支）；现有MCP/Worker/SQL门禁独立保留。
- 本轮可维护项目Skill仅`skills/project-pdca`；它和安装副本同步时不修改其他无关数学/文档/系统Skill，不设置全局应用框架。

近期模型/PRD原话来源见 [USER_REQUESTS.md](USER_REQUESTS.md)。历史用户选择以原progress ledger为准，不据资料中的候选技术推导新批准。
