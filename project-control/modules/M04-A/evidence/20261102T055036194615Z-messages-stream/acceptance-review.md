# M04-A Messages流式首切片自审

Reviewer=self_review。局部固定测试实现审查，不是独立审计/真实用户研究/模块验收。

## 用户任务与真实边界
在设置里显式同意固定非敏感文本与单次0.25USD估算，点击流式测试。上游请求stream=true，服务端严格解析Messages SSE并持有Key后缀以阻止跨chunk泄漏；页面500ms读取只读事件快照，无动画伪打字。短文本可能最后才安全释放。仅模型连接测试，不对业务问题生成SQL，不发数据行/全历史。

完成须message_start身份、blocks序列、message_delta合法停止/用量、message_stop与有界EOF都成立。缺结束、无输出、工具、不匹配model、坏编码、超限/断连/取消均不得completed；合法已释放文本保留partial，Key和thinking永不释放。同UUID读取不会发第二请求；预算跨Key/配置不reset，未知结果不退款。

## 代码治理
- ModelProvider.stream接口后是Messages薄适配，沿用httpx、SSRF/publicDNS/IP与固定批准私网目标，不安装新库/自由Agent循环。
- 15s墙钟，64KiB累计响应，16blocks/256events，128输出token上限，流式单请求busy＋全配置锁阻止换Key/启禁。
- 后台task/receipt最多60单请求、清配置/代际使旧回执失效。shutdown/取消回收task/锁；早取消callback保守failed_unknown。正常test与stream共用UUID排他命名空间。
- Stream能力仅当前配置有实测完成才verified，普通文本不推导stream；当前Responses/Chat Completions explicitly unsupported，不回退协议或批量调用。
- 回执/文本只后台sessionmemory，无secret历史/log/预算正文持久化。供应商错误只fixed代码；非敏感usage仅预算finish入账。

## 证据
28stream专项测试通过：网络分片/CRLF/Unicode、secret跨片段、thinking丢弃、tool拒绝、model/stop/EOF/usage/次序、401/403/429、编码/超限/超时/断网、sameUUID预算、cancel/busy/shutdown/无凭证无收费。之前80model-budget组合及1真实产品API浏览器流式固定测试通过。独立实际TCPHTTP/SSE loopback检验通过，不是企业网关/TLS验证。完整回归结果另附，未通过前不能标最终局部pass。

## 实际服务与门禁
只读核查当前真实运行glm-5.3 model_name_editable=true、生成已验证并启用，与用户“完成模型修改”一致；不看Key、不读模型正文、不发POST。当前真实API缺stream_management，因此尚未加载新stream代码。user本人加载新版后显式一次固定stream才能补真实网关AC02，不自动重启/搬Key/收费。

AC01网页模型修改非流式当前成功回执可确认，但完整clear/edit/启禁生命周期及跨生产身份不能从该状态推导。历史Responses失败与另root/x-api-key候选门禁保留。真实公共供应商/TLS、生产/PG仍required/not_run。整体验收仍partial/DO，M03只低风险准备，不能跳到M04-B或宣称MVP完成。

## 今天MVP路径
先补实网关流式和当前M04-A范围审查/人工验收；再M03批准语义最小包，之后M04-B LangGraph＋治理Harness实际模型规划→权限/SQL/人确认→M02执行→结果质检。B-MODEL-CATALOG-001一键网关模型目录/复用Key作为后续待办，不占主干，也不暗自扫描网关。时间目标不是免验收或生产数据授权。
