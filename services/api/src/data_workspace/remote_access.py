"""Product-owned endpoint grants and credential references. No host config scan."""
import ipaddress
import os
import re
from typing import Literal
from pydantic import Field, model_validator, SecretStr
from .contracts import Contract
from .auth import PublicError
from .warehouse.http_boundary import checked_endpoint

REF_PATTERN = r"^[A-Z][A-Z0-9_]{0,47}$"
SECRET_PREFIX = "WORKSPACE_CONNECTOR_SECRET_"

class HTTPMCPDraft(Contract):
    kind: Literal['http_mcp']
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(max_length=500)
    adapter: Literal['workspace_navigation_v1'] = 'workspace_navigation_v1'
    auth_mode: Literal['none', 'bearer'] = 'bearer'
    secret_ref: str | None = Field(default=None, pattern=REF_PATTERN)
    usage_authorized: Literal[True]

    @model_validator(mode='after')
    def check(self):
        checked_endpoint(self.url)
        if (self.auth_mode == 'bearer') != (self.secret_ref is not None):
            raise ValueError('Authentication and reference do not match')
        return self

class PostgresDraft(Contract):
    kind: Literal['postgresql']
    name: str = Field(min_length=1, max_length=80)
    host: str = Field(max_length=50)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=100)
    sslmode: Literal['verify-full', 'disable'] = 'verify-full'
    secret_ref: str = Field(pattern=REF_PATTERN)
    usage_authorized: Literal[True]

    @model_validator(mode='after')
    def check(self):
        address = ipaddress.ip_address(self.host)
        if str(address) != self.host or address.is_link_local or address.is_multicast or address.is_unspecified or (address.is_reserved and not address.is_loopback) or getattr(address, 'ipv4_mapped', None):
            raise ValueError('Invalid database address')
        if self.sslmode == 'disable' and not address.is_loopback:
            raise ValueError('TLS is required outside loopback')
        if any(ord(c) < 32 for c in self.database + self.username):
            raise ValueError('Invalid database identity')
        return self

class HTTPGrant(Contract):
    url: str
    secret_ref: str | None = Field(default=None, pattern=REF_PATTERN)
    table_ids: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def check(self):
        checked_endpoint(self.url)
        if len(set(self.table_ids)) != len(self.table_ids) or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', t) for t in self.table_ids):
            raise ValueError('Invalid resources')
        return self

class PostgresGrant(Contract):
    host: str
    port: int = Field(ge=1, le=65535)
    database: str
    username: str
    secret_ref: str = Field(pattern=REF_PATTERN)
    schemas: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def check(self):
        PostgresDraft(kind='postgresql', name='grant', host=self.host, port=self.port, database=self.database, username=self.username, secret_ref=self.secret_ref, usage_authorized=True)
        if any(not s or len(s) > 100 or any(ord(c)<32 for c in s) for s in self.schemas):
            raise ValueError('Invalid schemas')
        return self

class RemoteAccessPolicy(Contract):
    http_mcp: list[HTTPGrant] = Field(default_factory=list, max_length=20)
    postgresql: list[PostgresGrant] = Field(default_factory=list, max_length=20)

    @classmethod
    def from_env(cls):
        # One explicit PRODUCT configuration key. Never read .codex or enumerate secrets.
        raw = os.environ.get('WORKSPACE_CONNECTOR_POLICY', '{}')
        if len(raw) > 65536:
            raise ValueError('Product connector policy is too large')
        try:
            return cls.model_validate_json(raw)
        except Exception:
            raise ValueError('Invalid product connector policy; no connections enabled') from None

    def authorize(self, draft):
        if isinstance(draft, HTTPMCPDraft):
            grants = [g for g in self.http_mcp if (g.url, g.secret_ref) == (draft.url, draft.secret_ref)]
        else:
            grants = [g for g in self.postgresql if (g.host, g.port, g.database, g.username, g.secret_ref) == (draft.host, draft.port, draft.database, draft.username, draft.secret_ref)]
        if len(grants) != 1:
            raise PublicError(403, 'TARGET_NOT_APPROVED', '此地址、账号或凭证引用尚未获后端管理员授权；请配置专用连接白名单，不会尝试其他地址或账号。')
        return grants[0]

class ProductSecrets:
    def resolve(self, reference):
        if not re.fullmatch(REF_PATTERN, reference):
            raise PublicError(422, 'INVALID_SECRET_REFERENCE', '凭证引用格式无效；不要填写密码、token或环境变量全名。')
        value = os.environ.get(SECRET_PREFIX + reference)
        if not value:
            raise PublicError(409, 'CREDENTIAL_NOT_CONFIGURED', '后端尚未配置该项目专用凭证；请在可信后端配置渠道提供，勿粘贴到网页、JSON或聊天。')
        if len(value) > 4096 or any(ord(c) < 32 for c in value):
            raise PublicError(409, 'CREDENTIAL_INVALID', '项目专用凭证格式不可用，请由接入管理员更新后重新测试。')
        return SecretStr(value)
