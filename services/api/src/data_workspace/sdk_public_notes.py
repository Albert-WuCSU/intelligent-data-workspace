"""Conservative gate for complete, non-numeric public model intent notes.

This is NOT raw streaming or a proof of model correctness. Unsafe notes are
omitted without logging their content; execution facts still come from receipts.
"""
import re

MAX_PUBLIC_NOTES = 4
MAX_NOTE_CHARS = 500
INTENT = re.compile(r"^(?:我会|我将|我准备|接下来|请确认|需要确认|I will\b|I'll\b|Next\b|Please confirm\b)", re.IGNORECASE)
FORBIDDEN = re.compile(
    r"[0-9０-９一二三四五六七八九十百千万亿零两%％$￥¥€£]"
    r"|https?://|www\.|[A-Za-z]:[\\/]|[\\/](?:Users|home|tmp|etc|opt)[\\/]"
    r"|[<>{}\x00-\x08\x0b\x0c\x0e-\x1f]|```|`|\[.*\]\("
    r"|\b(?:select|insert|update|delete|drop|pragma|bash|powershell|api[_ -]?key|auth(?:orization)?|token|password|secret|sk-|ghp_)\b"
    r"|已经|已(?:读取|找到|匹配|执行|完成|通过|确认|发布|验证)|查询成功|质检通过|结果(?:为|是)|总计|合计|思维链|思考过程"
    r"|\b(?:succeeded|completed|published|verified|passed|result(?:s)? are|total is|chain of thought|reasoning)\b",
    re.IGNORECASE,
)


def safe_public_note(text, secret=''):
    if not isinstance(text,str): return None
    text=text.strip()
    if not text or len(text)>MAX_NOTE_CHARS or len(text.splitlines())>4: return None
    if secret and secret in text: return None
    if not INTENT.search(text) or FORBIDDEN.search(text): return None
    return text


class PublicIntentMessageBuffer:
    """Join only complete safe text blocks by upstream ID until a tool block.

    No raw unsafe text is retained. A bad block invalidates that whole message,
    not just the block, preventing a safe prefix escaping a later unsafe suffix.
    """
    def __init__(self, secret='', max_messages=16):
        self.secret=secret
        self.max_messages=max_messages
        self.notes={}
        self.rejected=set()
        self.seen=set()

    def add_text(self, message_id, text):
        if not isinstance(message_id,str) or not 1<=len(message_id)<=120: return
        if message_id not in self.seen:
            if len(self.seen)>=self.max_messages: return
            self.seen.add(message_id)
        if message_id in self.rejected: return
        safe=safe_public_note(text,self.secret)
        combined=safe_public_note((self.notes.get(message_id,'')+'\n'+safe).strip(),self.secret) if safe else None
        if combined is None:
            self.notes.pop(message_id,None)
            self.rejected.add(message_id)
        else: self.notes[message_id]=combined

    def for_tool(self,message_id):
        return self.notes.pop(message_id,'')
