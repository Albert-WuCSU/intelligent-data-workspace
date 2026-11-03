# M04-A 会话目录切片自审

Reviewer: self_review（非独立审计、非用户研究）。模块整体结论仍 partial / DO，不能验收关闭。

| 用户任务 / PRD | 实现与证据 | 剩余门禁 |
| --- | --- | --- |
| AC01 配置/测试/刷新/编辑启禁 | 当前单配置/本机身份，后台sessionmemory；显式测试后启用，换Key/禁用/清除后旧目录ID与测试失效；真实产品API＋隔离假Key/MockTransport浏览器链路通过 | 用户加载新版后的真实网页Key实操、公网真实账号；永久Profile/秘密存储未批准，不能声称完整生产配置 |
| R-U25 输入区模型选择 | 目录仅后端实测/启用项；选择不收费；代际/配置版本变化清选择，服务端resolve再核；明确问数未接入 | 仅一个当前实测配置；M04-B计划绑定与真正调用尚未实施 |
| AC02 流式 | stream/tool/structured/query能力全部false；未提供假流式按钮 | Provider.stream、真实服务事件、部分输出/断流/取消与UI验收 not_run |
| AC03 费用 | 预算沿用，不因Key/启禁/厂商清账；耗尽不提供可用目录 | 0.25仅估算，非实际单价；无硬成本保证 |
| AC04 权限/秘密 | 本机主体由服务端决定，拒绝伪版本/代际/角色、跨Origin、超大body；Key不回显、前端存储未包含fixtureKey | 生产身份/跨租户/TLS/秘密管理 not_run；公司授权不继承到未知厂商 |

正常路径、独立fixture刷新、禁用恢复、黑白主题与手机无水平溢出在浏览器走查/回归覆盖。截图为开发自测，不能称真实用户研究。后端旧默认服务保持不变，无真实厂商调用、SQL或JOIN。

保留历史Responses实际401/403 failed以及非当前root/x-api-key候选 not_run，按协议/当时版本归档，不改写成功；当前AIPlan Messages/Bearer DeepSeek最小真实文本成功只是其独立证据。
