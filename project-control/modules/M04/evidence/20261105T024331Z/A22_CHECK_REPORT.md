# A2.2 有界模型公开意图 CHECK / self_review
2026-11-05 · D077/D078体验切片 · D079 GitHub同步

## 实际结论
命令`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`退出0；**669后端/23前端/45浏览器/types/build/pip及源稳定全部通过**。fingerprint `5affed8ff4be07d2e1e5086a81be2233cd41060ec98399140554458213495543`；真实命令/环境/退出/日志与源清单见results.json/sources.json。不是用户验收/真实模型/生产或MVP交付，M04仍DO/not_verified。

## 实现与用户任务
工具调用之间的模型公开未来意图，以model_public_intent单独标注“意图，不是执行回执”；governed_event实际执行事实/用户补充/最终报告分层。只消费完整AssistantMessage/TextBlock，同上游ID完整块按锁定SDK/CLI实际拆块方式组合，直到ToolUseBlock；StreamEvent碎片/ThinkingBlock不转发。最多4条/500字符，16待处理ID；同ID去重，unsafe后块毒化整个消息，原文不留buffer/失败diagnostic，避免safe前缀泄漏。

门禁保守拒绝业务数字/数值词、成功声明、已知Key/凭证、URL/宿主路径/代码/SQL/非未来意图；runner和API镜像再次校验。提交/发布后不再接收意图。原路由/模板/metric/确认/权限/版本/SQL/MCP/自动QA/usage/receipt发布不变，无新model请求、工具或费用/结果行/全部历史外发。

无合格公开意图时省略，真实工具事实和后台结果仍可用；不以模板冒充模型正文。只在完整内容块边界渐进展示，不承诺任意token流或所有模型语言自动真值验证。最终报告仍按已发布后台权威数值/表和来源质量解释；模型语言的完整业务真值尚需真实评估。

## 验证与历史失败
公开意图逻辑/完整块/毒化/鉴权/预算/对话专项通过；SDK fake gateway+真实合成MCP证明工具间notes仍8步/8预算单位，未验证数字/失败成功声明不出现在对话或最终answer。UI-only快照验证来源标注/同任务问答/报告/结果保留/主题/窄屏/刷新，不当真实DeepSeek或用户研究。

初始SDK专项2failed/15pass：锁定CLI把完整text/tool拆为同ID AssistantMessages导致notes缺失；修复有界buffer后4受影响cases复跑pass。另原modelchange等待超时未独立证实根因，不声称已根治。

首次全量667pass/2fail：旧diagnostic要求原modeltext与新隐私合同冲突，已增强断言为model_textNone/不含原文与Key，保留events/usage/code；L2 CLI启动60s等待超时，仅补无敏感原文的startupcounts诊断、不放宽等待，3项复跑pass。023206Z failed/stale清单保留；024331Z最新完整669全部pass，仍注明本机CLI启动的间歇性风险，需实际环境补验。

## GitHub与运行边界
已把此前当前642/23/45基线非forcepush到origin/main702cabec3958ff87e06e4551ab8658511ca3e30f，lsremote核同；LangGraphbaseline92d0b03未变。源码/文档/独立合成fixture证据经规则扫描未见secret匹配，runtime/Key/上传/语义/账本/venv/tmp/rootdraft忽略，当前证据hash一致319项；不是全面独立安全认证。此次A2.2通过后增量推送结果另附receipt，不伪造未来SHA。

默认API200/model unconfigured/0task，只读账本49/60/估算余额2.75USD不变。没有重启当前用户服务、真实model调用/费用/公司数据/host工具权限/安装/生产部署。默认最新运行加载与A2.2实模型体验not_run；用户重输Key/显式复测及更多费用另授权，不能reset。

仍后续：完整企业L2/L3自由SQL/多表/分区、最小跨任务会话上下文、RAG业务知识、公司多源/导出/PythonQA、真实Claude/生产/MVP。现有A3-M1只是批准口径派生单表模板和绑定metadata基础，不能用本片测试替代新业务数据/语义/费用授权。
