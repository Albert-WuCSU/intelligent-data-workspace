# 磁盘状态合同与续接

## 存储结构

- `project-control/progress.json`：唯一当前状态，含完整模块队列、当前阶段、审批、证据、待决策和下一步。
- `project-control/HANDOFF.md`：由脚本生成的人类可读交接摘要，落后时重新生成，不反向覆盖JSON。
- `project-control/checkpoints/revision-000000.json`：每次提交保存上一版本。故障恢复先核对实际代码，不直接用旧状态覆盖新事实。
- `project-control/modules/<id>/plan.md`：当前方案与验收合同。
- `project-control/modules/<id>/evidence/`：使用不重复的运行编号保存测试、演示和审计报告，避免覆盖历史。

所有项目引用使用根目录相对路径；展示给用户时展开为完整绝对路径。脚本拒绝越出项目根目录的证据路径。Skill安装目录不是项目数据目录。新项目可以采用同一个Skill，但有独立project-control。

## 主要字段

schema_version=1；revision为乐观锁版本；project含id/name/source_refs/scope；status为in_progress/awaiting_decision/blocked/paused/complete。blocked表示实际不可继续且已注明外部条件，不以困难替代调查；paused只用于用户明确暂停。

active_module对应唯一active或needs_recheck模块。modules记录id/name/milestone/depends_on/status/phase/cycle_id/maturity/plan_ref/approvals/implementation_items/tests/evidence/audit/risks。模块status为pending/active/needs_recheck/closed，phase为plan/do/check/act。maturity为not_verified/local_ready/staging_verified/production_verified，不混淆代码完成与生产验证。

decisions是追加式人工决策列表，字段包括id/kind/module_id/cycle_id/source=user/user_statement/selected_option/rationale/recorded_at。kind为scope/plan/delivery/change/permission/method/risk。保存用户真实选择和解释；模型建议不能填成用户决定。脚本能要求证据字段存在，但不能鉴别真实用户身份，仍需Agent遵循对话授权边界。重新考虑已有决策时追加supersedes字段，不篡改旧记录。

pending_decision包含id、blocking=true、question、options、recommended及影响模块。next_action包含kind/description/decision_id/read_refs/commands；commands只是便于复现的说明，不自动执行。waiting决策必须有与之相同的next_action.decision_id。候选方案不是批准记录。

implementation_items记录具体切片及路径；tests记录id/required/status/environment/integration/command/exit_code/code_fingerprint/evidence_id。status为passed/failed/not_run/stale；environment区别local/staging/production，integration区别mock/real/unit。passed需真实命令、退出码0、代码指纹与证据。code_fingerprint是当时提交及相关文件摘要，不是脚本自动证明当前代码未变；每次续接和变更必须核对。

evidence记录id/kind/path/sha256/stale；hash由 `progress.py hash --root <root> --path <相对路径>` 获取。审计verdict为not_run/pass/fail，引用evidence_id并注明reviewer。closed要求当前cycle的plan与delivery人工批准、必测通过、当前证据、audit pass、无未解决critical/high风险。

release_gates记录项目或里程碑真实集成、安全和发布验证。缺凭证时做mock单元测试不影响开发，但真实集成not_run，不能直接closed。若用户批准有限本地交付，先修改验收范围并保留真实验证发布门禁；不得仅把required改false来绕过验收。

change_impacts记录原因、受影响模块、契约/代码/测试/部署及处理方式。closed模块内容变化必须有新增影响记录；进入needs_recheck后测试标stale，保留旧审计历史。working_state记录工作树、未提交变更、运行任务与环境事实；blockers写资源及解除条件，不写密钥。session含recommend_new_chat及理由，不能假设可访问精确上下文计数。

## 安全提交示例

使用当前可用Python运行时，绝对路径调用安装的脚本；不要假设python或Skill的固定用户路径。依次：

```text
progress.py show --root <项目根>
progress.py validate --root <项目根>
[读取旧progress，生成progress.draft.json；保留revision和已有decisions]
progress.py checkpoint --root <项目根> --draft <草稿绝对路径> --expected-revision <旧revision>
```

checkpoint不运行SQL、不安装包、不调用服务。它获取短期锁、检查revision及门禁、保存旧快照、原子替换JSON并生成HANDOFF。失败不修改主状态；revision冲突必须重读并合并，不能强制覆盖。脚本的安全门禁不替代代码审查及真实环境验证。

checkpoint.lock残留时先确认没有正在写入的进程；用户或当前执行环境授权范围内才清理锁。不自动抢锁、不同时让多个Agent写状态。主JSON成功但HANDOFF失败时用render-handoff恢复；历史文件存在且当前版本未推进时先检查是否上轮中断，不盲目删除备份。初始记录只在不存在时创建；已有记录按schema_version显式迁移。

## 接续最小上下文

恢复只加载进度、当前模块计划、最近证据、依赖合同及相关代码，不重新阅读完整策划文档和所有历史日志。首轮尚未批准时可阅读项目brief及首次方案卡。新聊天需关联同一目录并显式调用Skill一次；之后可说“继续推进”。
