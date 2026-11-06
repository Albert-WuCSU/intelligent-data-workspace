> 2026-11-03：D070更新R-U24/R-A05/R-A06，机器真源requirements.json；SDK主线运行not_run，旧LangGraph方向仅历史。

> 2026-10-27：D-M02-RETENTION-013 A已由用户采用，清理执行仍not_run；下方历史待选记录以最新progress决策为准。

# 需求追踪表｜用户反馈、原产品规划与验收证据

版本V1.0 · 2026-10-27。覆盖现有聊天、已登记决策、项目用户原则、交接及V0.1策划，不声称可访问项目外未保存历史。

## 来源与优先级
- 当前人类决定：`project-control/progress.json`中的append-only decisions；实施事实只取当前测试证据，不取旧聊天完成声明。
- 原产品方案：`output/product-plan/产品策划方案V0.1.md`是规划来源；候选技术/时程/90%等不作为已测或全部实现批准。
- 用户原则与交接：`project-control/PRODUCT_UX_PRINCIPLES.md`、`HANDOFF_DETAILS.md`。最新“连接器无筛选且保留日期”覆盖历史统一时间/可选筛选提议；筛选属于M04业务问题或M06看板，不属于M02导航。
- 本轮D-ROADMAP-MODEL-014批准PRD与顺序：M02→M04-A→M03→M04-B。原M04 ID保留为M04-B；LangGraph为编排方向，具体依赖/许可证/安装/外发/收费另核验。
- D-M02-RETENTION-013尚未回答；不从路线调整或“继续推进”推断清理A/B选择。

## 用户需求及后续架构需求
| ID | 需求 | 归属模块 | 来源与批准边界 | 当前证据边界 |
| --- | --- | --- | --- | --- |
| R-U01 | 真实Web产品：用户要求最终为网站/应用，不接受仅CLI/API；当前Web优先，桌面包装后续按需。 | M01, M12 | D-SCOPE-001+D-M01-PLAN-001 / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U02 | 专业视觉：科技感、专业数据工作台，减少泛AI装饰和虚夸文案，不复制截图业务数据。 | M01, M06 | D-M01-VISUAL-001 / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U03 | 黑白双主题：顶部始终可见黑色/白色文字选项、选中态，刷新保持，手机可用，不隐藏为难发现图标。 | M01, M06, M12 | D-M01-UX-002+D-M01-THEME-VISIBLE-003 / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U04 | 会话与历史：业务默认左侧历史/中间连续长对话/底部追问；新建切换删除与多轮保留。开发localStorage仅文字，不是生产认证/跨设备历史。 | M01, M04-B(M04), M05 | D-M01-UX-002 / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U05 | 真实顶部状态：pipeline置顶，只表达真实事件，未接入/失败/部分/恢复明确，不用动画模拟找表或SQL成功。 | M01, M04-B(M04), M08 | D-M01-UX-002+PRODUCT_UX_PRINCIPLES.md / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U06 | 证据渐进披露：Agent输出结果/口径/附件/来源质量/下一步优先，SQL/Schema/日志折叠在专业工具；业务不填JSON。 | M01, M04-B(M04), M06, M07 | D-M01-UX-002 / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U07 | 产品经理作品：按角色、任务、可理解证据与可行动失败设计；保存真实取舍，不编造访谈、市场指标、业务收益。 | M01, M08 | PRODUCT_UX_PRINCIPLES.md / user_statement | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U08 | 状态化推进：每模块PLAN/DO/CHECK/ACT、关键选择询问、真实测试审计与用户验收、检查点和新窗口交接；不重建已验收M01。 | M01, M02, M08 | D-WORKFLOW-UX-UPDATE-001+AGENTS.md / user_decision | M01本地已验收及累计回归；模型/生产历史部分仍按后续模块not_run。 |
| R-U09 | 真实数仓主干：取数Agent通过治理MCP/适配层获取授权真实元数据并运行SQL，目标可为Spark/Hive；数据资产是下游交接，不替代数仓连接。 | M02, M04-B(M04), M05 | D-ARCH-001 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U10 | 独立合成测试：本机测试仓与样例独立生成，合成结果不能冒充经营；不访问公司平台/复制宿主凭证，外部目标和生产另批。 | M02, M04-A, M08, M12 | D-M02-DATA-SOURCE-002+D-M02-ENGINE-003+AGENTS.md / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U11 | 自助数据接入：新增数据源/配置MCP/非秘密连接文件导入，用户填地址或上传文件，实际测试再保存、刷新复用、编辑重测与启停；内置仓只是可选例。 | M02 | D-M02-UX-REWORK-005+D-M02-CONNECTOR-UX-005 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U12 | 仅表导航：连接器像Power Query：原表头/类型和前100行，无时间或其他筛选、不猜日期含义、不删日期字段；自然顺序不称最早/最新。 | M02 | D-M02-NAVIGATION-006+D-M02-TIME-CLARIFY-007 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U13 | 本地文件范围：DuckDB/UTF8 CSV/Parquet/.xlsx上传或后端受控路径；快照隔离、原文件不修改，路径与格式限额服务端落实。 | M02, M05, M10 | M02 plan.md+CONNECTORS.md+D-M02-XLSX-008 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U14 | Excel兼容：只读多可见sheet/中文标题/第一行表头/原日期/100行；公式宏外链不执行，旧xls/复杂报表不承诺，失败提示副本粘贴为值等。 | M02, M10 | D-M02-XLSX-008 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U15 | PG及HTTP接入：完整接入包含PG与受支持Streamable HTTP MCP；协议/工具/方言/权限逐项核验，未知不称兼容，真实PG目前not_run。 | M02 | D-M02-CONNECTOR-UX-005 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U16 | A专用秘密引用：只保存项目专用secret_ref与后端目标账号资源绑定，网页/JSON/日志不接明文秘密，前端/Worker不继承宿主凭证；不是生产密钥柜。 | M02, M04-A, M12 | D-M02-REMOTE-SECURITY-009 / user_decision | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U17 | 受限Worker与恢复：上传预检/解析/SQL及工具调用资源受限，故障回收自己拥有Job、不盲杀服务，原数据保留，隔离不可用拒绝而不无限回退。 | M02, M04-B(M04), M10 | 2026-10-27用户继续Worker/stdIO要求+M02 plan.md / user_statement | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U18 | 不明任务不重提：长驻MCP故障旋转代际、旧结果失效，显式验证重建；丢回执/取消请求保留未知任务和幂等，不自动重复执行。 | M02, M04-B(M04), M05 | HANDOFF_DETAILS.md+M02 plan.md / user_statement | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U19 | 清理只读及待选：预检失败仅清本次新暂存，盘点不删历史；长期24h自动回收或手动确认未选，保存/禁用/原件/未知历史/证据保护。 | M02, M05 | D-M02-RETENTION-013（pending，不是批准） / pending_choice | 只读盘点/失败新暂存已测，D-M02-RETENTION-013未回答、长期清理执行not_run。 |
| R-U20 | 服务归属：先查5173/8000健康/拥有者/父链，不继承旧exec session，未知/PID变化拒绝操作；只停自己拥有且获批服务。 | M02, M08 | AGENTS.md+2026-10-27用户续接说明 / user_statement | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U21 | 真实证据门禁：实际命令/退出码/指纹/环境；mock不冒充真实，未验证not_run；M02未验收不closed，不因进度推进虚报生产。 | M01, M02, M08 | AGENTS.md+project-pdca / user_statement | M02本机切片部分已实测；Spark/Hive/真实PG/生产等未验证按progress.not_run，不当全能力完成。 |
| R-U22 | 模块PRD与追踪：项目目录每模块有PRD，已提出需求可追踪到来源、实现、验收或not_run；未来模块不虚构完成。 | M01, M02, M04-A, M03, M04-B(M04), M05, M06, M07, M08, M09, M10, M11, M12 | 2026-10-27本轮用户PRD要求 / user_statement | 本轮文档实现；文档审计不是产品功能测试。 |
| R-U23 | 大模型是核心能力：用户能配置自己的模型API，由真实调用驱动理解/生成；不能只做好数据连接而长期没有模型接入。 | M04-A, M04-B(M04) | 2026-10-27用户模型API反馈 / user_statement | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-U24 | 已批准模块顺序与SDK主线 | M02→M04-A→M03→M04（M04-B）顺序保留，D070改为Claude Agent SDK＋Skills＋治理Harness主线；LangGraph独立分支保留比较。 | D-M04B-CLAUDE-SDK-070（替代旧编排方向，原决策保留） / user_decision | SDK方向/文档已批准；运行迁移、安装和真实网关兼容not_run。LangGraph历史C01证据不当SDK证据。 |
| R-A01 | 模型服务分层：设置→模型服务和数据源连接器分开；管理员配置，业务选授权模型；ModelProvider薄适配优先，不为单API调用引入全套框架。 | M04-A, M04-B(M04) | 本轮采纳前一轮模型接入建议 / approved_direction | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-A02 | 模型能力与协议：供应商/base URL/模型名称/凭证引用/能力/限额配置，实测认证及最小生成/流式/结构化/工具支持分别声明。API兼容标签不等于全支持。 | M04-A | 本轮采纳前一轮模型接入建议 / approved_direction | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-A03 | 模型费用与失败：真实token用量/可核验费率；无费率显示未知，限制预算/最大输出/重试。401/403/429/超时/中断/部分输出有下一步，不假成功。 | M04-A, M08 | 本轮采纳前一轮模型接入建议 / approved_direction | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-A04 | 模型数据外发：连接数据源不自动批准把表行/Schema/知识/日志发给LLM；单独确认供应商/域/地域/处理条款/最小上下文，私有部署不自动保证驻留。 | M04-A, M03, M04-B(M04), M12 | 产品方案14.2+本轮架构方向 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-A05 | Claude SDK＋Skills编排 | 模型先产品Skill路由/加载，再自主澄清/探索与指标优先或受控SQL；Claude Agent SDK承载tool_use循环，版本/许可/网关/隔离/安装待核。 | D-M04B-CLAUDE-SDK-070（替代旧编排方向，原决策保留） / approved_direction | SDK方向/文档已批准；运行迁移、安装和真实网关兼容not_run。LangGraph历史C01证据不当SDK证据。 |
| R-A06 | 编排与安全边界分离 | Prompt/Skills/SDK权限hook不能替代后端授权/SQL/预算/确认/幂等；取数内部必QA且发布核回执，SDK resume非exactly-once，不默认外部trace或无限工具。 | D-M04B-CLAUDE-SDK-070（替代旧编排方向，原决策保留） / approved_direction | SDK方向/文档已批准；运行迁移、安装和真实网关兼容not_run。LangGraph历史C01证据不当SDK证据。 |
| R-P01 | 任务分类：取数/指标分析/体验洞察/建模/实验/普通对话；低置信多意图先选择，VOC独立授权，依赖操作串行。 | M04-B(M04), M09, M10, M11 | 产品方案6.1/6.8 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P02 | L1至L4治理：认证指标优先L1、审核模板L2、授权范围探索L3、明确目标L4；不机械全路试探，权限拒绝不换路线绕过。 | M03, M04-B(M04) | 产品方案6.2/6.7 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P03 | 关键口径澄清：指标版本/分子分母/粒度/实际时间字段/时区/币种/状态/基准集中澄清，只问缺关键项；已批准默认披露，不统一给所有表日期槽。 | M03, M04-B(M04) | 产品方案6.3+用户日期澄清 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P04 | 结构化语义包：Domain Pack包含manifest/metrics/glossary/entities/mappings/joins/clarification/templates/policies/quality-rules/examples/docs；导入校验/冲突/审批/版本回滚。 | M03 | 产品方案7 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P05 | 文档与执行知识区分：RAG仅解释/补充，不把未审文档变认证指标/权限；表映射绑定连接版本、关联基数/粒度，配置不带密码。 | M03, M04-B(M04) | 产品方案7/14.2 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P06 | SQL前后质检：所有平台SQL静态只读/白名单/方言/参数/权限/关联预算，LIMIT不等于扫描预算；结果类型单位/空值/唯一/膨胀/守恒/新鲜度/金标准检查。 | M02, M04-B(M04), M08 | 产品方案6.4 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P07 | Python质量：派生图表/归因/建模/实验代码均固定输入版本、依赖种子与输出Schema，资源网络隔离；模型自评不替代程序检查。 | M04-B(M04), M06, M09, M10, M11 | 产品方案6.5 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P08 | 来源质量分离：DIRECT_CERTIFIED/COMPUTED/INFERRED与PASS/WARN/FAIL独立；绿色不表示因果或绝对正确，推断不当已确认KPI进入正式看板。 | M04-B(M04), M05, M06, M07, M09, M11 | 产品方案6.6 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P09 | 能力声明：metadata/execution可分服务，source显式映射；ACL/方言/成本/取消/下载/分区能力unknown/unsupported不默认为true，按真实认证矩阵公布。 | M02, M04-B(M04), M08, M12 | 产品方案8 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P10 | 标准资产：不可变asset_id/version、hash、schema/row_count/grain/units/timezone/metric_contracts/provenance/quality/policy/retention；预览不当完整资产。 | M05, M06, M07, M09, M10, M11 | 产品方案9 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P11 | 派生和补数：派生资产input_asset_versions及操作参数代码血缘，权限取交集；下游通过DataRequirement回主干，允许已授权上传独立输入。 | M04-B(M04), M05, M06, M07, M09, M10, M11 | 产品方案5.3/9.3/9.4 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P12 | 正式任务和会话：鉴权持久任务/服务端历史、状态事件/幂等、权限撤销后缓存与导出失效；阶段性partial/expired明确，真正取消需上游回收回执。 | M05, M08 | 产品方案5.4/9.4+PRODUCT_UX_PRINCIPLES.md / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P13 | 可视化：KPI/趋势/条形/构成/明细与模板，ChartSpec/DashboardSpec布局/联动/钻取/筛选/刷新/版本/导出；根据真实资产语义选图，不执行任意生成HTMLJS。 | M06 | 产品方案10.1 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P14 | 报告证据：ReportSpec及claim_id固定数字/图表/资产版本，证据→结构→撰写→数字校验→用户审阅→发布，输出网页及首选一种导出格式另选；外发确认。 | M07 | 产品方案10.2 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P15 | 归因：同口径可比窗口/人群/单位，结构/漏斗/乘积/比例分解，贡献+交互/残差守恒及小样本警告，不称因果；Shapley仅方法需要时。 | M09, M07 | 产品方案11 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P16 | 建模IDE：资产/上传工作区、小型Notebook代码Markdown/运行停止/环境/Agent生成修复/图文件版本，Python优先；不复制VSCode全功能。 | M10 | 产品方案12 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P17 | 建模评估：固定快照/代码/环境/参数/种子/指标资源，训练验证测试切分/时间切分/泄漏不平衡检查/可用基线，离线登记不自动生产推断。 | M10 | 产品方案12.2 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P18 | AB分析：实验方案主要/护栏指标/MDE功效/随机单位窗口，SRM/曝光一致性/ITT/效应CI/多重或序贯方案；污染及SRM阻断正式结论，CUPED有条件。 | M11 | 产品方案13.1 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P19 | DID分析：有效对照/处理前覆盖/平行趋势证据/预期溢出组成，错位处理适配而非机械TWFE；局限与敏感性，无条件只描述。 | M11 | 产品方案13.2 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P20 | 在线分流排除：历史AB分析不等于在线实验；桶/互斥/曝光SDK/安全停止需独立接入需求与审批。 | M11, M12 | 产品方案13.3 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P21 | 权限驻留：服务端身份/RBAC/ABAC/行列ACL/导出分别鉴权，子Agent权限不高于发起者；文档和注释不可信，防注入不靠Prompt。 | M02, M03, M04-A, M04-B(M04), M05, M08, M12 | 产品方案14 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P22 | 评测：版本化真实金标准含正常/澄清/拒绝/空/超时/复用，报告正确率完整分母、延迟成本，90%/p95等旧建议待测不当成果。 | M04-A, M04-B(M04), M08 | 产品方案17 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P23 | 企业嵌入：iframe/React或WebComponent SDK/API，SSO短会话/服务器租户映射/来源postMessage，品牌/语言时区币种上下文配置安全底线不可关。 | M12, M01 | 产品方案16 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P24 | 部署与插件：模块化单体/独立Worker先行，不提前微服务/Temporal/K8s；ModuleManifest插件允许输入工具/资源网络、签名审查不覆盖权限。 | M08, M10, M12 | 产品方案15 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |
| R-P25 | 运营成本假设：经用户确认可复用任务为指标候选；模型/扫描/沙箱/存储/传输/重试计费边界、配额和拒绝；商业定价/团队时程是待验证假设。 | M04-A, M08, M12 | 产品方案18/19 / product_plan | 规划目标或已批准方向；真实模型/知识库/下游分析尚未实现，not_run。 |

## 验收映射
- 每个模块PRD包含需求ID→功能→ACxx行为；当前M02源码与证据映射保持原plan及evidence，不以本表覆盖。
- 后续模块先基于PRD写PLAN并冻结合同；没有真实环境用mock隔离测试，同时保留真实not_run。
- 更新需求时保留ID及来源，追踪审批/变更影响；已验收模块不得因新增PRD被宣称重新完成或取消原验收。


## 2026-10-28 新增用户反馈（机器索引同期更新）

| ID | 需求 | 模块 | 来源 | 当前边界 |
| --- | --- | --- | --- | --- |
| R-U25 | 输入区模型选择：用户明确要求工作台直接切换模型；仅选已配置/已授权/实测可用model，修改使后续计划失效，当前无模型要显示待接入而不冒充可用。 | M01, M04-A, M04 | D-MODEL-REFERENCE-BUDGET-035 | 模型/外发not_run；UI和非秘密参考不当作调用许可。 |
| R-U26 | 15美元测试预算与非秘密供应商参考：MVP测试模型调用总额不超过15USD；可参考本机ClaudeCode非秘密配置，不能复制宿主token或推导内网应用/外发授权。费率/用量未知不显示虚假余额，需专用限额或可靠预留计费。 | M04-A, M08 | D-MODEL-REFERENCE-BUDGET-035 | 模型/外发not_run；UI和非秘密参考不当作调用许可。 |
| R-U27 | 轻量三列会话与真实摘要：用户参考图明确左历史/中对话/右任务及来源文件摘要、底部输入模型选择；黑白主题/历史/pipeline保持，摘要只由真实回执投影，不复制截图中的公司数据或生成成功结论。 | M01, M04, M05 | D-MODEL-REFERENCE-BUDGET-035 | 模型/外发not_run；UI和非秘密参考不当作调用许可。 |


## 2026-10-28 接入位置纠正

- R-U28 · 聊天本地文件而非连接器重复入口：直接在聊天添加本地数据文件，安全预检/临时目录/100行真实预览复用后台导入层，connector只新建数据库/MCP；不删除旧配置或原件、不自动保存临时附件、不向模型发送行。 来源D-MVP-FAST-034，模型/JOIN未实测仍not_run。
- R-U29 · 右侧多来源与真实多表JOIN：来源候选范围放右侧可多选，取消输入单来源。实际JOIN须表关系/键/粒度/权限/预算和结果校验；同库多表与跨源融合区分，UI多选不等于已执行JOIN。 来源D-MVP-FAST-034，模型/JOIN未实测仍not_run。

## 2026-11-03 多供应商与多模型工作台选择

| ID | 需求 | 模块 | 来源 | 当前边界 |
| --- | --- | --- | --- | --- |
| R-U30 | 多供应商/多模型选择：兼容用户个人API或企业AI Plan网关；工作台提供类似Claude Code的模型选择器；同一连接可维护多个模型；只展示服务端已测试/启用模型；MVP开发测试默认`deepseek-v4.1-flash`，不写死为唯一模型。 | M04-A, M04 | D-M04B-MODEL-PICKER-075 / user_request | 需求已记录；多模型目录/选择器待实现；不复制截图第三方模型/价格，不自动发现网关模型，不读取宿主Token。 |
| R-A07 | 模型目录与选择治理：每个模型独立测试/验证/启用；catalog绑定generation/config/model版本；模型变化使旧计划/确认失效；不自动枚举/猜网关模型，不显示未验证价格/上下文；Key只在后端内存。 | M04-A, M04 | D-M04B-MODEL-PICKER-075 / approved_direction | 现有单模型catalog/resolve已实现；多模型registry/选择器未实现；自动发现与真实SDK绑定not_run。 |
| R-P26 | 选择器UX：搜索/来源分组、模型ID/来源/状态；价格与上下文仅在真实来源存在时显示；键盘/窄屏/黑白主题可用；选择不调用模型；未验证/预算耗尽/失效有可行动状态。 | M04-A, M04 | D-M04B-MODEL-PICKER-075 / user_request | 当前为简单select单模型；富选择器/多模型状态待实现。 |

## 2026-11-04 R-U31 / D078 常规Agent式交互
用户原话：“我希望我做出来的取数agent产品除了遵循L1-L4之外，接收到问题应该像这样，和常规agent产品类似，你现在的产品输出结果不是对话，是纯纯卡片结果，你看看PRD有没有描述我这个需求，没有就加上，继续推进”。三张图只作交互参考；不存公司数据/SQL。验收与边界见M04-B-AC05；收到问题后的过程说明/工具标签/发现与限制/澄清问答/正文报告是明确需求，不等于原始思维链或宿主工具授权。

## R-U32 / D080 通用架构设计与受限资料隔离
用户明确要求原始资料独立私有归档、主项目只保留不含具体组织业务信息的通用设计；新增ARCHITECTURE_V2与M04-B-AC06，保持现有SDK和安全门禁。受限原文、逐页提炼、内部案例/术语/字段/系统信息不得进入本项目或规划Skill；本地泛化文件不自动获得公开许可。


## 2026-11-06 D086（覆盖旧默认手选，不删除历史）
R-U29的旧右侧多选是历史设计，当前改为Agent授权内选源与只读来源投影；多源/关联安全要求保留。

| ID | 需求 | 模块 | 来源 | 当前证据 |
| --- | --- | --- | --- | --- |
| R-U33 | 自然语言优先与Agent自主选源及任务分流 | M01, M04 | D086 | design_only / not_run |
| R-U34 | 聊天任务附件与结构化上传统一临时表 | M01, M02, M04, M05 | D086 | design_only / not_run |
| R-U35 | 未接RAG时的知识证据兼容端口 | M03, M04 | D086 | design_only / not_run |
