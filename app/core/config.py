from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CURRENT_FILE = Path(__file__).resolve()
ENV_FILE = next(
    ((parent / ".env") for parent in CURRENT_FILE.parents if (parent / ".env").exists()),
    CURRENT_FILE.parents[2] / ".env",
)


class Settings(BaseSettings):
    app_name: str = "English Learning API"
    app_env: str = "development"
    backend_cors_origins: str = "*"
    jwt_secret_key: str = "change-me-in-production-minimum-32-characters"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    llm_provider: str = "openai"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 30.0
    llm_base_url: str = "https://api.openai.com/v1"
    stt_provider: str = "openai"
    stt_api_key: str | None = None
    stt_model: str = "gpt-4o-mini-transcribe"
    stt_fallback_model: str = "whisper-1"
    stt_language_hint: str | None = None
    stt_timeout_seconds: float = 30.0
    stt_base_url: str = "https://api.openai.com/v1"
    voice_max_upload_bytes: int = 10 * 1024 * 1024
    postgres_db: str = "english_learning"
    postgres_user: str = "english_user"
    postgres_password: str = "english_password"
    postgres_port: int = 5432
    database_url: str = (
        "postgresql+asyncpg://english_user:english_password@127.0.0.1:5432/english_learning"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return f"postgresql+asyncpg://{value[len('postgres://') :]}"
        if value.startswith("postgresql://"):
            return f"postgresql+asyncpg://{value[len('postgresql://') :]}"
        return value

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if self.backend_cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
