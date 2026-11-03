# 项目续接档案

状态版本 revision 165，更新时间 2026-11-03T05:52:11.143132+00:00 UTC。

先校验 progress.json 并核对实际文件；本档案由脚本生成，主进度为唯一状态真源。

- 项目：通用企业智能数据分析平台
- 当前：M04 取数Agent与Harness（M04-B Claude Agent SDK＋Skills主线） / plan
- 状态：in_progress
- 下一步：按D070SDK主线先只读调查确切SDK/内置CLI版本/hash/许可CommercialTerms/Windows隔离与现AIPlan网关tool_use/Skill/stream/usage兼容、有限turn/tool/token/墙钟预算和治理工具合同，准备明确安装许可点；方向已选不重问。旧LangGraph只比较基线，不按旧next_action自动调用/重启/继续图主线。不读hostKey、不自动付费/猜端点或扩大数据外发，完整SDK实现和MVP均not_run。

## 优先读取
- project-control/modules/M04/plan.md
- project-control/prd/M04-B.md
- skills/project-pdca/references/claude-sdk-routing.md
- CHANGELOG.md
- project-control/modules/M04/evidence/20261103-sdk-route-change/research.json

## 工作状态
- D070用户明确改Claude Agent SDK＋产品Skills＋治理Harness主线，旧D058/D069选择历史不删。M04原ID/M04-C02-SDK PLAN；已验收M01/M02/M04-A/M03、预算D053及PG/生产门禁保留。
- LangGraph完整C01源码/测试/证据/交接已commit92d0b03于codex/langgraph-baseline-20261103，main快进继承以复用底座。主线仅文档迁移，当前运行代码仍旧C01，不称SDK已实现；旧593/17/44为历史基线。
- M04SDK plan/PRD/Skill及对应安装副本、需求和日志已更新，SDK安装/运行/网关兼容not_run；官方docs403，officialPythonREADME/types调研成功，未锁release。
- 本轮未重启/核实时服务、读Key、实模型收费或productionSQL，未installSDK/新CLI，未授权子Agent。用户授权GitHub推送main及保留分支；main ce14cd4及LangGraphbaseline92d0b03已正常atomicpush；ls-remote同SHA证实。
- SDK方向文档self_review通过：PRD覆盖/引用/顺序、31测试+9subtests及3Skillfiles安装同步过；产品源SHA仍5be4b137...不变，旧C01未重跑。源代码/文档diffcheck过，原始evidence stdout空白保留。正常atomicpush和ls-remote实核通过，无force；后续收尾记录单独commit/push，续接以实际Git refs为准。
- GitHub main ce14cd4已承载SDK方案；codex/langgraph-baseline-20261103=92d0b03完整保留。官方PRD最终文档audit13模块/60需求通过，当前SDK所有runtime testsnot_run、M04-C02-SDK PLAN。下一步仅SDK兼容/锁版/隔离/安装计划，不复问选型、不自动实调用。
- 2026-11-03最终换窗口交接：GitHub main收尾6697c4e、LangGraph比较分支92d0b03已push/ls-remote核一致，当前源码工作区干净；本次仅交接更新，不新增SDK安装/调用/重跑产品测试。后续交接提交SHA以gitrefs为准。

## 阻碍

## 上下文建议
在模块边界保存后按需切换。

在同一项目目录使用 $project-pdca，读取 project-control/progress.json 和 HANDOFF.md，核对实际文件后继续推进；遵守已登记决策，不重建项目。
