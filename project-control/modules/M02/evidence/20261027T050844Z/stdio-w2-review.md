# M02-C03 W2 stdio硬限额与长驻故障恢复检查点

2026-10-27；reviewer=self_review。本机W2范围local_ready，不是独立审计/真实用户研究或完整M02交付。M02整体仍DO/not_verified/audit not_run，PG真实与生产持久化not_run。

## 用户任务→实现→证据

用户连接并浏览数据时，一个MCP故障不应拖垮API、显示旧有效结果或重复提交不明查询。新增warehouse/stdio_transport.py及stdio_entry.py复用W1父Windows Job，在发送路径/元数据前分配限额，固定base Python -S gate启动，只显式加载项目src/site-packages/pywin32 DLL；环境最小，无宿主凭证/代理/sitecustomize/.pth。MCP协议仍由官方ClientSession处理，不修改SDK、不接受浏览器command或任意入口。

每stdio进程384MB/Job512MB提交内存、进程数2，同时stdio连接4；会话累计用户CPU原生8s并监護Job用户+内核CPU8s，调用15s；输入每消息64KB，输出每行512KB/缓冲8条。输出预算为MCP线协议限额（SDK可能text/structured重复），不是扩大结果100行预算。CPU是累计会话预算而非每次调用重置，耗尽需重新验证，不能宣称无限长驻连接。关闭/超限/故障都通过父Job句柄清理拥有进程及管道，隔离不可用拒绝执行，不退回旧无限制SDK进程。

PersistentMCP由同一asyncio拥有任务管理整个ClientSession/AnyIO上下文，队列1序列调用，避免跨HTTP task退出CancelScope。空闲死亡也会被检测并清理；故障旋转执行代际，旧SUCCEEDED结果标RESULT_EXPIRED，旧结果接口拒绝。SUBMITTING通信丢失或请求取消保留OUTCOME_UNKNOWN；原任务/幂等键作内存tombstone保留，恢复后的新代际用旧键也不会重提。仅显式验证list_tables重建受限会话，普通schema/结果读取不自动恢复，容量拒绝不是会话故障，不旋转健康代际。

PreviewReceipt新增非秘密execution_generation和RESULT_EXPIRED，由Pydantic/OpenAPI重新生成前端类型，没有手改generated文件。网页只读状态轮询（2s）清旧预览/技术表导航；代际变化后过期的会话结果卡转换成明确错误说明，保留历史文字/主题，pipeline不继续宣称旧结果有效。重新验证后用户确认新预览才执行。原表头/日期字段、无筛选100行约束不变。

## 实际验证

最终完整命令services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser退出0，目录20261027T050844Z：188后端/10前端/19浏览器、类型/构建/pipcheck通过。90份sources前后稳定且最终逐文件一致，5份依赖锁未改，无新增依赖/容器/数据库服务。

单独证据20261027T051034477000Z-w2-extra：test_stdio_recovery.py 10项和原合成仓SQL/Parquet/goldenverify退出0，指纹与最终一致。实际原生stdio CPU/小内存拒绝/超输出/崩溃/Job分配失败gate无执行与连接容量清理通过；独立测试API真实Job终止、旧结果拒绝、三轮重建同拥有task/无进程残留通过。实际submit成功后用测试wrapper丢回执，旧幂等键不重提通过（网络丢包为软件注入，不称真实企业故障）；取消请求和容量用例为隔离单测，不冒充上游集成。

浏览器在独立临时真实API中终止其自己拥有的MCP Job，验证失败状态/旧预览清除→显式重建/不同代际→会话旧卡过期/无法当有效结果显示→新预览实际返回。fixture-only/stdio-fault仅测试脚本注册，标准API没有该接口；不触碰默认8000的工作Job、公司数据或用户凭证。原W1认证HTTP恢复、本地/.xlsx、主题/历史、手机/键盘/无筛选及API安全继续通过，PG只是配置/拒绝路径，仍无真实实例集成。

首轮20261027T050326Z后端187通过但浏览器18过1失败：页面关闭时真实转发响应尚未完成，route.fulfill看到disposed。afterEach等待全部路由收尾，不忽略异常/删断言。该轮运行期间说明更新也触发source-stability失败；保留退出1证据，更新完成并安全加载新版后完整重跑稳定通过。另补容量拒绝不触发健康故障的单测。

## 运行与视觉

旧服务API20600/Vite7380/launcher9252先核对健康/当前用户/父链，经审批检查完整项目树/创建时间后只停止拥有服务；源文件、SQLite配置、上传/快照保留。W2本轮exec session82874，API27564/Vite21940/launcher23752，两个loopback服务200；实际API子进程26588使用固定stdio_entry.py -S bootstrap，拥有者当前用户。新窗口不得继承session假设，应重新核对。

stdio-manual-recovery.png已视觉自查，恢复后的已验证状态、原表导航、无日期筛选与显式黑白主题/历史入口保留；实际数据与旧卡失效有浏览器断言。自测不是用户研究。无公司平台访问、宿主配置凭证读取、新安装或公开部署。

## 剩余与边界

- 此“持久故障恢复”是API内长驻MCP会话重建，未新增磁盘任务/结果持久队列。API重启仍清空内存任务/幂等记录，M05正式持久化/生产灾备not_run；不会恢复旧SQL结果或重提未确认查询。
- W1/W2是Windows操作/stdio原生资源限额，不是文件网络权限沙箱/API主进程总内存隔离；上传包预检、全局TTL/删除界面/生命周期清理、非Windows/生产资源/身份与权限安全仍未完全验收。
- PG真实SQL/实例/TLS/账号权限仍not_run，需要用户单独授权的独立本机实例，不能暗装服务或换公司平台补绿。HTTP真实只涵盖已审定loopback工具合同，不称任意远程兼容。
- 长期异步、真实取消/下载、OAuth/正式行列ACL及正式发布未实现/未验证。资源预算需要目标环境另核验，不自动上调。
- M02整体审计/用户验收未完成，不closed或进入M03。M01原人工验收保留，仅更新累计回归。

回滚恢复代码/停自己拥有服务并重新验证；不删除原数据、连接配置或历史证据，不自动恢复旧任务。
