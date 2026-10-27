# M02 供应商能力映射（仅工具说明发现）

2026-10-26；未调用供应商。本文件不记录端点、header或凭证值。

| 产品能力 | 会话工具 | 已知说明与缺口 |
|---|---|---|
| 限定范围找表 | metadata.search_table / smart_search_table | 搜索/分页；自然语言找表要求员工身份header；不证明搜索已按行列或租户授权过滤 |
| 字段/DDL | get_columns_by_table / get_create_table_ddl | 库表参数、类型/DDL；需实际响应确认字段形状和敏感分级；DDL仅专业诊断 |
| 最新分区 | get_partition_names_by_page | 官方说明推荐分页查最新分区；排序、返回格式、区域和权限需验证 |
| 数据新鲜度 | get_last_update_time | 表更新时间不等于业务数据完整性或指标认证 |
| 元数据部署区域 | 上述 metadata 工具 | 工具标记当前 sha，多数无 env 参数；不可宣称已支持 sgp 元数据 |
| SQL执行 | adhoc.bigdataQuery | SPARK3/HIVE/TRINO等引擎列表；默认 STARROCKS_HIVE，产品须明确指定引擎；同步 submit+poll；方言/表权限仍需实测 |
| 异步提交 | bigdataQueryAsync | 说明仅用于用户明确要求 async/fire-and-forget；本轮没有授权也没有调用 |
| 状态与结果 | adhoc_get_query_status / adhoc_get_query_result | 前者单次快照，后者运行中等待；FAILED需inspect状态。响应包裹、状态值、columns/rows形状未验证 |
| 执行诊断 | adhoc_get_query_log | 日志可能含SQL/敏感信息；不向浏览器透传，按需只取安全错误分类 |
| 下载 | adhoc_get_download_link | 返回URL、CSV/ZIP和Authorization；密钥不能出浏览器；完整性与权限重验未验证，初版默认关闭 |
| 取消 | 未列出 | 目录无取消接口，不支持产品承诺；本地停止等待不等于取消引擎 |
| 预算 | EXPLAIN说明、无明确cost硬限制接口 | 不证明费用估计、扫描行/字节硬上限或可取消。LIMIT不是扫描预算 |
| 行列权限 | Adhoc说明权限拒绝及DSC申请入口 | 证明工具描述预期拒绝，不证明RLS/CLS、用户身份映射、导出一致性已通过 |
| 通知 | enable_tp_notify参数 | 默认不开启；外部通知需单独授权 |

禁止调用已废弃 adhocAiAssistant；SQL由产品受控编译/M04 Agent产生，而非依赖已废弃工具。禁止把 sandbox建表/字段修改/发布类工具纳入允许工具清单。读取权限列表需确认账号范围，不默认枚举全库。

Adhoc调用必需 model_name、agent_name 与规范 query_name；region为sha/sgp，STARROCKS_CLUSTER还需集群参数。appid前置网络/合法注册条件另核对；不读取或复制宿主 HERALD_TOKEN。role_name留空；limit_disable不启用。

## 验证顺序

1. 用户选平台后提供非秘密协议说明/应用接入条件，确认是否允许产品进程独立调用。
2. 用户安全配置产品身份，授权后仅握手、工具schema与指定表元数据验证；保存脱敏响应结构和时间，不存行样例/令牌。
3. 批准小分区模板、引擎、预算与执行动作后才提交一次。同步/异步由平台与授权条件决定；查询状态、首行/总行语义与结果对账分别留证。
4. 权限负例、超时、幂等/不明提交、错误脱敏。缺能力明确 unknown/unsupported，不用mock宣称真实通过。

本轮事实仅为可见工具说明与本地源码/环境核对；工具可调用性、产品连接、完整数据访问均未验证。
