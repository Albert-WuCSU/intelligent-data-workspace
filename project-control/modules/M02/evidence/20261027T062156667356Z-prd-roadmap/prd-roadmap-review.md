# 模块PRD、模型前置路线与当前M02缺口复核

2026-10-27；reviewer=self_review。该报告是文档/范围与代码证据核对，不是M02最终交付audit，更不是模型服务或LangGraph运行验证。

## 本轮文档交付

13个交付PRD覆盖原12模块加M04-A；原进度M04保留为M04-B，没有重建项目/改M01验收/提前结束M02。每份PRD包含角色/用户任务/默认路径、需求ID/功能、非目标、输入输出/安全边界、可观察AC、风险/证据或not_run。55条需求从现存决策/用户原则/交接/产品方案及本聊天追踪，不声称找回未保存项目外聊天；USER_REQUESTS保留模型与PRD原话。V0.1中的候选/时程/准确率/兼容清单仍规划假设，不当已测成果。

D-ROADMAP-MODEL-014依据用户明确要求登记；模型API前置于语义库，数据源和模型服务分开。新增M04-A pending依赖M02，M03依赖M04-A，原M04对应M04-B依赖M02/M03/M04-A；其他模块依赖完整/无环。M04-A先薄ModelProvider，M04-B优先LangGraph混合图编排，旧安全/幂等/Worker独立。不默认LangChain全套或LangSmith外部追踪，实际版本/安装/供应商/端点/费用/数据外发/持久化仍需后续PLAN和授权。本轮未安装或调用模型，M04-A/M04-B为not_run。

项目ROADMAP/PRD/AGENTS/brief/用户原则/M02 plan及原产品方案补充同步。项目专用Skill只存在project-pdca，更新入口及路线/交付/用户思维三个引用；个人安装副本4文件在核对原hash、获运行审批后同步，未改脚本/其他Skill/凭证或应用配置。规则条件化，仅本项目有批准记录才使用顺序，不强加其他项目。

## 本轮验证与限制

PRD一致性命令实际退出0：13模块全部覆盖、55需求无孤立、来源文件/决策存在、M04 ID无重复、依赖图一致与无环、M01已验收/M02 active及原清理pending保留、Skill引用存在与副本一致。5个独立文档guardrail、21个原进度机制测试退出0。该检查不证明PRD市场正确、未来功能或用户研究真实。

通用Skill Creator quick_validate初次因PyYAML缺失不能运行，未为文档新增依赖；记录not_run。另做已知frontmatter格式/引用/项目条件与同步校验，不把替代窄检查写成通用YAML工具通过。自建校验脚本初次生成正则有转义语法错误，修复后完整复跑通过，未删行为断言。

产品src/UI/contracts/tests/scripts/锁/开发说明等93份文件与最近206后端/10前端/20浏览器来源指纹逐文件一致；本轮只改产品规划/Skill/档案，不涉及运行源码。故保留原运行回归作为可复用证据，不编造本轮新206测试执行或因此重启服务。5173/8000监听仍现有PID2204/12504、两个health200，本轮未停止/启动任何运行服务。新窗口仍核对拥有者，不能继承exec session。

## 文档完成后继续的M02范围审查（只读，不越过清理选择）

| PRD验收 | 当前代码/既有证据 | 缺口/下一步 |
| --- | --- | --- |
| M02-AC01 三类自助连接 | source_profiles/routes、DataSourceWorkspace及旧source/remote-onboarding真实local/认证HTTP测试 | PG配置与适配已有，但真实PG实例仍not_run；单独授权独立实例后补测试，不用公司数仓或自动安装服务 |
| M02-AC02 上传/资源/秘密拒绝 | upload_preflight、worker_runtime/stdio_transport/18上传专项/W1W2；只清本次新暂存 | API整体/生产DoS及非Windows/权限沙箱不是已验证；保持正式发布门禁，不能由框架替代 |
| M02-AC03 PG实例/TLS/权限 | requirements.postgres锁/adapter及隔离单测 | 当前无真实实例，required not_run，不删门禁 |
| M02-AC04 清理方式/竞态 | storage_inventory只读，SourceStore.tests在内存，save无TTL，cleanup只本次失败；D-M02-RETENTION-013未回答 | 24h或手动策略未选，自动清理/计划执行/跨重启过期/引用竞争not_run，不能把盘点变删除；选择后先建生命周期/provenance/活动引用合同及失败测试 |
| M02-AC05 审计与delivery | M01验收保持，M02现多个self_review切片 | 高风险/真实PG/清理尚未闭环，最终audit not_run；不得先进入M04-A/M03或将M02closed |

这一步实际阅读当前storage_inventory/SourceStore/测试状态并与PRD对照，没有用“建议审查”代替已执行检查，也没有重做旧单测或越过pending去实现TTL。下一可执行业务工作仍需清理A/B选择；不因本次路线批准推断该选择。模型供应商/协议/网络/数据外发将在M02交付后的M04-A PLAN明确。

## 交接与回滚

保留清理pending、所有旧决策及证据。PRD/route改变需要修progress并checkpoint，不删除M04/M01历史；如需回退顺序按新用户变更追加，不篡改旧决策。原PDF/历史图未重新导出，文件顶部已明确原策划不是新版PRD。后续Skill若变化先审差异，不全量覆盖个人配置。
