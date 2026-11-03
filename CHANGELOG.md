# 更新日志

## 2026-11-03｜SDK主线规划迁移（D-M04B-CLAUDE-SDK-070）
### 决策与理由
用户明确选择Claude Agent SDK＋产品Skills＋治理Harness，以按需工具调用和澄清应对不明确的数据诉求。模型负责路由/探索；Harness负责不可绕过的执行授权/确认/预算/SQL/幂等和取数后质量检查。不是把安全降为Prompt，也不声称LangGraph必然死板或SDK效果已优于它。
### 分支与保留
- main：SDK方案主线；本提交仅规划/文档迁移，运行代码暂仍旧C01，不是假实现。
- codex/langgraph-baseline-20261103：92d0b03，完整保存此前未push的M04-A/M03/C01源码、测试与交接。旧593后端/17前端/44浏览器历史回归、失败证据、26包锁保留，不删除、不force push。
- M04 plan/PRD旧版另归档LANGGRAPH_C01_PLAN_ARCHIVE.md与LANGGRAPH_C01_PRD_ARCHIVE.md。
### 同步文件
更新M04 plan/PRD、ROADMAP、AGENTS、AGENT、产品原则、需求R-U24/R-A05/R-A06、PRD index/specs/入口/来源、project-pdca项目条件规则与SDK reference、progress/HANDOFF/STATUS/新窗口prompt及对应安装Skill。原决策ledger不覆盖，M04-C02-SDK PLAN，不新建模块、不重置已验收模块。
### 尚未验证/批准
未安装/运行SDK或重启服务、读Key、调用模型、提交生产SQL。SDK＋内置CLI版本/许可/Commercial Terms/Windows隔离、AI Plan/DeepSeek工具协议、Skill加载/权限顺序、遥测/多轮费用与外发需进一步核。既有单次Messages文本/stream成功≠SDK。SDK依赖env覆盖不等于环境隔离，allowed_tools非安全白名单；不默认Bash/Write/任意Read或宿主settings/hooks/认证。SDK安装/循环/真实网关/MVP均not_run。
### 验证计划
本轮验证文档一致性、Skill引用与同步、progress checkpoint、需求覆盖、Git分支和秘密扫描。历史运行测试不声称新重跑。新SDK实现后再全回归＋真实工具/质量/恢复/网关测试。后续同问题/合成数据/工具/预算比较SDK与LangGraph，比较结果not_run。
