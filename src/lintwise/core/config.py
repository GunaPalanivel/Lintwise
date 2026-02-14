"""Environment-driven configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All env vars are prefixed with ``LINTWISE_`` and can be set via a ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LINTWISE_",
        case_sensitive=False,
    )

    # --- GitHub ---
    github_token: SecretStr
    github_api_base: str = "https://api.github.com"
    github_webhook_secret: SecretStr | None = None

    # --- LLM (OpenAI) ---
    openai_api_key: SecretStr
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.1
    openai_max_tokens: int = 4096

    # --- Agent Pipeline ---
    max_concurrent_agents: int = 4
    max_diff_lines: int = 5000
    review_timeout_seconds: int = 120
    max_files_per_review: int = 50

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False


def get_settings() -> Settings:
    """Factory that creates a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
