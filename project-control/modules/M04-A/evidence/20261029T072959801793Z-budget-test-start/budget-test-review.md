# 估算预算与最小模型测试切片审查

2026-10-29；reviewer=self_review，非独立审计/用户研究。
结论 **local_slice_pass；M04-A整体partial/not_verified，真实网关测试等待用户加载更新并点击。**
范围来自D-MODEL-ESTIMATE-BUDGET-053：用户接受近似10-20USD而非供应商硬价格保证；不再重复要求供应商限额证明，窄外发及Key隔离不变。

## 用户任务/实现/证据
- 本机隐藏Key实操：用户已双击入口隐输并启动，GETmodelstatus实际credential_configured=true/openai_responses，截图及布尔验证不包含Key值；Key auth或生成仍未验证。只读核API32652父2912/Vite25284父21672、CN1/luqianwu/15:22:13；不读环境/命令行/Key，也没有停止该持Key进程。
- 近似预算不阻断模型：25cents固定预留/60次/15USD目标/20USD预算参考，本机SQLite持久事务，路径/junction/hardlink/目录及文件handle pinning/CREATE_EXCLUSIVE/未知DB拒绝/2MB上限；Decimal展示精确预留累计，但实际费用unknown，非数学费用上界。无reset/退款接口，重启或失败/超时不清账。
- 真实测试入口：POST /api/v1/model-service/test，服务端本机身份/CSRF/64KB接收限额/currentconfiguration+runtimegeneration+UUID+acceptestimatedcost；只发送固定non-sensitive短文本，不接受Key/业务问题/rows/history/screenshot/SQL或外部目标。原两协议安全边界保留。
- 重复/失败/恢复：同UUID返回同回执，不再次网络/预留；并发其他UUID拒绝；timeout/cancel标unknown并保留预留，跨API重启旧generation拒绝，不自动重提。test/正文回执仍内存（非M05持久队列），只有UUID/time/outcome/usage写账本，不写Key/prompt/output。最多60内存回执，预算跨进程统一60上限。
- 业务层：模型服务显式接受估算后点击，成功只“最小模型生成”并显示实际token或unknown、估算成本/SQL未执行。模型目录仍空不开放自然语言SQL，底部普通问题仍未执行；测试不会把数据源上下文外发。旧hardlimit说明已纠正。黑白/历史/附件/多来源/noFilterdate/Worker/retention原路径保留。

## 实际检查
1. 95专项（原79协议+16预算/接口）实跑退出0。正式日志同完整backend：382 passed（原287+95）/16frontend/30browser、types/build/pipcheck全部退出0，073000Z/results.json。
2. 仅WorkbenchPanel旧hardfee说明和DEVELOPMENT文档在完整测试后更新；所有backend/tests/contracts/locks字节一致。全frontend/types/build和30browser按最终代码重跑退出0，073603754925Z-budget-ui-final/results-final.json含明确reuse记录，382保留原实际命令/指纹不冒称后端新跑。
3. 独立check_budget_processes.py真实4个Python进程竞争，最多60预留；全部退出后新进程读15.00USD估算账本并拒绝第61请求，退出0，budget-processes.txt。临时目录/环境白名单，无真实Key或网关/默认数据访问。线程竞争/同进程新Store不是该真实子进程证据替代。
4. PRD一致性、5PRD守卫、26进度守卫及warehouse SQL/Parquet对账退出0。Pydantic/OpenAPI导出Types，未手改generated；新非秘密data/model-runtime已.gitignore，不入Git。
5. 视觉检查最终estimated-model-test-light截图：成本接受/最小生成和fixture输出/SQL未执行/真实token估算、右侧可滚动说明，不冒充公司API生成。新增browser使用真实产品路由+isolatedMockTransport，明确fixture；原HTTP/stdio路径独立实际执行不等于真实模型网关。
6. 恢复进度draft阶段首括号拼写错误导致draftrev校验拒绝，修正后checkpoint96，无主状态覆盖/秘密丢失。完整测试期间DEVELOPMENT文档先改后立即按原字节恢复，结束manifest一致；最终文档更新作为UI复测diff显式登记，不把版本变更隐瞒。

## 当前真实运行与限制
用户当前Key在旧已运行API内存里；新预算/test路由代码没有热加载，不复制或迁移Key以更新。请本人在自己启动窗口Ctrl+C，双击start-workspace-model.cmd隐输一次，然后网页模型服务勾选估算并点击固定最小测试。这一次才会真正调用网关。测试开发过程从未使用其Key或收费。不能用当前credentialtrue/fixture通过宣称real-model-api已通过。
账本是有限本机软预算治理（Windows已核验），不是防同用户管理员篡改的生产费用保险，删账本可破坏约束所以无产品reset/API且文档禁止删账本绕限额；未知/损坏账本拒绝而不重建。没有供应商实际费用字段，真实账单仍需用户查看，不将估算余额当实际余额。
部分/别名/128输出/协议不兼容可能使首测试返回invalid/unknown，保留预留不自动扩大输出/换模型。请求成功不表示LangGraph/语义/SQL/JOIN已实现，模型目录保存/编辑/启禁/流式尚未完成。

## 下一步
用户加载更新并显式点击测试后，只读真实回执/usage/error并排查协议/模型（不读Key、不绕权限）；real-model-api仍required/not_run until actual evidence。然后M04-A其余非秘密配置/目录启禁/流式验收，之后才M03→原M04=M04-B。PG/生产后补门禁不删。本轮未安装/宿主认证复制/公司数仓/网关请求/部署/推送/用户文件删除。
