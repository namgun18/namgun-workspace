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

    # Stalwart Mail (JMAP)
    stalwart_url: str = "http://stalwart:8080"
    stalwart_admin_user: str = "admin"
    stalwart_admin_password: str = ""

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
    gitea_token: str = ""

    # LiveKit
    livekit_url: str = "http://livekit:7880"

    # Portal OAuth Provider (for Gitea etc.)
    oauth_clients_json: str = "{}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
