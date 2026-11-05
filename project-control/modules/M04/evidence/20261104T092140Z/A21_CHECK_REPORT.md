# A2.1 常规Agent式对话：本机CHECK / self_review
2026-11-04 · D-M04B-CONVERSATIONAL-UX-078 · R-U31 / M04-B-AC05

## 需求核对
原PRD有D077连续对话原则，但缺少收到问题后的顺序化公开执行说明/紧凑工具标签/发现限制/原任务澄清问答/最终正文报告验收。A2短句加大卡片未视为此体验已验收。本轮补R-U31/AC05、需求原话/机器追踪/索引/specs/PRD/plan/UX/ROADMAP；D078登记用户原话，不据截图推导公司数据或宿主权限批准。

## 实现
- AgentDialogueEntry按实际后台事件生成有序的公开说明、工具标签、澄清问题与用户补充，不转发原始thinking、工具参数、SQL、行数据或宿主路径；来源标为治理事实/用户回答，不冒充模型思考。
- 同任务恢复/确认、版本/预算/幂等/QA发布门禁不变；SDK主输出不再用大型result-card壳，模型正文支持安全标题/列表/强调/代码；HTML转义且不开外链/图片/脚本。
- 正文数值直接取经回执发布的后端结果、分组表内嵌；模型不猜数、不额外接收结果行。范围/单位/来源/质量/限制/下一步可阅读，SQL/回执折叠。黑白主题、原问题顺序、历史、右摘要、真实pipeline保留。
- 产品Skill1.0.5与system prompt明确要公开范围/发现/限制与正文报告，而非“仅查看结果卡”；最后一次AssistantMessage保留全部公开TextBlock，不只最后一块。

## 实际检查
完整命令：`services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser`，退出0。
**631后端 / 23前端 / 45浏览器 / types / build / pip及源稳定全部通过**。
code fingerprint：`dcbf6753a9f16844c1eccf1baaa19ff595b77af682993b84f17f30303a8b9dfd`。真实命令/环境/退出/日志与文件指纹见results.json/sources.json。

专项19（新增公开对话+SDK Web）通过；前端安全正文3项包含HTML/JS/链接/图片不执行；SDK Web用真实离线SDK/CLI+假网关+真实合成MCP验证DTO对话/工具/问答顺序/后端回执。新增浏览器对话场景是明确UI-only快照，其他真实产品组件fixture回归保留，不当实DeepSeek证据。补充visual临时测试1passed为合成UI正文/有序对话/主题/手机走查，不是用户研究。PRD审计13模块/64需求及5测试、progress26测试通过，self_review非独立审计。

首次091236Z运行产品项631/23/45通过，但末审Skill/prompt改动造成源稳定失败；保留stale清单和CHECK_RECHECK_NOTE，未放宽断言。092140Z从最新完整源码重新全量通过。

## 默认服务与未运行门禁
本轮重启命令被当前执行环境拒绝，**未停止/重启服务，也未换其他脚本绕过限制**。旧launcher20164及8000/5173仍响应200、模型unconfigured、0任务、原授权来源仍启用；新执行对话字段尚未验证在默认API运行。需要用户手动关闭本项目旧开发服务并重启启动器再验证；Vite可能热载新UI，不能因此称API已加载。见runtime-status.json/restart-not-run.txt。

D053只读账本49/60未变、估算余额2.75USD（非账单）；重测0.25+一个SDK任务2USD仅够一个完整复测，三项需补充预算授权/实施，不reset。没有真实模型调用、费用追加、公司数据/SQL/图片复制、host Bash/Read/Write/Key权限、安装或commit/push。

**仍未完成**：默认API加载/真实A2.1体验验收、模型中间公开消息的逐条安全流式（目前过程为治理事实，只有最终模型正文）、跨独立任务自动语义继承、A3 L2/L3、B业务RAG、公司多源/下载/PythonQA、真实Claude/生产/整体MVP。M04仍DO/not_verified、未关闭。
