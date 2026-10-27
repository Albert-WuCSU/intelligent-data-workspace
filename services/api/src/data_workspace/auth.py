from ipaddress import ip_address
from fastapi import Request
from .contracts import AuthContext

class PublicError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message

class DevelopmentIdentityProvider:
    """Only explicit loopback development. Replace with verified OIDC in a later module."""
    def resolve(self, request: Request) -> AuthContext:
        cfg = request.app.state.settings
        try:
            local = bool(request.client) and ip_address(request.client.host).is_loopback
        except ValueError:
            local = False
        if not (cfg.mode == "development" and cfg.dev_identity and local):
            raise PublicError(401, "AUTH_REQUIRED", "身份认证未配置或会话未授权。")
        return AuthContext(principal_id="local-developer", tenant_id="local-workspace", mode="development")

def identity(request: Request) -> AuthContext:
    return request.app.state.identity_provider.resolve(request)
