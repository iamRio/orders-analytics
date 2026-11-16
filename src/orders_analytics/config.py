"""Configuration settings for the Orders Analytics application."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the API and SQL execution layers."""

    DATABASE_URL: str = "sqlite:///./data/database/orders.db"
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 30
    SQLITE_QUERY_TIMEOUT_SECONDS: float = Field(default=5.0, gt=0)
    SQLITE_MAX_RESULT_ROWS: int = Field(default=1000, ge=1)

    @property
    def database_url(self) -> str:
        """Return the configured SQLite database URL as a lower-case property."""
        return self.DATABASE_URL

    @database_url.setter
    def database_url(self, value: str) -> None:
        self.DATABASE_URL = value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
