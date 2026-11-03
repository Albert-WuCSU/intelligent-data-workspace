# M03 下一步准备（未激活、未批准PLAN、不实现代码）

依据M03 PRD与既定M04-A→M03→M04-B顺序，为减少切换成本预整理。M04-A仍DO；不可据此启动M03或取数Agent。

## 最小垂直切片建议
分析师在知识库用结构化表单创建单域包：选择实际已授权data source/table/columns，描述对象粒度、主键、指标公式/单位/可加性，按需要显式选择时间字段/含义而非要求所有表有日期。批准后发布不可变版本供Agent使用；草稿/缺项不当已认证。首版JSON/Pydantic＋现有存储策略候选，不安装向量库/RAG或新数据库。

建议只第一切片：一个合法单表count/sum指标＋一个需澄清比率；JOIN留显式keys/cardinality/grain合同，不自动猜关联。数据源/MCP目录必须真实授权读取，不复制工具账号。结构metadata与语义批准分开，用户截图数字不可成为口径事实。

## 入PLAN时需冻结的选择
- 谁可以approve/publish：当前固定本机身份仍开发演示，人工确认不能冒充正式管理员认证。
- 元数据绑定：saved source/execution_generation/schema fingerprint；字段删改/停用使已验证映射stale，旧版本可追溯，不自动执行。
- Expression安全：有限结构化公式/聚合算子而非任意Python/SQL字符串；SQL模板若采用须受M02方言与白名单再质检，不让文档成为策略代码。
- 持久化：语义非秘密包/版本存储与已有local source SQLite候选比较，需确认生命周期/审批语义，不能直接拿progress作运行DB。
- 最短默认路径与审批：import/create→validate metadata→conflict repair→user approval→publish version。要保留可理解的错误/空态与隐藏SQL细节，不再把工程表单放业务聊天。

## M04-B准备但不执行
将来LangGraph节点：parse/clarify → retrieve authorized semantics/metadata → constrained generation → deterministic SQL/permission/预算 checks → human approval → M02 execution → result reconciliation → evidence.模型只访问已准问题/必要字段，不把多来源UI当JOIN已完成，不拿100行preview推全局。

测试计划与具体版本/安装在M03与M04-B各自PLAN确认后再实施；当前主干权限、预算、PG生产not_run、模块人工验收仍绑定。
