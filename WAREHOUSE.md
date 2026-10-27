# 最新连接器切片（2026-10-27）

用户可在连接器首页“新增数据源”上传DuckDB/CSV/Parquet或填写受控本机路径，测试后保存并刷新复用，选择表看到表头/原类型/前100行；也可导入非秘密本地连接JSON。详细操作、存储及限制见 CONNECTORS.md。

**日期字段不被删除。连接器没有时间或其他筛选控件；日期列原样展示，不按字段名猜含义。** 下面旧日期/开发字段筛选说明是历史切片，不再作为当前用户流程。

已有的专属合成仓作为可选内置例保留，用户数据通过独立MCP/只读快照查询，不强标合成或TEST。远程数据库/HTTP MCP接入仍未完成，不把入口信息声明为连接能力。实际源码指纹与回归证据见progress引用。

---

# 专属合成测试数仓与本机 MCP

此数仓不包含真实公司数据，所有记录由本项目独立生成。数据库/工具是真实执行，数据为合成；不能用于证明企业经营结果或真实模型效果。

## 文件与环境

- 种子：`data/demo/synthetic-v1/`，JSONL及来源/质量manifest。
- 数据库：`data/warehouse/synthetic-v1/warehouse.duckdb`。
- 独立设计DDL：同目录`schema.sql`；真实导入行数、数据库SHA、SQL golden检查见`manifest.json`。
- Parquet：同目录`parquet/`，五个表各一份快照。日期为逻辑分区字段，**不是**物理每日分区目录。
- 1000客户、100商品、3000订单、6125订单明细、11671事件；金额为整数TEST cents，时区UTC，日期为2025年1—3月模拟场景。

Python3.12/Windows本机验证。DuckDB1.5.6、MCP SDK1.30.0、SQLGlot30.24.0；选已存在1.x引擎/SDK版本控制主版本API变更，未承诺最新版2.x兼容。新增依赖在独立锁文件，不更改M01原锁或全局运行时。

新环境须同时安装基础和数仓锁（网络/安装按权限审批）：

```powershell
./services/api/.venv/Scripts/python.exe -m pip install -r services/api/requirements.lock.txt -r services/api/requirements.warehouse.lock.txt
./services/api/.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e services/api
./services/api/.venv/Scripts/python.exe -m pip check
```

DuckDB发行包主LICENSE为MIT，experimental/spark目录还包含Apache-2.0许可；未使用/验证Spark包装。SDK和SQLGlot元数据MIT，依赖中还有Apache-2.0/BSD/PSF等；发布必须保留相应发行物许可证。实际安装元数据和轮子摘要保存在本模块证据。没有进行全面供应链安全审计。

## 重建与验证

首次初始化（版本目录已存在会拒绝覆盖；不要重复运行默认build）：

```powershell
./services/api/.venv/Scripts/python.exe -m data_workspace.warehouse.build
```

若重建，选择新版本目录；不自动删除旧仓或清理未完成目录。种子文件需通过哈希、字段、关联、金额、时间核验。初始化器具有本机写文件能力，但**不是MCP允许工具**。

真实MCP演示（会启动/关闭自己拥有的stdio子进程，不打开公网端口）：

```powershell
./services/api/.venv/Scripts/python.exe -m data_workspace.warehouse.demo
./services/api/.venv/Scripts/python.exe -m pytest services/api/tests -q
```

演示实际调用initialize/tools/list/tools/call，查五表、订单字段、90个日期分区，执行受限预览并验证危险请求被拒。输出明确保留合成来源与WARN质量范围。不会修改数据库，也不会连接公司MCP。

## 连接器合同与权限

`OwnedMCPClient`现已接入FastAPI与网页连接器/开发预览。API启动时为本机固定身份建立受控stdio会话，退出时关闭自己拥有的MCP子进程；启动器默认启用，普通Settings默认关闭。自然语言工作台仍没有M04 Agent，不称网页已能自然语言问数。

允许工具：list_tables、describe_table、list_partitions、submit_query、get_query_status、get_query_result。表参数为固定五表的bare name；submit_query要求table、columns、start、end_exclusive、limit和幂等键。只读模板、最多90天/100行，参数绑定与AST拒绝非模板表达式。SQL输入、任意文件路径、数据库账号、租户、外部URL或工具名不从浏览器接受。跨表JOIN、聚合与自然语言SQL需M04扩展安全合同后开放。

仅服务器配置的local-developer/local-workspace/development身份可由客户端启动MCP。stdio进程是本机用户持有的会话能力，不是企业认证或多租户服务。同一会话内任务幂等；不同MCP进程不能读取彼此任务。数据库只读连接、外部访问/扩展自动加载安装关闭、配置锁定、128MB引擎内存、单线程、禁磁盘溢出；单查询引擎3秒中断保护。引擎设置不等于OS级沙箱或整个Python进程内存/CPU限额；部署前须进一步审核Worker/OS隔离。

submit_query工具等待真实执行回执，不是fire-and-forget；运行中状态来自实际执行服务。最多一个活动查询、100个进程内回执，超额拒绝。未提供取消工具/下载接口，不能声称已实现SQL取消。任务、幂等、结果随MCP进程关闭消失；正式持久化M05实现。接口读取权限每次检查本地身份；这不是正式用户登录/行列ACL认证。

## 已验证与剩余工作

已验证：本机DuckDB实际SQL与预期结果、五表/Parquet、MCP真实握手/预览、空/截断/幂等/跨会话负例、危险表达式/文件/写入/配置修改拒绝、原后端回归。

未完成：正式身份/持久化、OS级Worker强制资源/恢复策略、最终完整模块交付审计、生产部署、Spark/Hive兼容。M02尚未模块验收或closed；不存在真实用户研究。

## 本輪检查点补充

只读复核现有数据库与五份Parquet（不重建/覆盖）：

```powershell
./services/api/.venv/Scripts/python.exe -m data_workspace.warehouse.verify
```

该离线验证器仅读取固定本机版本文件，能读取Parquet但不是MCP工具；运行时MCP仍禁止外部文件访问。验证实际库表/Parquet行数、订单明细金额守恒、SQL预期结果及文件指纹。

## API 与网页执行切片

GET /api/v1/connectors/owned-synthetic 返回安全连接状态；POST 同路径 /verify 从MCP真实读取五表。GET /tables/{table}/schema 读取实际字段。POST /api/v1/execution-previews 要求受限 request、confirmed=true、idempotency_key 与当前 execution_generation。GET /execution-previews/{task_id} 和 /result 均验证服务端任务归属，浏览器不提交主体/租户/SQL/端点。

提交回执前状态 SUBMITTING（不能当成引擎 RUNNING）；真实回执后才是 SUCCEEDED/FAILED。提交结果不明保留 OUTCOME_UNKNOWN，同一键不自动重提；跨重启代际拒绝，用户必须重新连接/确认。当前接入仅本机固定开发身份；正式租户认证仍为 not_run。元数据验证不运行查询；预览需独立确认，结果不写入浏览器持久历史。

浏览器：连接器 → 验证数据源连接 → 进入开发验证 → 勾选只读范围 → 执行只读预览；在连接器页看结果，返回工作台也有真实输出卡/pipeline。桌面黑白主题和手机布局继续保留。服务重启后不要将旧卡当有效资产；M05再实现版本持久化。

## 最新约束：仅连接与表导航

用户明确要求Power Query式连接后浏览表头/类型及最多前100行；连接器不提供任何筛选器，不要求时间列，不按表名猜日期列，也不在后台添加WHERE时间条件。旧日期/字段勾选预览为历史实现，现已在代码中移除。数据库无自然排序保证时不能宣称前100行是最早/最新记录。新配置接入完整流程仍待实现；当前只有内置源导航切片，不能宣称任意数据源已可接入。浏览器需重启新版API后复核，不把旧运行服务当新版。

## .xlsx兼容补充（2026-10-27）

用户新增要求已落实到Excel本地来源导入，详见CONNECTORS.md末尾。接入流程不变：上传或路径→真实MCP测试→保存→按工作表导航/原列头类型/前100行，没有时间筛选。日期数据保留，不执行公式/宏/外链。第一行表头、可见工作表、空/重复标题与压缩包限额有明确规则；复杂Excel报表/旧.xls未承诺支持。项目新增requirements.excel.lock.txt，版本许可证已核验并获准安装；真实回归证据以progress为准。
