"""Thin, bounded Messages transport. No warehouse rows, tools, retries or host keys."""
import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import os
import re
from typing import Literal, Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .auth import PublicError

APPROVED_HOST = 'ada-cli-golang.ctripcorp.com'
MAX_RESPONSE = 64 * 1024

class ModelServiceStatus(BaseModel):
    state: Literal['unconfigured', 'credential_missing', 'configuration_missing', 'budget_unverified', 'ready_for_test']
    credential_configured: bool
    protocol: str | None = None
    model_id: str | None = None
    authentication: str | None = None
    config_version: str
    budget_limit_usd: Literal[15] = 15
    cost_status: Literal['unknown'] = 'unknown'
    budget_mode: str = 'unconfigured'
    test_available: bool = False
    generation_verified: bool = False
    stream_verified: bool = False
    models: list[str] = Field(default_factory=list)
    next_action: str

class ModelResponseDiagnostics(BaseModel):
    # Only fixed categories/counts, never copy arbitrary upstream strings or response text.
    reason: Literal['invalid_json','envelope_mismatch','model_mismatch','incomplete_output',
                    'content_shape','unsupported_content','empty_or_oversized_text','usage_invalid',
                    'output_budget_exceeded','secret_echo','unsupported_encoding','unknown']
    model_matches: bool | None = None
    model_binding: Literal['exact','observed_gateway_alias','unmatched'] = 'unmatched'
    returned_model: Literal['deepseek-v4.1-flash','claude-deepseek-v4.1-flash','deepseek-v4.1-flash-thinking','other_or_unreported'] = 'other_or_unreported'
    returned_model_identifier: str | None = Field(default=None,max_length=120)
    identifier_status: Literal['safe_identifier','withheld_or_missing'] = 'withheld_or_missing'
    stop_reason: Literal['end_turn','stop_sequence','max_tokens','tool_use','other','missing'] = 'missing'
    content_types: list[Literal['text','thinking','redacted_thinking','tool_use','other']] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None

class ModelGeneration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str
    model_id: str
    config_version: str
    returned_model_id: str | None = None
    model_binding: Literal['exact','observed_gateway_alias'] = 'exact'
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_status: Literal['unknown'] = 'unknown'
    sql_executed: Literal[False] = False

@dataclass(frozen=True)
class ModelConfiguration:
    endpoint: str = ''
    model_id: str = ''
    protocol: str = ''
    authentication: str = 'protocol_default'
    access_policy: str = 'governed_private'

    def valid(self):
        if self.access_policy=='public_https':
            from .model_egress import public_endpoint_valid
            return (self.authentication in ('protocol_default','bearer','x_api_key')
                and not (self.protocol in ('openai_responses','openai_chat_completions') and self.authentication=='x_api_key')
                and isinstance(self.model_id,str) and bool(re.fullmatch(r'[A-Za-z0-9_.:/\[\]-]{1,120}',self.model_id))
                and public_endpoint_valid(self.endpoint,self.protocol))
        if self.access_policy!='governed_private':return False
        try:
            url = urlsplit(self.endpoint)
            return (url.scheme == 'http' and url.hostname == APPROVED_HOST and url.port in (None, 80)
                    and not url.username and not url.password and not url.query and not url.fragment
                    and self.authentication in ('protocol_default','bearer','x_api_key')
                    and not (self.protocol == 'openai_responses' and self.authentication == 'x_api_key')
                    and (bool(re.fullmatch(r'/coding-plan/[A-Za-z0-9_/-]{1,100}', url.path))
                         or (url.path == '/v1/messages' and self.protocol == 'anthropic_messages'
                             and self.authentication in ('protocol_default','x_api_key')))
                    and '..' not in url.path and '//' not in url.path
                    and ((self.protocol == 'anthropic_messages' and url.path.endswith('/messages'))
                         or (self.protocol == 'openai_responses' and url.path.endswith('/responses')))
                    and bool(re.fullmatch(r'[A-Za-z0-9_.:\[\]-]{1,120}', self.model_id)))
        except ValueError:
            return False

    @property
    def observed_response_alias(self):
        # Provenance: user-authorized read-only receipt d94d4bec-d45d-4519-a3c5-530f6ab5a686.
        # This is one explicit gateway mapping, not fuzzy family/prefix/date matching.
        if (self.access_policy == 'governed_private' and self.endpoint == 'http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages'
            and self.protocol == 'anthropic_messages' and self.authentication == 'bearer'
            and self.model_id == 'deepseek-v4.1-flash'):
            return 'deepseek-v4-1-flash-261017'
        return None

    @property
    def version(self):
        return hashlib.sha256(json.dumps([self.endpoint, self.model_id, self.protocol, self.authentication, self.access_policy, self.observed_response_alias]).encode()).hexdigest()[:16]

class BudgetPermit(Protocol):
    # Internal governance only, not browser fields. No production permit exists in this slice.
    async def reserve(self, *, request_bytes: int, max_output_tokens: int) -> None: ...

class ModelProvider(Protocol):
    async def generate(self, question: str) -> ModelGeneration: ...
    def stream(self, question: str): ...

@dataclass(repr=False)
class MessagesProvider:
    configuration: ModelConfiguration
    key: str = field(repr=False)
    budget: BudgetPermit | None = field(default=None, repr=False)
    transport: httpx.AsyncBaseTransport | None = field(default=None, repr=False)
    _busy: bool = field(default=False, init=False, repr=False)
    _verified: bool = field(default=False, init=False, repr=False)
    _stream_verified: bool = field(default=False, init=False, repr=False)

    def __repr__(self):
        return f'{type(self).__name__}(version={self.configuration.version!r})'

    @classmethod
    def from_env(cls):
        # Never consult ANTHROPIC/OPENAI/Claude/Codex namespaces. Consume project key only.
        key = os.environ.pop('WORKSPACE_MODEL_KEY', '')
        config = ModelConfiguration(os.getenv('WORKSPACE_MODEL_ENDPOINT', ''),
                    os.getenv('WORKSPACE_MODEL_ID', ''), os.getenv('WORKSPACE_MODEL_PROTOCOL', ''),
                    os.getenv('WORKSPACE_MODEL_AUTH_MODE','protocol_default'))
        budget = None
        if key and os.getenv('WORKSPACE_MODEL_ESTIMATED_BUDGET') == '1':
            from .model_budget import EstimatedBudget
            root = __import__('pathlib').Path(__file__).resolve().parents[4]/'data/model-runtime'
            budget = EstimatedBudget(root)
        if config.protocol == 'openai_responses':
            from .responses_provider import ResponsesProvider
            return ResponsesProvider(config, key, budget)
        return cls(config, key, budget)

    def _valid_configuration(self):
        # Even accidental insertion of a credential into nonsecret fields must not reflect it.
        fields = (self.configuration.endpoint, self.configuration.model_id, self.configuration.protocol, self.configuration.authentication)
        return (all(isinstance(value, str) for value in fields)
                and not (self.key and any(self.key in value for value in fields))
                and self.configuration.protocol == self.supported_protocol
                and self.configuration.valid())

    def status(self):
        configured = bool(self.key)
        valid = self._valid_configuration()
        state = ('unconfigured' if not configured and not self.configuration.endpoint else
                 'credential_missing' if not configured else 'configuration_missing' if not valid else
                 'budget_unverified' if self.budget is None else 'ready_for_test')
        actions = {
            'unconfigured': '在模型服务中填写专用Key并保存；不在聊天提供密钥，保存不会调用模型。',
            'credential_missing': '请在模型服务中输入自己的专用Key并保存，再显式测试。',
            'configuration_missing': 'Key已在后端内存；需补精确路径、受支持协议及授权model，尚未请求网关。',
            'budget_unverified': '估算预算尚未加载，请更新本机服务后重试；未发起收费请求。',
            'ready_for_test': '可点击最小模型测试；每次估算预留0.25美元，费用不是硬保证，不执行SQL。',
        }
        return ModelServiceStatus(state=state, credential_configured=configured,
            protocol=self.configuration.protocol if valid else None,
            model_id=self.configuration.model_id if valid else None,
            authentication=self.authentication_mode if valid else None,
            config_version=self.configuration.version, next_action=actions[state],
            budget_mode='estimated_soft_budget' if self.budget is not None and hasattr(self.budget,'summary') else 'unconfigured',
            test_available=bool(configured and valid and self.budget is not None))

    supported_protocol = 'anthropic_messages'

    def network_transport(self):
        if self.transport is not None:return self.transport  # explicit isolated test injection only
        if self.configuration.access_policy=='public_https':
            from .model_egress import PublicModelTransport
            return PublicModelTransport(self.configuration.endpoint)
        return None

    def request_body(self, question):
        return json.dumps({'model': self.configuration.model_id, 'max_tokens': 128,
            'messages': [{'role': 'user', 'content': question}]}, ensure_ascii=False).encode()

    @property
    def authentication_mode(self):
        if self.configuration.authentication == 'protocol_default':
            return 'bearer' if self.supported_protocol in ('openai_responses','openai_chat_completions') else 'x_api_key'
        return self.configuration.authentication

    def request_headers(self):
        headers = {'anthropic-version': '2023-06-01',
                   'Content-Type': 'application/json', 'Accept-Encoding': 'identity'}
        if self.authentication_mode == 'bearer':headers['Authorization']='Bearer '+self.key
        else:headers['x-api-key']=self.key
        return headers

    def parse_response(self, raw):
        diagnostic=ModelResponseDiagnostics(reason='unknown')
        def reject(reason):
            diagnostic.reason=reason
            error=PublicError(502,'MODEL_RESPONSE_INVALID','模型响应未通过校验，请查看不含正文的诊断分类；未自动重试。')
            error.response_diagnostics=diagnostic
            raise error
        try:
            data=json.loads(raw)
        except (ValueError,TypeError,UnicodeError):
            reject('invalid_json')
        if not isinstance(data,dict):reject('envelope_mismatch')
        diagnostic.model_matches=isinstance(data.get('model'),str) and data['model']==self.configuration.model_id
        # Report only already-known public identifiers, never arbitrary upstream strings.
        if data.get('model') in ('deepseek-v4.1-flash','claude-deepseek-v4.1-flash','deepseek-v4.1-flash-thinking') and self.key not in data['model']:
            diagnostic.returned_model=data['model']
        returned=data.get('model')
        # This is diagnostic metadata, not a permitted mapping or a runnable model choice.
        # Restrict format/family and suppress secret-looking values before reflecting it.
        if (isinstance(returned,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/\[\]-]{0,119}',returned)
            and re.search(r'deepseek|claude|gpt-|glm-|gemini|qwen|kimi',returned,re.IGNORECASE)
            and not re.search(r'(?:^|[/.:_-])(?:sk|ada|token|secret|bearer|apikey)(?:[/.:_-]|$)',returned,re.IGNORECASE)
            and self.key and self.key not in returned):
            diagnostic.returned_model_identifier=returned
            diagnostic.identifier_status='safe_identifier'
        stop=data.get('stop_reason')
        diagnostic.stop_reason=stop if stop in ('end_turn','stop_sequence','max_tokens','tool_use') else 'missing' if stop is None else 'other'
        content=data.get('content')
        if isinstance(content,list):
            diagnostic.content_types=[c.get('type') if isinstance(c,dict) and c.get('type') in ('text','thinking','redacted_thinking','tool_use') else 'other' for c in content[:16]]
        usage=data.get('usage',{})
        if isinstance(usage,dict):
            for name in ('input_tokens','output_tokens'):
                v=usage.get(name)
                if type(v) is int and 0<=v<=1000000:setattr(diagnostic,name,v)
        if data.get('type')!='message' or data.get('role')!='assistant':reject('envelope_mismatch')
        if not diagnostic.model_matches and data.get('model') != self.configuration.observed_response_alias:
            reject('model_mismatch')
        if not isinstance(data.get('model'),str):reject('model_mismatch')
        diagnostic.model_binding='exact' if diagnostic.model_matches else 'observed_gateway_alias'
        if stop not in ('end_turn','stop_sequence'):reject('incomplete_output')
        if not isinstance(content,list) or not content or len(content)>16:reject('content_shape')
        texts=[]
        for c in content:
            if not isinstance(c,dict):reject('unsupported_content')
            kind=c.get('type')
            if kind=='text' and isinstance(c.get('text'),str):texts.append(c['text'])
            elif kind in ('thinking','redacted_thinking') and diagnostic.model_binding=='observed_gateway_alias':
                # This gateway's non-text reasoning envelope is opaque metadata, not a signed
                # message we replay or execute. Discard it without interpreting fields. Bound
                # bytes/counts and the exact model binding were checked before this branch.
                continue
            elif kind=='thinking' and isinstance(c.get('thinking'),str) and isinstance(c.get('signature'),str):
                # Validate protocol shape, but never return or persist reasoning/signatures.
                continue
            elif kind=='redacted_thinking' and isinstance(c.get('data'),str):continue
            else:reject('unsupported_content')
        text=''.join(texts)
        if not text.strip() or len(text)>8192:reject('empty_or_oversized_text')
        if not isinstance(usage,dict):reject('usage_invalid')
        counts=[usage.get(k) for k in ('input_tokens','output_tokens')]
        if any(v is not None and (type(v) is not int or not 0<=v<=1000000) for v in counts):reject('usage_invalid')
        if counts[1] is not None and counts[1]>128:reject('output_budget_exceeded')
        if self.key in text:reject('secret_echo')
        return ModelGeneration(text=text,model_id=self.configuration.model_id,
            config_version=self.configuration.version,returned_model_id=data['model'],
            model_binding='exact' if diagnostic.model_matches else 'observed_gateway_alias',
            input_tokens=counts[0],output_tokens=counts[1])

    def stream(self, question: str):
        from .model_stream import messages_stream
        return messages_stream(self,question)

    async def generate(self, question: str):
        if not self.key:
            raise PublicError(409, 'MODEL_CREDENTIAL_MISSING', '请在本机安全输入应用专用Key。')
        if not self._valid_configuration() or not re.fullmatch(r'[\x21-\x7e]{8,4096}', self.key):
            raise PublicError(409, 'MODEL_CONFIGURATION_INVALID', '模型配置无效，请核对专用配置。')
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise PublicError(422, 'MODEL_INPUT_INVALID', '问题需为1至2000字符；本接口不接受行数据或全历史字段。')
        if self.budget is None:
            raise PublicError(409, 'MODEL_BUDGET_UNVERIFIED', '尚无可靠费用控制，未调用模型。')
        if self._busy:
            raise PublicError(429, 'MODEL_BUSY', '模型已有请求进行中，请稍后再试。')
        self._busy = True
        reservation = None
        generation = None
        try:
            body = self.request_body(question)
            # Reserve before network. Cancellation/unknown response never refunds here or retries.
            reservation = await self.budget.reserve(request_bytes=len(body), max_output_tokens=128)
            async with asyncio.timeout(15):
                async with httpx.AsyncClient(transport=self.network_transport(), trust_env=False,
                    follow_redirects=False, timeout=httpx.Timeout(10, connect=3)) as client:
                    async with client.stream('POST', self.configuration.endpoint, content=body,
                        headers=self.request_headers()) as response:
                        if response.status_code in (401,403):
                            error = PublicError(403, 'MODEL_ACCESS_DENIED', '模型认证或权限拒绝，请核对专用配置；不会切换账号。')
                            error.upstream_status = response.status_code
                            raise error
                        if response.status_code == 429:
                            raise PublicError(429, 'MODEL_RATE_LIMITED', '模型限流，未自动重试。')
                        if response.status_code != 200:
                            raise PublicError(502, 'MODEL_SERVICE_FAILED', '模型服务未完成请求，未自动重试。')
                        if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                            error=PublicError(502,'MODEL_RESPONSE_INVALID','模型响应编码不受支持，结果未验证。')
                            error.response_diagnostics=ModelResponseDiagnostics(reason='unsupported_encoding')
                            raise error
                        raw = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            raw.extend(chunk)
                            if len(raw) > MAX_RESPONSE:
                                raise PublicError(502, 'MODEL_RESPONSE_LIMIT', '模型响应超限，结果未验证。')
                        generation = self.parse_response(raw)
                        return generation
        except (httpx.TimeoutException, TimeoutError):
            raise PublicError(504, 'MODEL_RESULT_UNKNOWN', '模型请求超时，费用或结果可能已产生；未自动重试。') from None
        except httpx.HTTPError:
            raise PublicError(502, 'MODEL_TRANSPORT_FAILED', '模型通信失败，未自动重试，请检查连接。') from None
        finally:
            try:
                if reservation is not None and hasattr(self.budget,'finish'):
                    self.budget.finish(reservation,generation)
            finally:
                self._busy = False
