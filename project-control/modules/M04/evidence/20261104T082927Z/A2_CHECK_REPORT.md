# A2 本机 CHECK 与 self_review（2026-11-04）

## 结论
已完成本机切片检查，**不是用户验收/独立审计/生产或整体MVP交付**。当前M04仍DO/not_verified。最终命令：`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`，退出0。

- 627后端 / 20前端 / 45浏览器 / types / build / pip全部通过，源稳定检查通过。
- code fingerprint：`ddf9d400751aed4b4ca065da80447e1d481110318205052152e597413fbd451b`；完整命令/退出/日志与源清单见results.json、sources.json。
- SDK/CLI真实离线运行、本地假网关、独立合成数据真实MCP/SQL/QA；新的A2浏览器场景是明确的UI-only快照，不冒充真实DeepSeek或用户研究。

## 用户任务→实现→证据
- 原发布后max_turns问题：后端执行+QA自动发布，runner只在有效发布及非空/正数/类型合法input/output/cache usage回执时成功；空/零/缺项/非法usage拒绝。test_sdk_agent包含max_turns与有效usage门禁。
- 同任务澄清：SDK工具等待原任务回答；owner/generation/随机clarification_id/配置/语义/来源/实时schema复核，响应幂等；两轮/1600字符/共享预算。补充不授权SQL；原计划/确认失效，计划hash包含澄清轮次。SDK Web E2E证明同ID、同8单位预留、确认后真实150行MCP+QA；旧回答/取消/Schema和模型变化/异步确认竞态拒绝。
- 连贯对话：每任务位于原请求UUID用户消息之后，澄清问答先于Agent回答/报告；卡片作为结果/质量/来源/限制证据，SQL/版本折叠，右侧显示真实元数据/事件。轮询失败保留已收结果，未配置Agent不制造错误提示；SDK2USD估算非账单明确展示。
- 黑白主题/键盘/手机/历史/刷新及旧M01/M02/M03/M04-A回归保留。当前仅本机后台内存任务，不是跨重启生产持久化；独立新问题不自动继承旧筛选/结果。

## 失败与修复历史（保留）
- 此前专项：版本断言未更新、合成物理表名误用、澄清ID先后写入竞态；已修正fixture/version及原子状态，没有删断言/放宽成功标准。
- 080447Z全量：626/20及types/build/pip通过，浏览器44/45；未配置Agent时的轮询notice干扰Schema状态。修复为仅已有任务时保留/报告轮询失败。
- 081413Z全量626/20/45通过；收尾增加严格usage门禁与回归后，082927Z重新全量627/20/45通过。
- Git默认diff-check把Windows CRLF当尾随空白；仅本命令采用`-c core.whitespace=cr-at-eol`实际退出0，未改全局配置或裁剪历史证据。

## 运行与未运行门禁
最终全量后重新核对本项目venv启动器与两个loopback监听的父子树/创建时间，仅停止自己的树，隐藏启动dev。web/API200，新澄清路由无效合同probe422（没有任务/模型执行）。原授权来源仍启用、已发布语义1、账本49/60不变；模型unconfigured，Key需用户重输。详见service-health.json/restart.txt/listeners.json。

估算余额2.75USD，仅够模型重测0.25+一个SDK任务2USD，三项真实复测需要补充授权且不得reset账本。真实收费/费率不verified。

**not_run**：本轮真实DeepSeek筛选/分组/澄清三项复测、真实Claude、生产与整体MVP。A3 L2/L3、B业务RAG、C公司多源/导出/Python QA未实施；公司数据与新连接需另授权。截图只用合成UI，未复制公司数据/SQL；无宿主Bash/Read/Write/Key暴露、无新安装、无commit/push。
