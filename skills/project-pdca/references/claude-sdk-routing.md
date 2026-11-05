# 本项目 Claude Agent SDK 路由与迁移约束

适用条件：universal-data-agent、D-M04B-CLAUDE-SDK-070；其他项目不强制SDK。当前实施真源是progress/ROADMAP/M04 plan/PRD。此文指导项目规划，不是已部署的产品 Skill，也不授权子Agent、Shell、网络、安装或付费。

## 路由与治理分工
- 产品托管的、版本固定的Skills指导问题澄清/元数据探索/指标选择/受控SQL；先取得技能路由及加载记录，再允许执行。只读探索可多轮，不要求业务用户先知道metric_id；同一明确槽位不反复问。
- Skill文本和工具返回都是模型输入，不能提高权限。SDK自动选Skill不构成遵循流程的证明；执行工具校验Skill版本和route token，未加载/不适配拒绝执行。
- 发布的指标匹配则优先指标引擎；不匹配需明确口径/字段/关系并申请受控SQL，不偷偷fallback或猜JOIN。
- 模型自主选择工具顺序，Harness仅限制危险动作。通过受治理MCP/adapter提交；取数工具自动执行必要质量检查，结果发布工具核执行＋质量回执/版本/owner。FAIL/UNKNOWN不得显示已验证成功，WARN必须解释；质检是数据质量不是因果或企业认证。
- 不能仅依靠SDK hooks/can_use_tool：allowed_tools的权限顺序须按所锁版本确认，可能提前自动批准。安全必须落在服务端工具与发布入口。禁止bypassPermissions，默认不提供Bash/Write/任意Read/WebFetch/子Agent等旁路；未来确需代码分析先单独批准沙箱。

## 迁移前核验
1. 官方SDK与内置CLI版本/wheel/hash、Python/Windows、许可与Commercial Terms逐项核，不把SDK当MIT库；官方仓库main仅调研非版本锁。
2. 现有AI Plan Messages文本通过不证明SDK工具/Skill/stream兼容；核受支持Claude模型/鉴权/端点/上下文/用量，不猜网关支持，不继承host账号，不索取聊天Key。
3. 隔离runner使用最小父环境＋独立HOME/cwd/config，设置来源不加载user/local；若project设置用于Skills，只加载项目控制、可审计目录并禁hooks/未知MCP。SDK env参数可能继承环境，不以env={}称隔离成功。
4. 多轮tool_use需要新的明确turn/tool/token/wallclock与预算预留策略。沿用D053总campaign，不reset，不把max_budget_usd当第三方网关实际费率硬保证；费用未知或不明执行不自动重试。
5. 同一业务任务绑定owner、模型/技能/语义/来源/计划版本，确认失效与MCP tombstone保持。SDK resume不是exactly-once，M05之前不宣称跨重启生产持久化。

## 检查与分支
主线main按SDK计划推进；codex/langgraph-baseline-20261103保留C01 baseline/历史证据。SDK未实现前旧代码仅迁移基线，不冒称SDK运行。比较时用同一合成数据、问题/授权/工具/质检预算，记录完成/正确/澄清/成本/延迟/违规调用，不能虚构比较结果。保留原required/not_run、失败记录、已验收模块与回滚，SDK失败不暗换回图或其他供应商。

## 通用架构补充
本项目D080之后规划结合[governed-agent-design.md](governed-agent-design.md)及ARCHITECTURE_V2：适用性路由/结构化语义落地/有界任务依赖/记忆知识分离，保持SDK动态编排与Harness执行门禁。机密资料不写Skill或公开项目，泛化不授予公开许可。
