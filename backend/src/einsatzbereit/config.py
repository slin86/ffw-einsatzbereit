"""Application settings, loaded from environment variables (prefix ``EB_``)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EB_", env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://einsatzbereit:einsatzbereit@localhost:5432/einsatzbereit"
    )

    # JWT
    jwt_secret: str = Field(default="change-me-in-production-please-32b", min_length=32)
    jwt_issuer: str = "einsatzbereit"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    mfa_token_minutes: int = 5

    # Cookies
    cookie_secure: bool = True

    # Public base URL, used in password reset mails
    public_base_url: str = "https://einsatzbereit.slin.io"

    # Login hardening
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    password_reset_minutes: int = 60
    reset_cooldown_minutes: int = 5

    # SMTP (password reset). If smtp_host is empty, mails are logged instead of sent.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "einsatzbereit@slin.io"

    # Bootstrap admin, created on startup if no user exists
    initial_admin_email: str = ""
    initial_admin_password: str = ""

    # Directory with the built SPA (served at /). Empty disables static serving.
    static_dir: str = "static"

    totp_issuer: str = "Einsatzbereit"


@lru_cache
def get_settings() -> Settings:
    return Settings()
