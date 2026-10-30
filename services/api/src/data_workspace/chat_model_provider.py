"""Text-only OpenAI-compatible Chat Completions, sharing bounded governed transport."""
import json
from .model_provider import MessagesProvider,ModelGeneration
from .auth import PublicError
class ChatCompletionsProvider(MessagesProvider):
    supported_protocol='openai_chat_completions'
    def request_headers(self):
        return {'Authorization':'Bearer '+self.key,'Content-Type':'application/json','Accept-Encoding':'identity'}
    def request_body(self,question):
        return json.dumps({'model':self.configuration.model_id,'messages':[{'role':'user','content':question}],
                           'max_tokens':128,'stream':False},ensure_ascii=False).encode()
    def parse_response(self,raw):
        try:
            data=json.loads(raw)
            if not isinstance(data,dict) or data.get('model')!=self.configuration.model_id:raise ValueError()
            choices=data['choices']
            if not isinstance(choices,list) or len(choices)!=1:raise ValueError()
            item=choices[0]
            if item.get('finish_reason')!='stop':raise ValueError()
            message=item['message']
            if message.get('role')!='assistant' or message.get('tool_calls') or message.get('function_call'):raise ValueError()
            text=message['content']
            if not isinstance(text,str) or not text.strip() or len(text)>8192 or self.key in text:raise ValueError()
            usage=data.get('usage') or {}
            if not isinstance(usage,dict):raise ValueError()
            counts=[usage.get(k) for k in ('prompt_tokens','completion_tokens')]
            if any(v is not None and (type(v) is not int or not 0<=v<=1000000) for v in counts):raise ValueError()
            if counts[1] is not None and counts[1]>128:raise ValueError()
            return ModelGeneration(text=text,model_id=self.configuration.model_id,returned_model_id=data['model'],
                config_version=self.configuration.version,input_tokens=counts[0],output_tokens=counts[1])
        except (ValueError,KeyError,TypeError,UnicodeError,AttributeError):
            raise PublicError(502,'MODEL_RESPONSE_INVALID','Chat Completions响应不完整或协议/模型不匹配，结果未验证。') from None
