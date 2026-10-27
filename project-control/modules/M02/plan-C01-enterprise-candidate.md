# M02 真实元数据与 SQL 执行接入计划

2026-10-26；M02-C01；PLAN，待 D-M02-PLAN-001。推荐方案不是实施或生产查询授权。

## 用户任务与范围

- 业务用户需要知道数据是否可用、失败后怎么办，而非配置平台令牌；默认仍使用已验收会话工作台、显式黑白主题、历史、顶部真实状态和结果摘要。M02 不开放尚未实现的自然语言取数。
- 管理员/接入人员需要安全配置一个数据源并判断鉴权、权限、执行与结果是否各自成功。最短验证路径：连接器入口→查看安全配置指引与允许范围→验证连接→选择范围内表/字段→确认受控查询→真实状态与结果预览。专业 SQL/Schema 仅开发工具内可查。
- 成功标准：接入人员无需把秘密输入浏览器，即可在一个明确批准的表/分区完成字段核对和一次只读预览；未配置、拒绝、超时、空结果都有可理解原因和下一步。属于待验证设计假设，不是用户研究结论。
- 本轮仅规划；M02 最小切片负责连接器与受控执行。自然语言理解、L1/L2/L3/L4 路由与任意 SQL 生成在 M04；业务口径认证在 M03；持久任务、会话与资产生命周期在 M05。预览不冒充完整 DatasetAsset 或已认证业务结果。
- 不重建 M01，不新增前端框架，不接全库搜索、不写生产数据、不建沙箱表、不外发、不部署。后续调用真实服务须获得资源与动作级批准。

## 接入路线与取舍（D-M02-PLAN-001）

A（推荐）：复用企业元数据 MCP + Adhoc 执行 MCP，由 FastAPI 后端通过受治理适配层调用；先一个连接器、一个区域 sha、一个经批准引擎（优先 SPARK3，须实际支持），限定表/字段/分区。先验证协议和身份，再决定 MCP 客户端实现。减少自建 Spark/Hive 网关成本，但依赖企业服务授权和网络，非通用客户即插即用。

B：用户指定另一个可部署 MCP，沿用相同 MetadataProvider/ExecutionProvider 合同；更便于跨企业，但需重新核实工具、传输、引擎、授权与结果协议，工作量未知。

C：通过平台官方 API/驱动实现内部治理适配器，不依赖宿主会话 MCP；控制力更强，但增加认证、驱动、升级、网关与运维负担，不能绕过原平台权限。没有服务端点时不可假装可用。

选择 A 只批准方案和后续本地实现范围，不授权读取宿主配置、复制 token、安装新包、生产查询、下载或部署。具体账号/表/字段/分区、预算与许可另行确认；不要求用户在聊天发送秘密。

## 现有环境与新增依赖

已核对本机 Python 3.12.14、FastAPI 0.162.0、Pydantic 2.14.1、httpx 0.28.1、pytest 9.1.1；现有 React/TypeScript/Vite 与锁文件沿用。MCP Python 包尚未安装。本轮没有联网安装或查最新版本。

优先评估服务实际传输（Streamable HTTP、旧 HTTP/SSE、或 stdio）及 initialize/tools/list/tools/call、协议版本和错误响应，不能只凭工具清单选 SDK。远端 stdio 不是默认方案。httpx 可用于受限 HTTP API 适配（不是完整 MCP SDK），只能在官方接口/协议证据明确后决定。

候选 MCP SDK：维护成本低于手写完整会话；版本、许可证、Windows/Python 3.12 与目标内网兼容待联网核实，新增依赖另开选择/安装审批。现有 httpx/FastAPI 通常为 BSD-3-Clause/MIT、Pydantic/pytest 通常为 MIT，最终以安装分发物许可证核验，不在此宣称已完成许可审计。企业服务使用授权与费用也待确认。

最小执行切片使用服务端受限模板编译，不开放任意 SQL 输入；避免为 M02 临时实现不可靠 SQL 正则防火墙。若要提前开放任意 SQL，则另决策引入 SQLGlot 等解析与引擎验证，且需扩充门禁；解析器不能证明上游权限或扫描成本。

## 架构与身份边界

浏览器 → FastAPI（既有 AuthContext）→ ConnectorRegistry/Policy → MetadataProvider + ExecutionProvider → 各自 MCP/官方服务。供应商工具名、引擎、区域在适配器内固定映射；浏览器不得指定任意端点、工具、租户、角色或 headers。

1. 产品必须获得独立、合法的身份配置；会话工具可见≠真实调用成功≠产品进程可部署。禁止读取 .codex/配置或宿主 token 来替产品接入。
2. 首个验证限定 loopback 开发身份、明确单人试点。服务端将固定开发身份绑定到明确批准的上游账号与白名单，不把同一上游账号共享到多租户产品。真正企业用户授权映射未通过前拒绝生产模式执行。
3. 管理配置是服务端部署配置/秘密引用；浏览器只显示 configured、到期/错误类别和安全配置说明，不接收/回显 token。访问需既有身份校验与管理员角色门禁（本地限定接入人员；非正式 RBAC）。
4. 元数据权限未证实，搜索只能在批准资源范围内进行；先服务端白名单过滤再返回。禁止 get_db/get_tables_by_db 全目录作为默认入口。禁止权限拒绝后改账号/引擎/区域/接口兜底。
5. 允许目标主机/端口与固定区域；TLS 默认校验。若服务仅内网 HTTP，要说明明文风险并取得网络隔离风险接受，未接受不发送凭证。禁重定向转发 Authorization；响应/日志限长、脱敏且不缓存敏感原文。
6. 任务与结果每次读取依据 tenant+principal+连接器授权重新校验，query_id 属于本地任务的内部映射，不能由浏览器任意查询。上游行列权限需服务证据，白名单不能替代完整 RLS/CLS。

## 接口与合同（拟定，非已存在）

沿用现有 /api/v1/capabilities、QuerySpec、Task、AuthContext；新增合同由 Pydantic 导出，禁止手改 api.generated.ts。原 /tasks 的未接入语义在执行路径真正可用前不改成成功，接口变更需生成类型与回归。

- MetadataProvider：search(scope, keyword, pagination)、describe(scope, full_table_name)、partitions(scope, table, page)。返回 canonical db.table、字段原类型/归一类型/分区格式、来源区域、获取时间、权限验证范围；未识别类型保留 raw_type 并拒绝不支持的结果映射，不强行塞入现有六类 FieldSchema。
- ExecutionProvider：submit(approved_plan, identity, idempotency_key)、status(handle)、result(handle, bounded_preview)、cancel(handle)。未支持的动作返回明确 unsupported；不伪造 CANCELLED。
- Proposed API：GET /connectors（安全状态）；POST /connectors/{id}/verify（管理员）；GET /connectors/{id}/tables 与 /tables/{table}/schema（授权过滤）；POST /execution-previews（开发工具受控模板，显式确认）；GET /execution-previews/{task_id}/status、/result。下载不作为最小切片必备。
- ApprovedQueryPlan：服务器持有身份/资源范围、固定引擎/区域、解析后的字段/分区与预算、确认版本和 fingerprint。用户输入 tenant、平台 query_name、appid、role_name、工具名均不作为可信授权。
- ExecutionReceipt：task_id、上游句柄（内部）、真实状态、提交时间、来源、trace_id、submitted/unknown_outcome。Task 状态不足的 timeout/unknown/expired 以独立执行详情表达，不把本地停止等待当成 SQL 已停止；如需合同枚举扩展先评估消费者兼容。
- QueryPreview：columns（类型）、rows、returned_row_count、reported_total_rows（可空）、truncated（true/false/unknown）、retrieved_at、execution_source、verification_coverage、limitations。total_rows 的供应商语义未核实时不宣称是全量；首50行只是预览。零行可为真实成功，但不杜撰“没有业务发生”。
- DIRECT_CERTIFIED 不用于表直查认证；只有执行结果和来源证据，不等于指标认证或 Quality.PASS。M02 不凭预览发布完整资产，M05 再实现受保护完整数据引用。

## 能力与供应商映射

详情见 capability-map.md。工具说明仅是发现证据；连接器 configured 与 verified 分开，metadata/async/cancel/cost/ACL 未实测保持 unknown 或已知 unsupported。M02 初版不承诺取消、扫描费用估计、全量下载、断线恢复或 sgp 元数据。

## SQL、预算与状态门禁

- 初始仅单表模板 SELECT 显式字段 FROM 批准表 WHERE 经批准分区/过滤 LIMIT N；N 默认50且建议最大100，具体值待权限/预算批准。字段与表只来自可信目录校验；值采用方言安全编码/参数绑定（供应商是否支持绑定待验）。不拼接用户 SQL；拒绝多语句、注释片段、子查询、自定义函数、JOIN、DDL/DML、导出、UDF与外部路径。
- 要求批准有限分区和单任务并发；无批准分区的表默认不能执行。LIMIT 只限制返回行，不限制扫描。上游扫描预算/硬超时若不支持，保持成本能力 unknown；只有经批准的小测试分区且风险接受才做实际试点，不能把本地超时称成本封顶。
- query_name 由后端生成 intent|subject|goal|db.table|shape，<=200字；model_name/agent_name 固定应用归属。appid 按工具要求先核对运行网络与合法应用注册，绝不遍历或拷贝宿主秘密；role_name 留空，limit_disable 禁用，禁 SHOW FUNCTIONS。
- 提交不盲重试。幂等记录绑定身份、计划指纹和确认版本；同键异内容拒绝。提交超时若可能已执行，标 outcome_unknown 并停止自动重提，人工/上游查询核对；内存幂等只当前进程有效。无重启恢复/持久映射不得宣传 exactly-once。
- 供应商同步 bigdataQuery 通常包含等待；优先核实是否可获早期句柄。异步工具仅在用户明确授权异步提交后选用，工具说明要求不得默认 fire-and-forget。若同步路径无早期句柄，UI 只显示“提交/等待平台回执”，不声称已知道 RUNNING。
- 有句柄后以单次 status 快照有限退避轮询；用 actual currentStatus 映射。FAILED 不等于空结果；响应 success=false 与业务 status 分别判断。端点超时与引擎失败分开；上游 raw queryLog 不回显浏览器。
- 工具目录没有取消接口，MVP 不展示可用“取消SQL”。若停止本地等待，提示上游可能仍运行及平台处理途径（未配置处理途径不编造链接）。
- 下载后续独立切片：按任务身份再鉴权，后台使用上游 Authorization 取流，不给浏览器 token；只允许预设源主机、不转发到重定向目标，限制大小/时间、检查 CSV/ZIP 与文件名、公式注入策略、数据驻留。未经导出权限/保存策略确认默认关闭。

## 实施步骤（待批准）

1. 协议与权限盘点：安全配置说明、受限连接器注册、能力三态；授权后握手/工具schema验证，保存脱敏证据。无法独立合法配置则不执行后续真实调用。
2. 元数据切片：限定表的字段/分区、类型映射、拒绝/超时；管理员诊断与业务只读能力提示。未知权限不展示全集目录。
3. 执行切片：批准模板与范围、幂等映射、真实回执/状态/预览及质量范围；未配置保持原拒绝。M02 对话不假装已有 M04 Agent。
4. 安全/错误与回归：故障注入和真实小分区对账；管理员向导及开发验证、黑白主题/历史回归。更新 DEVELOPＭENT 文档（实际文件 DEVELOPMENT.md）、Schema/类型及证据。
5. self_review 审计并请用户验收。没有真实集成，最多局部 local_ready，不关闭 M02；若请求延期，另登记明确风险接受与正式发布补验门禁。

## 验收矩阵

| ID | 可观察验收 | 检查与门禁 |
|---|---|---|
| M02-T01 | 配置缺失、过期、拒绝、协议不兼容可区分；无秘密回显 | 单元/契约，模拟 JSON与SSE/工具错误；真实握手另记 |
| M02-T02 | 白名单内字段/分区可核对，范围外无元数据泄漏 | 契约+真实指定表对账；未知类型、分页、分区格式 |
| M02-T03 | 仅经批准有限模板可执行，修改表/字段/值无法扩大范围 | 单元安全；多语句/注释/路径/函数/无分区拒绝 |
| M02-T04 | 真实提交、成功/失败/空、预览截断语义准确 | 真实小分区查询与平台结果对账，不造业务数字 |
| M02-T05 | 重复提交不盲重提，提交不明与轮询超时有准确状态 | 故障注入；取消不支持、重启限制与预算提示 |
| M02-T06 | 他人任务/句柄不可读，原平台拒绝不绕路 | 租户/主体/角色隔离单元+真实账号权限验证；生产映射另门禁 |
| M02-T07 | 日志/错误/浏览器/历史不含 token 或原始敏感工具响应 | 哨兵秘密测试；URL/重定向/SSRF、TLS、数据驻留检查 |
| M02-T08 | 管理员完成验证路径；业务页保留主题/历史/真实pipeline | 前端单元、类型/构建、浏览器走查；不是真实用户研究 |
| M02-T09 | 任一下载未批准时不可用；批准后每次重验权限 | 最小切片默认禁用，导出切片需真实证据才开放 |

所有 M02 功能/集成测试本轮均 not_run。待实施后用既有 scripts/check.py --browser 复跑；新增检查保存真实命令、退出码、环境、源码指纹，不把规划证据当测试通过。RG-REAL-MCP、RG-TENANT、RG-MVP-E2E、RG-DEPLOY 保持 not_run。

## 风险、回滚与下一选择

最高风险是产品独立身份/权限映射和内网传输；方言、扫描预算、取消与响应结构均需真实验证。首期一个平台降低成本，但耦合企业环境；合同隔离用于后续替换。实际工作量取决于凭证、网络与接口证据，不承诺日期。

回滚通过禁用连接器/执行开关恢复“未接入”行为，不删会话、不删证据、不撤销 M01 已验收约束。若可能已提交上游任务，关本地服务不是取消，需先核对上游状态。任何 M01 源码变更记录影响并复跑相关检查。

下一阻断选择 D-M02-PLAN-001：批准推荐 A 的 M02 方案，或改平台路线。批准后先准备本地合同/安全配置与协议调查；真实调用前再确认允许表/字段/分区、身份配置、引擎、预算和具体动作。秘密通过安全渠道由用户配置，不粘贴聊天。
