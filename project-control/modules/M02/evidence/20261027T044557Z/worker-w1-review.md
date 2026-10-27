# M02-C03 Worker W1检查点

2026-10-27；reviewer=self_review。W1操作级资源和手动恢复局部local_ready；完整Worker门禁/M02 audit仍not_run，不是独立审计或用户验收。

## 用户任务→实现→证据

用户连接文件/MCP/PG并浏览原表头/类型/100行时，不应因一个超时或解析异常拖垮API，也不应自动重提远端结果不明的查询。新增worker_runtime.py/worker_entry.py把快照导入、HTTP MCP与PG读取移到固定、父进程拥有的Windows Job操作。后台保护不增加业务首页技术面板，不改变黑白主题、历史/真实pipeline，不加筛选或删日期列。

Job分配成功前，base Python -S固定bootstrap只阻塞读取pipe，未收到配置/凭证；之后仅显式加入项目src/site-packages和批准pywin32路径/DLL目录，不执行宿主sitecustomize/.pth。凭证走父子管道，不进argv/env；服务器仍先检查目标/账号/资源/代号绑定，导入配置不能扩大授权。无新依赖/容器/数据库服务，复用既有pywin32。

默认每进程384MB、每Job512MB提交内存，Job/进程用户CPU原生限制8秒且父监护按Job用户+内核CPU8秒终止，最多2进程/同时2Worker；导入25秒、HTTP20秒、PG12秒墙钟、入64KB/出250KB。过量输出在流式读取时截断失败，不无限communicate积累。Job不可用/分配失败拒绝执行，无无限制线程回退。父Job句柄清理其拥有后代，不用猜PID杀无关进程；finally清理管道/句柄/名额。

源导入失败只清理此次UUID新建快照暂存目录，目录MCP验证失败也清理该暂存，不删原文件、上传副本、已保存profile或旧快照。读取失败profile保留版本/配置并标NEEDS_RETEST；页面重读非秘密状态，清旧预览。只有手动重新连接/预览触发读取，成功后刷新并解除旧失败标签。未实现持久任务恢复，不假称服务重启保留活动查询。

## 实际测试

最终完整命令services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser退出0，唯一最终目录20261027T044557Z：178后端、10前端、18浏览器、类型/构建/pipcheck通过。85个sources前后稳定并最终逐文件一致；5份依赖锁未改。

额外证据20261027T044756181340Z-worker-extra：14项worker_runtime测试及原合成仓/Parquet/golden完整性verify独立退出0、指纹与完整回归一致。真实原生测试涵盖Job设置、小内存真实拒绝、CPU预算触发Job终止（不是仅墙钟超时）、额外进程数拒绝、超时/崩溃/超输出、后代清理、Job分配失败gate未执行和名额复用。SourceStore两个故障注入用例用monkeypatch制造安全故障，属于隔离单测，不称真实上游崩溃；恢复重试随后运行真实本地MCP。生产run_worker操作白名单不包含probe，worker_probe仅软件测试fixture。

浏览器认证HTTP和凭证丢失恢复用独立临时真实API/认证FastMCP/临时DuckDB；故障开关只在独立remote_browser_fixture注册，标准API没有fixture-only接口。实际恢复流程：凭证丢失→明确失败/配置保留/NEEDS_RETEST→恢复测试凭证但没有自动读取→用户手动连接和预览→实际日期数据与状态恢复。不是mock协议响应。PG浏览器仅拒绝未授权目标，真实PG集成仍not_run。原本地文件/.xlsx、无筛选/日期列、主题/历史/pipeline和错误空态回归通过。

## 修复记录

1. -S严格启动不加载pywin32 .pth，首次HTTP缺pywintypes而拒绝。显式添加仅项目pywin32路径和DLL目录后真实HTTP11项通过，不重新开放宿主启动钩子。
2. 首次CPU专项只达到墙钟超时，未通过CPU断言。明确设置原生Job/进程用户CPU及终止动作（pywin32要求字典参数），并按原生Job总CPU计时监护；保留CPU专属故障断言，不把超时当CPU隔离通过。最终14项实际通过。
3. 首轮完整回归20261027T044104Z后端178通过但浏览器17通过1失败：后端已恢复，UI旧失败标签未刷新。补成功连接后刷新配置状态，重启新版并完整重跑18通过，失败日志保留，不删断言/跳过测试。

## 服务与视觉

先核对旧API/Vite PID24816/28192、项目launcher9268、当前用户归属；获运行审批后逐个核对完整项目树/创建时间，只停项目拥有进程并保留原数据。新本轮session27245启动，API20600、Vite7380、launcher父链9252、当前用户、两个loopback健康200。新聊天不能继承该exec session假设，仍须先核对拥有者。

worker-manual-recovery.png已视觉自查：恢复后的连接状态正确、原created_at/shipped_on日期列及100行、顶部主题和侧栏历史可见，没有日期筛选。功能/视觉为自测，不是招募用户研究。测试凭证都是独立哨兵，未读取公司或宿主配置，没有外部访问、安装或部署。

## 未完成门禁

- W1不是文件/网络权限沙箱，也没有限制API主进程总内存。上传/Excel包预检仍在API接受既有限额，复杂解析整体隔离未认证。
- 旧SDK stdio MCP具自己的生命周期Job与DuckDB引擎限额，未应用W1内存CPU硬限额；持久内置例MCP故障重建、任务失效/不明结果处理与完整Worker恢复门禁待做。
- 非Windows资源隔离、正式生产认证/ACL/秘密轮换、长期异步/取消/下载、全局TTL/删除界面、持久队列恢复仍not_run/未实现；不标production_verified。
- PG真实实例、真实TLS/账号权限/SQL仍not_run；需要用户另行指定授权独立本机测试实例，不暗装PG服务或绕用公司数据库。
- M02整体maturity not_verified/audit not_run，高风险未全部解决，无delivery批准，不closed或进入M03。M01原人工验收保持、累计回归更新。

回滚仅恢复代码/停自己拥有服务、禁用来源；不删除原数据或配置。失败暂存清理路径校验与资源限额仍服务端实施，不靠提示文案保护。
