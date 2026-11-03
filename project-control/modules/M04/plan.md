# M04-B PLAN｜Claude Agent SDK＋Skills＋治理 Harness
2026-11-03 · M04-C02-SDK · 主线方向变更 D-M04B-CLAUDE-SDK-070 · 当前 PLAN / not_verified

## 1. 用户任务与选择理由
业务用户可能只知道经营问题，不知道数据/口径/表名。通过连续对话理解意图、按需读取Skills并探索授权元数据，补齐关键口径后取数，不要求先选metric_id或把思考拆成审批步骤。模型选择路线；真正执行仍有必要的人类确认。保留已验收黑白主题、历史、左设置/知识库、右来源摘要、真实pipeline和结构卡，SQL/Schema/工具日志折叠。用户选择SDK以获得更灵活工具编排，这是设计假设，不宣称Claude比LangGraph更准确。

## 2. 已批准与本轮边界
用户明确决定Claude SDK主线，更新规划/Skill/PRD/更新日志并上传GitHub，LangGraph另留分支。保留M04原ID、M01/M02/M04-A/M03验收、预算D053与PG/生产后补，旧方向D058/D069原记录不删，D070替代编排方向，不撤销历史安装许可。
本轮仅迁移方案和Git保存，不安装SDK/新CLI、不修改运行引擎、不重启/读Key/真实收费、不授权新端点/数据外发/production。版本锁和安装需要后续调查及明确许可；已选SDK方向不再重复询问。

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
官方Python仓库README/types已调研：SDK捆绑Claude Code CLI；allowed_tools可能自动批准而非完整工具白名单；env覆盖合并父环境；setting_sources控制加载设置来源；存在turn与预算选项。源仓库main是调研不是已锁release，不能当当前安装行为保证。官方文档站本轮403，未宣称完整核实。
1. 核确切SDK＋内置CLI版本/哈希/包大小/依赖/Python3.12-Windows wheel、运行前置工具、许可和Anthropic Commercial Terms，部署/分发义务。不能把原MIT LangGraph结论套SDK。
2. 确认用户现有AI Plan网关对Claude SDK消息/工具/Skill/stream/上下文/用量的支持及合法使用条件。原DeepSeek Messages文本/stream成功≠SDK通过；SDK并不保证接受任何OpenAI/BYOK模型。模型名称自由配置但仅实测能力允许执行，不猜端点或别名。若需新模型/端点/账号/付费/外发先单独确认，不自动换供应商。
3. 独立runner进程最小环境、HOME/cwd/设置隔离、最小网络白名单和资源限额。SDK env={}不阻断继承，禁宿主Claude/Codex登录/keys/user settings/hooks/plugin自动加载。产品Skill目录只受版本审计，不给任意文件Read权限。需要project setting_sources时只项目托管目录，禁未知MCP/hooks。
4. 明确tools暴露/disallowed工具/权限回调/hooks优先级，禁bypassPermissions；不靠allowed_tools或hook保证工具安全。执行/发布工具的后端鉴权是最终门禁。Bash/Write/任意Read/WebFetch/子Agent等默认不暴露；后续代码分析按明确沙箱新方案，不为灵活性放开主机。
5. 关闭不必要遥测/外部trace/缓存外发，核SDK启动/退出和进程树/WindowsJob；挂起确认不能占无限runner。真实状态事件映射现有任务卡，不显示模型思考链/Key。

## 5. 预算、恢复与复用
D053整体campaign不重置。旧一次generate/128输出token/2000输入字符路径是LangGraph首切片上限，不能直接扩成SDK多轮工具预算；需形成每任务turn/tool/token/墙钟与费用预留子合同，SDK max_budget_usd不是第三方网关实际账单硬保证。未知收费保留预留、不静默repair/fallback，新付费测试用户明确进行。
复用既有MCP/Worker/SQLAST/semantic/version/receipt/QA逻辑，迁移不重写底座。SDK resume不等于SQL exactly-once；确认绑定版本，提交前tombstone、未知ACK同键读取不重提；M05前不宣称生产持久任务。结果进入模型上下文须另审最小数据用途，既有只问题/必要字段授权不自动扩大至行/全历史。

## 6. 切片与下一步
S00（本轮）：保存LangGraph分支/归档，记录D070，更新需求和Skill，文档审计/Git推送。没有运行SDK。
S01：只读官方release/许可与网关适配调查，列出确切依赖/隔离/预算/工具合同及安装授权点；SDK方向已定，不重新选择框架。兼容未知则先报告，不暗换路线。
S02：经批准安装后，独立合成fixture验证load Skill→探索/澄清→指标/受控SQL→人工确认→真实MCP→QA发布；产品API/UI以capability明确区分legacy和SDK，不冒称已有实现迁移。
S03：用户网页显式实际网关调用/取数、故障/版本/恢复/预算/安全测试；L2/L3/L4与JOIN按依赖逐项实施。M05–M08才形成MVP完整交付。

## 7. CHECK/ACT验收与回滚
需实测：含糊问题能提出关键澄清；加载错误/恶意Skill无法扩权；指标匹配优先、无指标有依据转SQL；不支持adapter拒绝；无路由/无确认/跨owner/旧schema不能执行；每次取数必QA；无质量回执不能发布。涵盖超时/429/预算/取消/失联/重复确认/恢复，Prompt注入、Bash/文件/环境/网络旁路，黑白主题/键盘/窄屏/历史和真事件。
旧593backend/17frontend/44browser仅LangGraph baseline，不是SDK通过；新工具循环需完整重跑＋独立SDK兼容/真实网关门禁，not_run保持。self_review非独立审计，无用户验收不closed。
回滚使用codex/langgraph-baseline-20261103（92d0b03），旧方案见LANGGRAPH_C01_PLAN_ARCHIVE.md和LANGGRAPH_C01_PRD_ARCHIVE.md。不要删除数据/Key/历史/旧锁或强制重置Git。SDK与图未来比较同任务/工具/口径/质量/预算，记录正确性/澄清/成本/耗时/违规，不伪造基准结果。
