# 已绑定网关思考元数据兼容审查

2026-10-30；reviewer=self_review（不是独立审计/用户研究）。结论local_slice_pass，M04-A整体partial/not_verified，新真实生成待用户更新后显式测试。

## 实际问题
用户32a14cea回执由授权GET实际200读取，仅安全字段：unsupported_content、deepseek-v4-1-flash-261017、end_turn、thinking/text、input49/output17。代码此阶段已通过exactaliasmodel检查，model_matchesfalse只是词面名字不同。原body/字段没有保留，因此无法证明实际signature缺失，不能声称读取过原思考；问题是在不需要回放/验证签名的网关思考元数据上施加原生signedClaude格式约束。

## 修复与边界
仅对完整已观察gatewaymapping的observed_gateway_alias分支，thinking/redactedthinking当不透明元数据直接丢弃，既不解释字段、不展示、执行、回放或保存思考/签名。整个response64KB和16块上限、完成状态、精确modeltuple与返回版本、最终text字符串/非空/长度/secret检查、usage及128output上限保持。其他模型和原生exactmodel的thinking形状规则保留；未知工具、仅思考/没有text、partial、错误text类型、Keyecho仍拒绝。新增diagnostic.model_binding显示exact/observed_gateway_alias/unmatched，不混淆词面model_matches。
这不是忽略模型权限或全部内容校验，而是针对已观察的隔离元数据停止无意义的格式依赖。预算账本/请求路径/auth/Key处理未变，无自动retry或费用扩张，LangGraph＋Harness保持。

## 实际验证
157模型专项passed（原150+7新gatewayopaque分支反例），完整scripts/check.py --module M04-A --browser **444backend（原287+157）/16frontend/33browser**、types/build/pip全部退出0，085625Z/results.json和source稳定。原工具/非gatewaymalformedthinking拒绝断言保留，未删skip；新测试覆盖无signature、字段差异、空thinking、redactedobject只丢弃且最终text必须有效，以及仅thinking/tool/secrettext拒绝。
浏览器已有observed-aliasfixture改为无signature思考，实际产品路由和MockTransport生成测试OK，双modelID、思考不回显、同UUID1预留/noSQL验证；不是公司网关本次success证据。PRD一致性/5PRD守卫/26状态守卫/warehouse SQLParquet对账0，Pydantic/OpenAPI生成TS、格式检查CRLF0，无新包安装。

## 未验证与下一步
本轮仅真实GET用户已有diagnostic，不读Key/环境/响应正文、不停止用户持Key进程或发送真实POST。旧运行代码不热加载，用户本人CtrlC/Y、新start-workspace-claude.cmd隐输一次、网页刷新后显式test取得新真实结果，不能把旧失败回执改成功。若失败给只读链接继续GET，不自动换model/协议/扩大token。
真实模型未成功、目录保存启禁/stream/语义/SQLJOIN未完成，M04A不closed或跳M03；PG/生产后补required门禁不删。默认DeepSeekAIPlan支持用户已确认，产品integration仍需actualreceipt。估算累计不是实际账单，保持同ledger不reset，未部署/push或删除用户文件。
