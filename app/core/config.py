from functools import lru_cache
from typing import Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr
    database_url: str
    admin_telegram_id: int | None = None
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    background_removal_timeout_seconds: float = 30.0
    background_removal_max_file_mb: int = 20
    background_removal_max_pixels: int = 25_000_000
    background_removal_max_concurrency: int = 1

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("BOT_TOKEN must be set")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must be set")
        return value

    @field_validator("admin_telegram_id", mode="before")
    @classmethod
    def empty_admin_id_is_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @field_validator("background_removal_timeout_seconds")
    @classmethod
    def validate_background_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("BACKGROUND_REMOVAL_TIMEOUT_SECONDS must be positive")
        return value

    @field_validator("background_removal_max_pixels")
    @classmethod
    def validate_background_pixels(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("BACKGROUND_REMOVAL_MAX_PIXELS must be positive")
        return value

    @field_validator("background_removal_max_file_mb")
    @classmethod
    def validate_background_file_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("BACKGROUND_REMOVAL_MAX_FILE_MB must be positive")
        return value

    @field_validator("background_removal_max_concurrency")
    @classmethod
    def validate_background_concurrency(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("BACKGROUND_REMOVAL_MAX_CONCURRENCY must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
