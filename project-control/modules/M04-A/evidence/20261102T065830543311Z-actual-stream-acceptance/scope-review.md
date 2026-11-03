# 当前 M04-A 验收范围核对（用户确认前不闭模块）

Reviewer=self_review，非独立审计。真实AIPlan Messages生成与流式已由用户操作/截图及只读status确认，525backend/16frontend/39browser稳定代码证据有效，不重新收费或要求用户再次测试。当前catalog_enabled=false只意味着用户未显式启用当前配置，不能自动设置true。

## 已完成本机能力
设置独立页、专用Key后台会话内存、自选model、保存不调用/显式测试、版本失效、目录启禁/输入选择、预算未知保留/幂等/防排队、Messages真实固定stream、partial/cancel/诊断、安全SSRF/Key隔离；错误和其他协议本机fixture回归有效。

## 不能自动宣称已完成的范围
个人公网账号/API/TLS、整个真实Key编辑/清除/恢复生命周期、生产身份/秘密持久化/部署、硬成本保证、自动完整模型目录、Responses/Chat真实stream。当前本机固定开发身份与会话profile不取代生产。所有这些不因一句“继续”自动延期。

## 历史与当前scope应分开
real-model-api是旧Responses候选401/403实际failed；当前用户选定Messages已成功，不可把旧failed改passed或当成not_run延期。拟经明确范围确认，将旧候选测试原字段/required/status/evidence完整保留到历史scope档案，并绑定对应能力重新启用前必验门禁，而不是隐藏/删除失败。
real-sdk-root-key-model-test是另一root/v1/messages/x-api-key候选required/not_run，当前选定coding-plan/Messages/Bearer是不同合同。同样需明确范围确认，保留未验约束，不为了关闭自动降required。
公网供应商/生产风险与完整真实生命周期可在用户选定有限本机交付后，按现有finite_local schema列deferred_tests/deferred_risks→release gate/owner/condition，required/status不改。工具/结构化与自动目录仍明确未实现，不称多模型完整兼容。

## 推荐确认（D-M04A-DELIVERY-M03-064，未回答）
以“当前本机AIPlan Messages实测生成/流式＋通用表单隔离测试”为M04-A有限local交付，不声明公网/生产验证；旧候选原失败/未验按协议归档并保留重启该能力时必验门禁；其他外部/生命周期补验保留明确发布门禁。确认后才正式scope审计/登记delivery/关闭M04-A，不把图或测试数当自动验收。

下一M03采用PLAN_DRAFT推荐：单表结构化count/sum/ratio语义包，真实字段映射/冲突校验、人工批准不可变版本、非秘密SQLite版本存储，不装RAG/向量库、不调用模型自动认证。审批/保留策略：只本机开发主体的显式批准，包版本持久保留直至用户明确删除政策（无自动回收/删除入口），不涉及秘密存储/生产角色。用户确认该方案后才M03 DO，之后M04-B保持LangGraph＋治理Harness与M02受控SQL执行。
