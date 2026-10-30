> 用户已明确不采纳引擎变更，保留原LangGraph＋Harness（D-CLAUDE-ENGINE-058）。下方提案仅历史备选，不作为当前实施路线。

# Claude Code作为取数工作台Agent引擎：变更提案

2026-10-30；self_review；待明确方案选择，不是已接通。

## 配置提供的证据
CLI方式：ANTHROPIC_BASE_URL为coding-plan，ANTHROPIC_AUTH_TOKEN认证；rootbaseURL+apiKey的SDK示例是另一接入合同，不能把它们互换。顶层model和三个默认映射不一致；modelSettings出现claude-deepseek-v4.1-flash，而用户产品默认是deepseek-v4.1-flash。不得仅因modelSettings存在就认为它是实际授权modelID；需要最小实测/非秘密接口说明，不自动试多个别名绕拒绝。
本轮不执行提供的hooks、ada statusline、发现开关、长超时或自动继承CLI配置。密钥值为用户占位文本，不存入档案/代码、不请求真实值。

## 核心区别
当前ModelProvider是模型API薄适配，不是ClaudeCode的规划/工具循环。新需求是AgentEngine运行时。API薄适配可保留作为基础连接测试/回退，但不能将改baseURL后宣称底层是ClaudeCode。

## 推荐方案A：Claude Agent SDK引擎＋项目治理Harness
网页会话 → 后端任务/成本准入 → 受限AgentEngine适配 → ClaudeAgentSDK的规划/工具循环 → 仅本项目批准的MCP工具 → 服务端语义/SQL/字段权限/用户确认/预算门禁 → WarehouseWorker实际执行 → 固定回执与结果质检 → 工作台真实事件/卡片。
ClaudeCode承担规划和工具选择，不独自获得数据库凭证或执行权限；任何SQL仍须既有AST/只读/范围/粒度/JOIN/扫描/批准与幂等门禁。所有 tool-call 外发记录类型，不能让文件Read工具把用户表行、全历史或秘密绕过已批准窄外发。
禁止直接在项目源目录或用户HOME启动开放式CLI，禁止Bash/任意Read/Edit/网络插件和permission bypass。专用隔离运行目录/环境/配置，显式批准工具；不继承宿主hooks/MCP/历史/登录token。实际限制需OS/服务端实施，不能仅靠提示词或SDKpermission callback称沙箱。
主Agent循环采用SDK，不再同时装第二套自由循环。原M04-B仍原ID M04，但LangGraph首选方向需本次明确调整；项目Harness保留显式状态、人工确认、工具回执/幂等和恢复，必要外层图日后按需决定，不提前安装LangGraph。
第一切片只固定非敏感模型请求＋无数据工具的Agent运行，验证Windows/协议/费用/取消；再一个严格白名单MCP工具规划测试。不立刻让SDK自由读附件/执行SQL。

## 替代B：受控CLI非交互桥接
封装明确版本的claude非交互命令与结构化事件（协议须按版本文档验证），同样专用工作目录/环境/配置/工具限制，不连接用户已打开的ClaudeCode会话。初期可复用现有CLI安装但其许可/Windows/配置隔离仍要核实；不通过读/复制Claude宿主认证完成产品接入。事件/进程生命周期/输入输出限制要自己维护，比SDK长期服务集成更脆弱。

## 费用与安装边界
D053近似10-20USD已批准不重问；15USD目标/20USD软参考不是硬保证。现有0.25USD/128output单模型请求估算不适用于无限Agent循环：必须额外总turn/tool/time/output限制和每模型调用/轮次预留，未知中断保留，不能调用SDK一次只记0.25而内部无限调用。费用协议及SDK用量可信度逐项实测，默认短测试，不直接继承xhigh或50分钟超时。
SDK具体版本/许可证/Windows支撑及安装包需独立核查；本方案选择不是任意安装/费用扩张或生产部署授权，不能把当前Codex工具权限变成产品权限。

## 状态与顺序
M01/M02有限交付已验收保持，M04-A当前DO不得自动closed；M04-A先真实运行时最小连接验证，M03语义再原M04=M04-B治理问数。原PG/生产后补门禁保留，历史拒绝failed证据保留。未完成模型/SQL/JOIN仍未完成。
本轮仅写提案/脱敏发现，不变更产品启动器/默认模型、不收费、不安装/执行hooks/CLI、不处理服务。

## 官方核验来源
- https://platform.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/headless
两页本轮HTTP200实际读取；官方支持programmatic方式不证明公司网关兼容第三方DeepSeek工具协议/授权或许可证适用。
