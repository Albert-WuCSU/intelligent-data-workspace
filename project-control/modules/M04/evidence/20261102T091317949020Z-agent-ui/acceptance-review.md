# M04-B C01首次垂直切片审查（最终全量结果待补）
Reviewer=self_review，非独立审计、用户研究或整模块验收。

## 当前链路与条件
LangGraph1.2.19 StateGraph明确resolve→model→validate→humaninterrupt→execute。typedplan只指标ID/最多3维度/UTC批准时间段，不是任意SQL/工具。语义必须latest、enabled并metadata/schema/sourceversion/state_revision重验；模型启用/实测/代际绑定。planhash含模型、语义版本/schema/SQL/params，确认前没有SQL执行，恢复确认重查，schema/model/source变拒绝。
后台task按owner/requestUUID/requesthash和browserconversationUUID关联，仅sessionmemory，不是productionauth；graphstate只taskID，不放prompt/rows，每次调用tracing_contextdisabled/emptycallbacks。mandatoryLangSmith安装包未建云client，hosttracingfakeenabled下networkdeniedsmoke已过。旧模型provider硬输入2000/输出128上限不改，超上下文请求要求缩小，不截断定义或隐藏预算。

## 查询执行治理
workspace_aggregate_v1独立bootstrap/server/client只aggregate_metadata/submit/status/result四工具，精准schema检查；旧6toolpreview/HTTP定义不改。父WindowsJob/stdioenv白名单仍复用，新HTTPPG聚合不开放。执行端读取真实cataloghash匹配请求，有限count/sum/ratio/SQL AST按实际字段/表/参数生成验证，用户/模型不能给任意SQL，不能query注释/DDL/DML/外部函数。
实际全表输入<=200000/最大100输出组/结果200KB，有界只读engine/Job限制/5秒SQLdeadline，输出limit不用于input。单表COUNT/SUM/ratio150行金标准11325及零分母/空集/duplicategrain/维度时间/超输出组测试证明完整聚合而非100preview；QA单独WARN/PASS不做企业认证。
outer storagelease整个MCP操作保持，内部metadata_reader只在本函数已持有lease时绕装饰器避免nesteddeadlock，不新增公开skipLease。snapshotmanifest完整hash核对，unknown/deleted/sourcechangesfailclosed，允许source只是服务端savedlocalprofile，不浏览器路径。

## 模型与SQL幂等
模型单task一次，无自动JSONrepair/retry。API双确认原phase锁保证仅一次resume，提交前tombstone，MCP同UUID指纹回执；模拟执行已发生后丢ack状态UNKNOWN、同taskconfirm不重提。graphcheckpoint不是恰好一次，M05前重启后旧memorytask失效，页刷新只GETreadsameownedtasks，history不持久化model结果/SQL/result数字。

## UI真实状态
会话输入区选择授权semantic/model，右侧明确source，固定外发/估算同意→send才请求provider。没有齐上下文只本地提示；人工confirm独立勾选指标/range/unit/grain，SQL折叠查阅。结果与pipeline/右摘要由实际graphevents/MCPreceipt/result驱动，不计时动画。真实150row计算全量出11325，刷新待确认恢复与重复confirm/noadditionalcostbrowserfixture过。

## 已捕获/修复错误
no-networksmoke首次在Windowsloop初始化之前封socket导致自身socketpair失败，改在运行loop内禁止graphnetwork，声明不证明import无网络。MCPreturndict annotation不支持structuredSDK导致bootstrapexit，改dict[str,Any]。unsafeSQLtest替换了不存在的tableword导致unchangedSQL，改真实FROM变更，断言保留。执行outerlease嵌套metadata失败修内部ownedreader，真实MCP链路实跑通过。初TypeScriptoptionalfields检查修缺省值，没有全局跳过断言。

## 未完成/不能宣布完整
actualusergateway受限JSON规划＋自己的发布语义/真实Query尚未实测，当前browsermodel是假Key+MockTransport，数仓/MCP为独立真实localfixture。完整M04模块后继JOIN/L2L3L4依关系/adaptercapability再实现；M05资产/下载持久/M06图表/M07报告/M08集成和PG/production仍not_run。
已准D069首C01不是免后继门禁。当前独立fixture首切片进展不能称MVP已完成，userKey不读取/搬运/实际call，当前defaultAPI是否加载Agent未核，不重启或继承PID。本轮不部署/Gitpush/重新选预算或PG延期。
