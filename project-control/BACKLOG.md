# 产品待办（来源与未验证边界）

## B-MODEL-CATALOG-001｜AI Plan 网关模型目录＋工作台一键切换（D063）
用户2026-11-02提出并同意列入待办：不每换模型重输model/Key，应在输入下拉直接选择网关支持且账号有权用的模型。
- 先核实官方/获批网关模型目录接口；不可猜测/v1/models或批量试调用。目录advertised与account-authorized与generation-verified分开，不假造完整模型清单。
- 同一批准endpoint/auth绑定当前后端内存Key，切换只更新model/version，保留预算/启禁/失效语义，不把Key交给浏览器或新供应商。
- 需要多模型能力回执与请求绑定，未实测选项明确需要验证，不自动批量收费。返回未知model版本仍exact拒绝，别名需证据。
- 跨重启免输Key依赖秘密持久化新决策，当前不做；当前单会话配置与手动model仍可用。
- 该项状态：backlog，接口/账号scope未核实，不作为今天主干取数Agent阻塞；当前先M04-A流式→模块审查验收→M03→M04-B。
