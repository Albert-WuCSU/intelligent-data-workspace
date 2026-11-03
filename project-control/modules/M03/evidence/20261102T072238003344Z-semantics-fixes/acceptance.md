# M03 单表语义切片自审（最终后端重跑结果另附）

Reviewer=self_review，非独立审计或真实用户研究。批准方案D-M03-PLAN-066，active M03不自动验收关闭。

## 用户任务到实现
知识库独立页：选择真实授权来源/表和元数据字段，声明对象grain/单位/可加性/必要时的时间语义，定义count_rows/sum/ratio与别名→校验缺字段/类型/名称冲突→明确Boolean批准→发布不可变版本→编辑为v2/重启追溯。高级JSON导入只创建未批准草稿，32KiB且extra字段/SQL/Python拒绝，默认不让业务聊天填JSON。

## 实際元数据/权限
semantic_metadata只调用MCP describe_table；HTTP先验证现有授权目录和返回表名，PG仅实际允许账号系统目录分支（realPG未验，fakeconnect仅契约）。没有通过100行预览反推出字段。真实localMCP/HTTPfixture测试把preview设失败断言仍通过，浏览器无preview/execution请求。
主体服务器固定development/local-workspace/local-developer，owner字段由服务端绑定，未知源/版本和禁用源拒绝。source_version/schemafingerprint记录实际字段，发布时重查并冻结source版本，后继resolve每次重查，stale/disabled拒绝；不当独立企业口径认证/唯一性检验。

## 结构与数值合同
有限operators，不执行任意定义字符串。sum/ratio严格实际数值type白名单，不把INTERVAL或名字前缀当数值。ratio显式分子分母且不可加、分母0为空，无强制统一时间。source/metric/alias缺失歧义需人工修复；approval必须实际true布尔，不接受1/stringtrue。

## 存储与恢复
草稿最多100/校验200，32KiB包/最多12metrics，session-only；SQLite版本500持久保留，无删除/自动回收。拒绝版本文件/目录链接（模拟分支tested，不冒称生产符号链接故障认证），事务+owner/pack/version唯一性，同请求指纹重读和并发两store测试防重复版本，不同请求复用编号/旧expected_version拒绝。编辑新版本不修改旧定义；重启可读发布幂等回执/不可变版本但草稿失效。

## CHECK证据与失败保留
早期21semantics专项/实际localMCP、HTTPmetadata和fakePGcontract过，65semantics+foundation专项及2browser语义路径过。初全回归545backend+1旧capability断言failed/39browser+1旧知识库placeholderfailed，修为实际knowledgeauthoring/noSQL且保留其他未实现不可用断言。第二全回归551backend+1已有PIDfixture创建/写入竞态failed，16frontend/41browser/types/build/pip实际passed。修fixture等待完整PID同5秒、assertaliveowner/同6秒stop/OSdead/2slots，以及finally自己资源清理；1专项passed。最终所有backend重跑，产品/前端/合同没变，16/41UI证据按hashproof复用，不混称再次实跑。
桌面黑白/手机发布历史截图已查看，无水平溢出；JSONimport+ratioaliases编辑/来源disable不可consume/发布v1v2/重启路径来自实际产品API和独立MCP测试源。不是市场/用户访谈研究。

## 产品边界与未完成
当前单表定义首切片本机实现，非M03整个未来PRD全部交付。JOIN/entityhierarchy/SQLtemplates/RAG/externalpolicy和更复杂术语检索明确未实现，不伪装按钮可用。发布版本resolve契约已核，实际M04-B LangGraph查询节点消费和最终SQL/质检仍后继RG门禁，不能以读取JSON当模型已执行或MVP完成。
默认用户后端若未加载semantic路由须用户本人安全加载新版一次，不读取/搬运Key、不盲杀；本轮未收费调用模型、公司数据或部署。实际用户当前知识库输入/审批未走查，测试fixture不等同真实用户确认。M04-A D064有限本机验收与历史failed/外部风险/requirednotrun发布补验保持。
M03验收由用户独立确认，之后M04-B PLAN核LangGraph版本/依赖与聚合MCP能力：实核PreviewRequest/compile_preview只SELECT列/LIMIT，不能拿100行求总体或向旧HTTP强发聚合；详见M04/PREPARATION。
