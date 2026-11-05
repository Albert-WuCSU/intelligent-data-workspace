# A2.2 self_review（最终CHECK运行中）

目的：解决“只有固定执行事实+最终卡片短句”的剩余体验缺口，在真实工具之间显示符合门禁的模型公开意图。不是泄露完整思维链，不装新库、不增加模型调用、不开放新工具。

锁定SDK/CLI会在内容块结束后将text/tool拆成同ID AssistantMessages；buffer仅读完整TextBlock并按message_id关联，ThinkingBlock/StreamEvent不处理。安全文本只允许短未来意图/确认范围，禁数字/数值词/凭证/路径/URL/code/SQL/未验证成功声明；unsafe后块毒化消息，避免先放safe前缀。4公开消息/每条500字符/最多16待处理ID，重复ID幂等。提交或publication后不追加。

公开notes以model_public_intent来源标注，与governed_event执行事实/user_answer分离，不显示tools成功标签。runner与APIpublic_dialogue同门禁重核；已过滤text只进隔离task状态，同owner/模型/语义/来源/版本/任务生命周期，后端重启不恢复。unsafe中间text不写失败diagnostic正文。原SQL/QA/receipt/usage/预算/确认门禁不变。

初始SDK专项公开note缺失（CLI拆块），修复后4受影响SDKcasepassed；一项旧modelchange等待失败复跑正常，无独立根因断言，不放宽timeout。31逻辑/公开对话检查passed，browser1passed，最终全量在运行，首失败日志保留。

仍未证实：真实DeepSeek效果或合格意图频率、完整token流/任意模型文本安全语义/跨任务上下文、企业主题/自由SQL/RAG/公司数据/生产与MVP。过滤保守可省略所有notes，事实/确认/结果仍可用，不能为效果放宽。最终模型报告沿用已有结果门禁与说明，不宣称所有模型语言真值已自动验证。

GitHub baseline702cabe已非forcepush并lsremote确认；642/23/45源码证据匹配，LangGraphbaseline92d0b03未变。新代码只有全量通过才再同步；credentials/runtime/user上传/语义/账本/临时draft未提交。用户专用Key未配置，账本49/60/估算2.75USD不变，无收费/公司工具或生产调用。
