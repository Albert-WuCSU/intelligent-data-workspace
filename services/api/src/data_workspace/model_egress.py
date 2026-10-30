"""Public BYOK destination guard with DNS pinning. Private gateways are separate presets."""
import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlsplit
import httpx
from .auth import PublicError

def public_endpoint_valid(endpoint, protocol):
    try:
        u=urlsplit(endpoint)
        if (u.scheme!='https' or not u.hostname or u.port not in (None,443) or u.username or u.password
            or u.query or u.fragment or len(endpoint)>512 or not re.fullmatch(r'[A-Za-z0-9.-]+',u.hostname)
            or '..' in u.path or '//' in u.path or not re.fullmatch(r'/[A-Za-z0-9_/-]+',u.path)):
            return False
        suffix={'anthropic_messages':'/messages','openai_responses':'/responses','openai_chat_completions':'/chat/completions'}.get(protocol)
        if not suffix or not u.path.endswith(suffix):return False
        host=u.hostname.lower()
        if host=='localhost' or host.endswith(('.localhost','.local','.internal')) or '.' not in host:return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:return True
    except (ValueError,TypeError):return False

def resolve_public(host):
    try:
        addresses={row[4][0] for row in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):raise ValueError()
        return sorted(addresses)[0]
    except (OSError,ValueError):
        raise PublicError(403,'MODEL_DESTINATION_DENIED','地址未解析为允许的公网IP，请检查域名；未发送Key或调用模型。') from None

class PublicModelTransport(httpx.AsyncBaseTransport):
    def __init__(self,endpoint,resolver=None,transport=None):
        self.endpoint=httpx.URL(endpoint)
        self.resolver=resolver or resolve_public
        self.inner=transport or httpx.AsyncHTTPTransport(retries=0)
    async def handle_async_request(self,request):
        if request.url!=self.endpoint or request.method!='POST':
            raise PublicError(403,'MODEL_DESTINATION_DENIED','模型请求目标不匹配，未发送凭证。')
        # DNS is resolved once per request and the actual TCP URL uses that validated IP.
        ip=await asyncio.wait_for(asyncio.to_thread(self.resolver,self.endpoint.host),3)
        if not ipaddress.ip_address(ip).is_global:
            raise PublicError(403,'MODEL_DESTINATION_DENIED','禁止访问非公网模型地址。')
        url=self.endpoint.copy_with(host=ip)
        headers=httpx.Headers(request.headers);headers['Host']=self.endpoint.host
        extensions={**request.extensions,'sni_hostname':self.endpoint.host}
        forwarded=httpx.Request(request.method,url,headers=headers,content=request.content,extensions=extensions)
        return await self.inner.handle_async_request(forwarded)
    async def aclose(self):await self.inner.aclose()
