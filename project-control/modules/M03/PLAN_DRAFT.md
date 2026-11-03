# M03 语义知识库最小切片方案草稿

状态：draft，仅相邻低风险准备，未获PLAN批准/未进入DO。依赖M04-A整体审查＋人工验收；当前active仍M04-A，不新增后台运行组件。

## 用户任务
分析师把“求和/数量/比率意味着什么”绑定真实数据表与字段，业务用户选定已批准版本问数而不写SQL。最短路径：知识库→新建语义包→选已授权来源及真实字段→定义指标/粒度/单位→检查映射与冲突→人工确认→发布版本。默认拒绝缺项与未知粒度，不按字段名猜日期/币种/关联。

## 第一切片范围（拟）
- 单域、单真实授权表，count_rows、sum、ratio有限结构化算子；比率分子/分母、去重与grain不可隐式默认。
- 术语/名称/别名、责任人声明、实际字段映射、单位和需要时的时间字段/时区/含义。无时间表不强制填日期。
- 草稿validate→用户批准publish、不可变版本与只读追溯、废弃/停用不删历史。审批主体来自后端当前开发身份，负责人声明不冒充生产权限。
- 当前目录从已有M02受治理连接/表导航获取；不读任意公司元数据、不复制宿主工具权限。元数据变化/连接停用使mapping stale，问数重新核验。
- 知识文本不作为执行指令，拒绝额外字段/未知算子/任意Python/插件/网络策略；不执行包内字符串SQL。
- JOIN关系合同只能显式keys/cardinality/grain声明，未验证join不开放；本切片不执行SQL、不调用模型自动认证。下游M04-B再消费发布版本。

## 方案比较与拟推荐
推荐复用已安装Pydantic/SQLite标准库：有限JSON契约＋独立非秘密语义版本库，部署在项目现有local runtime模式下，不安装向量库/RAG/第二套框架；利用事务和唯一版本约束。持久存储路径与保留/审批策略需要PLAN确认，不把progress作为业务DB。
备选JSON快照文件：可读但原子版本/并发治理成本更高。暂不推荐向量数据库：当前结构化口径的授权/执行真源不需embedding，增加外发和依赖而无验证收益。

## 拟输入输出
DomainDraft{id,domain,name,source_ref,table_ref,mappings,metrics,aliases,owner_note};版本由后端生成，schema_hash/connector_generation来自真实M02回执。Metric{operator,columns,grain,unit,ratio_components,time_semantics?}。Validation{mapping_state,conflicts,required_clarifications}。PublishedVersion{version,approved_by,published_at,schema_fingerprint,immutable_contract}。
不接受客户端tenant/scope/价格/执行权限，不输出Key、本机绝对原件路径、供应商正文。口径版本是执行定义，不保证业务收益或因果认证。

## CHECK计划
合法创建/真实元数据映射/缺字段与类型冲突/别名歧义/ratio条件/无时间表；未知算子/注入/跨身份拒绝；schema变化stale和版本发布原子性；重复提交幂等、并发版本、只读回滚追溯；浏览器字段选择→校验失败修复→明确批准→版本显示，黑白/键盘/手机/空失败下一步。实际M04-B消费要在其后续模块验收，不造Agent成功。

## 待PLAN确认的判断点
确认M04-A交付范围后，建议一次冻结上述单表语义切片、非秘密SQLite版本存储/保留及当前开发角色审批语义，再进入M03 DO；不是重新询问模型预算/PG延期。生产身份/SSO/公司数据外发/向量库/保留删除规则不包含在草稿批准。

## 回滚与边界
关闭新模块路由/恢复代码，不删已发布包/用户原件/现有source/model ledger或证据。模型目录自动发现和Key持久化仍BACKLOG待办。顺序M03→M04-B LangGraph＋治理Harness：生成计划→口径澄清→权限/SQL/预算→人确认→M02执行→结果对账，不靠框架恰好一次或preview100行推总体。
