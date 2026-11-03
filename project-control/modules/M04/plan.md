# M04-B PLAN｜LangGraph＋治理 Harness 的真实问数闭环

状态：用户已确认D-M04B-PLAN-INSTALL-069，进入DO；项目依赖已按哈希锁安装。保留原progress ID `M04`、cycle `M04-C01`，不建重复Agent模块。依赖M01/M02/M04-A/M03的既有本机验收范围，全部生产/PG/公网/历史协议失败门禁保持。

## 1. 用户任务、默认路径与可观察标准
业务用户在已接受的会话工作台，用自然语言提出指标问题，选授权模型和数据范围，必要时确认口径，拿到来自真实完整查询的数字与证据，而不是开发预览。分析师维护知识库/关联；管理员维护模型/来源；开发者只在折叠技术区查SQL/回执。
最短路径：输入问题 → 找到并重新校验已批准语义/实际字段 → 受限模型计划 → 澄清或口径卡 → **用户确认执行** → 真MCP/Worker执行 → 结果质检 → 结构化结果卡。计划前须可见“问题/必要字段将发给所选模型”的明确动作与预算说明；保存设置/读取状态/选择下拉不调用模型。
可观察标准：同一独立测试表>100行，提问数量/求和/比率，结果与全表SQL金标准一致而非前100行；错误、缺槽和旧模型/语义版本不能导致执行；用户等待确认时刷新/重复提交不能产生第二次SQL。

## 2. 现状与安装核验（已查，不是已实现）
- LangGraph `1.2.19`（2026-10-30发布）、MIT，Python>=3.10。当前Windows AMD64 CPython3.12.14环境匹配；PyPI轮子SHA256与MIT LICENSE已核。
- `pip install --dry-run --only-binary=:all: langgraph==1.2.19` 退出0，**26个新增包、0个现有包替换**。完整候选pin/hash见evidence/20261102T084251541800Z-plan-investigation；无实际安装/运行验证。
- 必须传递依赖包含langchain-core/checkpoint/prebuilt/sdk以及langsmith包。仅使用StateGraph/明确节点/本机checkpointer，不使用prebuilt自由工具Agent，不启用LangSmith tracing、云SDK/遥测，不继承LANGSMITH/LANGCHAIN/宿主Key/env。安装包存在不等于允许发送外部日志。
- 新包许可证声明：MIT、BSD、Apache-2.0等；orjson为MPL-2.0 AND (Apache-2.0 OR MIT)。分发物保留许可证，若改动MPL覆盖的库需另审义务。首安装按已核wheel哈希锁，项目venv内，不全局升级pip/SDK；pip check/Windows import/无网络graph smoke/全基线回归后才能称兼容。
- 实核M02的PreviewRequest/ExecutionService/SQL AST只SELECT列＋LIMIT。不得更改原导航预览成任意查询，更不能求前100行的和冒充总体；聚合能力需要新的明确MCP请求/回执与adapter capability合同。

### 技术比较
推荐：LangGraph显式有限图＋自有ModelProvider/SQL/Worker治理。优点是中断/状态路由可审计，不重写MCP；代价是新增26包与图版本维护。备选是继续自写状态机：无新依赖但背离已选图编排方向，必须用户新变更才采用。无第二套CLI/AgentSDK、无完整LangChain Agent循环。

## 3. 模块完整范围与切片顺序（不是只做最容易通过的一条链路）
模块仍对照M04-B AC01–04与R-P01/P06/P07等：授权路由、澄清、LangGraph可观测节点/interrupt、真实生成与执行、SQL/结果质检、幂等与异常、UI恢复、依赖安全。不能将首切片完成当整个模块/MVP完成。

### C01：首先完成可演示的单表L1主干
1. 安装并锁定已核LangGraph，零外部trace/env继承；实现有限graph states/typed nodeoutputs/递归与墙钟上限。
2. 模型绑定当前启用/实测provider的config_version＋execution_generation，语义必须latest/启用且resolve重新核实际sourceversion/schemahash/state_revision。只发问题与本请求必要的字段/metric/grain/time说明，不发数据行/全历史/供应商secret/原件路径。任意注释/语义文本都是不可信数据而非策略。
3. 模型输出受限JSON `metric_id / dimensions / approved_time_filter / needs_clarification`，不让模型选租户、执行器、SQL权限、路径/命令/工具/网络地址；只接受已授权候选。第一步保留128输出token/2000输入字符现有provider硬界限；受限上下文无法装下则要求缩小范围/澄清，不静默truncate语义或放大预算。复杂步骤需要新的明确子方案而非为通过放宽。
4. 确定性编译批准的count_rows/sum/ratio表达式，字段/表均来自MCP实际元数据、方言与白名单；SQLGlot单SELECT AST检测、参数化时间边界、禁止注释/多语句/DDL/DML/UDF/外部文件函数/扩展加载/任意SQL。用户看到口径/范围/单位/预算/限制，SQL折叠可查。
5. 图human interrupt产生明确不可变plan hash，确认绑定model/semantic/source全部版本。恢复确认时重查，版本改变/停用/时间歧义/缺关联不执行。模型一请求最多1次generate、无自动repair/retry；错误可用户显式另发新问题而不是后台重提。
6. 新增 `workspace_aggregate_v1` **受限聚合合同**，只服务器拥有的local文件/独立自有仓路径；输入不是浏览器任意SQL。复用OwnedMCP/WindowsJob/worker/token门禁，旧6-tool HTTP导航适配不增加工具/能力声明。聚合请求经服务端编译与执行端再次检查，一致hash/权限/schema版本才执行；不绕路用直接SQL或preview。
7. 执行必须全符合过滤的记录求聚合，基数/空值/重复grain/分母0明确质量检查；执行器硬上限输入行数200000（当前来源快照导入仍原20000行更严格上限，不能为聚合自动扩大）、已支持快照20MB上限、输出分组<=100、结果字节<=200KB、Worker原有内存/CPU/15–20s墙钟；超限拒绝/partial不发完整结果，不把LIMIT前100用于aggregate输入。输入行数检查本身在受限Worker内，成本/时间真实上限，不声称服务费保证。
8. API request UUID/owner/代际/planhash/单向状态，确认后提交tombstone置位；结果不明保留同幂等键/不可自动重提。Graph replay不在irreversible提交节点做同一SQL两次；Worker/MCP同一owned上下文回执＋API tombstone共守，重启旧会话计划失效（M05前不声称磁盘任务恢复）。不把LangGraph checkpoint叫恰好一次保证。
9. 输出真实columns/rows/units/QA/semanticversion/queryreceipt/modelbinding结构化卡；pipeline绑定node/实际回执，不计时动画。没有下载资产/持久文件时不造下载按钮。M05提供资产与正式历史；M06/07随后提供图表报告。

### 后继C02/C03（仍属模块范围，首切片验收不等于全闭环）
- L2字段/表导航模板与L3受约束探索路由按真实metadata/权限/语义条件扩展，L4明确目标入口；不支持的归因/建模/实验请求明确未接或路由到其待实施模块，不乱给计算/因果结论。
- 同数据库多表JOIN需要M03加入明确关系keys/cardinality/grain合同、授权来源、粒度膨胀/守恒与重复键检验，再扩展聚合AST/MCP请求。不根据用户UI多选、相似字段名或modelfamily自动JOIN。
- 跨源融合、旧HTTP导航/PG/Spark/Hive扩展必须有实际adapter capability/身份/取消/成本/方言证据与新授权；缺能力拒绝，不借另一账号/路径绕过。本机单数据库完整执行可首先实证，真实生产/PG原延期门禁照旧。
- M03首切片只有单表语义，与此路线依赖一致；关系扩展在该具体切片进入前写变更与审核，不伪装已实现。

## 4. 状态/契约与产品信息层级
拟 `AgentRequest{question, model_ref, semantic_version?, selected_source_refs, request_id, accept_model_egress}`；`AgentTask{owner-derived, phase, versions, plan_hash, events, receipt, result/quality}`；`ConfirmPlan{task_id, plan_hash, expected_generation}`，客户端不传tenant或权限。所有schema用Pydantic/OpenAPI生成TS，禁止手改。
状态：NEEDS_CONTEXT / PLANNING / NEEDS_CLARIFICATION / AWAITING_CONFIRMATION / VALIDATING / EXECUTING / CHECKING / SUCCEEDED / PARTIAL / FAILED / UNKNOWN / EXPIRED。请求开始不是SQL已执行；旧消息/历史本机文字不是有效结果或新请求进度。
输入区模型可选真实启用目录；来源/语义选择和缺项提示在右侧摘要轻量化，管理员设置/知识库页面保持独立。不再往默认业务区放JSON/连接表单。支持黑白主题、历史/多轮、新会话隔离、键盘/手机、取消/失败有效下一步。模型费用仍D053原估算15USD目标/0.25每次/60次/20软参考，不重问费率或偷偷reset。

## 5. 网络、费用与存储授权边界
- 详细PLAN/安装确认只包含项目venv依赖与本机独立fixture实现/验证；**不授权自动使用用户Key实测、公司生产查询或部署**。真实用户通过网页显式generate/确认执行；budget/最小已准问题和必要字段外发合同沿用，未知供应商需要其表单用途同意。
- 新增非秘密图状态/任务只后台会话内存，复用M02强隔离/receipt，不读取Codex/Claude配置或凭证。外部LangSmith/观测日志始终关，model/network只由existinggovernedprovider和ownedMCP/Worker触发；依赖SDK不得创建外部云会话。
- 本次候选锁26包不覆盖原requirements.lock或PG/excel锁，不升级现有pydantic/httpx，完整依赖快照/rollback记录。dryrun仅解析证明，安装后runtime兼容必须实跑，不能以wheel可下载代替已验证。

## 6. CHECK/ACT矩阵与完成标准
- 无联网graph smoke：typedstates、conditionaledges、interrupt/Commandresume、cancel/节点timeout/递归限制、graphreplay不二次提交。
- Modelprovider：只有approvedquestions/requiredfields，秘密/注释promptinjection隔离，非法JSON/超长/不存在metric/dimension/forgedscope/modelversion/stale semantic拒绝；429/未知结果保留预算无fallback；构造嵌套数据不提升权限。
- 新MCP聚合合同：旧preview/HTTP工具列表/导航行为全回归；受限AST/大小/读取路径/资源/模式schema/源版本/MCPidempotency全部校验；无授权或不支持adapter严格refuse。
- 真实数值金标准：独立fixture>100行COUNT/SUM/ratio/维度/显式time，聚合与全表受限SQL对账；重复grain、非数值字段、分母0、空集/空值、输入行数/输出组超限、时间type冲突、JOIN膨胀（C02进入后）质量分项。来源色标与质量分开。
- API/browser：真实ownedMCP任务→图规划/人确认→执行/QA→resultcard，错model/pack/源change拒绝；同UUID/双确认/刷新/中断/旧代际未知不得二次SQL；状态/价格未知/Key隔离/主题/手机/历史不回归。
- 当前真正公司模型+已批准语义+授权MCP一请求真实闭环由用户网页操作确认，记录脱敏回执/模型和版本/实际结果，不制造成功。没有凭证或未加载服务=not_run；fixture隔离通过不当实网关/生产验证。
- 至少525/560等原既有基线全量检查按真实sourcefingerprint重跑，不修改assertions降低治理约束。安装httpx2等新传递包可能影响StarletteTestClient路径，必须专项和fullbackend覆盖。
- 局部self_review明示，每切片保存；PRD全范围/真实gate/用户验收达标才模块closed。MVP还需M05–M08，不能以本模块单例成功宣布完整产品交付。

## 7. 风险与回滚
风险：包依赖数量/外部trace行为、model128输出太短/JSON能力未实证、完整聚合接口没有legacy兼容保证、跨节点版本漂移/确认重放、无M05持久队列、JOIN/单表依赖扩展、用户原数据私密度。主动失败不走替代权限/账户/engine。
回滚：关闭Agent入口与新aggregatecapability，回退本切片代码/专用依赖锁并验证原pipcheck；用户semantic/source/modelbudget/history不删除，不resetcampaign，不执行gitreset盲删，服务停止只拥有者/用户明确授权。依赖不兼容回PLAN，不暗换框架。

## 8. 当前待确认 D-M04B-PLAN-INSTALL-069
推荐按上述完整模块方向实施，先C01真实单表主干再依条件C02/C03；批准在项目venv安装候选 LangGraph1.2.19及26个已核新增轮子、禁外部trace；新增localMCP受限聚合合同/人工确认/数值质检，沿用预算/Key/生产边界。具体未知目标不由此批准。未确认前只能研究/准备，不能安装或实现与方案选择相关的Agent执行器。


## 2026-11-02 C01实际开发检查点
已安装26包，无现有升级；pip/no-networkinterrupt-resume通过。后端/工作台独立fixture第一全回归581passed/1optionalbaseimportfailure，43browser/17front/types/build/pip过；修aggregateSQL/lazygraph依赖默认生产基础模式不加载，保留加强原门禁。当前新增模型权限/128tokenJSON失败、语义/schema/state/version漂移、人工确认幂等、UNKNOWN无重提等专项和完整回归尚待最终，首C01并非完整模块。实际用户网关JSON规划/执行未验，不能批量收费或声称MVP完成。


## 2026-11-02 最新 C01 检查点（revision160）
D069 已批准并实现，不再待安装或待方案确认。最终全回归593backend/17frontend/44browser/types/build/pip通过，来源指纹一致，证据094834Z/results.json及checkpoint-review.json。真实网关闭环required/not_run、运行旧API Agent404需安全加载；M04仍DO，完整模块审计/验收和L2/L3/L4/JOIN尚未完成。上方规划/首轮测试时间快照仅供历史追溯，不覆盖progress当前事实。
