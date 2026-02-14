"""Dependency injection — shared services and configuration."""

from __future__ import annotations

import functools
from typing import AsyncIterator

from lintwise.core.config import Settings, get_settings
from lintwise.github.client import GitHubClient
from lintwise.llm.base import LLMProvider
from lintwise.llm.openai_provider import OpenAIProvider


@functools.lru_cache
def get_app_settings() -> Settings:
    """Cached application settings (singleton)."""
    return get_settings()


def create_github_client(settings: Settings | None = None) -> GitHubClient:
    """Create a GitHub API client from settings."""
    s = settings or get_app_settings()
    return GitHubClient(
        token=s.github_token.get_secret_value(),
    )


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Create an LLM provider from settings."""
    s = settings or get_app_settings()
    return OpenAIProvider(s)
