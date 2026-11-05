from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    mode: str = "production"
    dev_identity: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    owned_warehouse: bool = False
    retention_cleanup: bool = False
    sdk_web_agent: bool = True
    sdk_web_test_base_url: str | None = None

    def __post_init__(self):
        if self.mode not in {"development", "production"}:
            raise ValueError("invalid mode")
        if self.dev_identity and (self.mode != "development" or self.host not in {"127.0.0.1", "::1"}):
            raise ValueError("development identity requires loopback development mode")
        if self.owned_warehouse and not (self.mode == "development" and self.dev_identity and self.host in {"127.0.0.1", "::1"}):
            raise ValueError("owned warehouse requires loopback development identity")
        if self.retention_cleanup and not (self.mode == 'development' and self.dev_identity and self.host in {'127.0.0.1','::1'}):
            raise ValueError('retention cleanup requires loopback development identity')
        if not 1 <= self.port <= 65535:
            raise ValueError("invalid port")
        if self.sdk_web_test_base_url is not None and not (self.mode == "development" and self.dev_identity):
            raise ValueError("sdk web test gateway requires development identity")

    @classmethod
    def from_env(cls):
        flag = os.getenv("WORKSPACE_DEV_IDENTITY", "0")
        retention = os.getenv('WORKSPACE_RETENTION_CLEANUP','0')
        if retention not in {'0','1'}:raise ValueError('invalid retention flag')
        warehouse = os.getenv("WORKSPACE_OWNED_WAREHOUSE", "0")
        if warehouse not in {"0", "1"}:
            raise ValueError("invalid warehouse flag")
        if flag not in {"0", "1"}:
            raise ValueError("invalid development identity flag")
        return cls(mode=os.getenv("WORKSPACE_MODE", "production"), dev_identity=flag == "1",
                   host=os.getenv("WORKSPACE_HOST", "127.0.0.1"), port=int(os.getenv("WORKSPACE_PORT", "8000")), owned_warehouse=warehouse == "1",retention_cleanup=retention == "1")