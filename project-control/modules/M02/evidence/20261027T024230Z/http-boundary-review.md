# M02-C03 HTTP传输前置边界检查点

2026-10-27；reviewer=self_review；局部范围local_ready，不是完整M02 ACT/验收。

## 用户任务→实现→证据

配置人员最终需要输入自己的MCP地址/数据库并建立可复用只读连接；本轮先防止新HTTP入口成为任意网络/秘密转发器。新增http_boundary.py尚未挂接产品profile API/UI，所以现有MCP接入进度提示仍真实；配置认证与PG仍not_run。网页原任务保持本地来源→测试→保存→表导航，原列头/类型/100行，保留日期字段且无WHERE时间筛选。

真实完整命令services/api/.venv/Scripts/python.exe scripts/check.py --module M02 --browser退出0；153后端（其中45 HTTP新增）、10前端、15浏览器通过，类型/构建/pip check通过。额外单跑真实HTTP fixture与原数仓verify退出0，见extra-results.json。前后74文件sources一致，只有CONNECTORS.md在原72文件中修改，另新增两个源码/测试文件；四份依赖锁、已有UI/main/config/profile/stdio客户端/合同未改，未安装任何依赖。

HTTP真实集成使用临时loopback端口+uvicorn/FastMCP+临时合成CSV只读快照；实际SDK握手/六工具目录/执行100行并返回两列日期值。证据仅表明该内部传输与自有已知工具服务可组合，不证明任意平台、权限、认证或自助保存。没有HTTP协议mock代替此集成；重定向和大小异常负例用MockTransport，明确是隔离安全单测。现有15浏览器测试验证本地来源/.xlsx/内置合成例、无筛选、主题/历史/失败与空态，不声称PG/MCP新增UI已经走查。未招募真实用户，不属于用户研究。

## 边界与整改

SDK1.30会自行跟随部分同源重定向，无视HTTPX follow_redirects设置；在底层直接拒绝所有3xx并关闭响应。服务器精确端点白名单默认空，数字IP/明确端口/安全路径，禁止URL密码/query/hash/编码路径、metadata/link-local/Host覆盖、环境代理/CA继承。非loopback必须HTTPS，禁止压缩、请求64KB、流式响应1MB，当前禁止认证头。IPv6 loopback及HTTPS默认443标准化有测试；端口0负例初跑发现校验遗漏，已增加1..65535校验并完整复跑，不删断言或跳过测试。

初次/修复后局部pytest曾因沙箱不能清理宿主pytest临时链接退出1；按权限申请重跑。最终完整回归与独立real fixture均退出0，不能把初次全点绿但退出1称passed。保留此失败原因，未盲删临时目录或改主机权限。

## not_run/剩余风险

- PG驱动版本/许可/安装和真实实例、HTTP认证与产品配置/保存/刷新/启停、工具合同映射均not_run；待D-M02-REMOTE-SECURITY-009。
- DNS hostname/SNI、真实非loopback TLS、企业OAuth/权限/行列ACL等not_run；数字IP严格限制为本轮策略，不声称域名通用接入。
- 1MB为每响应预算，不是进程级内存/CPU/总时限；Worker/OS硬隔离、连接池、恢复、清理/TTL仍待验证。HTTP当前禁认证头不是认证方案，用户选定秘密方式后要实现并重新测试凭证隔离。
- 原scripts/dev.py仍向两个进程传入开发环境；新增产品专用秘密前必须分离Vite/其他子进程环境，不以宿主工具凭证替代配置。
- 原合成仓/Parquet/golden完整性verify通过，未删日期列或改源数据。
- 正式多用户/生产秘密与部署门禁仍not_run。M02 maturity=not_verified，audit=not_run，不关闭M02或进入M03。

## 运行与回滚

5173/8000始终200，监听PID10824/7932未换，拥有者CN1/luqianwu且父链指向项目scripts/dev.py PID11716；复用已有服务，不继承旧exec session，不停止任何既有进程。HTTP临时fixture线程/端口由测试finally退出并断言释放。仅新增未接线的传输模块/测试，不影响已运行版本；回滚不需要删除原数据或profile。
