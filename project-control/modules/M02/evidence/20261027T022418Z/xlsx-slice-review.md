# M02-C03 Excel导入切片检查点

2026-10-27；self_review，局部已验证，不是完整M02验收。

用户反馈.xlsx上传失败，现已支持文件选择/受控路径.xlsx→只读工作簿解析→隔离DuckDB快照→真实stdio MCP测试→保存profile→按工作表导航→原表头、类型/日期值、前100行。第一行作标题、中文sheet名保留、多个可见工作表分别成表，空/重复表头规则写入CONNECTORS.md。日期列未删除，没有时间筛选或隐式WHERE。

后端108（Excel5专项）、前端10、浏览器15，类型/构建/pip check通过。新增浏览器xlsx测试真实上传双sheet含120条日期记录，读取100行/中文列标题/日期值，再切换字典sheet；不从用户公司取文件或数据。查看xlsx-navigation.png核对列头、100行窗口与表列表可读。sources.json逐文件一致，原合成仓SQL/Parquet/golden另外复核，未修改旧数据。

openpyxl3.1.5/et-xmlfile2.0.0在项目venv，MIT元数据/轮子摘要/安装审批和独立锁保存，原基础及warehouse锁约束不升级。使用读取功能，不用其创建用户交付工作簿；OOXML测试样例仅有限软件测试fixture。只读/data_only=False/keep_links=False，不执行公式、不用缓存冒充最新计算，不自动读取外链/宏。未支持.xls/.xlsm/加密、隐藏sheet、复杂报表等，拒绝信息具体可行动。公式文件提示在副本粘贴为值后重试，用户原件不修改。

ZIP文件数量/解压总量/单项/压缩比限制、路径/XML实体/宏/外链/嵌入对象拒绝及公式/错误值处理，避免伪装任意ZIP；不extractall。上层20MB上传预算/每sheet20K行100列50万cells等保持。尚未进行全量Excel兼容或OS级解析隔离认证。

剩余M02：PostgreSQL、HTTP MCP地址/认证/受治理工具映射，Worker/OS硬限额与故障恢复，秘密管理/配置和上传副本TTL/删除界面，完整模块self_review与用户验收。M01原UI/历史/安全基线继续通过，没重建项目。不标M02closed/production_verified，不称自然语言Agent已实现；新窗口从当前progress继续。
