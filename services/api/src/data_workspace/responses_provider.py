"""Explicit non-streaming OpenAI Responses candidate, with shared governed transport."""
import json
from .auth import PublicError
from .model_provider import MessagesProvider, ModelGeneration

class ResponsesProvider(MessagesProvider):
    supported_protocol = 'openai_responses'

    def request_body(self, question):
        # No history, rows, tools, previous_response_id, background or remote storage.
        return json.dumps({'model': self.configuration.model_id, 'input': question,
            'max_output_tokens': 128, 'store': False, 'stream': False}, ensure_ascii=False).encode()

    def request_headers(self):
        return {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
                'Accept-Encoding': 'identity'}

    def parse_response(self, raw):
        try:
            data = json.loads(raw)
            if (not isinstance(data, dict) or data.get('object') != 'response'
                or data.get('status') != 'completed' or data.get('model') != self.configuration.model_id
                or data.get('error') is not None or data.get('incomplete_details') is not None):
                raise ValueError()
            output = data['output']
            if not isinstance(output, list) or not output or len(output) > 16:
                raise ValueError()
            text_parts = []
            for item in output:
                if not isinstance(item, dict): raise ValueError()
                if item.get('type') == 'reasoning':
                    # Do not expose reasoning/opaque encrypted data; only text messages are results.
                    continue
                if (item.get('type') != 'message' or item.get('role') != 'assistant'
                    or item.get('status') != 'completed'):
                    raise ValueError()
                content = item['content']
                if not isinstance(content, list) or not content or len(content) > 16: raise ValueError()
                for block in content:
                    if not isinstance(block, dict) or block.get('type') != 'output_text' or not isinstance(block.get('text'), str):
                        raise ValueError()
                    text_parts.append(block['text'])
            text = ''.join(text_parts)
            if not text.strip() or len(text) > 8192 or self.key in text: raise ValueError()
            usage = data.get('usage')
            counts = [None, None]
            if usage is not None:
                if not isinstance(usage, dict): raise ValueError()
                counts = [usage.get(k) for k in ('input_tokens','output_tokens')]
                if any(v is not None and (type(v) is not int or not 0 <= v <= 1000000) for v in counts): raise ValueError()
                if counts[1] is not None and counts[1] > 128: raise ValueError()
            return ModelGeneration(text=text, model_id=self.configuration.model_id,
                config_version=self.configuration.version, input_tokens=counts[0], output_tokens=counts[1])
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise PublicError(502, 'MODEL_RESPONSE_INVALID', 'Responses响应不完整或合同不兼容，结果未验证。') from None
