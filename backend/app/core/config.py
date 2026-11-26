from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CommandOS"
    environment: str = "development"
    owner_email: str = Field(alias="COMMANDOS_OWNER_EMAIL")
    owner_password_hash: SecretStr = Field(alias="COMMANDOS_OWNER_PASSWORD_HASH")
    session_secret: SecretStr = Field(alias="COMMANDOS_SESSION_SECRET")
    token_encryption_key: SecretStr = Field(alias="COMMANDOS_TOKEN_ENCRYPTION_KEY")
    database_url: str = Field(default="sqlite:///./commandos.db", alias="COMMANDOS_DATABASE_URL")
    auto_create_schema: bool = Field(default=False, alias="COMMANDOS_AUTO_CREATE_SCHEMA")
    frontend_origin: str = Field(default="http://localhost:5173", alias="COMMANDOS_FRONTEND_ORIGIN")
    secure_cookies: bool = Field(default=False, alias="COMMANDOS_SECURE_COOKIES")

    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_client_secret: SecretStr = Field(alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(alias="GOOGLE_REDIRECT_URI")

    session_ttl_seconds: int = 8 * 60 * 60
    oauth_state_ttl_seconds: int = 10 * 60
    youtube_initial_history_days: int = 90
    youtube_max_videos: int = 200
    scheduled_sync_enabled: bool = Field(default=False, alias="COMMANDOS_SCHEDULED_SYNC_ENABLED")
    youtube_sync_interval_hours: int = Field(
        default=24, alias="COMMANDOS_YOUTUBE_SYNC_INTERVAL_HOURS"
    )
    youtube_scheduler_poll_seconds: int = Field(
        default=60, alias="COMMANDOS_YOUTUBE_SCHEDULER_POLL_SECONDS"
    )

    @field_validator("owner_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("COMMANDOS_SESSION_SECRET must contain at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
