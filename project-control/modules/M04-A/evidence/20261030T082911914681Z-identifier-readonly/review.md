# 模型标识与只读诊断修复审查

2026-10-30，reviewer=self_review，非独立审计/用户研究。
结论local_slice_pass；M04-A仍partial/not_verified、实际model_mismatch未解决不标模型接通。

## 真实证据与问题
用户最新截图request358e4262-c36c-473e-a279-341b093ecc70：model_mismatch/returnedother_or_unreported/end_turn/thinkingtext/output11。不是认证或输出截断；旧固定3别名白名单过窄，诊断未提供确切模型。旧response原ID未保留，不能回溯。此次没有真实POST/Key读取/环境搬运/用户服务重启，不向用户保证再测试一定成功。

## 修复
- 新returned_model_identifier经<=120长度/安全字符/模型家族及Key/secretmarker排除，仅诊断元数据，非任意远程文本。未知/秘密形态仍withheld，旧enum仅兼容保留。模型ID可说明网关映射差异，但不自动授权模型/接受别名，strictmismatch继续拒绝。测试包含vendor/deepseek等非预猜版本ID和恶意Key/text，避免重复扩3个猜名单。
- 标准Messages thinking需要thinking及signature字符串、redactedthinking需要data，形状验证后跳过，不返回或存思考/签名；只有最终text输出。仅thinking/工具/partial/空文本/错误usage/128output超限继续拒绝。原非法thinking缺signature断言保留；标准合法thinking可独立通过，不为所有内容放宽。
- 新GET model-service/tests/{request_id}/diagnostics需现有身份/Origin边界，只返回UUID/status/error/safediagnostics/noSQL，不返回generation正文。不创建请求、预算或模型网络，未知当前UUID404，不跨重启找旧Key或自动重提。网页追踪里提供只读链接，后续助手读取元数据不需用户不断截图。旧回执不含rawID所以仍需更新后一次显式test获取，明确这个限制。

## 实际检查
136模型/预算专项passed（原125+11新的标识/思考/只读route tests）；完整scripts/check.py --module M04-A --browser **423后端（原287+136）/16前端/32browser**、types/build/pip全退出0、082912Z结果和source稳定。原安全断言/错误类型/预算不删skip，不因返回模型未知而接受任意ID。
新增只读route验证同UUID读三次只网络一次/预留一次、认证拒绝/未知404/no正文；浏览器原诊断路径补实际GET只读断言，不改变其他32路径。原model/private字符串测试继续保留旧enum隐私语义。Pydantic/OpenAPI生成Types，不手改；PRD一致性/5PRD/26状态守卫/仓SQLParquet对账0，格式检查CRLF兼容0。

## 限制/下步
用户当前旧进程Key不由助手搬运或停止。需本人CtrlC/Y、新start-workspace-claude.cmd隐输一次加载，然后仅一次显式test。新回执的只读安全诊断链接可给助手，GET读取本次observedidentifier，无收费重试。实际identifier与mapping证据确认后才能配置明确alias映射、版本绑定并复测；不能仅看名字有deepseek就当正确模型。
LangGraph+Harness不变，Key本机/窄外发/估算账本保留不reset；目录保存启禁/stream/SQLJOIN仍未完成，PG生产后补门禁不删，不closed。本轮无新依赖/部署/push或用户文件删除。
