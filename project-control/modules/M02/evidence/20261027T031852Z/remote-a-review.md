# M02-C03 方案A远程配置切片检查点

2026-10-27；reviewer=self_review；局部HTTP/配置范围local_ready，完整M02仍DO/not_verified/audit not_run，不是模块交付验收。

## 需求→实现→证据

接入人员可通过新增数据源选择本地/PostgreSQL/HTTP MCP，或直接配置MCP；网页和JSON只接受非秘密字段及凭证代号，不接受密码/token/命令/主体。后端专用策略将目标、账号、资源和代号绑定，默认全拒绝；只有授权后才读WORKSPACE_CONNECTOR_SECRET_专用值，不扫描宿主工具配置。测试/保存分开，刷新复用配置、编辑重测、禁用清空预览。取消授权确认会使旧测试失效，不能继续保存。

HTTP实际浏览器→产品API→授权引用→认证Streamable HTTP→真实FastMCP→临时DuckDB目录/100行链路通过。浏览器测试仅将source-profiles请求地址转到同一源码的独立真实API（不是mock响应），隔离临时授权和哨兵，不往默认8000存认证fixture或向浏览器发送密码。SDK工具名称/必需参数严格匹配workspace_navigation_v1，表白名单过滤后才提交limit100；目录测试不执行SQL，不发WHERE/时间筛选。返回字段类型与两个日期列保持；远端认证/币种/业务质量标签不被当作证据，归一为来源external_mcp、WARN，不制造数字。

PG表单/导入/持久配置分支和只读适配器已实现，但没有用户单独授权的真实实例，PostgreSQL连通/真实目录/SQL/TLS/权限仍not_run。PG SQL和100行/日期逻辑、schema目录过滤/引号转义及环境/管道隔离仅单测，不宣称真实PG已接入。专属PG子进程只接受固定操作，密码走管道不在argv/env，passfile空设备、无PG*/宿主凭证继承；固定READ ONLY/statement_timeout/lock_timeout，运行12秒上限会终止自己，不等于OS硬限额。

## 执行证据

最终完整命令services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser退出0，目录20261027T031852Z：164后端/10前端/17浏览器通过，类型、构建、pip check通过。后台新增11项（包括参数化结果负例）；HTTP边界原45项继续通过。单独真实认证HTTP API用例及原合成仓SQL/Parquet/golden完整性验证退出0，见20261027T031952342756Z-remote-extra/results.json。81文件sources前后与最终逐文件一致，原4依赖锁未修改。

psycopg/psycopg-binary3.3.6公开元数据、CPython3.12/WindowsAMD64轮子哈希、随包LGPL-3.0文本和libpq/OpenSSL上游许可已核验，获运行审批后项目venv离线hash安装，import binary/libpq180004及pipcheck退出0。新增可选requirements.postgres.lock.txt，不升级旧锁或安装数据库服务。完整发布物法律/供应链审计仍not_run。

前两次切片测试发现新TestClient未声明loopback身份、tagged union破坏旧省略kind请求；修复测试身份并保留原省略kind兼容，没有削弱断言。tagged union+BeforeValidator还产生不合法OpenAPI discriminator mapping，改为各variant严格Literal kind/extra forbid的普通union，由Pydantic/OpenAPI重新生成类型，未手改generated。修复后完整回归通过；取消授权确认防误操作补丁后又重跑全部通过。

## 服务与产品走查

旧5173/8000先确认HTTP200、拥有者当前用户、父链项目scripts/dev.py。停止前发现未知项即拒绝操作，两次均没有停止任何进程；只读核实为本项目esbuild与Windows控制台helper后，获运行审批，校验完整树/PID创建时间，才停止其拥有后代并重启。保留SQLite、上传原件及快照。新版本轮exec session3925运行，API PID24816、Vite PID28192，启动器父链9268，只有loopback且200；默认未经授权的HTTP地址实际返回TARGET_NOT_APPROVED，未去访问该地址。新聊天不能假设继承此session。

scripts/dev.py拆分前端允许环境/后端专用环境，Vite不接收产品及宿主token，stdio MCP仍最小环境，PG进程无继承秘密。哨兵测试检查HTTP响应、SQLite、日志、localStorage、argv/env未出现密码。没有用宿主MCP账号、公司数据、外部数据库或生产部署。

浏览器验证原本地文件/.xlsx/内置合成例、主题/历史/真实pipeline、失败/空态，并新增HTTP真实配置保存刷新日期导航和PG未授权拒绝/保留字段/手机主题。http-mcp-navigation.png与postgres-config-mobile.png已视觉自查：原表头/类型/日期可读，无日期/密码输入，主题选中态可见，没有横向溢出。没有招募真实用户，属自测，不是用户研究。

## 剩余与下一步

- PostgreSQL真实实例、非loopback TLS/证书、账号权限/复杂类型与各厂商兼容not_run；需用户另行明确授权本机测试实例，不安装PG服务或访问公司平台来补绿。
- Worker/OS内存CPU强限额、故障恢复/circuit breaker、池与进程清理仍not_run；下一切片优先推进，不拿当前引擎定时器/PG子进程超时冒充完整强隔离。
- HTTP当前仅已审定六工具及完成回执；长期异步查询/真实取消/下载、DNS/SNI/旧SSE、OAuth及正式ACL未验证/不支持，不声称任意MCP兼容。权限拒绝不改账号、目标或工具绕路。
- 上传副本/未保存草稿TTL或删除UI、正式多用户认证/生产秘密轮换/持久队列恢复仍门禁。当前配置持久化不是M05生产认证或历史存储。
- M01原人工验收保留，更新累计回归，不把A新能力自动验收；M02整体未closed，不进入M03。

回滚可禁用新remote profiles并恢复代码/启动器，保留原本地配置和源文件；不自动删数据、秘密配置或历史证据。
