"""Deny-by-default HTTP boundary for the approved MCP connector work.

Not wired to the product profile routes yet. Rules are server-owned; imported
profiles must never manufacture them. This slice is deliberately credential-free
unless a server-resolved product SecretStr is explicitly supplied. Numeric IP endpoints
avoid DNS/proxy rebinding; hostname support needs a separately verified resolver.
"""
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr


class HTTPBoundaryError(ValueError):
    """Only fixed safe messages; never include URLs, headers or server bodies."""


def checked_endpoint(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 500:
        raise HTTPBoundaryError("Invalid MCP endpoint.")
    # No URL credentials, token query strings, encoded paths, whitespace or DNS.
    if any(ord(c) < 33 or ord(c) > 126 for c in value) or "\\" in value or "%" in value:
        raise HTTPBoundaryError("Invalid MCP endpoint.")
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or parts.username is not None or parts.password is not None:
            raise ValueError()
        if "?" in value or "#" in value or not parts.hostname or parts.port is None or not 1 <= parts.port <= 65535:
            raise ValueError()
        address = ipaddress.ip_address(parts.hostname)
        # Metadata/link-local, broadcast, unspecified and multicast are never targets.
        if address.is_link_local or address.is_unspecified or address.is_multicast or (address.is_reserved and not address.is_loopback):
            raise ValueError()
        if address.version == 6 and address.ipv4_mapped is not None:
            raise ValueError()
        if parts.scheme == "http" and not address.is_loopback:
            raise ValueError()
        if not re.fullmatch(r"/[A-Za-z0-9_./-]{1,200}", parts.path):
            raise ValueError()
        if any(segment in {".", "..", ""} for segment in parts.path.split("/")[1:]):
            raise ValueError()
        host = f"[{address}]" if address.version == 6 else str(address)
        canonical = f"{parts.scheme}://{host}:{parts.port}{parts.path}"
        if value != canonical:
            raise ValueError()
        return canonical
    except ValueError:
        raise HTTPBoundaryError("MCP endpoint requires an exact numeric IP, explicit port and safe path; HTTPS outside loopback.") from None


@dataclass(frozen=True)
class HTTPEndpointPolicy:
    # Empty means no network access. This is NOT read from browser JSON.
    approved_endpoints: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.approved_endpoints, tuple):
            raise HTTPBoundaryError("Server endpoint rules must be immutable.")
        for endpoint in self.approved_endpoints:
            checked_endpoint(endpoint)

    def authorize(self, endpoint: str) -> str:
        canonical = checked_endpoint(endpoint)
        if canonical not in self.approved_endpoints:
            raise HTTPBoundaryError("MCP endpoint has not been approved by the server administrator.")
        return canonical


class _BoundedResponse(httpx.AsyncByteStream):
    def __init__(self, wrapped, max_bytes):
        self.wrapped = wrapped
        self.max_bytes = max_bytes

    async def __aiter__(self):
        count = 0
        try:
            async for chunk in self.wrapped:
                count += len(chunk)
                if count > self.max_bytes:
                    raise HTTPBoundaryError("MCP response exceeded the byte budget.")
                yield chunk
        finally:
            await self.wrapped.aclose()

    async def aclose(self):
        await self.wrapped.aclose()


class GovernedHTTPTransport(httpx.AsyncBaseTransport):
    def __init__(self, endpoint, policy, *, transport=None, max_response_bytes=1024 * 1024, credential: SecretStr | None = None):
        self.endpoint = policy.authorize(endpoint)
        if not 1 <= max_response_bytes <= 1024 * 1024:
            raise HTTPBoundaryError("Invalid MCP response budget.")
        self._credential = credential
        self.max_response_bytes = max_response_bytes
        self.policy = policy
        # Explicitly no environment proxies, retry, TLS bypass or custom cert path.
        self.transport = transport or httpx.AsyncHTTPTransport(verify=True, retries=0, trust_env=False, limits=httpx.Limits(max_connections=2, max_keepalive_connections=1))

    async def handle_async_request(self, request):
        self.policy.authorize(self.endpoint)
        if request.url != httpx.URL(self.endpoint) or request.method not in {"GET", "POST", "DELETE"}:
            raise HTTPBoundaryError("MCP request left its approved endpoint or method.")
        if request.headers.get("host") != httpx.URL(self.endpoint).netloc.decode("ascii"):
            raise HTTPBoundaryError("MCP authority override is not permitted.")
        if any(header in request.headers for header in ("authorization", "proxy-authorization", "cookie", "forwarded", "x-forwarded-host", "x-original-url", "x-http-method-override")):
            raise HTTPBoundaryError("Credential handling is not enabled in this transport slice.")
        content = await request.aread()
        if len(content) > 64 * 1024:
            raise HTTPBoundaryError("MCP request exceeded the byte budget.")
        # Disable compression to bound bytes BEFORE parsing. Encoded responses fail closed.
        request.headers["accept-encoding"] = "identity"
        if self._credential is not None:
            request.headers["Authorization"] = "Bearer " + self._credential.get_secret_value()
        response = await self.transport.handle_async_request(request)
        try:
            # MCP1.30 follows same-origin redirects itself, even if httpx's
            # follow_redirects=False. Deny at transport level, including /mcp -> /other.
            if 300 <= response.status_code < 400:
                raise HTTPBoundaryError("MCP redirects are not permitted; review the exact endpoint.")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise HTTPBoundaryError("Encoded MCP responses are not permitted.")
            length = response.headers.get("content-length")
            if length is not None and (not length.isascii() or not length.isdigit() or int(length) > self.max_response_bytes):
                raise HTTPBoundaryError("Invalid or excessive MCP response length.")
            response.stream = _BoundedResponse(response.stream, self.max_response_bytes)
            return response
        except Exception:
            await response.aclose()
            raise

    async def aclose(self):
        await self.transport.aclose()


def create_governed_http_client(endpoint: str, policy: HTTPEndpointPolicy, *, transport=None, credential: SecretStr | None = None):
    boundary = GovernedHTTPTransport(endpoint, policy, transport=transport, credential=credential)
    return httpx.AsyncClient(
        transport=boundary, trust_env=False, follow_redirects=False,
        timeout=httpx.Timeout(5, read=10), headers={"Accept-Encoding": "identity"},
        limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
    )
