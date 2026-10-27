# M02 专属测试数仓与自建 MCP

2026-10-26；M02-C02 PLAN（数据来源与准备已获用户批准；引擎/MCP方案已获 D-M02-ENGINE-003 批准）。旧C01候选保留于 plan-C01-enterprise-candidate.md，不再自动推进企业数仓接入。

## 用户价值与事实

用户希望拥有可控、可公开展示、与任一真实企业无关联的测试数仓，后续产品设计依托该数据。用户本轮同意此前明确提出的独立合成路线，并要求准备数据、建立数仓。不是公司数据抽取、导出或来源隐瞒授权。

业务用户沿用M01会话、显式黑白主题、历史、真实pipeline和结果卡；无需配置数据库、填写JSON或SQL。管理员一次配置自有数据源，开发者查元数据、只读查询与失败诊断。合成数据标记和质量状态分开；真实查询合成数据不等于真实经营结论。

目标路径：管理员确认测试数据与来源→初始化专属数仓→自建MCP读取真实目录/字段→批准只读查询→真实状态/预览→后续M04自然语言、M05资产、M06/07图表报告。M02不提前实现完整Agent或正式企业认证。

当前已做的是独立生成器/测试数据，不是已运行的数据库或MCP。数据未下载自公司或公网，不参考专有字段、真实记录、公司分布、指标或DDL。M01不重建。

## 数据路线与授权边界

选定来源：independently_generated_synthetic；所有ID、日期、价格、区域、事件独立生成。TEST为虚拟币种，不可换算成真实营业额；时间为UTC、90个模拟日期。公开作品可注明“虚构企业合成测试数据”，不得伪称真实客户案例。

若未来考虑真实公司数据，需数据所有者/安全团队批准用途、具体字段/分区、导出目的地、公开展示、保存期限及处理流程。查询权限不等于外用权，少量分区不等于低风险。处理应在批准边界内完成，任何源记录离开边界前需审核；简单改名、hash、日期平移不能保证匿名。直接标识、自由文本、稀有组合、精细时地、精确商业金额、关联可识别性与公司商业秘密均需评估。受限审计保留真实溯源，不能为隐藏来源删除历史证据。无批准不取数，公开作品继续用合成版。

## 五张企业通用表（已生成种子，数据库待初始化）

| 表 | 粒度/关键字段 | 用途 |
|---|---|---|
| dim_customer | customer_id；region_group、segment、registered_date、snapshot_date | 分群、客户维度 |
| dim_product | product_id；category、unit_price_cents、currency、snapshot_date | 品类、价格维度 |
| fact_order | order_id→customer_id；ordered_at、paid_at、status、channel、gross_amount_cents、discount_cents、paid_amount_cents、partition_date | 订单、支付、渠道分析 |
| fact_order_item | order_item_id→order_id/product_id；quantity、unit_price_cents、line_amount_cents、partition_date | 品类金额与订单守恒 |
| fact_event | event_id→customer_id/order_id；session_id、event_type、event_at、channel、partition_date | 订单会话事件与流程测试 |

默认1000客户、100商品、3000订单，关联明细与事件由生成器产生；没有姓名、手机号、邮箱、精确地址、企业标识、自由文本。JSONL用于无额外依赖的可复现种子，manifest保存字段、行数、哈希、来源、生成参数与局限，不是最终数据资产。

维表一份快照、事实表按模拟日期逻辑分区。自有合成数据不受公司“一两个分区”限制：90天便于测试趋势/对比；时间跨度仍不代表真实季节性。事件由订单会话生成，不包含所有无订单访客，不能作为真实总体转化率估计。M09/10/11若需归因/预测/AB/DID，要另建适用数据和方法检查；不能承诺这五表覆盖所有未来任务。

## 引擎与MCP选型：D-M02-ENGINE-003

A（推荐）DuckDB分析数仓 + 本地Parquet/种子文件 + 自建Python MCP（优先官方SDK，stdio仅本机由后端管理）。优点是单文件、低运维、真实分析SQL、适合小型个人测试仓；不足是非Spark/Hive、多租户服务/并发写入有限，需独立Worker和治理。保持PostgreSQL为M05目标控制面，不以DuckDB替代身份/历史存储。

B PostgreSQL测试分析库 + 自建MCP：更接近多用户数据库，权限和事务成熟；需安装/运行服务、驱动和迁移，维护比单文件高。也不等于Spark/Hive兼容。SQLite可作为零依赖临时校验库，但不推荐作为长期分析引擎，不能暗中替换待选方案。

新依赖duckdb、pyarrow、mcp、sqlglot当前均未安装。本轮只用Python标准库和已有pytest；无新依赖安装/联网。候选DuckDB/SQLGlot通常MIT、Arrow通常Apache-2.0、MCP SDK通常MIT，准确版本、发行物许可证和Python3.12/Windows兼容必须在安装前核验；不宣称已核验。允许依赖下载仍按环境审批。优先最小依赖集合，pyarrow若DuckDB可直接写Parquet则不必安装。

## 拟定合同与安全实现

FastAPI现有AuthContext→MetadataProvider/ExecutionProvider→真实MCP客户端→自建MCP服务→自有DuckDB。不能绕过MCP直接在产品伪造工具响应；MCP握手/工具Schema/实际调用均要留证。不是公司服务改名包装。

- MCP限定工具：list_tables、describe_table、list_partitions、submit_query、get_query_status、get_query_result；cancel_query仅真实中断验证通过才开放。工具列表不能由浏览器随意扩展。
- 元数据来自已初始化数据库目录；返回表/字段类型、粒度、关系、分区、synthetic来源与版本。独立通用描述，不复制公司DDL。
- 查询计划绑定服务端主体、租户、允许表/字段、方言、预算及确认指纹；默认只读受限模板。任意SQL须AST限制与引擎校验，不靠正则过滤；禁INSTALL/LOAD/ATTACH/COPY/DDL/DML/PRAGMA/文件及网络函数、多语句、外部路径和不受限UDF。
- 数据库只读打开仍不足：引擎层禁外部访问/扩展自动安装加载并锁定配置（具体版本支持需实测），目录/进程隔离、防读任意本机文件；客户端不传任意文件路径或主机。只读连接不代替这些门禁。
- 初期仅本机开发身份；服务端授权每次校验，跨主体/租户任务不可读。stdio服务不公开HTTP端口；若远程MCP另决策TLS/认证/部署。
- 真实任务句柄、状态、行列、预览截断、时间/trace及数据版本可追溯；进程超时/退出不能伪称查询取消。单任务并发、限行、限时/内存及Worker回收要实测；预算无法约束则fail closed。
- 返回QueryPreview而非冒充完整DatasetAsset；金额保持整数cents与TEST币种。合成来源不是指标认证或Quality.PASS。完整资产/下载在M05合同下实现；本机公开合成文件不自动授权未来真实数据外发。
- 沿用QuerySpec/Task/ConnectorCapability，新增Schema由Pydantic生成前端类型。SQL方言标duckdb（若A获批）；不能标SPARK3/HIVE已兼容。

## 分步交付

1. 数据准备（已批准）：可复现独立生成器、五表种子、manifest/golden与关联/金额/时间检查；只服务测试，不改业务页成伪成功。
2. 方案A获批准并依赖安装获准后：核验版本许可，建立数据库/Parquet、DDL/索引或视图、版本清单，重建幂等与不覆盖已有数据；golden与真实SQL对账。
3. 建MCP服务/客户端，鉴权与SQL安全、状态/取消/结果，故障与资源边界验证；未接入时保留既有拒绝。
4. 管理员接入与开发验证切片、主题/会话/真实pipeline回归；真实端到端演示并self_review，用户验收后才closed。

## 验收矩阵

数据：固定seed重现、五表主键/外键、明细总额、支付状态、日期分区与事件一致性；故障样例必须被拒绝；manifest如实标合成。当前检查只针对生成不变量，不是隐私认证、统计合理性或用户研究。

数仓：真实导入行数/类型/约束、只读连接、golden SQL、分区与时区、重复重建不覆盖、版本哈希。

MCP：真实握手/工具调用、表字段查询、SQL成功/失败/空/截断、权限拒绝不换路、任务幂等/超时/取消真实性、文件/网络/扩展逃逸负例、日志秘密、跨主体/租户访问。

产品：管理员完成接入测试而业务用户不用SQL/JSON；正常/未配置/拒绝/失败/空态可理解且有下一步；黑白主题/历史/结果层级不回归。既有scripts/check.py --browser；M02新增专项记录真实命令、退出码、环境、指纹。

数据检查已执行，数仓/MCP/UI集成仍not_run。RG-REAL-MCP目标随已批准数据源切换至自有仓库，但不是测试豁免；Spark/Hive兼容未来另验。正式认证、持久化与部署门禁仍保留。

## 风险与回滚

合成数据不证明市场需求、企业兼容或真实模型效果；不从真实企业分布学习生成规则。M02新增引擎依赖需批准。目录/运行时文件隔离与SQL限制为高优先级实现门禁。断电/重启和Worker状态恢复需明确限制，不宣称exactly-once。

禁用自建连接器恢复未接入状态；不删M01会话/证据。版本数据生成拒绝覆盖已存在目录；清理、公开发布、迁移均按权限。生产环境部署不是本轮范围。

## 最新DO检查点

D-M02-ENGINE-003已由用户“采用”确认。真实数仓/Parquet及stdio MCP后端建成；80项后端测试、pip check、实际SQL/Parquet对账与真实MCP演示通过。具体证据以progress引用为准，运行说明WAREHOUSE.md。FastAPI/网页接入、Worker硬资源/恢复验证及最终模块审计仍待做，M02未closed。原计划中的“待初始化/未安装”描述为计划时边界，当前以本检查点和progress为准。

## API/UI实际检查点（2026-10-26）

已完成本机真实API/MCP/DuckDB网页预览，管理员验证与开发确认分层；后端93、前端10、浏览器11及类型/构建/依赖通过，具体唯一证据见progress。提交代际过期/不明提交不盲重提、回执归属与不保存数据快照已验证。旧M01基线累计回归保持。下一步仍为Worker/OS硬限额、故障恢复及完整模块审计；未closed/未进入M03，不宣称生产认证或自然语言Agent完成。
