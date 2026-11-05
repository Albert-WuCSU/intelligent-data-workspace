# A3-M1 本机CHECK / self_review
2026-11-04 · M04-C02-SDK · D077/D078已批准范围内切片

## 结论与实际证据
已完成本机授权元数据发现与批准口径派生的L2单表模板切片；不是完整企业主题Skill库/L3自由SQL/公司数仓或用户验收。命令`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`退出0：**642后端 / 23前端 / 45浏览器 / types / build / pip / 源稳定全通过**。fingerprint `4d39b9b48bd499383292b6526d9bea41d009dc71025e85928b2371555f1a7f0d`，实际命令/日志/清单见results.json与sources.json。

初始专项26通过后补3项安全与1项实际L2工具标签测试；当前全量包含这些最终新增检查。Progress26/PRD5测试与PRD审计13模块/64需求通过，CRLF-aware diff-check退出0。此次实现中一次JSON Schema括号编译错误在检查前修复，未放宽测试。自审非独立审计；UI-only快照非实模型/用户研究。

## 用户任务→实现→检查
- 不知道字段：list_authorized_tables列当前任务唯一授权绑定表及可用批准metric ID/name；search_authorized_fields给实际字段/name/type/schema_hash，无行数据/分区猜测/全仓目录。未加载Skill/其他table/超长/无匹配字段/预算拒绝已测。
- L1未匹配但可采用已有批准口径：load_topic_sql_template返回版本1.0.0的canonical metric/表/grain/time/筛选合同与绑定receipt；propose_topic_query只允许该模板参数。不新增业务指标定义；L1匹配拒绝L2，不以主题路径绕口径。
- receipt绑定route/Skill/task/source/schema/澄清轮次；换route/绑定/schema/Skill/未知metric/旧receipt拒绝。字段/grain/filter/time/只读/AST与扫描预算复用原编译器；Web自由SQL仍禁，多表JOIN/未选源仍禁。
- 修复原_set_plan仅比metric ID的安全缺口：现在完整canonical定义对比，测试同ID换column/unit/name/additive均拒绝；提交后禁止再规划或改变已发布结果。
- 同一显式用户确认→真实独立合成MCP全输入150/匹配51/两组，总6375作为合成金标准，自动QA/PASS/receipt发布不靠模型记忆。SDK Web假网关真实CLI9步走完L1查找→元数据→模板→计划→确认→执行/QA→正文，不是实AIPlan调用。
- query_path来自真实计划/发布合同并再核，正文区分L1指标与L2批准口径派生模板，标签不是质量认证。实际工具步骤显示正确propose_topic_query，不误标L1；黑白主题/历史/手机/刷新/结果保留既有回归通过。
- Skill1.0.6，工具协议1.0.1，模板1.0.0；只新增4个治理工具，不开Bash/任意Read/Write/Key/host配置。新增元数据读取共享原6调用预算；16步20工具200K/600秒与2USD估算预留不变。

## 运行与授权事实
用户已手动重启A2.1，新监听8000PID32324/Vite30252于18:01:32启动；本轮只读200、model unconfigured/0task、原source启用，账本49/60/估算余额2.75USD不变。A3改动在其后，**A3默认API加载/真实模型测试not_run**；不停止用户服务或绕过前轮环境拒绝，Vite热载不等于API加载。见runtime-observation.json。没有真实model调用/费用追加/公司数据SQL或截图复制/依赖安装/子Agent/commit/push。

## 剩余门禁
M04仍DO/not_verified、未用户验收；真实DeepSeek复测需Key及用户明确动作，预算只够重测0.25+一任务2USD，三项需补授权不得reset。真实Claude、生产/MVP门禁保持not_run。

完整企业L2主题Skill（有真实批准表/业务口径版本）、L3无语义/自由SQL/多表/分区、模型中间公开消息安全流与跨独立任务context、B M03业务RAG、C公司多源/导出/PythonQA仍未完成。现有模板基于已批准metric，不能说已经自动覆盖新业务语义。下一步独立可做合成合同/评估与公开消息流脱敏调查，不需要用户今晚操作；具体业务/数据/费用新授权另留门禁。
