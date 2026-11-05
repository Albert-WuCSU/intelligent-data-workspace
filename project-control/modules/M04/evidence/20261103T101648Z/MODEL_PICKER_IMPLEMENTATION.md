# 2026-11-03 多模型目录与工作台选择器首切片

决策：D-M04B-MODEL-PICKER-075  
需求：R-U30 / R-A07 / R-P26  
状态：首切片实现并通过本地回归；真实网关 Web 调用仍 not_run

## 实现内容

- M04-A 连接层保持单连接/单Key/单base URL；同一连接下新增服务端多模型目录。
- 新增模型注册：`POST /api/v1/model-service/connection/models`；移除：`/connection/models/remove`。
- 每个附加模型独立测试/启停：`POST /models/test`、`POST /models/enabled`；各自有独立验证状态，不共享“已验证”标记。
- catalog 返回主模型+附加模型，条目包含 model_id、source（personal_api/ai_plan）、default、enabled/available、generation_verified、stream_verified、context_window（未知为null）、price_status/price_note（未知）、note；不自动枚举网关模型。
- 选择解析：`resolve_catalog_model` / `resolve_bound_model` 支持主模型和附加模型；Agent 任务按 catalog 引用重新解析 provider，模型变更使旧计划/确认失效。
- 工作台选择器重写：按钮+可搜索弹层、按个人API/AI Plan分组、显示模型ID/状态/默认标识/未知价格/未知上下文；键盘/窄屏/黑白主题；选择不调用模型。
- 设置页新增“模型目录”管理：添加模型ID、独立测试（每次$0.25估算、显式勾选）、启用/禁用、移除；不要求再次输入Key，不使用浏览器存储Key。
- MVP默认：选择公司AI Plan预设时预填 `deepseek-v4.1-flash`（可编辑）；服务端默认模型可用时选择器自动选中。

## 验证证据

`project-control/modules/M04/evidence/20261103T101648Z/results.json`

- 606 后端通过（含新增多模型 registry 测试）
- 19 前端通过
- 44 浏览器通过（既有 remote-onboarding 测试已改为使用新选择器 helper，未放宽断言）
- types / build / pip check 通过
- 浏览器覆盖：模型选择、设置页保留、输入可用性、移动端无横向溢出；未新增真实模型调用

## 边界与残余

- 未实现网关 `/v1/models` 自动发现；用户需手动添加 model ID 并逐个测试。
- 价格与上下文没有真实来源，catalog 显示未知；不复制截图中的第三方模型/价格/Effort/Ultracode。
- 当前 Web 问数仍是既有 Agent 路径；选中模型已进入该路径的 provider 解析。Claude Agent SDK runner 尚未接入 Web/默认业务 API。
- 单连接多模型；多个并行连接/多租户/生产秘密存储未实现。
- 真实 DeepSeek Web 端到端、真实 Claude、生产与 SDK 官方兼容均 not_run。
- 附加模型与主模型共享同一连接Key/端点/预算；更换连接会清空附加目录并失效旧选择。

## 下一切片

1. 将选中的模型绑定到 SDK runner / 默认 Web 问数路径，保留同一 catalog/选择合同。
2. 可选：受控、用户显式触发的网关模型发现（advertised/authorized/verified分离）。
3. 价格/上下文元数据仅在真实来源可用时展示。
