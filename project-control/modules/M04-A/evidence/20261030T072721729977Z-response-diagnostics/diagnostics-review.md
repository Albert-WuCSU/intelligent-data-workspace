# 响应安全诊断切片审查

2026-10-30；reviewer=self_review，非独立审计/用户研究。
结论local_slice_pass，仅固定安全分类诊断；M04-A整体partial/not_verified，实际最新模型test failed保持。

## 已观察与边界
用户实际反馈MODEL_RESPONSE_INVALID。本轮只GET安全modelstatus，实际Messages/Bearer/deepseek-v4.1-flash/keybooltrue/verifiedfalse/估算1.50USD6预留。当前Messages返回此码只有HTTP200后编码或解析未过校验，不代表文本生成成功/工具调用兼容。旧错误没有具体原因/原响应未保留，不能回溯认定modelalias、128截断或thinking根因。
本轮没有真实POST或Key/环境/命令行读取、用户持Key进程停止，没有为诊断自动再次收费。

## 实现
ModelResponseDiagnostics仅固定reason、model_matches布尔、固定stopreason/contenttype白名单及有界有效token。未知远程字符串只other，不输出原model、正文、thinking、Key或header；模型名不匹配/partialoutput/unsupportedcontent/坏JSON/usage/secretEcho/输出超限各自拒绝，不放宽原完成/模型/128输出/工具禁用。原Responses解析不变，公共响应限制保持。
ModelTestReceipt新增可选diagnostics，错误不修改为成功；同UUID保持一回执一预留，用户重复读取不自动重提，跨重启generation拒绝。前端显示分类和安全值、不回显partialtext；需用户更新服务后一次显式test采集真实分类，成本按0.25估算保留。没有增加输出/换model/认证fallback。LangGraph＋项目治理Harness方向保持。

## 实际检查
122模型/预算/诊断专项退出0（原109+13诊断）；完整命令scripts/check.py --module M04-A --browser：409backend（原287+122）/16frontend/32browser、types/build/pip全部0，072722Z/results.json，sources稳定。原安全断言/预算测试未删skip放宽。Types由Pydantic/OpenAPI导出；初可选contenttypes类型错误修默认空数组后最终编译0。
新浏览器使用独立当前产品API+MockTransportpartialfixture，固定diag incomplete_output/max_tokens/128、禁止partialbody泄露、同UUID预算仅1验证；不当公司网关实际根因证据。页面截图已视觉核验模型DeepSeek/未验证、固定安全诊断可读；旧下方Haiku说明是既有残留，下一UX清理需改为当前model，不作为本次默认模型或调用证据，真实默认仍DeepSeek。
PRD一致性/5PRD守卫/26状态守卫/warehouseSQLParquet对账退出0，GitCRLF兼容格式检查0。无依赖安装/推送部署或用户数据删除。默认服务没有重载，Key不能由助手搬运热加载。

## 下一步
请用户本人CtrlC/Y原窗口、新start-workspace-claude.cmd重新隐输Key，网页一次显式最小test后复制diagnostics字段即可，不发响应原文或Key。model_mismatch需要实际网关映射证据再评估允许绑定，incomplete_output需实际截断证据再评估受限输出预算，unsupported_content需按协议类型设计；不靠猜测放宽。
实际test未成功，M04-A还缺授权目录/配置保存启禁/stream等，不closed/M03。PG/生产补验门禁不删，预算预留非实账/非供应商硬保证。
