# Responses第二切片审查

2026-10-29（Asia/Shanghai）；reviewer=self_review，不是独立审计/用户研究。
结论 **local_slice_pass，仅Responses候选适配切片；M04-A仍partial/not_verified，实际生成未验证。**

## 用户任务→实现→真实证据
- 用户不懂请求示例：已提取非秘密Codex参考，--model-key启动内置Responses候选地址/model；项目专用环境明确值优先。没有重读宿主配置/auth文件，没有复制宿主Key。只是候选，不表示应用授权/model映射/协议已实证。
- 两协议不能混用：openai_responses→ResponsesProvider；anthropic_messages→MessagesProvider；其他或协议/路径不匹配拒绝，无自动协议fallback/账号重试。共享受限传输、状态、费用准入，原36Messages专项保留。
- 请求隔离：Responses固定Bearer产品专用Key（协议候选）、仅model/input/max_output_tokens128/store=false/stream=false，不发送工具/历史/previous_response_id/数据行；请求身份/字段授权与SQL仍在后续治理，不按模型扩大数仓权限。
- 输出真实分层：仅completed response/model匹配、完成assistant message/output_text；忽略reasoning不输出，拒绝partial/queued/refusal/toolcall/模型映射错/空文本/坏JSON/超限/错误usage；未知用量None不是0，费用unknown；只读状态不能将fixture标verified。
- 安全：沿用非secretrepr/秘密正文反射拒绝、Key意外放model配置拒绝、字节/time/单并发/无proxyenv/无redirect/无自动重试，超时结果不明/取消不退款不重提；Node/Worker不继承。没有productionBudgetPermit仍请求前拒绝收费。
- UI候选：从真实独立API读协议/model/未配置Key、尚未实测、未验证；模型下拉空/禁用，不提供网页Key输入。原CSV/Excel/日期/100行/右多源/历史/显式黑白/Worker-retention路径完整回归。

## 实际检查
1. `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_model_provider.py services/api/tests/test_responses_provider.py -q`：79 passed，原36+43Responses，含2个实际本机HTTP正常/403请求。独立loopback地址映射仅测试，真实HTTP body/headers/parser；公司网关未调用。专项详细工具输出非本文件伪造rawlog，完整最终backend.txt有实际执行证据。
2. `services/api/.venv/Scripts/python.exe scripts/check.py --module M04-A --browser`：获批本机完整 **366后端（原287+79协议专项）/16前端/29网页**、types/build/pip全部退出0，当前source稳定。结果与manifest在20261029T025600Z。所有旧sharedprovider/dev/fixture相关323/28证据此前stale，本最终重跑不借用旧fp。
3. PRD一致性、5PRD守卫、26状态守卫及warehouse SQL/Parquet/golden verify退出0；GitCRLF兼容只读格式检查0。契约导出从Pydantic，未手改generatedTypes。没有新依赖安装。
4. 官方Responses create参考只读获取以核input/max_output_tokens/完成输出合同：https://developers.openai.com/api/reference/resources/responses/methods/create 。官方协议不是公司网关兼容/价目保证。
5. candidate-light截图视觉核验可见openai_responses/gpt-6.1-sol[1M]/缺Key/尚未实测，说明区独立滚动；开发走查非用户研究。

## 实际运行边界
客户端日期已为2026-10-29。启动前实际只读确认旧5173/8000无监听和健康不可用，不复用旧PID或exec；获批普通dev启动，无Key。当前API25260父24924、Vite14436父4260、CN1/luqianwu、10:57创建/loopback健康200；实际model/status200unconfigured、credentialfalse、verifiedfalse/models空。没有停止未知服务。本轮拥有exec92389仅本轮有效，新会话须重核。已加载新版状态，不再沿用“默认API旧版”历史描述；仍不是模型已连接。

## 保留未完成
- 用户自己hiddenKey实操not_run；请在自己终端隐输，不在聊天Key，不读取Codex/Claude认证。当前普通无Key默认服务，仅加载代码。
- 候选/v1/responses与model来自配置推导；实际协议/认证/模型映射未验证，real-model-apirequired/not_run。
- 15USD费用准入仍缺可核实项目专用供应商硬限额或完整真实计价/用量；production预算治理、真实最小test endpoint/回执、配置保存/启禁/授权模型目录、流式/structuredplan未完成。金额/网关/窄外发/PG后补已批准不重问。未知费用仍拒绝收费，不能从Codex能用推导本产品费用安全。
- M03/原M04=M04-B真实SQL/JOIN未实现；PG/正式身份/生产后补与高风险门禁保留。没有网关/公司数仓调用、宿主认证复制、用户数据删除、push或部署。

## 下一步
不再要求用户提供手写调用示例；请核实网关是否有专用Key的限额/计价页面，提供不含Key的页面/文档/脱敏截图，或由维护者向网关管理员确认。然后实现可靠费用准入与实际固定非敏感测试入口/回执。专用Key输入仍由用户自己本机完成。未齐费用证据时可准备配置/回执代码但收费保持not_run，不提前M04-A验收/进入M03。
