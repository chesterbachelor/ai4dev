"""Centralised application configuration loaded from environment / .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (two levels up from this file)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """All runtime configuration, loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_api_key: str = Field(alias="PROJECT_API_KEY")
    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    verify_url: str = Field(alias="VERIFY_URL")
    first_task_url: str = Field(alias="FIRST_TASK_URL")

    # Tunable defaults
    current_year: int = 2026
    min_age: int = 20
    max_age: int = 40
    target_city: str = "Grudziądz"
    target_gender: str = "M"
    llm_model: str = "openai/gpt-4o-mini"
    max_workers: int = 5
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    @property
    def data_url(self) -> str:
        """Fully-resolved URL to fetch the CSV data."""
        return self.first_task_url.format(PROJECT_API_KEY=self.project_api_key)

