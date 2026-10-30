# 本轮早期失败观察（非最终测试证据）

1. 第一测试collection因dev.py机械替换少括号触发SyntaxError；修回正确Popen append后继续。
2. 沙箱内模型专项有pytest临时目录收尾WinError5，按原命令获批沙箱外运行，不忽略收尾或改断言。
3. 超大65537字节fixture使用默认长参数ID时setup/teardown报错，30项过/2 errors；改成显式短IDmalformed-json/oversize-response，同一响应字节和断言未变，31项实际通过。
4. 后又加压缩响应/Worker环境/input/未知usage4项并硬化response编码，最终完整322后端（含35模型专项）通过。

前3步详细输出留在本轮工具记录；本文件只转录观察与改进，不伪称完整原始stderr副本。最终日志见完整回归backend.txt。没有真实网关/Key参与。

5. 首完整322/16/types/build/pip通过，28浏览器27过1；新增模型状态用例误写API已连接，而实际文本为API 已连接。按实际DOM精确定位修正空格，仍断言可见，不改产品/放宽或删断言。随后全28浏览器重跑，后台字节不变保留原322结果，不冒称后台重跑。

6. 全28浏览器实际退出0/源码稳定，结果已写到085008539417Z-browser-final；包装runner最后print日志使用主机GBK编码报UnicodeEncodeError，wrapper退出1不等于浏览器失败。没有改浏览器结果码；新最终完整回归脚本自身强制UTF8。
7. self_review补强非秘密字段意外填入专用Key时的反射保护：status不回传、generate拒绝发送，新增1安全专项。旧322/28证据不作为该补强后的最终证据，完整重跑。
