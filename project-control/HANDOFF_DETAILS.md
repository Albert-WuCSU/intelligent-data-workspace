# 项目交接详细说明

更新2026年10月26日。配合自动生成的HANDOFF.md阅读；当前状态以progress.json为准，不根据本文件覆盖JSON。

## 已完成与用户验收

M01 工程底座与核心合同完成并经用户本轮“OK…推进项目到下一步”确认验收。交付为Web网站优先，React/TypeScript/Vite前端、Python/FastAPI/Pydantic后端；不是CLI替代产品。

已实现：本地网页与API、核心QuerySpec/Task/DatasetAsset/ConnectorCapability合同及OpenAPI生成前端类型；服务器固定开发身份及默认生产认证拒绝；内存任务与规范错误；双主题、显式顶部黑色/白色选项、选中态与刷新保持；会话布局、开发身份浏览器历史、新建/切换/删除/多轮消息；pipeline置顶、开发工具抽屉、输出口径/来源/质量卡及折叠技术细节。

用户明确要求：此项目为AI产品经理求职作品；功能不仅齐全，还需体现用户任务与信息分层。不要重做浅色工程验证首页、移除显式主题入口或要求业务用户填JSON。规则已写进项目原则和project-pdca Skill。

## 已完成验证

最后完整产品证据：project-control/modules/M01/evidence/20261026T071751Z/results.json、sources.json，后端38、前端9、浏览器8项通过；依赖/类型/构建通过。最终审计：audit-theme003.md；会话化交互范围与局限：audit-ux002.md。此次交接检查所有sources.json文件SHA256仍一致，没有修改产品源码；不需因写交接文档重复启动产品测试。

本次Skill更新后需使用最新版用户思维门禁；结构校验/21项进度测试仅证明Skill机制，不代表产品新模块完成。

## 当前未实现

没有真实MCP数仓连接、LLM自然语言理解、SQL执行、认证指标、业务结果文件、持久任务、服务端历史、OIDC、公开部署或生产数据面。聊天中的自然语言反馈为明确标注的本地未接入提示。开发验证“结构通过”不是业务口径认证。测试任务登记即FAILED/EXECUTOR_NOT_CONFIGURED，不得改成伪造成功。

浏览器历史仅开发身份下本地文字，不跨设备，不保存API结果快照；不要输入敏感数据。API任务内存重启丢失，1000条上限。真实服务端鉴权会话与资产历史计划M05细化。产品依赖有低风险httpx测试弃用提示，锁定版本通过，升级需回归。

## 文件地图

- apps/web/src/App.tsx：会话UI、pipeline、结果卡、开发工具及主题入口。
- apps/web/src/styles.css：双主题Token和响应布局。
- apps/web/src/conversations.ts：开发本地历史及主题读写，含边界与容量限制。
- apps/web/src/api.ts / api.generated.ts：请求封装与生成类型，后者禁止手改。
- services/api/src/data_workspace/：contracts、auth、config、repository、main。
- contracts/：JSON Schema/OpenAPI导出，真源为后端模型。
- services/api/tests/、apps/web/src/*.test.ts、tests/workspace.spec.mjs：测试。
- scripts/dev.py / scripts/check.py、start-workspace.cmd、DEVELOPMENT.md：本地启动/停止及复现检查。
- project-control/progress.json / HANDOFF.md：唯一进度与自动摘要。
- project-control/PRODUCT_UX_PRINCIPLES.md：项目具体用户约束。
- skills/project-pdca/：可维护Skill源码；个人安装版在用户.codex/skills/project-pdca。

目前未初始化Git仓库，不存在提交或远端PR；以源码hash核对。未承诺公开网站域名或生产就绪。

## 本地服务与环境

之前使用scripts/dev.py启动服务，仅127.0.0.1:5173（网页）、8000（API），exec session曾为29102。新会话不能假设继承该会话ID或服务仍活着，先确认端口/HTTP健康及拥有者；不要杀未知进程或重复占用端口。

启动：services/api/.venv/Scripts/python.exe scripts/dev.py，或Windows双击start-workspace.cmd；Ctrl+C仅停止该启动器拥有的子进程。若运行权限要求审批按环境申请。不开放0.0.0.0或外网，不以开发身份部署生产。

检查：services/api/.venv/Scripts/python.exe scripts/check.py --browser（浏览器须已启动本机服务）。锁：services/api/requirements.lock.txt和apps/web/pnpm-lock.yaml；不安装/升级全局运行时，依赖装在项目内。Node24/Python3.12的本机环境已验证，跨平台/生产环境未认证。

## 下一步与决策

当前M02 PLAN。首先读project-control/modules/M02/NEXT_STEP.md，盘点可用元数据及执行平台，提出实际连接路径与M02 plan，让用户确认后实施。首个建议候选是当前企业元数据+Adhoc执行平台，但本产品应用进程是否有独立合法配置未知。必须解释身份、scope、能力缺失、预算、取消和数据驻留，不复制宿主令牌或假设会话MCP自动属于产品。

用户说“继续推进”可以执行当前已授权的方案盘点和计划生成，不等于批准生产SQL、全库扫描、外部安装或新栈。后续模块仍走PLAN/DO/CHECK/ACT；一个模块用户验收后才跳下一模块。

## 新对话起始指令

在同一项目目录使用 $project-pdca。先读取project-control/progress.json、HANDOFF.md、HANDOFF_DETAILS.md和PRODUCT_UX_PRINCIPLES.md，核对M01已验收事实；从M02 NEXT_STEP开始做真实MCP元数据与SQL执行连接方案。保持现有UI及已确认技术栈，关键平台/权限/计划选择征询我，不重建项目。

## 最新变更：独立合成测试仓

此前企业元数据/Adhoc仅为未批准候选，已由M02-C02替代；以当前progress为准。用户同意独立合成方案，五表种子与manifest在data/demo/synthetic-v1，生成代码在services/api/src/data_workspace/demo_data。实际后端48项通过，M01的40份指纹不变。当前待D-M02-ENGINE-003确认DuckDB+自建MCP；数据库、Parquet与MCP未初始化，不能称数仓建成。没有读取任何公司数据或公网数据，没有安装依赖。后续先确认引擎并依法安装/验证，不再要求用户提供公司表或凭证。

## 最新检查点：专属仓与真实MCP后端

用户“采用”批准D-M02-ENGINE-003。DuckDB五表和Parquet已在data/warehouse/synthetic-v1生成，来源仍为独立合成；stdio MCP通过真实握手、元数据、SQL、状态和结果验证。80项后端测试通过，运行说明WAREHOUSE.md，当前证据见progress。原锁和40个M01文件未改。现在继续M02 FastAPI/管理员/开发入口及Worker边界，不要重新生成默认数仓（已有目录会拒绝覆盖），不要声称网页已可问数或整个M02已交付。

## 最新检查点：M02 API 与网页真实预览

旧“API/网页未接入”段落现为历史边界。当前M02已接真实API/MCP/DuckDB，网页连接器→验证→开发预览→确认→真实结果卡可用，普通聊天仍未接Agent。最终后端93/前端10/浏览器11通过，WAREHOUSE.md与DEVELOPMENT.md已更新，进度引用唯一证据。M01约束保持并累计回归，M02仍DO，Worker硬隔离/恢复和模块审计待做，不closed。当前本机最新服务由本轮session6487拥有，后续先核对监听与健康，不继承session假设。无公司数据、无新包安装或部署。

## 最新用户反馈：连接器自助配置缺失，M02返工

用户明确拒绝仅固定预配置数据库验证页，要求自己的数据库/本地地址或MCP配置、配置文件导入入口。旧API/MCP/SQL是真实执行而非静态模拟，但不能满足自助接入；旧通过测试只证明固定链路。M02现在C03 PLAN，首读当前plan/connector-onboarding-C03和PRODUCT_UX_PRINCIPLES，待D-M02-CONNECTOR-UX-005新范围批准，不继续按旧页面关闭M02或先做Worker后绕过UX缺项。已有数仓/代码/测试保留，M01不重建。新配置/上传/保存/PG/HTTP MCP尚未实现，不能宣称已支持任意地址。

## 最新检查点（2026-10-27）：可配置本地来源

C03本地用户接入已落地：新增/文件或受控路径/非秘密JSON导入/测试保存/刷新/编辑禁用，真实MCP读取列头类型与100行。保留实际表中所有日期列，禁止连接器时间筛选。原固定源作为折叠示例保留。最终103/10/14回归通过，详细CONNECTORS.md及progress evidence。PG/HTTP MCP仍未接入，当前信息按钮明确标进度，不能称通用三类已完成；M02 DO与Worker门禁继续。运行会话32190仅本轮有效，后续核对健康。无需重做M01或重复问是否要无时间表。

## 最新交接（2026-10-27）：Excel兼容完成，准备新窗口

当前progress revision25（以校验JSON为准），M02-C03 DO。用户发现.xlsx不能导入，已增加只读Excel读取器/可选锁（openpyxl3.1.5 et-xmlfile2.0.0 MIT）、文件选择与受控路径.xlsx，中文/多工作表/原列头/日期值/100行真实MCP链路验证。最终108后端/10前端/15浏览器、构建类型依赖通过，唯一证据project-control/modules/M02/evidence/20261027T022418Z。原仓/Parquet/golden保持。限制与公式粘贴为值提示见CONNECTORS.md。当前不会自动执行Excel公式/宏/外链、不会修改用户源文件。

用户明确需要新窗口prompt，已保存project-control/NEW_WINDOW_PROMPT.md。不自动创建新聊天。旧日期相关段落为历史；接入不得添加筛选器/删除日期列。PG/HTTP MCP地址认证和通用真实接入仍待做，继续已批准完整范围，不反复询问基础计划。Worker/OS硬隔离/故障恢复、上传TTL/删除和正式秘密/权限门禁仍保留，M02未验收/未closed。最新本机开发服务session85598只在旧窗口有效，新窗口核对127.0.0.1监听/健康/拥有者后复用，不盲杀。无Git/远端PR、无公司数据或全局安装。

## 2026-10-27 HTTP安全前置切片与待决策

本新窗口已校验revision25、核对原72源码一致，实际健康/拥有者核对后复用5173/8000（PID10824/7932，当前用户，父链项目scripts/dev.py PID11716），不假设旧session可控，不杀任何既有服务。恢复checkpoint26，HTTP基础与测试checkpoint27，关键选择checkpoint28。

新增warehouse/http_boundary.py与test_http_boundary.py：空服务器精确端点白名单默认拒绝，数字IP/TLS/禁止跳转与环境proxy/URL秘密/流式预算；SDK1.30会自行跟随部分同源redirect，需底层拒绝，不靠follow_redirects标志。当前禁认证头，未挂接产品profile API/UI，不称配置MCP已经完成。真实独立loopback FastMCP/SDK/临时DuckDB快照握手、目录与100行原日期预览通过，45新增安全/集成测试。无公司目标、凭证读取或新依赖。

最新唯一完整证据project-control/modules/M02/evidence/20261027T024230Z/results.json：153/10/15以及类型/构建/pip check退出0，额外真实HTTP fixture与原数仓/Parquet/goldenverify退出0见extra-results.json，74源码一致，四份锁未改。self_review是局部检查点，http-boundary-review.md明确not_run；M02仍DO/not_verified/audit not_run，M01已验收只更新累计证据。现有网页主题/历史/无筛选/日期字段未改，服务不需要本轮重启。

当前待D-M02-REMOTE-SECURITY-009，读modules/M02/REMOTE_CONNECTORS_DECISION.md；A推荐项目专用secret_ref+核验后锁定项目psycopg3+仅独立loopback验证，B会话内秘密、重启重认证。没有替用户选择或安装驱动；版本/许可/兼容尚待核验。外部真实目标、PG服务安装/部署另批，实例不足PG仍not_run。实施秘密前分离scripts/dev.py的Vite/子进程环境，不把专用产品秘密/宿主工具秘密继承给无关进程。

继续从pending decision回答登记后做PG与产品HTTP认证配置/测试保存刷新/工具映射，接着Worker隔离、恢复清理与模块审计验收；不提前关闭M02、缩小三类范围或进入M03。旧session信息仅历史，下一轮仍先核对本机拥有者。

## 方案A实现与最终检查点（2026-10-27）

用户明确“我选择A方案，继续推进吧”，D-M02-REMOTE-SECURITY-009已登记（revision29），无需再问A/B。核验psycopg/psycopg-binary3.3.6公开元数据/WindowsCPython3.12轮子SHA256/许可证及上游libpq/OpenSSL许可后获运行审批离线安装项目venv（checkpoint30），四份旧锁不改，新增requirements.postgres.lock.txt。没有安装PG数据库服务、公司目标或宿主凭证读取。

remote_access.py实现专用secret_ref、目标/账号/资源/代号绑定，默认全拒绝。remote_sources.py严格审定HTTP六工具目录/前100行、结果限额和秘密添加，postgres_worker.py专属只读进程/管道凭证/12秒生命周期。source_profiles SQLite追加kind/config_json保留原local行；三类UI/JSON导入/测试保存刷新编辑禁用，取消授权确认失效旧测试，日期列保留且无筛选。合同由Pydantic/OpenAPI重导生成，普通严格union保留旧省略kind请求，未手改generated.ts。

认证HTTP实际API与浏览器用独立临时真实API/FastMCP/DuckDB验证，不是mock响应；PG只有驱动/SQL逻辑/隔离单测和表单拒绝，真实实例/真实SQLnot_run。scripts/dev.py已拆分前后端允许环境，Vite不继承秘密，stdio仍最小环境，PG密码不出现在argv/env。SecretRef仅用户专用后端环境，不读取.codex配置或任意环境变量。

最终完整证据project-control/modules/M02/evidence/20261027T031852Z/results.json，164后端/10前端/17浏览器、类型构建pipcheck退出0，81个来源指纹一致；额外真实认证HTTP API及原合成仓SQL/Parquet/golden完整性退出0见20261027T031952342756Z-remote-extra/results.json。remote-a-review.md为局部self_review，不是M02模块audit或独立审计。原M01人工验收保留并累计复测，M02仍DO/not_verified/audit not_run，PG/OS Worker未补证，绝不提前关闭或进入M03。

旧服务先验证拥有者/父链，发现未知子项就停止检查而没有杀进程；只读确认esbuild和Windowsconsole helper后获审批核对完整树/PID创建时间才重启，SQLite/上传/快照保留。最新本轮exec session3925，API PID24816、Vite PID28192、launcher父链9268，两个loopback服务健康200，未授权HTTP地址实际返回TARGET_NOT_APPROVED（未发起目标连接）。新窗口必须重新核对，不继承本会话ID。

下一步优先Worker/OS强资源隔离、失败恢复/清理；PG真实补验缺用户单独批准的独立本机实例，记录not_run，不绕用公司平台或暗装服务。长期HTTP异步/取消/下载、非loopbackTLS/DNS/SNI、正式认证ACL/生产秘密/TTL与发布门禁仍保留。当前无新待决策A/B，可直接继续推进已批准Worker范围；如需新依赖、真实目标或重大运行架构取舍再请用户确认。

## 当前推进入口（2026-10-27）

用户要求先更新进度交接再继续。已复核revision32及最终81份源码指纹一致；当前M02-C03 DO，164/10/17为最近真实回归而非本轮新测试。接下来在既有已批准Worker范围内使用已安装pywin32核验Windows Job Object可行性，推进资源限额/隔离与失败恢复；不新增容器/服务/全局依赖、不改普通用户路径、不处理公司数仓。PG真实实例继续not_run。若原生隔离不可用必须明确拒绝或保留门禁，不偷偷降为线程超时。

## Worker W1实现中检查点（2026-10-27）

新受限worker_runtime.py/worker_entry.py已将产品快照导入及HTTP/PG调用移入Job受控操作；复用现有pywin32，不新增依赖/容器。原生内存/CPU/进程数/后代清理/入出预算/隔离失败无执行等14项专项已实际通过，完整178后端/原前端/新增恢复浏览器回归正在运行，未把它登记为passed。

CPU专项曾只触发墙钟超时，现同时明确原生job/进程用户CPU限制与终止动作，父监护通过原生用户+内核CPU计时达到预算时终止该Job；不放宽断言。-S启动时HTTP缺pywin32路径导致拒绝，显式加载项目依赖/DLL目录后真实认证HTTP11项回归通过；不启用宿主site/.pth/env凭证。

当前旧5173/8000尚需安全重启加载后端改动；此前session3925仅本会话拥有，不假设新窗口可继承。源码有W1未闭环切片，不用旧164/10/17作为新Worker证据。旧stdioMCP内存CPU隔离/持久示例故障重建、TTL/持久恢复仍未验收，W1局部通过也不关闭Worker完整门禁/M02，PG真实继续not_run。

W1第一轮完整回归20261027T044104Z：178后端/10前端/类型构建依赖通过，浏览器17通过1失败，原因是恢复成功后前端未重读配置导致NEEDS_RETEST标签滞留。已修复成功连接后刷新状态；失败证据保留，当前待加载新版服务/最终复跑，不能声称18浏览器已通过。

## Worker W1最终交接（2026-10-27）

以最终checkpoint35为准（具体revision仍校验progress）：20261027T044557Z完整回归178后端/10前端/18浏览器及类型构建pipcheck退出0；044756181340Z-worker-extra单跑14原生/恢复专项及原仓SQL/Parquet/goldenverify退出0，指纹与最终一致，85来源文件一致、五份锁不改。worker-w1-review.md记录真实OS故障与隔离mock注入区分及首次失败/修复，局部self_review不关闭完整Worker门禁/M02。

W1后台隔离快照导入/HTTP/PG操作，Windows Job父句柄/pipe gate、固定入口/最小环境/入出预算、原生内存/CPU进程数与CPU计时监护、墙钟和finally回收。失败只清理本次新建快照暂存；旧原件/上传/配置不删除。NEEDS_RETEST真实呈现，成功手动连接刷新解除，不自动重提不明查询。CPU初次只墙钟失败后修复，不放宽断言；恢复UI失败日志保留，最终18浏览器通过。

旧开发服务树核对当前用户及创建时间后获审批重启；现在本轮exec27245、API20600/Vite7380/launcher9252、两个loopback健康200，后续窗口仍须核对，不继承session。没有新依赖/容器/服务、宿主凭证读取或公司平台访问。NEW_WINDOW_PROMPT.md已更新为引用磁盘最新状态而非旧计数。

下一步是旧stdio MCP硬内存CPU、持久内置例故障重建/任务结果失效及完整恢复；W1不等于文件网络沙箱/全API资源限制，上传预检、TTL/清理UI和持久队列恢复、非Windows/生产门禁仍保留。PG真实实例需另行用户授权，不暗装服务或绕用公司。M01已验收累计回归保持，M02-C03 DO/not_verified/audit not_run，未用户验收前不closed/进入M03。

最终状态核对追加checkpoint36：HTTP能力测试别名引用本轮完整backend命令中实际重跑的认证fixture用例及当前W1代码指纹，而非保留旧A指纹为当前证明。仅进度引用更新，无源码/测试行为变更；下一步仍stdio/持久恢复，PG真实与完整Worker门禁not_run。

## W2实施中（2026-10-27）

本轮用户明确继续stdio硬限额/长驻故障恢复，已核对revision36和85源码指纹、服务200。新增stdio_transport/stdio_entry固定-S gate+父Job、PersistentMCP单一asyncio拥有任务，故障失效generation及旧成功结果，unknown任务/幂等键不重提；前端清旧预览/会话卡、只读状态轮询。47旧API/仓回归和8stdio故障专项实际通过，追加取消/浏览器后完整回归运行中，不称全套已通过。旧服务仍W1需安全核对后加载。持久在此是长驻MCP上下文恢复，不是磁盘队列/M05持久化；PG真实/非Windows/生产保留not_run。

W2首轮完整回归20261027T050326Z后端187通过，但浏览器18过1失败（测试页销毁时真实转发响应disposed）；测试afterEach改为等待路由处理收尾，不吞异常/弱化断言。文档更新也使source-stability门禁失败，保留证据并完整重跑。新增容量拒绝不失效健康代际单测，当前未称全套通过。

## W2最终交接（2026-10-27）

本轮最终checkpoint40（仍以校验JSON为准），W2硬stdio/长驻会话恢复本机范围已验证：188后端/10前端/19浏览器、类型构建pipcheck退出0，证据20261027T050844Z/results.json。单跑10项stdio原生/重建专项与原仓SQL/Parquet/goldenverify退出0见20261027T051034477000Z-w2-extra/results.json，90源码一致、五锁未改，无新依赖/容器/服务。stdio-w2-review.md局部self_review，不是完整模块audit/delivery。首轮路由disposed及说明变更稳定门禁失败保留，afterEach等路由收尾后稳定新版完整复跑通过。

stdio_transport/stdio_entry父Job固定-S bootstrap在限额成功前不收元数据，384MB进程/512MBJob/2进程/4连接、会话累计CPU8s、15s调用/64KB输入/512KB行消息/8缓冲；CPU预算耗尽需显式验证，不无限长驻。PersistentMCP同一asyncio task拥有ClientSession/资源上下文，空闲死亡可清理，显式验证重建，不跨HTTP任务退出CancelScope。故障旋转generation，旧结果RESULT_EXPIRED且读取拒绝，旧unknown任务/幂等键不自动重提，取消请求仍安全留不明回执，容量拒绝不算健康故障。前端只读轮询清旧预览/会话卡，保留历史文字/主题与无筛选日期列；新类型由OpenAPI真源导出。

当前运行本轮exec82874、API27564/Vite21940/launcher23752/固定stdio子进程26588，两个loopback健康200。旧项目树经拥有者/路径/创建时间核实和审批后安全重启，仅项目进程被停止，配置/原文件不删。新窗口仍重新核对，不继承session。测试故障API只独立fixture注册，默认8000没有fault接口，不控制公司/用户连接。

这里“持久故障恢复”是API内长驻MCP的恢复，不是磁盘任务/结果队列；API重启仍丢任务/幂等，生产持久化/M05、非Windows/权限沙箱、PG真实仍not_run。下一步上传预检/全局TTL和生命周期清理审查及PG授权补验；自动删除/保留重大政策需用户确认，不偷删上传或已保存数据。M01已验收累计回归，M02-C03 DO/not_verified/audit not_run，未完整审计与用户验收前不closed/进入M03。

## 上传预检与盘点实施中（2026-10-27）

恢复revision40核对90sources后checkpoint41；新增upload_preflight受限Worker，仅新UUID暂存/SHA/编码/ZIP/XML预检成功才转uploads并返回编号，失败清本次暂存。API接收前身份/2并发、路由to_thread避免ZIP在事件循环运行。新只读存储盘点/UI实际计数、保存/禁用/测试引用保护、旧无标记unknown，不删除历史文件。18新专项及早先29组合测试实际通过，完整新回归运行中未称通过。

D-M02-RETENTION-013策略草案见modules/M02/CLEANUP_STRATEGY.md，A只回收24h归属可证明无引用临时副本，B手动确认；保存/禁用连接数据、原文件/未知旧副本均保留，策略未选择/执行not_run。PG真实、生产队列及模块验收不变，不关闭M02。旧8000尚需核对拥有者后加载新版，不能用旧188/10/19证据当上传改动已通过。

上传预检/只读盘点第一轮完整20261027T052911Z：206后端/10前端/20浏览器及类型构建pipcheck退出0、来源稳定。默认API还需安全加载新版；新增storage UI浏览器链路由独立新版本fixture真实API返回，不冒充旧8000已经新增接口。下一步核对进程树并获批重启，最终复跑后存证并提出清理策略选择。

## 上传预检与只读清理盘点最终检查点（2026-10-27）

最终206后端/10前端/20浏览器及类型构建pipcheck退出0，证据20261027T053552Z/results.json，93sources当前一致、五锁未改。单跑18项预检/盘点及原合成仓SQL/Parquet/goldenverify退出0见053644987970Z-preflight-extra/results.json。preflight-storage-review.md为局部self_review，不是M02最终audit/delivery。两轮完整回归通过，没有长期清理执行。

新upload_preflight在W1固定Job Worker检查新暂存/SHA/格式CSV编码与ExcelZIPXML，失败只清此次新UUID，成功原子转uploads才返回编号；API读body前认证/2并发，to_thread不在事件循环解析。source_profiles新upload.receipt仅时间/主体/哈希/大小，snapshot manifest可关联upload_id，旧数据兼容保留。storage_inventory现提供只读API/UI、已有SQLite mode=ro/没DB不初始化、有界引用/未知/忙/PARTIAL，无原路径或秘密输出，无删除按钮。

旧服务树检查中处理已验证子进程后创建时间/PID变化即停止后续动作，再只读确认原启动器与监听已退出，才获批启动新版；未处理变化PID。现在本轮exec20280，API12504/Vite2204/launcher3152，5173/8000 loopback健康200、当前用户；runtime-inventory.json为该时点真实维护数，不是业务数据或执行删除授权。原保存SQLite/历史副本/用户原件不删，新窗口仍核对拥有者，不继承session。

D-M02-RETENTION-013见modules/M02/CLEANUP_STRATEGY.md：推荐24h只回收可证明无引用临时副本，替代全部手动确认；保存/禁用连接数据、原文件、未知旧文件和证据均保护。尚未用户选择，策略执行/跨重启过期/引用竞争/幂等失败测试not_run。接下来应先询问该关键保留选择，不能拿继续推进代替自动删除授权。PG真实、生产队列、非Windows/正式认证/模块审计仍not_run，M02-C03 DO/not_verified/audit not_run，不closed/进入M03；M01原人工验收保持累计回归。

最终追加checkpoint45：D-M02-RETENTION-013待回答，状态awaiting_decision，M02仍DO；A24h自动安全临时回收或B手动确认，两者不清保存/禁用/原件/未知历史。尚无人工选择，不实施长期TTL。最终206/10/20证据不变，新增上传/盘点本机服务健康，下一轮应先定位pending decision再推进，不能重问已批准A凭证方案。

## 全模块PRD与模型服务路线（2026-10-27）

本轮用户明确要求将既有需求写入各模块PRD并采纳模型API前置顺序，D-ROADMAP-MODEL-014已登记（checkpoint46）。新增project-control/prd共13交付PRD、55需求、README/REQUIREMENTS/USER_REQUESTS与机器索引；新ROADMAP为路线真源。M04-A为独立pending模块，仅依赖M02；M03依赖M04-A；旧M04 ID保留为M04-B且依赖M02/M03/M04-A，不删除历史，M05以后沿用。当前M02-C03 DO不变、M01验收保留。

模型服务独立设置入口，M04-A先薄ModelProvider适配/真实测试，M04-B优先LangGraph图编排复用确定性安全/MCP/Worker/幂等。不默默安装框架或全套LangChain/外部LangSmith，不从文档请求推导具体模型/端点/预算/数据外发/付费批准；详细模块PLAN另确认。当前没有模型/Agent运行证据，皆not_run。

项目Skill只有project-pdca：入口及路线/交付/用户思维3引用已更新，原安装hash核对后获审批只同步个人安装4个文件，不改无关Skill/脚本/配置或凭证。本项目条件规则保留其他项目自主路线。AGENTS/PROJECT_BRIEF/PRODUCT_UX_PRINCIPLES/M02 plan与V0.1策划顶部补充同步；旧PDF/图未重新导出，不称其新版。

文档审计记录见project-control/modules/M02/evidence/20261027T062156667356Z-prd-roadmap/results-final.json、document-manifest-final.json与prd-roadmap-review.md：13PRD/55需求、模块依赖无环/M04别名/源决策/原pending保留/Skill一致性通过，5文档行为及21进度门禁测试退出0。通用Skill校验器缺PyYAMLnot_run，未增加依赖，替代仅已知frontmatter/引用/sync窄检查，首次自建regex语法错误修复后重跑，不伪称官方校验通过。

本轮93份原产品来源与最近206/10/20证据一致，无运行源码/锁变更，未重跑完整产品测试/服务重启；5173/8000仍PID2204/12504健康200，原本轮旧exec20280不应假设跨窗口可控制。文档完成后已只读检查M02 PRD各AC与source_profiles/storage_inventory及not_run门禁，长期清理执行未做、PG真实无独立授权实例，最终M02审计仍not_run。

D-M02-RETENTION-013仍唯一未答pending，路线变更不意味着选24h自动清理；等待实际答后再做对应过期/活动引用/安全执行。PRD写完并不是产品验收，不能取消required或进入新模块。M02delivery后下一步M04-A PLAN，不再直接M03。新窗口读ROADMAP/PRD入口/当前prd_ref和pending，不重建项目、不复制宿主凭证或访问公司平台。

## 新窗口前最终批准（2026-10-27）

用户“采用，但是我要开新窗口了，给我写一个新窗口的第一句prompt”明确对应D-M02-RETENTION-013 A。当前checkpoint48（以validate为准），pending=null、in_progress、M02-C03 DO；不再等清理选择。24h临时副本清理须可核实归属/创建时间且无保存或禁用连接/有效测试/活动请求引用，未知旧文件/原件/项目证据不删。本轮仅记录批准/更新需求计划交接，无产品代码、TTL运行或历史数据删除，retention-policy-execution仍not_run。

新窗口先恢复最新progress/HANDOFF/ROADMAP/PRD/清理策略及既有206/10/20真实证据，核对文件与5173/8000拥有者；不继承exec20280或旧PID为事实。下一步实现来源标记/草稿24h过期、安全引用竞态/跨重启恢复/有界清理与失败测试，测试通过后按批准范围启用。PG真实实例仍not_run，不暗装或取公司数据；M02未验收不closed，之后M04-A→M03→原M04=M04-B LangGraph路线已批准。


## 2026-10-27 保留安全底座实现中

revision49恢复后实现新临时来源标记、严格24h草稿失效、全请求跨进程Windows租约与跨重启非秘密引用收据；不是磁盘测试/任务恢复。只读候选校验不提供删除或scheduler，执行not_run。初26既有专项授权重跑通过，初新增18过1fixture缺kind失败已修待复跑；受影响旧证据stale。默认5173/8000未重启仍旧代码，不能拿其健康称新版运行。


## 2026-10-27 保留A R1最终检查点

R1来源标记、24h草稿过期、全请求合作进程Windows锁与跨重启非秘密测试引用底座完成。24专项/230后端/10前端、类型构建pipcheck及仓SQL/Parquet/goldenverify退出0；当前95源指纹一致，五锁和UI/契约未改。证据20261027T064537Z/results.json及20261027T0645333372854Z-retention-final/results-final.json、retention-review.md（局部self_review）。失败日志保留，原Worker安全断言未放宽。

没有执行接口/scheduler/TTL删除；R2异常暂存资格、执行冻结/路径引用重核/幂等故障/跨重启执行恢复、收据维护、用户预览及最近记录仍待实现。默认API旧版，未停止重启或浏览器重跑；M02 browser stale，不把旧健康当新版本。页面旧“策略待确认”文案需R2同步。PG真实及模块audit/delivery继续not_run，M02仍C03 DO，A不重问，验收后M04-A→M03→原M04=M04-B。


## 2026-10-27 R2执行层实现中

revision52恢复，95来源一致；服务原拥有者/200无重启。新retention_native/executor及执行专项实现中：DB写冻结+全请求租约、原生目录文件句柄固定/逐项删除、UUID持久journal与过期引用维护。尚未实测通过，无默认API/scheduler或data/connections清理；当前所有执行待验证。


## 2026-10-27 R2首回归及加强

首完整257后端/10前端/22浏览器及51原生/保留专项通过（20261027T071330Z）。独立真实fixture验证回执与草稿过期UI，默认API未重启/自动未启用。self_review发现status独立导入循环，已修且新加独立进程导入测试；加强保存DB native handle及SQLite写冻/别名替换测试，修link目标PublicError分类；最终复测待做，不拿旧指纹冒充加强版。无新依赖/宿主凭证/公司数据。


## 2026-10-27 R2最终检查点

内部原生安全执行/可信中断副本/引用维护/持久journal幂等恢复和只读回执、过期重测交互完成。最终54专项/260后端/10前端/22浏览器及类型构建依赖、仓对账/文档与进度门禁退出0，99source稳定、五锁/4核心Schema不变。证据20261027T071957Z及20261027T0719441916296Z-retention-r2-final/results-final.json/retention-r2-review.md（局部self_review）。独立导入循环与DB别名/写竞争保护已修并专项复跑；早期13失败日志保留。

真正删除仅独立新建测试UUID副本；新UIAPI回执/过期真实fixture通过，默认8000仍旧版本未重启，两个端口200/原PID，不能称默认新版/自动周期已启用。产品无执行端点/scheduler、automatic_cleanup=false。下一步有界周期/忙预算/停止恢复/周期状态独立验证后核完整拥有树安全加载启用，不重问A。未知历史/原文件/保存与禁用数据/有效测试及证据保护，PG真实和模块audit/delivery仍not_run，M02仍C03 DO，随后M04-A→M03→原M04=M04-B。


## 2026-10-27 Excel浏览器桥接诊断

核心55专项/261后端/10前端等已过且产品源码没有再改变。浏览器Excel旧5秒等待与独立API30秒同步均失败，实际拦截器只取到246字节multipart骨架导致422。使用同一工作簿完整字节填入真实文件控件、明确保留Buffer与长度，4644字节实际上传/200、解析/MCP/日期/100行/禁用所有断言通过。未伪造响应/跳过/删除或放宽断言，保留失败与正例探测证据；全23浏览器复跑中，原产品代码逐字节复用55/261等真实证据，不冒充新执行。


## 2026-10-27 最终R2/过期能力/Excel桥接检查点

最新20261027T0841324874169Z-browser-final全23浏览器退出0，99sources稳定。55专项/261后端/10前端/类型构建pipcheck原实际过，此后唯一变更source-onboarding测试，产品/相关测试/合同/锁字节一致，reuse.json明确复用原指纹，不称重跑。仓对账和文档/进度门禁新跑退出0，最终review self_review不关闭模块。

Excel失败根因是路径文件在Chrome拦截只提供246字节multipart骨架，422；同一合成工作簿完整字节进真实文件控件且原Buffer转发后4644/200、真实预检/导入/MCP/原日期/101行/禁用全断言过。保留失败/探测，不删/skip/弱化原断言、不删原数据。来源测试均独立当前代码真实API；旧expiry字段缺失仅显式兼容响应fixture。新expires_at来自服务端，不让旧默认API暗示已支持24h。

默认API未安全加载/自动周期未启用，原端口健康无重启/杀进程。下一步有界周期/忙预算/停止恢复/周期状态，独立实测后核完整拥有树安全加载按A启用；默认执行/PG真实/模块audit及delivery继续not_run，M02-C03仍DO，之后M04-A→M03→原M04=M04-B。建议同目录新窗口读取最新进度和本交接，不能复用旧exec、绕过保护或复制宿主凭证。


## GitHub同步准备（2026-10-27）

用户明确授权在Albert-WuCSU新建仓库并push、补README。账号经CLI联网核实，采用private最小披露；原项目无Git，现main初始化。README/ignore完成，凭证/宿主配置/依赖/用户data/connections/tmp/download wheels排除但不删除。常见令牌/私钥/JWT/凭证字面扫描仅显式test sentinel，非全面DLP认证；远程create/push尚未运行。源码与M02阶段/默认清理/PG真实门禁不变，此操作不是部署或模块验收。


## GitHub私有仓库已创建

Albert-WuCSU/intelligent-data-workspace创建退出0，repo view确认private/ADMIN。README、安全ignore和逐字节暂存核对完成，没有真实密钥（测试哨兵不当凭证）。本仓库使用GitHub noreply作者，仅local配置；未改全局credential，commit/push待运行。原CRLF和二进制保留不影响原证据hash；文档旧空白未为commit批量修。M02仍DO/自动启用PG真实not_run，不是部署。
