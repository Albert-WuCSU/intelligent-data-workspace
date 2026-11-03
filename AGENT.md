# 受控问数 Agent（M04-B C01 开发切片，尚未整体验收）

## 当前路径
用户在设置配置、实测启用模型，在知识库发布并启用当前单表定义。在取数工作台输入区选已发布口径、启用模型，并在右侧来源中勾选该定义的来源。明确同意发送本次问题和必要字段与0.25USD估算预留后，发送问题才调用模型。

LangGraph显式resolve→model→validate→approval interrupt→execute，模型只返回有限JSON指标/维度/时间计划，不能指定SQL、账号、工具、路径、网络或租户。缺口径/歧义/不支持请求先澄清；非法JSON不执行/不自动重试。128输出token/2000字符模型输入上限沿用，大定义或长问题需缩小范围，不暗截断。

口径卡显示指标/单位/声明粒度/全表或起止时间/维度。勾选“确认本次口径与查询执行”再执行；确认绑定plan hash、语义版本与schema/source/state revision/model配置和代际。变化或停用时计划失效，不继续旧SQL。时间过滤首版只消费UTC已批准时间定义，其他时区需明确处理，不按字段名猜时间。

## 查询与质量
新 `workspace_aggregate_v1` 独立固定stdio MCP server/client，沿用WindowsJob/stdio边界；旧导航6工具和预览功能不改。只本机保存快照来源，当前HTTP/PG只导航能力不能偷扩聚合。不接受浏览器任意SQL，指标结构由服务端有限编译、SQLGlot只读AST/真实字段/模式检查、执行端再次核schema。

全输入扫描/匹配聚合，不读取“前100行”来算总体。执行端额外硬上限输入<=200000行；当前本机快照导入仍保持原20000行门禁、不自动扩大，结果分组<=100、200KB、引擎/Job资源时限，超限不返回假完整结果。count_rows、sum、ratio、最多3维度、显式日期参数；ratio分母0/null输出NULL，空集不是0业务值。结果包含真实输入/匹配行、重复/空grain、空metric行、零分母组、单位、来源、QA与限制。人类grain声明不等于统计唯一性，WARN不冒充认证。

## 恢复与预算
API任务/graph检查点/确认只后台内存，与浏览器会话ID绑定（非身份授权），页面刷新后读取同一已授权任务并恢复待确认，不重提模型；不把结果持久存入浏览器history。M05前重启旧任务失效，不承诺磁盘任务恢复。
API owner由服务器确定、UUID/请求指纹冲突拒绝；模型一次，确认后tombstone先置、MCP幂等回执后查。未知执行保留UNKNOWN/同任务，双确认不重复SQL。取消后若已提交结果不明，不自动再执行。图checkpoint不是exactly-once保证。模型预算现有跨Key/厂商campaign不reset，未知不退款；无声批量调用或硬费率保证。

## 依赖与外发
已按D069安装LangGraph1.2.19及26项目venv哈希锁依赖，pip check/无网络runtime interrupt-resume通过。LangSmith/SDK是传递安装包，实际graph invocation tracing_context(enabled=False)/callbacks=[]，禁trace/不建云client、不继承宿主凭证；WindowsJob subprocess环境保持原最小白名单。没有第二套CLI/AgentSDK或自由工具Agent。

生成上下文仅本次问题、已批准metric名称/算子/必要字段类型/必要时间说明，不发rows/全历史/负责人说明/原件路径/Key。用户显式发送与查询确认，不把依赖安装当自动付费/生产访问授权。

## 未实现/未验证
当前C01代码和独立模型fixture→真实MCP测试不等于用户实网关JSON规划已经成功，需实际网页用户操作验证。JOIN/L2/L3/L4后继范围、跨源融合、PG/HTTP真实聚合、完整持久资产/下载/M05–M08、生产身份/部署继续原门禁。模型目录/Key复用自动切换仍单独待办。当前模型真实成功只支持此前固定文本/流式，不直接升级为问数成功。

## 验证
`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`。需先核本机服务归属；不要继承旧PID或盲杀，运行旧API时业务路径仍清楚未接入。新API加载由用户安全重启并网页输入Key，不读取/搬运旧内存Key。
