from __future__ import annotations

from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def _package_version(default: str = "0.1.0") -> str:
    try:
        return pkg_version("oauth-tester")
    except PackageNotFoundError:
        return default


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = True
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "info"


class CorsSettings(BaseModel):
    allow_origins: str = "*"  # comma-separated or "*"
    allow_methods: str = "GET"  # comma-separated
    allow_headers: str = "*"  # comma-separated or "*"

    def origins(self) -> List[str]:
        value = self.allow_origins.strip()
        if value in ("", "*"):
            return ["*"]
        return [part.strip() for part in value.split(",") if part.strip()]

    def methods(self) -> List[str]:
        value = self.allow_methods.strip()
        return [part.strip().upper() for part in value.split(",") if part.strip()]

    def headers(self) -> List[str]:
        value = self.allow_headers.strip()
        if value in ("", "*"):
            return ["*"]
        return [part.strip() for part in value.split(",") if part.strip()]


class OAuthSettings(BaseModel):
    # Frontend/base URL and redirect path
    base_url: HttpUrl = HttpUrl("https://localhost:8000")
    redirect_path: str = "/auth/callback"

    # Provider info
    provider_name: str = "threads"
    scopes: str = "threads_basic"
    oidc_discovery_url: Optional[str] = None

    # Manual endpoints if discovery is unavailable
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    jwks_url: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    userinfo_fields: Optional[str] = None  # e.g., "id,name"

    # OAuth client
    client_id: str = ""
    client_secret: Optional[str] = None
    use_pkce: bool = False  # Threads docs do not require PKCE
    compute_appsecret_proof: bool = False  # Only for providers that require it

    # Sessions/crypto
    secret_key: str = "dev-secret-change-me"
    session_cookie_name: str = "oauth_tester_session"

    # Local TLS certs (required by provider Thread)
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


class LoggingSettings(BaseModel):
    as_json: bool = False


class Settings(BaseSettings):
    """Application settings loaded from environment (and .env)."""

    # App metadata
    app_name: str = "OAuth Tester"
    app_version: str = Field(default_factory=_package_version)

    # Groups
    server: ServerSettings = ServerSettings()
    cors: CorsSettings = CorsSettings()
    oauth: OAuthSettings = OAuthSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_prefix="OAUTH_TESTER_",
        env_nested_delimiter="__",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
