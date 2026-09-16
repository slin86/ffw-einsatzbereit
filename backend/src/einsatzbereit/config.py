from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "change-me-in-production-please-32b"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EB_", env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://einsatzbereit:einsatzbereit@localhost:5432/einsatzbereit"
    )

    jwt_secret: str = Field(default=DEV_JWT_SECRET, min_length=32)
    jwt_issuer: str = "einsatzbereit"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    mfa_token_minutes: int = 5

    cookie_secure: bool = True

    public_base_url: str = "https://einsatzbereit.slin.io"

    max_failed_logins: int = 5
    lockout_minutes: int = 15
    password_reset_minutes: int = 60
    reset_cooldown_minutes: int = 5

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "einsatzbereit@slin.io"

    initial_admin_email: str = ""
    initial_admin_password: str = ""
    seed_demo_data: bool = False

    static_dir: str = "static"

    totp_issuer: str = "Einsatzbereit"

    def check_production_safety(self) -> None:
        """
        Stops the application when secure cookies are enabled but the JWT secret is still the
        development default. Secure cookies indicate a production deployment.
        """
        if self.cookie_secure and self.jwt_secret == DEV_JWT_SECRET:
            raise RuntimeError("EB_JWT_SECRET must be set in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
