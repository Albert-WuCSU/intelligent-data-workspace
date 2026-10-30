# 通用个人BYOK首切片交付审查

2026-10-30，reviewer=self_review，不是独立审计或用户研究。
结论local_slice_pass；M04-A整体partial/not_verified，真实个人厂商/新网页输入实操/授权目录/stream未验收，不提前进入M03。原用户AIPlan最小文本成功证据保留，真实SQL/JOIN仍未完成。

## 用户任务→实现
个人接入：模型服务→厂商预设或自定义协议→完整API地址/model/passwordKey→同意固定非敏感测试用途/估算→保存连接（不收费）→显式最小测试。OpenAI/DeepSeek官方/Anthropic预设可编辑，公司AIPlan只是可选且exactprivategrant。预设不自动证明模型存在、账号授权、别名映射或协议兼容。特殊私有协议不是“所有厂商已支持”。
只接入标准Responses、OpenAI-compatibleChatCompletions、AnthropicMessages文本合同；Key在浏览器瞬时输入和POSTbody，SecretStr验证错误不会反射Key，提交成功/失败后字段清空，不存localStorage/sessionStorage/history/日志/文件。后台只本次memory，clear及replace不需重启，不复制宿主认证。Python内存不是可保证物理擦除的生产secretstore，浏览器密码管理器行为不由应用保证，用户不得截图/共享秘密。
API POSTconnection和clear需已有loopback固定开发身份/Origin/CSRF，接收secretbody前认证并8192byte限额；completepreset固定私网地址，custom只HTTPSpublic。配置锁/actualinflight拒绝换Key和clear，生成新runtimegeneration失效旧test，失败不破坏oldKey；配置/厂商变化清旧验证，不resetbudget。首次加载新代码需要用户本人重启自己的旧服务一次，之后配置变更不重启。

## 安全和费用
自定义地址拒绝userinfo/query/fragment/非HTTPS/非法port/localhost/privateliteral/内部域/不符协议后缀。请求前解析所有DNS地址要求global，实际TCP使用一次验证后的IP，原Host和SNI保留TLS认证原域名，不在validate之后重新DNS连接任意地址；retries0、proxyenvfalse、redirectsfalse。返回类型/内容字节/总时限/输出token/model对应仍受控。内网AIPlan只已批准exactpreset，不能用custom绕SSRF扩大到privatehost。
测试允许显式注入独立transport，产品接口不接受transport/解析器/预算参数；TLS/真实publicsupplier联网实测仍not_run，只有内部httpcoreSNI代码契约核对和真实fixture产品路由验证，不冒称所有公网厂商TLS兼容。正式多人账户/租户/域权限和HTTPS部署仍门禁，当前loopback开发版本不发布公网。
用户单独接受当前固定非敏感test和0.25USD估算启发式；这不是套AIPlan历史为其他厂商真实价格。每个provider同一campaignledger最多60/15USD估算target/20USD参考，未知失败不退款，不因clear/model/provider换而reset；实际账单unknown，后续厂商价格/上限仍需相应治理。没有普通聊天数据行/历史/截图发送，新供应商只用户明确固定test文本。

## 实际验证
182初模型/预算/SSRF/connection专项passed，后追加2defaultauth/inflight案例，通用connection27专项passed。
最终 scripts/check.py --module M04-A --browser：**471 backend（原287+184模型/预算专项）/16frontend/34browser**、types/build/pip全部0；093324Z/results.json/sources稳定。原文件/日期/noFilter、黑白、历史、多源/附件、Worker/retention所有路径回归。
通用浏览器真实productAPI保存/清除，独立MockTransport模型fixedtest，Keypassword字段/提交清空/storage不含fixtureKey、save费用基线不变/test+1/clear不reset、invalidstates/手机无溢出通过。不用fixture标用户真厂商connected。
首469/16passed/34browser33过1是新test错误假定sharedfixtureledger从0开始；改保存不变baseline、测试和clear后baseline+1，保存计费/不reset安全语义保持，不清账/skip放宽。defaultChatprotocolauth显示错误经selfreview修Bearer，真实asyncinflightsaveclear409测试补证；当前全471再次实跑覆盖修复。
PRD一致性、5PRD守卫、26状态守卫、warehouseSQL/Parquetgolden对账0，PydanticOpenAPI导出TS无手改，格式CRLF兼容检查0。没有新依赖安装。

## 当前默认运行和Git交付
本轮不读取真实Key/环境/密码字段、不自动POST真实厂商、不停止用户持Key服务。普通defaultAPI还未加载connection新路由，网页报告connectionmanagement能力缺失时禁Key提交，用户需本人CtrlC/Y/new普通start一次加载，再直接网页configure；此后不需终端Key/换provider重启。
用户授权开发后同步所有当前改动到现有私有GitHub；此前几十轮local变更并非已push。先stage前candidate约2053files/129MB无高置信token/私钥/JWT、无forbiddenruntime/toolpath及>95MB单文件；是有限pattern检查而非全面DLP保证。实际暂存blob复检及commit/push后远端SHA核验仍待执行。data/model-runtime、data/connections、tmp、.codex/.agents/.aws、Keyfiles忽略保留不上传不删除。原同Git仓ADMIN/private读核，不改全局safe.directory，仅命令指定本repo以处理沙箱所有者差异。公开展示公司配置/截图/真实数据需另审，当前只私有同步非秘密源码/开发证据，不是部署或模块验收。

## 下一步
完成stage安全扫描/commitpush用户授权后，让用户本人加载新后端一次，网页厂商→passwordKey→save→test验证新路径。通用真实个人供应商账号调用not_run，M04-A还需授权目录/流式/配置持久元数据与实际test验收；LangGraph+Harness保持，M03/原M04B查询JOIN与PG生产后补门禁保留。
