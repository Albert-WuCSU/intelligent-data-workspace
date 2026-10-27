# M02-C03 本地用户接入切片检查点

2026-10-27；self_review；只对本地配置闭环评审，完整M02 audit仍not_run。

## 用户任务与真实证据

用户要求连接器接自己的来源，而非固定例，也不是时间筛选器。本次完成首页新增本地来源/非秘密配置导入→文件选择或受控路径→使用授权确认→真实MCP连接测试→保存profile→刷新复用→连接表导航→列头/原类型/前100行→配置修改重测/版本检查→禁用。内置合成例仅可选折叠；PostgreSQL/HTTP MCP信息入口明确说明尚未支持，不称其已连通。

日期列没有删除。真实CSV连接同时保留created_at TIMESTAMP和shipped_on DATE及原值；DuckDB保留registered_on和posted_at、Parquet保留effective_date。网页无input[type=date]、无时间/任何筛选器，MCP预览无WHERE，不猜字段语义/币种/时区；用户来源标user_provided/质量WARN。无时间列表只是通用性负例，不是要求。

真实网页→API→profile→隔离stdio MCP→只读导入快照；非默认源，非mock。后端103（包含8项本地profile专项）、前端10、浏览器14，类型/构建/pip check全部通过；截图核对桌面黑白和手机配置/表导航可读、无页面横向溢出。字段较多时表格自身滚动；当前100行窗口并非排序保证或完整资产。

配置服务器持久化（sqlite3），未存浏览器localStorage或project-control；测试token绑定草稿，修改重新测、旧版本拒绝。上传器检验类型/头部/路径/大小/表数行数列数，multipart body预解析预算拒绝超限；配置导入拒绝命令/秘密/主体字段，失败不清空用户输入。后端固定开发主体校验、原文件不修改、禁止未知源/表访问。runtime-data已加入gitignore，当前仍无Git仓库。没有使用真实公司文件、宿主凭证或生产网络。

代码指纹以sources.json为准，已逐项比对一致。旧数仓/Parquet/golden仍通过warehouse-check.json验证，未删除/重建原日期字段。

## 剩余工作及风险

整个M02未closed。首期已批准完整三类方案中的PostgreSQL与HTTP MCP地址/认证及其真实测试尚未做；不能拿本地回归替代。原有Worker/OS硬资源限额/故障恢复、安全秘密管理/正式多用户认证/生产部署仍not_run。profile文件副本及未保存测试快照尚无自动TTL/删除UI；明确保留政策，禁用不删原文件。引擎限额不等于Python/OS级强隔离。

SQLite配置仅非秘密本机profile，不是正式M05资产/历史持久化。用户上传复制许可不是公司数据外用许可。此处为测试/走查，不是真实用户研究或市场需求验证。下一步继续远程MCP/数据库接入与资源/恢复门禁，不再次请求已批准方案、不擅自减少范围。
