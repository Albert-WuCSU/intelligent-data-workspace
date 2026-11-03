"""Bounded Messages SSE adapter. No raw upstream objects, reasoning or tools escape."""
import asyncio,json,re
import httpx
from pydantic import BaseModel,ConfigDict
from typing import Literal
from .auth import PublicError
from .model_provider import MAX_RESPONSE,ModelGeneration

class ProviderStreamEvent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['text_delta','completed']
    text: str = ''
    generation: ModelGeneration | None = None

class StreamDiagnostics(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reason: Literal['sequence','sse_frame','model_mismatch','message_envelope','unsupported_content',
                    'incomplete_output','usage_invalid','secret_echo','resource_limit',
                    'invalid_encoding','transport','timeout','upstream_refused','cancelled','unknown']
    upstream_status: Literal[401,403,429] | None = None


def invalid(reason='sequence'):
    error=PublicError(502,'MODEL_STREAM_INVALID','流式事件不完整或未通过安全校验；不自动重试。')
    error.stream_diagnostics=StreamDiagnostics(reason=reason)
    return error

async def sse_frames(response):
    buf=bytearray();total=0;count=0
    async for chunk in response.aiter_raw():
        total+=len(chunk)
        if total>MAX_RESPONSE:raise PublicError(502,'MODEL_RESPONSE_LIMIT','流式响应超限，结果未验证。')
        buf.extend(chunk)
        if len(buf)>16384:raise invalid('resource_limit')
        while True:
            raw=bytes(buf).replace(b'\r\n',b'\n')
            end=raw.find(b'\n\n')
            if end<0:break
            frame=raw[:end];buf=bytearray(raw[end+2:]);count+=1
            if count>256:raise invalid('resource_limit')
            data=[];event=None
            try:
                for line in frame.decode('utf-8').split('\n'):
                    if not line or line.startswith(':'):continue
                    field,_,value=line.partition(':');value=value.lstrip(' ')
                    if field=='data':data.append(value)
                    elif field=='event':event=value
                    elif field not in ('id','retry'):raise ValueError()
                if not data:continue
                value=json.loads('\n'.join(data))
                if not isinstance(value,dict) or event is not None and event!=value.get('type'):raise ValueError()
            except (ValueError,UnicodeError):raise invalid('sse_frame') from None
            yield value
    if bytes(buf).strip():raise invalid('sse_frame')

class MessageState:
    def __init__(self,provider):
        self.p=provider;self.message=None;self.blocks=[];self.open=None;self.stopped=False;self.delta_done=False;self.text='';self.emitted=0
    def feed(self,d):
        typ=d.get('type')
        if self.stopped:raise invalid()
        if typ=='ping':return None
        if typ=='message_start':
            m=d.get('message')
            if self.message is not None or not isinstance(m,dict):raise invalid()
            if not isinstance(m.get('model'),str) or m['model'] not in (self.p.configuration.model_id,self.p.configuration.observed_response_alias):raise invalid('model_mismatch')
            if (m.get('type')!='message' or m.get('role')!='assistant'
                or not isinstance(m.get('model'),str)
                or m['model'] not in (self.p.configuration.model_id,self.p.configuration.observed_response_alias)
                or m.get('content')!=[] or m.get('stop_reason') is not None):raise invalid('message_envelope')
            usage=m.get('usage')
            if not isinstance(usage,dict) or type(usage.get('input_tokens')) is not int or not 0<=usage['input_tokens']<=1000000:raise invalid('usage_invalid')
            self.message={'type':'message','role':'assistant','model':m['model'],'usage':{'input_tokens':usage['input_tokens']},'content':[]}
        elif self.message is None:raise invalid()
        elif typ=='content_block_start':
            block=d.get('content_block')
            if self.open is not None or self.delta_done or type(d.get('index')) is not int or d['index']!=len(self.blocks) or len(self.blocks)>=16:raise invalid()
            if not isinstance(block,dict) or block.get('type') not in ('text','thinking','redacted_thinking'):raise invalid('unsupported_content')
            kind=block['type']
            if kind=='text':
                if not isinstance(block.get('text'),str):raise invalid()
                self.text+=block['text'];self.blocks.append({'type':'text','text':block['text']})
            else:
                # Opaque upstream reasoning is discarded, never accumulated or replayed.
                self.blocks.append({'type':'thinking','thinking':'','signature':''})
            self.open=len(self.blocks)-1
        elif typ=='content_block_delta':
            if self.open is None or type(d.get('index')) is not int or d['index']!=self.open:raise invalid()
            delta=d.get('delta');block=self.blocks[self.open]
            if not isinstance(delta,dict):raise invalid()
            if block['type']=='text':
                if delta.get('type')!='text_delta' or not isinstance(delta.get('text'),str):raise invalid()
                self.text+=delta['text'];block['text']+=delta['text']
            elif delta.get('type') not in ('thinking_delta','signature_delta'):raise invalid()
        elif typ=='content_block_stop':
            if self.open is None or type(d.get('index')) is not int or d['index']!=self.open:raise invalid()
            self.open=None
        elif typ=='message_delta':
            if self.open is not None or self.delta_done:raise invalid()
            delta=d.get('delta');usage=d.get('usage')
            if not isinstance(delta,dict) or delta.get('stop_reason') not in ('end_turn','stop_sequence'):raise invalid('incomplete_output')
            if not isinstance(usage,dict) or type(usage.get('output_tokens')) is not int or not 0<=usage['output_tokens']<=128:raise invalid('usage_invalid')
            self.message['stop_reason']=delta['stop_reason'];self.message['usage']['output_tokens']=usage['output_tokens'];self.delta_done=True
        elif typ=='message_stop':
            if not self.delta_done or self.open is not None:raise invalid()
            self.stopped=True;self.message['content']=self.blocks
            return self.p.parse_response(json.dumps(self.message).encode())
        else:raise invalid()
        if len(self.text)>8192:raise invalid('resource_limit')
        if self.p.key in self.text:raise invalid('secret_echo')
        return None
    def release(self,final=False):
        # Hold a Key-sized suffix so a credential split over future chunks cannot escape.
        safe=len(self.text) if final else max(0,len(self.text)-len(self.p.key)+1)
        value=self.text[self.emitted:safe];self.emitted=safe
        return value

async def messages_stream(provider,question):
    if provider.supported_protocol!='anthropic_messages':raise PublicError(409,'MODEL_STREAM_UNSUPPORTED','当前协议尚未实现流式测试，不自动换协议。')
    if not provider.key or not re.fullmatch(r'[\x21-\x7e]{8,4096}',provider.key) or not provider._valid_configuration():raise PublicError(409,'MODEL_CREDENTIAL_MISSING','请配置合法专用模型连接。')
    if provider.budget is None:raise PublicError(409,'MODEL_BUDGET_UNVERIFIED','未加载模型预算。')
    if provider._busy:raise PublicError(429,'MODEL_BUSY','已有请求进行中。')
    if not isinstance(question,str) or not question.strip() or len(question)>2000:raise PublicError(422,'MODEL_INPUT_INVALID','流式输入无效。')
    provider._busy=True;reservation=None;generation=None
    try:
        body=json.loads(provider.request_body(question));body['stream']=True;body=json.dumps(body).encode()
        reservation=await provider.budget.reserve(request_bytes=len(body),max_output_tokens=128)
        async with asyncio.timeout(15):
            async with httpx.AsyncClient(transport=provider.network_transport(),trust_env=False,follow_redirects=False,timeout=httpx.Timeout(10,connect=3)) as client:
                async with client.stream('POST',provider.configuration.endpoint,content=body,headers={**provider.request_headers(),'Accept':'text/event-stream'}) as response:
                    if response.status_code in (401,403):
                        error=PublicError(403,'MODEL_ACCESS_DENIED','模型认证或权限拒绝，不切换账号。')
                        error.stream_diagnostics=StreamDiagnostics(reason='upstream_refused',upstream_status=response.status_code)
                        raise error
                    if response.status_code==429:
                        error=PublicError(429,'MODEL_RATE_LIMITED','模型限流，不自动重试。')
                        error.stream_diagnostics=StreamDiagnostics(reason='upstream_refused',upstream_status=429)
                        raise error
                    if response.status_code!=200:raise PublicError(502,'MODEL_SERVICE_FAILED','模型服务未完成流式请求。')
                    if response.headers.get('content-type','').split(';')[0].strip()!='text/event-stream' or response.headers.get('content-encoding','identity').lower()!='identity':raise invalid('invalid_encoding')
                    state=MessageState(provider);candidate=None
                    async for data in sse_frames(response):
                        complete=state.feed(data)
                        if complete is not None:candidate=complete
                        else:
                            text=state.release()
                            if text:yield ProviderStreamEvent(kind='text_delta',text=text)
                    if candidate is None or not state.stopped:raise invalid('incomplete_output')
                    # Only successful bounded EOF can flush the secret-holdback suffix.
                    text=state.release(final=True)
                    if text:yield ProviderStreamEvent(kind='text_delta',text=text)
                    generation=candidate
                    yield ProviderStreamEvent(kind='completed',generation=generation)
    except (httpx.TimeoutException,TimeoutError):raise PublicError(504,'MODEL_RESULT_UNKNOWN','流式请求超时，预留保留，不自动重试。') from None
    except httpx.HTTPError:raise PublicError(502,'MODEL_TRANSPORT_FAILED','流式通信中断，预留保留。') from None
    finally:
        try:
            if reservation is not None and hasattr(provider.budget,'finish'):provider.budget.finish(reservation,generation)
        finally:provider._busy=False
