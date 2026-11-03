# C01时间与诊断修复的证据范围

第三次全量真实捕获2个新timezoneguard失败，旧guard要求所有DATE/naiveTIMESTAMP也依赖engineUTC，与实际类型语义不符。修复不是删除UTC规则或解锁配置：
- DATE/无时区TIMESTAMP使用日期边界，字面午夜在已声明列语义下比较，不被展示时区左右。
- TIMESTAMP WITH TIME ZONE只绑定显式ISO+00:00UTC上下边界，避免连接Asia/Shanghai默认。三个实际类型/两条UTC边界行的lockedShanghai独立DuckDB测试返回明确sum9/匹配1；没有改生产全局配置。
- TIME/TIMETZ不支持日历日期区间，模型计划澄清，compiler拒绝；不是强行cast或丢日期。带tz分组结果datetime保留instant并UTC呈现。
- 模型截断/不完整响应在同一ownedtask回执里保留既有safeModelResponseDiagnostics，UI只reason/token/已允许ID字段，无正文/Key；GET诊断不再花费或调用。
- 第二Agentfixture同域/同label创建违反了真实语义alias冲突门禁，独立fixture域/来源label改sourceUUID，安全校验和实查询断言不减。2浏览器E2E过，包括完整query与截断无SQL+诊断。

33Agent专项包含真实独立MCP/无network图runtime/预算/版本/超限、当前33过；2Agentbrowser过。最新最终全回归未结束之前不能宣称整体通过。原first/second/thirdfailedresults都是历史证据，不覆盖成passed。
真实userproviderJSON/businessSQL/当前liveAgent404与Key未配置的状态不由fixture提升，需用户加载新版并网页显式验证。不盲杀/读取Key/外部trace/公司prodquery，完整后续JOIN/M05MVP仍未完成。
