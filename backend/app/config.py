from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Workspace"
    app_url: str = "http://localhost"
    debug: bool = False
    secret_key: str = "CHANGE_ME"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://workspace:workspace@postgres:5432/workspace"

    # Domain
    domain: str = "localhost"

    # File storage
    storage_root: str = "/storage"
    upload_max_size_mb: int = 5120

    # Built-in mail server (Stalwart/Postfix+Dovecot) — disabled by default
    feature_builtin_mailserver: bool = False
    stalwart_url: str = "http://stalwart:8080"
    stalwart_admin_user: str = "admin"
    stalwart_admin_password: str = ""

    # Dovecot master user (SSO: backend accesses any mailbox without per-user passwords)
    dovecot_master_user: str = ""
    dovecot_master_password: str = ""

    # SMTP (noreply sender)
    smtp_host: str = "stalwart"
    smtp_port: int = 587
    smtp_user: str = "noreply@localhost"
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"

    # Admin notification
    admin_emails: str = ""

    # Gitea
    gitea_url: str = "http://gitea:3000"
    gitea_external_url: str = ""  # browser-facing URL (empty → APP_URL/git/)
    gitea_token: str = ""
    gitea_webhook_secret: str = ""
    gitea_webhook_channel: str = ""  # empty → "git-notifications"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # LiveKit
    livekit_url: str = "http://livekit:7880"
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_ws_url: str = ""  # 브라우저용 WS URL (빈값이면 app_url에서 자동 파생)

    # Branding
    brand_logo: str = ""       # URL or path to logo image
    brand_color: str = "#3B82F6"  # Primary brand color (hex)

    # Portal OAuth Provider (for Gitea etc.)
    oauth_clients_json: str = "{}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
