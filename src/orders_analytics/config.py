"""Configuration settings for the Orders Analytics application."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the API and SQL execution layers."""

    DATABASE_URL: str = "sqlite:///./data/database/orders.db"
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 30

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
