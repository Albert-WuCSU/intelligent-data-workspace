# M02 有限本机交付审计

2026-10-28；reviewer=self_review（同一主Agent，不是独立审计或用户研究）。
**结论：pass，仅 finite_local / local_ready；等待用户 delivery，M02 尚未 closed。**
范围批准为 D-MVP-FAST-034，不是本审计自行取消要求。M01已验收保持不变。

## 用户任务 → 实现 → 证据
| 验收任务 | 实现与范围 | 本轮证据 |
|---|---|---|
| 聊天中导入自己的文件 | 安全确认→受限预检→真实MCP目录→临时附件，不保存连接；CSV/Excel原头、类型、日期和100行无筛选 | 287后端含6附件专项；27浏览器中的CSV/Excel/移动端 |
| 多来源会话上下文 | 右侧按会话选择最多8源/4附件，禁用不可选；不是已完成JOIN | multiple attachments/right sources真实路径 |
| 远程接入与旧数据 | HTTP独立授权fixture握手/目录/预览/测试保存刷新禁用；PG仅配置/拒绝，真实实例后补；旧本地profile不迁移删除 | authenticated HTTP/API与浏览器；PG拒绝不冒充连通 |
| 失败后有下一步 | 失效重测、权限拒绝、凭证丢失、旧代际结果过期、显式恢复，不自动重提未知执行 | 完整回归；legacy expiry缺字段为一项显式兼容响应fixture |
| 后台保护不扰乱业务 | Windows Job CPU/内存/进程数/取消/子进程回收与真实stdio恢复；24h临时来源/引用冻结/原生保留周期 | 287后端包含native/retention专项；隔离25h fixture及周期浏览器，不代表真实用户自然24h长期实证 |
| 主题、历史、证据和边界 | 可见黑白选中态、历史/移动端、SQL折叠、顶部真实未执行状态；快照不持久化浏览器历史 | 27浏览器/16前端；新白色CSV截图与既有暗色Excel截图视觉走查 |
| 服务与操作安全 | loopback 8000/5173健康200；当前拥有者CN1/luqianwu、PID/时间/父链实际只读重核，无stop/restart/旧exec继承 | recovery.json，/health误探测修正为实际/health/live，不拿404称API坏 |

## 实际检查
- `services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser`：获批准沙箱外按原命令，287 backend /16 frontend /27 browser、pip check/types/build全部退出0。完整结果和指纹：project-control/modules/M02/evidence/20261028T082433Z/results.json、sources.json。
- 首次沙箱执行退出1（原生Worker/tmp teardown/祖先目录读取拒绝，网页25/27），完整失败日志保留于082022Z；没有改产品、删除/skip/放宽断言解决。
- warehouse.verify、PRD一致性、5项PRD guardrails退出0；进度guardrails从原21项新增至26项，全部退出0。仅项目内Skill合同修复，未改个人安装Skill。
- 原required Worker总项旧not_run与本机native证据不一致：本轮已运行同一原生测试矩阵，改为真实Windows本机通过；API整体DoS、其他OS与生产长期保护没有被说成通过。

## 明确延期（不得删required或伪造passed）
- postgresql-onboarding仍required=true / not_run。责任人：用户/项目维护者；首次提供PG已验证能力或正式发布前，提供独立授权实例，补握手/目录/只读SQL/TLS/权限拒绝、真实接口及浏览器证据。
- 高风险M02-R-WORKER与M02-R-ONBOARDING-TRUST原样unresolved，剩余针对整个API DoS、非Windows、正式身份/RLS/CLS/TLS、目标环境恢复/长期驻留。绑定RG-PG-PRODUCTION-DEFERRED及原RG-TENANT/RG-DEPLOY/RG-CONNECTOR-ONBOARDING，发布门禁不通过。
- medium保留：合成证据不证明企业效果/因果；unknown或损坏来源保守保留可能占空间；本机共享隐私与开发内存任务不可当生产持久化。这些是已批准有限环境的披露，不是风险消失。

## 状态合同自查
有限本机交付必须逐项引用真实scope/change批准、延期门禁、owner/condition与匹配finite_local审计；仅local_ready，不允许critical/failed/stale/非真实延期。仍必须人工delivery才closed，依赖才可激活；项目complete前补验并重新审查。没有用required=false、风险resolved=true或虚构用户delivery让校验绿。

## 下游与本轮非目标
M04-A相邻计划已明确getpass本机隐藏输入、非TTY拒绝、后端内存专用Key、不传Node/数据源Worker、不读取Claude/Codex令牌；**入口及适配未实现**。实际model协议/model/可核实价格或专用供应商硬限额待落实，收费调用not_run。网关许可/15USD/问题与必要字段外发/PG后补不重问。
验收后M04-A→M03→原M04=M04-B；真实自然语言SQL和JOIN均未完成。本轮没有模型/公司数仓调用、依赖安装、Key读取或持久化、Git push、部署、用户数据删除。
