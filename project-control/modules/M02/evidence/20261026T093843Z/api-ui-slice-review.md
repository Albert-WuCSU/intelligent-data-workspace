# M02 API/UI 切片 self_review

2026-10-26；检查点结论：本机切片已验证，非完整模块审计/生产验收。

## 用户任务→实现→证据

管理员检查连接→连接器状态/验证接口→实际调用已初始化stdio MCP的list_tables（不是假工具或目录样例）。开发者确认表、字段、日期→独立开发预览表单+Pydantic白名单模板→真实SQL/回执/结果卡。业务默认会话不要求SQL/JSON；自然语言Agent仍未接入，提示准确。

真实网页/API/MCP/DuckDB路径、授权与确认、幂等、拒绝、错误、空结果、截断、真实pipeline、TEST单位、WARN质量范围通过。预览结果与任务不持久到localStorage。后端93、前端10、浏览器11通过；类型/构建/pip check通过。results.json及sources.json记录实际命令、退出码、环境和源码指纹；额外warehouse-verification.txt复核数据库/Parquet/golden未被改动。

SUBMITTING只表示发起提交，不能伪称引擎RUNNING。提交通信不明记录OUTCOME_UNKNOWN，同一键只返回既有回执；execution_generation跨重启拒绝，重新验证和确认后才允许新查询。每次API操作检查服务器身份/任务归属；生产默认禁用，本机非授权主体/租户拒绝。连接器可选依赖缺失不妨碍未启用的基础API加载。正式登录/RLS/CLS认证未完成。

黑/白主题、历史、移动布局、技术折叠与原结构/测试任务接口保持。查看桌面黑/白及手机截图确认可读，无横向页面溢出；长预览表在自身滚动区域。这里只是开发者自测/走查，不是真实用户研究。

## 失败及处理

初次Vite/esbuild构建和前端单元因沙箱目录访问拒绝失败；按审批复跑原检查通过，没有改配置或删断言绕过限制。最初TS发现旧不可达connectors判断，删去已被真实连接器替代的候选占位；旧连接器未接入断言迁移为新真实/未配置/拒绝路径测试，其他旧业务断言保留。源码稳定检查通过。旧API进程按路径/父启动器核实并获准重启；没有删除历史或数仓。

## 剩余门禁与回滚

M02尚未closed，完整模块audit仍not_run。Windows/OS级Worker硬资源限额、进程故障清理/恢复还需验证；已验证的DuckDB 128MB/3秒interrupt不等于Python进程/OS级沙箱。真实取消、下载、正式认证、持久化、Spark/Hive兼容未提供。禁用WORKSPACE_OWNED_WAREHOUSE恢复未接入，无数据删除；旧QuerySpec测试任务保持未执行。
