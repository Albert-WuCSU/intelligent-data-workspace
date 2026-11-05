# 2026-11-05 有界公开模型意图说明
工具调用间的完整TextBlock经双层门禁显示，最多4条/500字符；ThinkingBlock/StreamEvent碎片不显示。数字/凭证/路径/代码/成功声明/非未来意图省略且不入诊断，正文标注非执行回执。不是任意token流，拒绝不影响后端查询/QA/发布，不新增模型调用或费用。
专项：`services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_public_notes.py services/api/tests/test_sdk_web_agent.py -q`；完整仍`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`。默认运行尚需用户加载，真实模型需要用户显式输入Key/授权复测，D053不reset。

# 2026-11-04 A3-M1本机检查范围
新工具只检索任务绑定单表元数据、选择已批准metric派生L2模板；不可调用自由SQL或生成未批准口径。模板receipt绑定版本/route/source/schema/Skill，提案经原confirm/MCP/QA门禁。query_path显示实际L1/L2，非质量认证。Skill1.0.6。
专项：`services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_topic.py services/api/tests/test_sdk_web_agent.py services/api/tests/test_sdk_dialogue.py -q`；最终完整仍`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`。模型与公司数据不自动调用，默认运行加载另验。

# 2026-11-04 A2 同任务澄清（待完整回归）

Agent澄清回答在同一运行任务中由服务端写入隔离回答通道；仅当前owner/generation/clarification_id有效。页面勾选本次回答外发同意后“继续同一任务”，重新核口径后仍需另点确认执行。最多2轮/1600字符，共享原有有限预算，不跨后端重启、不发结果行/全历史；独立新问题不自动继承旧筛选。

专项：`services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_agent.py services/api/tests/test_sdk_web_agent.py -q`；完整：`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`。check的源指纹新增SDK依赖锁，UI-only SDK快照测试明确不代替真实SDK+合成MCP。Schema仍从`python -m data_workspace.export_contracts`和openapi-typescript生成，不手改。

加载新API前验证8000/5173归属；完整检查后安全重启本项目开发启动器，不重置来源/语义/估算账本。Key只在设置页由用户重输，deepseek-v4.1-flash可用请求名，返回版本alias不可作为请求名。真实筛选/分组/同任务澄清复测、Claude官方/生产/MVP保持not_run直到真实证据与验收。

# M04-C02-SDK 离线 fixture（2026-11-03）

D-M04B-SDK-INSTALL-071已批准固定SHA wheel项目venv离线安装。当前依赖为`claude-agent-sdk==0.2.177`＋捆绑Claude Code CLI 2.1.317，增量锁`services/api/requirements.sdk.lock.txt`；wheel SHA256=7997db488354a539c08b5b6b16717d99ae67903ae7351da43d51b68b80097fad，CLI SHA256=26b01ec22df2c17ac7f5703aa547d36706e8d58412136ced0344a8ced4d86038。安装/版本证据在M04对应evidence。

离线专项：`./services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_agent.py -q`。完整回归：`./services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`（需先核本机服务归属）。runner只用独立loopback假Messages网关和真实合成MCP，`setting_sources=[]`＋受控`governed:data-query` plugin、最小父环境、专属Windows Job；不读宿主Key/settings/hooks、不调用真实AIPlan/收费/生产SQL。真实Claude模型与AIPlan SDK协议仍未验证，不能用当前DeepSeek文本/流式结果替代。

## 2026-11-04 SDK runner / 默认 Web 模型绑定
- AI Plan catalog 模型经服务端 catalog 引用进入 SDK runner；本机开发默认启用 `sdk_web_agent`。个人 API / 非 AI Plan 模型仍走既有 LangGraph 路径。浏览器只传模型引用，端点、模型 ID 与 Key 由后端解析，不读宿主凭证。
- 任务级估算预留 2 USD（8×0.25 单元，D053 不 reset）；真实用户确认桥、模型/语义/来源失效、执行/质量回执复核保留。SDK runner 仍只接受服务端生成的 `web_catalog` 绑定，不自动发现网关模型。
- 专项：`./services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_web_agent.py -q`。完整回归仍为 `scripts/check.py --module M04 --browser`。
- 真实 DeepSeek Web、Claude 官方支持、生产与用户验收仍 `not_run`；真实测试需用户显式操作与本机隐藏 Key，不自动收费或扩大外发。

---


按用户D-MODEL-ESTIMATE-BUDGET-053近似预算，--model-key启动新增WORKSPACE_MODEL_ESTIMATED_BUDGET=1，仅后端继承；跨重启SQLite估算账本0.25USD/次、最多60、15USD目标，20USD为软预算参考。新增POST model-service/test，认证/CSRF/64KB请求体、当前配置与runtimegeneration、同UUID幂等回执、固定非敏感文本；浏览器不发送Key/问题/行。仅用户显式点击测试收费，不自动调用。前端合同由Pydantic导出。用户持Key旧进程必须本人重启隐输新版，不读取或迁移环境秘密。
详细步骤MODEL_SERVICE.md；账本data/model-runtime不入Git，不删除/reset预留，未知结果/超时保留。单元在临时根/假Key/fixture运行，实际网关验证单独not_run直到用户实操。下面旧“无费用许可永远拒绝/no测试端点”文字为历史。

# M04-A 当前模型适配/本机Key入口（2026-10-28）

M02有限本机交付已人工验收，PG/生产required/not_run仍保留。M04-A第一切片支持 `start-workspace-model.cmd` 或 `scripts/dev.py --model-key` 本机隐藏输入，专用Key不写盘、不传Node/Worker，退出后重输；原启动器不继承环境已有modelKey。只读 `/api/v1/model-service/status` 需本机身份，显示安全状态不返回Key。
真实模型/授权目录/流式/SQL/JOIN未完成；无费用许可实现前拒绝收费请求，不把输入Key称为已连通。详细步骤和非秘密协议/费用证据需求见 MODEL_SERVICE.md。

# 2026-10-28 聊天附件与右侧多来源（当前交互）

本地文件在取数工作台输入区“添加数据文件”进入。用户确认有使用权及复制到本机后，经既有20MB预算/受限预检/真实MCP目录后成为当前会话临时附件；不自动保存profile/不修改原件、不向模型发送数据行。CSV/Parquet/DuckDB/Excel沿用原解析和安全边界，真实表头/类型/日期/最多100行无筛选预览。API重启或24h后草稿失效需重新导入，行数据/附件testid不存浏览器历史；每会话最多4个附件。

连接器新建只提供PostgreSQL与HTTP MCP，不再重复提供文件上传/路径表单。后端原local_file API是聊天公用安全导入层，未删除；旧本地profile折叠为“历史本地来源”保留可浏览/启禁，原文件/保存数据/unknown保护。安全存储只读计数与周期仍可查，无一键删除或降低原安全门禁。

右摘要可勾选多个已启用来源（每会话最多8个），多份附件也在右侧列出。源/附件上下文按会话隔离且刷新后不当作有效资产恢复；不再在输入区单选数据源。选择来源只是限定未来查询候选，不执行SQL。多表JOIN属于真正取数计划，要确认表/关联键/粒度/权限/数据量；同一数据库的多表与跨数据源融合不同，当前UI不声称已经执行JOIN/聚合或自然语言取数。

本轮用户明确确认有限本机MVP、PG/生产后补及应用专用调用公司coding-plan网关，外发仅本轮问题+必要字段信息，禁止表行/全历史/截图。15USD测试上限不变。无认证入口与openapi.json只读探测404，专用应用密钥未配置/实际model协议费率未核实，真实模型生成not_run；不会复制ClaudeCode token、猜模型/费用或用缺凭证伪造成功。M02仍须有限范围审查及用户验收后M04-A→M03→原M04=M04-B，不擅自关闭。

附件预览GET /api/v1/source-profiles/drafts/{test_id}/tables/{table_id}/preview：服务端校验主体/目录/期限，持全请求引用锁和运行互斥，真正MCP提交取回结果；读取中上下文过期拒绝结果，不自动保存连接。不接任意SQL/外部路径。移除UI冗余不移除后端安全导入层。

PG后补验证指真实独立PostgreSQL实例的连接/元数据/只读SQL/TLS/账号权限及失败分支；生产后补验证指正式身份/多用户数据隔离/部署/安全/恢复，不代表今天本机演示不能跑，也不能说已生产可用。保留not_run和负责补验的人/条件，不拿UI表单或DuckDB结果代替PG。

---

# 2026-10-28 只读连接释放修复

周期与盘点的SQLite只读连接通过closing显式释放；sqlite3.Connection自身的with只结束事务，不保证关闭原生句柄。已新增关闭垃圾回收后的重复读取/原生句柄打开验证，以及真实独立API重复盘点后停止检查。首次完整网页收尾WinError32失败和诊断保留，不用gc/删除数据/忽略cleanup异常让测试变绿。默认服务需加载修复版本后再记录准确启用状态，不能沿用旧进程健康证明新代码。

---

# 2026-10-28 保留A R3：有界自动周期

已批准的24h方案由应用lifespan持有一个原生单领导租约与单async任务。scripts/dev.py的本机开发模式默认WORKSPACE_RETENTION_CLEANUP=1；Settings/生产默认0，且拒绝在非本机开发身份启用。实际启动/启用以进度中运行证据为准，代码默认不当执行证明。可在PowerShell设置$env:WORKSPACE_RETENTION_CLEANUP='0'后启动停用；前端/受限Worker不继承这个开关或凭证，产品没有公开执行POST端点。

启动后5秒开始，完成后延后600秒再触发（无并发周期/补跑积压）；每周期在既有固定WindowsJob Worker执行，墙钟15秒/累计CPU8秒/384MB进程与512MBJob/最多2进程，父监护和cancel只收回自己的Job。完整目录/引用预扫描（每区及journal/引用2000，元数据8MB），最多8个副本/实际固定句柄核验总64MB；保存SQLite写冻及全生命周期引用租约内重核。引用收据一轮最多维护64个。超范围不拿部分盘点执行，超过数量/字节的候选延期下一周期。已保存/禁用/有效测试与活动请求引用、原件、unknown历史与项目证据始终保护；不按mtime猜归属。

循环开始先flush/fsync/原子保存非秘密RUNNING回执，完成回执落盘才发布SUCCEEDED/PARTIAL；Job超时/崩溃或取消记录INTERRUPTED/STOPPED，不推断删除成功。下周期/重启仅按UUID journal重新核对象/引用续接清理，不恢复SQL/模型/内存任务。损坏或ambiguous周期.tmp保留并阻止执行，需要管理员核查。未知/超限副本保守保留、可能占空间，不是全API/多用户/掉电耐久认证。

GET /api/v1/source-profiles/retention是只读状态。页面存储盘点每2秒只读获取最近周期/计数/错误与配置状态；忙时分开报告、读取失败明确为上次回执，GET不触发删除。不模拟成功，不加筛选或删除日期列。已有API不返回该能力时不宣称已启用。

专项：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_retention_cycle.py services/api/tests/test_retention_execution.py services/api/tests/test_retention.py -q。首69项68过1捕获先发布后持久回执竞态，修为持久后发布并增阻塞回执的确定性检查；失败证据保留。72项中间专项通过，最终完整源码/运行证据看progress，不能把中间输出替代默认启用门禁。

本轮开始两个端口都未运行，先核实际监听/归属再按权限启动，无盲杀或旧exec继承。独立browser fixture第三API用默认5s/600s真实周期，仅测试自己的25h标记副本与保存禁用数据；模拟时刻只用于fixture准备，不是生产年龄证明。普通测试API默认关闭自动回收，控制不出现在标准API。正式PG实例/身份/目标部署/磁盘SQL任务及M02审计验收仍not_run；M02不因清理通过自动关闭，验收后M04-A→M03→原M04=M04-B。

---

# 旧API过期能力兼容边界（2026-10-27）

TestedDraft新增可选expires_at，由后端测试创建时刻+24h推导；前端只有收到此字段才说明24h过期能力。默认旧8000未报告该字段时，显示“当前运行API未报告草稿过期能力，需加载新版后核查”，不会把批准政策或新版fixture能力当作旧服务已实现。合同已由Pydantic/OpenAPI重导。新增字段缺失浏览器用显式兼容响应fixture测试（从真实新API响应去除字段），不是旧服务或新功能真实执行证明；实际新API过期/回执路径仍用独立真实API。

---

# 2026-10-27 保留A R2：内部执行与只读状态（默认自动回收未启用）

新retention_executor.py在全请求Windows租约+已有profiles SQLite原生数据库/祖先无删除句柄固定及BEGIN IMMEDIATE写冻结下，再查保存含禁用/有效测试/活动请求引用，重新校验root/UUID/owner/明确创建时刻/全部后代。仅新可信且严格超过24h的上传、快照或明确标记的中断暂存可进入内部执行。旧归属不明/未标记/未来时间/额外子项/链接/硬链接保护。

retention_native.py固定所有目录祖先及子文件Windows句柄，拒绝reparse、写入与路径替换，对已核实对象按句柄逐项标删除并关闭；不调用rmtree/递归删除/跨shell删除。不读取原数据源/公司平台或宿主凭证。每UUID非秘密journal在实际删除前flush/fsync/原子落盘，文件及目录volume/index/size/hash和状态提供重启校验；同UUID已DONE重试只核对不存在，不重删。崩溃后剩余对象必须为原身份/内容的子集，无新引用才续；重新创建/替换/未知对象或损坏回执停止。完整同对象单调.tmp写回执可核实恢复，无法核实的损坏.tmp保留。

prune_expired_references仅清理可信且超过24h的测试引用收据，当前/边界/未知/未来时间保留；没有恢复测试草稿/SQL队列。每目录8文件、文件32MB/对象hash64MB、引用/journal2000预算；journal保留而有容量门禁，不能任意删历史回执“解锁”。全API/生产沙箱和电源掉电耐久不由此证明。

存储GET接口增可选RetentionStatus（由Pydantic/OpenAPI重新生成类型）：A已批准、自动未启用、完整副本只读候选/保护计数、实际持久回执完成/待核查/未知状态。查看不执行清理；旧/空根不会因此建DB或锁，旧API没有新字段仍能显示原计数。未完成暂存的执行资格必须由执行层重核，完整副本候选计数不是删除计划。界面已改旧“待确认”为A已批准/未启用；保存过期409清旧测试并保留字段，提示重测。

产品没有注册删除执行HTTP接口或scheduler，默认data/connections未扫描执行/删除。内部原生执行仅在独立新建测试副本上实际验证。默认5173/8000原拥有者/200未停止重启；新版保留API/过期/回执网页使用独立临时真实API fixture验证，不能把它当默认新版已加载或自动周期已运行。fixture-only时钟/示例操作只在独立测试API，标准API没有这些入口。

专项：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_retention.py services/api/tests/test_retention_execution.py -q。完整：services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser。首执行专项13失败34通过：pywin32常量位于win32file而非win32con、非法UUID分类错误；修实现不删断言。原生目录探测沙箱访问拒绝后原探测授权重跑成功，实际执行测试按审批在沙箱外。日志/当前指纹及最终结果见progress，不用中间47项通过替代最终全回归。

M02仍C03 DO/audit及delivery未完成，PG真实/默认自动周期启用/正式身份/生产恢复not_run。下一步安全加载默认新版，完成有界自动周期触发与状态/停止恢复测试，再按已批准A启用；不提前关闭M02或开始模型。依赖/模型端点/费用/外发另确认。

---

# 2026-10-27 保留A：R1安全底座（尚未启用TTL删除）

D-M02-RETENTION-013 A已批准，无需重问。新上传/快照在受限操作前记录应用来源/明确UTC创建时刻，完成后记录固定子文件size/hash；缺失/未完成/损坏/链接/未知历史不能据此回收。测试草稿24小时失效，保存时重新核时，超时409 TEST_EXPIRED需重新测试；不会因过期直接删除副本。

同运行时根的上传/测试/保存/启禁/导航/预览持有全请求Windows跨进程字节租约，异常退出由OS释放句柄，不删lock文件。引用收据只存非秘密root摘要/主体/UUID/时间/副本关联，跨重启保护仍在24h内的引用；不是磁盘草稿/SQL任务恢复，API重启后原test_id依然不能保存。不恢复查询、不外发数据或读取宿主凭证。

内部retention_preview仅核查候选计数：SQLite mode=ro、已保存含禁用/内存与磁盘有效测试保护；完整可信且严格超过24h才列候选。引用不明/收据损坏/未来时间/超预算拒绝或unknown保留。最多每区和引用2000项/目录8子项/单文件32MB/整轮hash64MB。可能初始化非秘密OS锁文件，但不改用户副本、不建profiles数据库。

目前无删除执行接口或scheduler，automatic_cleanup=false/retention-policy-execution=not_run。中断未完成暂存、执行幂等/隔离和删除故障恢复/收据有界维护及网页清理预览/最近记录在R2；启用前重核所有绝对目标及后代、重新核引用并冻结竞争、仅对独立测试新副本验证。原文件、已保存/禁用数据、未知历史与project-control证据不删。

本轮默认5173/8000没有重启仍旧代码，不能将其健康当新版运行证据。下一次加载要重核拥有者及父链并按运行权限重启。原网页未改：显式黑白主题/历史/真实pipeline、原表头类型及前100行无筛选日期保留；页面旧“策略待确认”文案在R2上线真实状态时修订，A批准不等于清理已运行。

专项：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_retention.py -q。完整后端/依赖/类型/构建/前端：services/api/.venv/Scripts/python.exe scripts/check.py --module M02；当前浏览器未重跑需加载新API后以--browser复验。首次完整回归捕获旧Worker故障fixture假设Worker才mkdir，与父进程先落来源标记冲突；fixture改为先断言父标记存在再制造同样partial/timeout，保留全部原安全断言，失败日志不删。

R1仅局部self_review，不是模块audit或独立审计。PG真实实例、非Windows/正式权限/生产/磁盘任务恢复仍not_run；M02仍C03 DO，审计和用户delivery后才M04-A→M03→原M04=M04-B，新依赖/端点/费用/外发另确认。

---

# 当前上传预检隔离/只读盘点（2026-10-27）

新增upload_preflight.py并经固定worker_entry执行：数据只写新暂存，Worker校验路径/哈希、格式编码和Excel安全包；成功才原子转uploads，失败仅清理本次新目录。API路由通过to_thread等待受限进程，不在事件循环解析ZIP/XML；body接收认证/同时2路/21MB门禁。非Windows隔离依然拒绝或not_run，无新依赖。

storage_inventory.py提供GET /api/v1/source-profiles/storage及网页“存储与清理”只读摘要，已有SQLite用mode=ro读取引用，没有就不建DB，不输出原文件内容/秘密/路径。只读盘点无法证明可安全删除，不提供清理执行/自动TTL。策略选择见M02/CLEANUP_STRATEGY.md，未经用户选择不删除历史数据；旧缺标记/异常链接保守保留。

专项命令：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_upload_preflight_storage.py -q。真实受限预检/原Excel链路、失败目录清理及回执拒绝、API响应/并发门禁/只读盘点；路径链接状态与故障注入是隔离单测，不称原生符号链接或生产磁盘故障认证。完整回归仍scripts/check.py --module M02 --browser；后端更新需核对服务拥有者再获批重启，不把旧API当新版本运行。

不自动恢复磁盘任务、不访问公司/复制宿主凭证，不暗装PG服务；保留原无筛选/日期字段、主题、历史/pipeline。M02仍DO，清理执行、PG真实及生产/模块审计门禁not_run。

---
# 当前 W2 stdio 长驻恢复（2026-10-27）

新增warehouse/stdio_transport.py/stdio_entry.py/PersistentMCP，沿用MCP SDK ClientSession协议但不再使用不带本项目硬限额的SDK启动器。父Job + pipe gate + 固定-S bootstrap、内存/累计CPU/进程数/消息预算、错误清理详见CONNECTORS.md。SDK自身没有被修改，不允许浏览器指定入口/命令或环境。

专项命令：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_stdio_recovery.py -q。实际Job内存/CPU/超输出/分配失败、长驻进程死亡/多轮重建/旧结果失效、实际提交成功后模拟丢回执无重提及请求取消安全回执。生产API没有fault接口；remote_browser_fixture.py仅为独立测试API注册/fixture-only/stdio-fault，终止的是其自己持有的测试Job，不能拿它控制默认8000或公司服务。

每长驻MCP由同一asyncio后台任务开关ClientSession/AnyIO上下文，避免在不同HTTP请求任务跨task退出CancelScope。队列1、显式目录验证后才能重建，生命周期关闭收回拥有任务和全部Job。CPU8s是会话累计而非无限长驻预算，耗尽后必须手动验证新上下文；不得宣传无限连接池/自动查询恢复。

PreviewReceipt新增非秘密execution_generation与RESULT_EXPIRED状态，由Pydantic/OpenAPI导出前端类型。实际故障后旧成功结果过期、未知任务不重提；网页仅2s只读状态轮询，旧卡失效但历史文字仍保留。结果/任务并未新增磁盘持久化，API重启仍丢失，正式M05持久及PG真实/部署继续not_run。

完整检查仍为services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser。加载新版前检查5173/8000归属并获权限重启，不假设继承旧exec session，不杀未知服务。

---
# 当前 Worker W1 开发检查点（2026-10-27）

新增worker_runtime.py/worker_entry.py以父Job与pipe gate隔离本地快照、HTTP/PG受控操作。Windows-only、使用已安装pywin32，base Python -S仅显式加载项目src/site-packages与pywin32路径/DLL目录，不执行宿主sitecustomize/.pth，不继承PG*/代理/凭证环境。原生内存/CPU/进程数及父CPU计时监护、墙钟/出入预算详见CONNECTORS.md。

故障专项：services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_worker_runtime.py -q。14项涵盖真实资源拒绝/Job后代清理、分配失败前无读取、名额复用、只清理新失败暂存和手动恢复。worker_probe.py是独立软件故障fixture；产品worker允许操作固定，不能请求probe/命令/任意模块。

完整检查仍为services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser。新增浏览器凭证丢失故障控制仅存在于独立remote_browser_fixture测试API，标准产品API没有fixture-only接口，不可将测试控制用于真实凭证。此前恢复测试捕获UI旧失败标签滞留，已补成功连接后的状态刷新，不通过放宽断言消除失败。

当前只有W1操作级资源与手动恢复；旧stdio/持久内置MCP硬限额与故障重建、TTL和持久恢复未闭环，不能标Worker全验收。PG真实实例和非Windows/生产仍not_run。变更后核对服务拥有树并获批重启加载新版，不能把旧API当当前运行证据。

---
# 方案 A 连接配置检查点（2026-10-27）

当前源码增加PostgreSQL/HTTP MCP表单、非秘密配置导入、项目凭证代号与授权绑定，详细操作及边界见CONNECTORS.md。真实认证HTTP MCP使用独立loopback fixture进行API/浏览器测试；PG缺真实实例时必须not_run，不能把驱动安装/单测当已连通。

PostgreSQL可选依赖已核验并安装项目venv，新增requirements.postgres.lock.txt按哈希锁Windows CPython3.12轮子；pip check/import通过，不安装数据库服务，不升级原锁。重建其他平台仍需独立核验轮子。

scripts/dev.py已分离前后端环境，后端接受专用WORKSPACE_CONNECTOR_POLICY及WORKSPACE_CONNECTOR_SECRET_引用，前端不继承秘密。专用配置仅由管理员提供，不复制Codex工具配置，不向本助手提供真实密码。默认无远程grant，页面会正确拒绝未批准目标。

完整检查命令仍为services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser。新增remote-onboarding浏览器测试启动独立临时API和认证HTTP MCP，网页请求转发到同一产品源码的真实测试API，响应/目录/预览不是mock；临时服务、数据和测试哨兵不进入默认8000配置或持久浏览器历史。PG浏览器只检验配置/拒绝/保留输入，不证明实例连通。

M01主题/历史/业务会话继续保留；连接器无筛选，不删日期。Worker强隔离/恢复/TTL、正式身份和完整M02验收仍待做，不进入M03。

---
# 最新连接器切片（2026-10-27）

用户可在连接器首页“新增数据源”上传DuckDB/CSV/Parquet或填写受控本机路径，测试后保存并刷新复用，选择表看到表头/原类型/前100行；也可导入非秘密本地连接JSON。详细操作、存储及限制见 CONNECTORS.md。

**日期字段不被删除。连接器没有时间或其他筛选控件；日期列原样展示，不按字段名猜含义。** 下面旧日期/开发字段筛选说明是历史切片，不再作为当前用户流程。

已有的专属合成仓作为可选内置例保留，用户数据通过独立MCP/只读快照查询，不强标合成或TEST。远程数据库/HTTP MCP接入仍未完成，不把入口信息声明为连接能力。实际源码指纹与回归证据见progress引用。

---

# 当前开发版本：M02 真实连接器切片

本机启动器已默认启用自有合成数仓（WORKSPACE_OWNED_WAREHOUSE=1），仅 loopback 开发身份。先按 WAREHOUSE.md 配置项目数仓依赖及已存在的数据库，再启动 scripts/dev.py。没有公司凭证或真实公司数据。

网页检查路径：连接器 → 验证数据源连接 → 进入开发验证 → 选择授权表/字段/日期 → 勾选确认 → 执行只读预览。数据和回执经真实 API/MCP/DuckDB 返回，合成来源/预览限制/TEST 单位/WARN 与任务详情明确展示。

自然语言聊天仍未接入 M04，不能因为连接器可预览而宣称自然语言取数完成。原 QuerySpec 结构校验和“登记测试任务”仍是 M01 检查入口，不接真实执行器；请用新的“开发只读预览”，不要把旧接口改成伪成功。

服务重启会清空内存任务。API 返回 execution_generation（非秘密执行上下文编号）；旧代际提交拒绝，必须重新验证并确认查询。通信结果不明保留原幂等键，不自动重复提交。真实取消/下载/正式身份和持久化未实现；Worker/OS 强资源隔离仍待验收。

默认生产 Settings 不启用连接器；本机可设置 WORKSPACE_OWNED_WAREHOUSE=0 退回未接入行为。新依赖仍位于项目 venv，基础模式可不加载 DuckDB/MCP/SQLGlot。前端类型由 Pydantic/OpenAPI 导出，仍禁止手改生成文件。

完整回归：services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser，运行中应已有本机服务；证据与截图每次保存在新的 M02 evidence 目录，不覆盖历史。启动前检查端口与拥有者，不杀未知服务。

---
以下是 M01 已验收的历史基线说明，涉及“未接 MCP”的段落仅描述 M01；当前能力以上方 M02 和 WAREHOUSE.md 为准。

# 本地开发与 M01 验收

本版本是实际可运行的网页工程底座，不是完整取数产品。没有接入MCP、数仓、LLM、持久数据库或生产认证。页面不生成业务数据。登记任务后返回FAILED / EXECUTOR_NOT_CONFIGURED，表示任务记录创建成功但没有SQL执行。

## 已安装环境

项目后端虚拟环境在services/api/.venv，前端项目依赖在apps/web/node_modules。依赖锁分别为services/api/requirements.lock.txt及apps/web/pnpm-lock.yaml，不使用PDCA进度作为运行时业务数据库。

首次重建环境需要Python3.12和Node22.12以上（本次验证Python3.12.14、Node24.22.1），以及pnpm11.25.0。联网安装须遵守运行环境授权。Windows示例从项目根执行：

```powershell
python -m venv services/api/.venv
./services/api/.venv/Scripts/python.exe -m pip install -r services/api/requirements.lock.txt
./services/api/.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e services/api
pnpm --dir apps/web install --frozen-lockfile
```

setuptools在锁文件内，用于本地可编辑安装。Linux虚拟环境执行文件改为.venv/bin/python；Windows生成的运行锁包含colorama等平台包，Linux目标环境仍需独立验证，不宣称跨平台已认证。pnpm配置仅允许esbuild安装脚本，其他新增构建脚本需评审。项目依赖与应用托管运行时隔离。

## 启动与停止

```powershell
./services/api/.venv/Scripts/python.exe scripts/dev.py
```

Windows也可双击start-workspace.cmd。服务只监听127.0.0.1；浏览器打开http://127.0.0.1:5173。Ctrl+C停止脚本启动的两个子进程。端口8000或5173被占用时拒绝启动，不杀其他服务。Node不在PATH时可设置WORKSPACE_NODE为完整可执行路径；当前电脑支持已存在的本地托管Node后备路径。

不要用0.0.0.0启动开发身份或把此服务暴露给网络。此版本的开发身份是服务器固定的local-developer/local-workspace，仅本机隔离演示，不是企业登录；生产默认未配置认证则业务接口401。不要手工使用uvicorn --host 0.0.0.0开启该模式，开发运行入口为scripts/dev.py，正式部署须单独审核。

任务内存最多1000条，重启会清空，不提供持久队列或进度恢复承诺；容量满时503。PDCA项目进度独立保存在project-control内。M05负责真正的资产生命周期及持久化；M02负责真实SQL服务。

## 验收步骤

1. 网页侧栏显示“API已连接”，页面持续显示开发身份/内存/未接入提醒。
2. 点击“验证数据契约”，显示结构通过但业务口径和SQL未验证。
3. 添加tenant_id字段或反转时间，验证应拒绝；无效JSON在前端明确报错。
4. “登记测试任务”显示真实API返回的任务ID及未执行FAILED；重新读取ID保持一致。
5. 查看实际Schema可从后端读取，恢复示例后继续验证。
6. 连接器、知识库、资产、看板、报告均为明确未接入状态，不宣称已有产品功能。
7. 手机窄屏导航可用，断开API或加载中禁用提交。

自然语言输入只是后续模块入口，此时“了解当前能力”说明尚未执行；不会保存、传输或生成自然语言查询。页面不展示任何伪造经营指标。

## 测试与合同生成

```powershell
./services/api/.venv/Scripts/python.exe -m data_workspace.export_contracts
pnpm --dir apps/web run contracts
./services/api/.venv/Scripts/python.exe scripts/check.py --browser
```

浏览器检查需要已启动本机服务，使用Chrome无界面模式；可设PLAYWRIGHT_EXECUTABLE_PATH为现有Chrome/Chromium路径。仅本机交互测试，测试截图及日志保存在project-control/modules/M01/evidence。check.py不安装依赖或修改授权；可不带--browser只运行后端、类型、构建和前端测试。

API Schema是Pydantic模型导出的真源，前端api.generated.ts由OpenAPI自动生成，禁止手改。基础合同缺少实际业务槽位规则、SQL安全门禁和完整资产治理，分别在M03/M04/M05实现。

## 已知边界

没有公开部署、HTTPS、OIDC、真实数据库、执行器或企业级安全认证。上游运行平台的权限、取消和方言兼容需要M02实测。当前测试套件有Starlette提示TestClient未来改用httpx2的弃用警告；当前httpx0.28.1测试通过，后续升级需要回归，不在本轮临时扩张依赖。

回滚只停止本地服务并恢复源码版本，不自动删除已有文档和进度。当前尚无Git仓库，以SHA256源码清单核对；后续初始化Git另行确认。

## 当前会话化界面修订

业务首页不再展示QuerySpec编辑器：顶部为请求执行进度，左侧历史，中间长对话和结果卡，底部追问。黑白主题可以切换并在此浏览器保留。示例问题只填入输入框，点击发送仅生成明确的本地未接入提示，不调用LLM或解析业务口径。

左侧历史仅当前开发身份的浏览器本地文字，最多30个会话、每会话80条消息，单条问题4000字符；不要输入敏感数据。可切换、删除和清除，不跨设备。正式会话身份、持久化及审计在M05规划。会话中的API验证/测试任务卡不存入浏览器持久历史，刷新后不会将旧内存结果冒充有效资产。

开发工具从右上角显式打开。真实接口验证结果成为会话卡片，口径摘要/未验证项优先，Schema与任务编号折叠。验证卡只表示结构通过，不表示正式认证指标或查询质量通过。查看Schema后恢复示例才能执行验证。关闭抽屉或按Escape回到业务页面。

本轮应检验：业务页面没有JSON编辑器，pipeline在顶部且不虚构进度；黑白主题刷新保持；发送两次保留完整消息；新建、切换、刷新和删除会话；默认技术细节折叠；开发工具原API错误、任务读取和鉴权测试继续通过；手机无溢出及隐藏侧栏不可聚焦。

## 最新约束：仅连接与表导航

用户明确要求Power Query式连接后浏览表头/类型及最多前100行；连接器不提供任何筛选器，不要求时间列，不按表名猜日期列，也不在后台添加WHERE时间条件。旧日期/字段勾选预览为历史实现，现已在代码中移除。数据库无自然排序保证时不能宣称前100行是最早/最新记录。新配置接入完整流程仍待实现；当前只有内置源导航切片，不能宣称任意数据源已可接入。浏览器需重启新版API后复核，不把旧运行服务当新版。

## .xlsx兼容补充（2026-10-27）

用户新增要求已落实到Excel本地来源导入，详见CONNECTORS.md末尾。接入流程不变：上传或路径→真实MCP测试→保存→按工作表导航/原列头类型/前100行，没有时间筛选。日期数据保留，不执行公式/宏/外链。第一行表头、可见工作表、空/重复标题与压缩包限额有明确规则；复杂Excel报表/旧.xls未承诺支持。项目新增requirements.excel.lock.txt，版本许可证已核验并获准安装；真实回归证据以progress为准。
