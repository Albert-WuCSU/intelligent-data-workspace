# M04-A 首切片审查（不是模块交付）

2026-10-28；reviewer=self_review，非独立审计/用户研究。
**结论：第一切片 local_slice_pass；M04-A整体未验收/not_verified。**
M02已由用户D-M02-DELIVERY-049验收有限本机范围，PG真实/生产后补与高风险门禁未删。批准首切片D-M04A-PLAN-051，不延伸为收费准入/新安装或持久秘密仓库。

## 任务→实现→证据
- 接入管理员不在聊天提供Key：start-workspace-model.cmd或scripts/dev.py --model-key，本机getpass；非TTY/隐藏失败警告拒绝，不回退回显。Key只存在launcher/backend内存及初始后端专用环境，不写文件/URL/命令参数/日志/storage/Git，后端consume pop；Node/Vite和Worker白名单不继承。OS同用户/管理员仍可检查进程内存，不是生产秘密仓库。
- 服务状态可理解：GET model-service/status需服务端本机身份，仅boolean/配置版本/缺项/未验证状态，不返回Key或掩码、不接受网页Key/费用许可。右侧说明从独立实际API读状态，模型选择保持禁用/目录为空。
- 薄ModelProvider/Messages协议候选：仅显式配置已批准host/coding-plan路径，固定x-api-key Messages适配；实际路径/model必须资料核实，不猜默认。无proxy环境继承/跳转/重试/工具调用；最多并发1、15s网络总限时、128输出token、2k字符问题、64KB响应、identity响应编码，认证/限流/网络/超时未知/部分/坏JSON/模型别名不匹配/空输出有固定错误；配置版本绑定，不执行SQL。
- 保守费用：生产BudgetPermit未实现，因此缺可靠费用治理必定调用前拒绝。测试Permit只在隔离测试注入，不由浏览器设置、不代表供应商限额；unknown用量是None不是0，费用unknown，不虚构15USD余额。超时/取消无退款/自动重试逻辑。
- 秘密防反射：remote正文包含专用Key则拒绝；误将Key填到非秘密model等字段也不回传/不发送，新增安全专项真实运行。错误不输出响应正文/原HTTP异常。
- 原产品路径：聊天CSV/Excel/原日期与100行、右侧多来源/旧profile、黑白/历史/真实pipeline、Worker/retention恢复无回归。

## 实际命令和结果
`services/api/.venv/Scripts/python.exe scripts/check.py --module M04-A --browser`，批准沙箱外本机运行：**323 backend（原287+36模型隔离专项）/16 frontend/28 browser**、pip check/types/build全部退出0。代码稳定manifest在20261028T085300Z/sources.json，结果在同目录results.json。模型请求仅MockTransport/测试哨兵，不是网关调用；新增model状态浏览器使用独立真实当前API。
PRD一致性、5项PRD守卫、26项进度守卫和warehouse SQL/Parquet/golden verify退出0。Pydantic/OpenAPI导出TypeScript，无手改generated。未安装依赖，httpx沿用0.28.1。
页面视觉：模型说明白色截图可读、显示未配置/未验证及隐藏输入步骤；原主题/附件/移动与历史路径实跑。不是实际用户研究。
首collection括号错误/长pytest参数ID/沙箱收尾、首27/28精确空格定位错误修正均记录observed-failures.md；原数据和断言未删skip放宽。此前全28浏览器实际0但wrapper最后GBK打印失败，保留其真实result不冒称wrapper0；本最终标准脚本UTF8整体0。
Git格式检查Windows CRLF默认被报whitespace，单命令cr-at-eol核实退出0，不改全局配置或批量规范化行尾。

## 未完成/必保留not_run
- 用户本机真实隐藏Key输入尚未由本人执行，助手不会运行可读取真实Key的交互。不得把getpass单测当真实Key配置成功。
- 默认API仍此前9208旧代码；当前实际拥有者CN1/luqianwu/创建14:27:21/父1772与Vite22240父13472只读复核，loopback健康200，无stop/restart/继承旧exec。新路由在独立测试API验过，不能称默认已加载。用户需在自己的原启动终端CtrlC后使用新启动器；占用端口拒绝，不盲杀。
- 网关精确路径/认证协议/model及可核实计价或专用供应商硬限额未核实；没有网关请求，real-model-api仍required/not_run，15USD金额/许可不重问。
- 生产预算治理/账本、真实最小收费测试入口、非秘密配置保存/编辑/启禁/授权模型目录、流式和结构化能力仍未完成。当前没有收费测试HTTP端点，不冒充API完整接入。
- 真实自然语言SQL/JOIN依赖M03/原M04=M04-B，当前not_run；PG/生产原门禁保持。无新依赖/宿主认证读取复制/公司数仓/发布/push或用户数据删除。

## 下一步
获取不含Key的网关精确调用示例及model/实际计价或供应商专用Key限额证据，固定协议和费用实现；接入治理后的真实最小测试/回执与模型目录，再由用户自己本机隐藏输入专用Key触发真实调用。资料与Key分别处理，不要求聊天Key。M04-A完整验收后才M03→原M04=M04-B。
