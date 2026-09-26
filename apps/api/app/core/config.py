import ipaddress
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1] if len(API_ROOT.parents) > 1 else API_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ml_service_url: str = "http://127.0.0.1:8001"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://dubsibhai:local-dev-only@localhost:5432/dubsibhai"
    redis_url: str = "redis://localhost:6379/0"
    auth_secret: str = "development-only-change-before-deployment"
    cookie_secure: bool = False
    session_idle_seconds: int = 1800
    session_absolute_seconds: int = 86400
    csrf_seconds: int = 3600
    google_client_id: str = ""
    trusted_proxy_cidrs: list[str] = []
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    mail_from: str = "noreply@dubsibhai.local"

    @property
    def session_cookie(self) -> str:
        return "__Host-session" if self.cookie_secure else "session"

    @property
    def csrf_cookie(self) -> str:
        return "__Host-csrf" if self.cookie_secure else "csrf"

    @model_validator(mode="after")
    def validate_security(self):
        if min(self.session_idle_seconds, self.session_absolute_seconds, self.csrf_seconds) <= 0:
            raise ValueError("Auth expiry settings must be positive")
        if self.environment == "production":
            if (
                not self.cookie_secure
                or len(self.auth_secret) < 32
                or self.auth_secret.startswith("development")
            ):
                raise ValueError("Production requires secure cookies and a random AUTH_SECRET")
            if any(not origin.startswith("https://") for origin in self.api_cors_origins):
                raise ValueError("Production requires explicit HTTPS frontend origins")
            if "local-dev-only" in self.database_url or self.smtp_host == "localhost":
                raise ValueError("Production requires a configured database and mail server")
        for cidr in self.trusted_proxy_cidrs:
            ipaddress.ip_network(cidr)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
