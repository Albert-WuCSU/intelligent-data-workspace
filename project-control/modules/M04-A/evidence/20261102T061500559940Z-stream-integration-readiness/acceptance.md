# 流式联调准备修复检查

Reviewer=self_review；局部工程检查，不是独立审计或模块/生产验收。

## 已落实
StreamDiagnostics为服务端Literal分类：frame/sequence/model/usage/secret/incomplete/resource/encoding/transport/timeout/refusal/cancelled/unknown。只白名单HTTP401/403/429，不输出任意模型ID/供应商正文/思考/Key。GET同一stream回执只读、不预留、不调用；浏览器明确diagnostic和HTTP分类而非要求用户贴供应商原文。

已有stream或配置锁时普通test新UUID立即409 MODEL_CONNECTION_BUSY，不排队或第二次收费；当前代际/版本的已有普通testUUID只读回执可返回。未知context不返别的回执，normal/streamUUID不能跨类型复用。安全靠API/锁/严格parser实施，不靠Prompt。

## 初验
97后端stream/预算/目录/BYOK专项passed；2浏览器casepassed（真实产品API＋隔离fakeKey stream：success/cancel＋403diagnostic/只读回执预算仅一次）；TypeScript编译passed。新分类测试覆盖$model/secret/stop/tool/usage/sequence；原所有截断/分片/超限/权限/泄漏断言保留。全回归结果另附，完成前不称最终通过。

## 真实状态与依赖
本轮只读核26880:8000 API由项目venv启动、22332:5173为项目Vite；不继承PID到下轮或停止进程。状态仍glm-5.3已验证并启用，没有stream_management，尚未加载stream新代码。没有调用实际模型、读取Key/env、重启服务、向公司SQL/模型目录发请求。

本轮用户“抓紧推进”不是批准盲杀/自动花费或提前验收。当前真实网关stream所需用户动作：在原项目启动终端本人停止并普通start-workspace.cmd加载新版→网页安全输入Key（不聊天）→设置流式固定非敏感测试→返回同一回执。后续定位只读回执/分类，不重复测试索费率。

## 后继准备
M03/PLAN_DRAFT.md已细化用户任务、单表count/sum/ratio契约、真实字段映射/人工发布版本、非秘密SQLite候选/风险/测试。仅草稿，没有激活或申请新依赖；需要M04-A范围审查/人工验收之后确认PLAN。M04-B仍LangGraph＋治理Harness与M02执行底座，不编造问数/SQL/JOIN已完成。

完整模型目录/同连接Key复用选模型仍D063 BACKLOG；PG生产/真实公网/历史Responsesfailed与不同rootauth候选门禁见remaining-gates.json，未改required或推为绿灯。
