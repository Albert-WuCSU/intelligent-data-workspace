# Claude Code风格接入套餐切片审查

2026-10-29；reviewer=self_review，非独立审计/用户研究。
**local_slice_pass，M04-A仍partial/not_verified。** 本轮是D-MODEL-CLAUDE-PRESET-054用户主动纠正协议/签发平台并授权从截图选择默认model，非Agent遇拒绝后自动更换协议/账号/模型绕权限。

## 用户任务与实现
- 用户提供签发平台ada-config并要求如ClaudeCode；选择claude-haiku-4-5（截图及既有非秘密Claude映射一致），单独start-workspace-claude.cmd/package：anthropic_messages候选/v1/messages、Bearer认证（ANTHROPIC_AUTH_TOKEN-style）、专用本机隐藏Key，预算估算许可。没有复制Claude/Codex令牌或配置文件，没有打开含Key控制台页面。
- Key字符串不能证明协议或权限；套餐基于明确用户选择和此前非秘密字段的合理候选。传统Anthropic x-api-key仍支持，Responses入口保留，无自动header双发、fallback、重试或权限绕路。若控制台实际给ANTHROPIC_API_KEY需按其非秘密合同确认，而不是自动猜Key类型。
- 套餐显式绑定全部非秘密字段，覆盖冲突Responses环境但不继承宿主Key；authmode加入配置version，旧执行上下文/请求不能跨新协议重提。显示协议/auth/model及未验证，模型问数目录仍空，不拿候选名当授权成功。
- safeupstreamstatus在401/403拒绝回执显示数值，不回传remoteerror正文/Key，仍固定MODEL_ACCESS_DENIED。幂等同UUID复读不重提，不改变预算预留；错误后不自动换模型。固定non-sensitive短test/noSQL/窄外发与原Worker/文件/数据源限制不变。
- 两入口共用现有0.25USD预留/60次/15USD目标/20USD软参考账本，不因model/Key或协议切换清零。实际费用unknown，旧0.50USD保留预留不是账单。

## 实际检查
`services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_claude_preset.py services/api/tests/test_model_provider.py services/api/tests/test_responses_provider.py services/api/tests/test_model_budget.py -q`：103专项退出0（原95+8新套餐/401/403），假Key/临时账本/HTTPfixture。
`services/api/.venv/Scripts/python.exe scripts/check.py --module M04-A --browser`：**390backend/16frontend/31browser**及types/build/pip全部0，084030Z/results.json。新31browser含显式Claude套餐协议/auth/Haiku与401安全拒绝，不输出原错误body/不自动fallback，fixture不当公司API实证。
后只WorkbenchPanel旧“仅Responses候选”静态文案改协议中立；所有backend/tests/contracts/locks字节一致，最终16frontend/types/build/全部31browser重跑0，最终results-final.json有原390backend真实指纹复用说明，不称再次backend运行。
PRD一致性/5PRD/26状态守卫/warehouse SQL+Parquet对账0，生成TypeScript来自Pydantic/OpenAPI，非手改；无依赖安装。预算四进程测试此前证据保留，ledger未变，本轮不冒称再次运行。最终页面截图候选Messages/bearer/Haiku/未验证/固定401拒绝和估算，selfwalkthrough非用户研究。

## 真实运行与未完成
本轮未执行网关POST、未读Key/env/认证文件、未停止持Key进程，旧实际GETstatus仍openai_responses/gpt61/Keybooltrue/verifiedfalse/0.50USD估算2预留；新Claude方案尚未被用户隐藏输入加载与实测。旧real-model-api失败证据保留，新增real-claude-model-test为required/not_run，不能以换入口称成功。用户本人CtrlC/Y旧窗口后用newclaudecmd重新隐输，在网页确认协议/auth/model并显式点击test才收费；如仍401403需签发平台权限/非秘密authcontract排查，不拿宿主令牌或账号绕拒绝。
M04-A配置保存编辑启禁/授权目录/流式未闭环，M03/原M04=M04-B SQL/JOIN未实现，PG/生产后补门禁未删，不closed。当前仍开发固定身份/内存testreceipts/非秘密估算ledger，不宣传生产秘密/跨租户/硬费用保险。

## 用户可操作交付
入口start-workspace-claude.cmd（不是旧start-workspace-model.cmd），默认候选claude-haiku-4-5。MODEL_SERVICE.md说明重启/隐输/查看auth和状态/401403反馈；不能请求聊天Key或粘Key截图。最后一次测试前先确认页面模型为Haiku；加载原Responses入口时仍旧gpt61。新候选仍可能model别名映射/认证拒绝，未验证不自动放宽校验。
