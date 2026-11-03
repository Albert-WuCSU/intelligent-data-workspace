# M04-B 相邻准备（未激活/未批准PLAN/不安装）

## 2026-11-02 实核输入条件
- M04-A有限本机已验收；ModelProvider.generate/stream可用，真实Messages固定文本已验。当前generate输入2000字符/输出128tokens，caller不能把测试成功推成业务Agent支持，结构计划parser需单独验收。
- M03新增单表count_rows/sum/ratio语义包、人确认发布/不可变version与metadata-only resolve（执行未接）。当前仅保存source profile，聊天附件是短期上下文，不能自动保存为永久来源或假设发布语义可跨其TTL。
- 本机包检查langgraph/langchain未安装；pydantic2.14.1/mcp1.30.0/sqlglot30.24.0已在项目venv。框架方向LangGraph批准不等于具体版本/新依赖安装许可，需在M04-B PLAN核兼容/许可证/传递依赖后批准。
- 实核M02 PreviewRequest/compile_preview只允许单表SELECT字段/LIMIT，AST拒绝聚合/WHERE/JOIN。**不能把现有前100行预览求和当完整业务结果，也不能对旧HTTP适配器强发聚合SQL。**

## 首PLAN需冻结的受控闭环
建议明确单表已发布语义→真实model受限JSON计划→确定性口径/权限/schema/version/预算检查→SQLGlot AST受限聚合编译→人确认→已审定MCP新增受限执行合同→结果schema/单位/分母/总数对账。优先L1指标路径，未知口径澄清而非编造默认。模型JSON计划不是任意代码，非法/注入计划拒绝，不执行tools/hook。

需新增或扩展受审定的聚合请求/适配capability，而不是绕过M02安全器：本机owned/localMCP可按显式新合同扩展，旧HTTPworkspace_navigation_v1/PG未实证聚合能力时拒绝，保持原工具/权限/Worker/幂等。WHERE/time语义必须来自真实字段与批准定义，JOIN键/粒度/基数没有合同不开放。后续多表不由右侧多选替代。

LangGraph节点：resolve_semantics→bounded_model_plan→clarify_or_validate→compile_check→human_interrupt→M02_submit→status_receipt→quality→structured_result。框架checkpoint不保证SQL恰好一次；继续复用UUID/tombstone/generation/request receipts，未知不重提。模型/发布semantic/version/sourcegeneration绑定单请求，旧模型或口径变化计划失效。

最短默认用户路径仍聊天提问→口径确认卡→显式执行确认→真实pipeline和结构化结果；SQL/工具折叠，未选择授权模型/语义/来源时给有效入口。Key设置不搬到聊天，单位真实/未知不得乱写，真实全量聚合不可从100行算总体。

## 不在本准备批准的范围
未安装任何框架、未提交实际SQL/付费model/公司元数据，不用第二套CLI/AgentSDK/外部trace。PG真实/生产、跨租户/secretstore、全厂商模型目录、业务持久任务/资产仍原门禁。M03CHECK/ACT/用户验收后再正式M04-B PLAN与版本/安装选择，当前active仍M03。
