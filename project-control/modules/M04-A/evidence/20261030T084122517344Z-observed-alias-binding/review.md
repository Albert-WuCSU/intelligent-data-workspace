# 实测精确模型别名绑定审查

2026-10-30；reviewer=self_review，非独立审计/用户研究。
结论local_slice_pass：代码支持已观察的网关版本别名；M04-A仍partial/not_verified，需要更新后真实新回执，不将历史failed改success。

## 证据与修复
实际GET用户给诊断URL，requestd94d4bec-d45d-4519-a3c5-530f6ab5a686、HTTP200返回安全字段：请求deepseek-v4.1-flash收到deepseek-v4-1-flash-261017，end_turn、thinking/text、input49/output16。无读取Key/响应正文/思考或重新模型调用。既有标识差异是版本化网关路由，不依靠猜prefix匹配；一条实际观察支持一条exacttuple映射。
ModelConfiguration.observed_response_alias仅完整http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages、anthropic_messages、bearer、deepseek-v4.1-flash对应deepseek-v4-1-flash-261017。别的地址/auth/model/版本不接受。版本fingerprint纳入mapping，旧context请求拒绝不重提，原失败receipt保留。
ModelGeneration保留请求model_id、returned_model_id与model_binding=observed_gateway_alias，不静默统一名称；模型目录或SQL权限不随之提升。标准thinking/signature及redactedthinking形状校验后丢弃不返回/持久化，最终仅text。未知模型仍mismatch，tool/partial/空文本/secrettext/输出token上限/usage检查不变。Responses仍其独立严格合同，预算同账本不reset。

## 实际测试
150模型专项退出0（原136+14exactmapping反例/receipt tests）。完整scripts/check.py --module M04-A --browser：437backend（原287+150）/16frontend/33browser、types/build/pip全部0，084123Z/results.json、sources稳定。没有删skip原断言，精确alias已凭真实元数据证据修复而非任意宽化。
反例覆盖新日期261018、claude前缀、其他auth/根URL/其他path/model、partial/tool/Keytext；成功receipt双ID，重复UUID和GET只网络一次。新增浏览器fixture是独立产品API+MockTransport匹配已观察元数据并生成fixtureOK，不是公司网关新成功实证。视觉核验双ID/bindingmode/OK、不显示思考签名、SQL未执行，原附件/日期/noFilter/主题历史多源/Worker-retention全部33路径回归。
PRD一致性、5PRD/26状态守卫、warehouseSQL/Parquet对账0；Types由Pydantic导出，格式检查CRLF0。无安装/推送/部署/用户数据删除。

## 运行和下一步
此次不停止用户持Key窗口、不迁移秘密、不发真实POST。旧运行代码仍拒绝alias，需用户本人CtrlC/Y、新start-workspace-claude.cmd隐输更新后一次显式最小test，才有新真实success或安全失败诊断；只读链接可继续GET，旧失败不能回写。网关模型版本将来变化应重新验证，不自动regex接受新日期。
当前仅最小生成测试、模型目录保存编辑启禁/流式以及M03/原M04B SQLJOIN还未完成。保持LangGraph＋治理Harness，PG/生产后补required门禁保留，近似预算目标15/参考20非硬保证，估算预留不退款或reset。
