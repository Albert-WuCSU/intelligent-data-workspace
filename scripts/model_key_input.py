"""User-operated local terminal entry; no fallback echo or persistent credential."""
import getpass
import re
import sys
import warnings

def read_model_key(*, stream=None, prompt=None):
    stream = sys.stdin if stream is None else stream
    if not stream.isatty():
        raise ValueError('需要本机交互终端隐藏输入，不接受管道或聊天输入。')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            value = (prompt or getpass.getpass)('应用专用模型 Key（隐藏输入，退出后不保存）：')
        except (getpass.GetPassWarning, EOFError):
            raise ValueError('无法隐藏输入，已拒绝；请在本机终端重新运行。') from None
    if not isinstance(value, str) or not re.fullmatch(r'[\x21-\x7e]{8,4096}', value):
        raise ValueError('Key格式无效，未启动模型服务。')
    return value
