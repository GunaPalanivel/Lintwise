"""Comprehensive tests for lintwise.core.config — Settings and configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from lintwise.core.config import Settings, get_settings


# Minimal valid env vars for Settings
VALID_ENV = {
    "LINTWISE_GITHUB_TOKEN": "ghp_test_token_123",
    "LINTWISE_OPENAI_API_KEY": "sk-test_key_456",
}


class TestSettings:
    """Tests for the Settings Pydantic model."""

    def test_creation_with_required_fields(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
        )
        assert s.github_token.get_secret_value() == "ghp_test"
        assert s.openai_api_key.get_secret_value() == "sk-test"

    def test_defaults(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
        )
        assert s.github_api_base == "https://api.github.com"
        assert s.github_webhook_secret is None
        assert s.openai_model == "gpt-4o"
        assert s.openai_temperature == 0.1
        assert s.openai_max_tokens == 4096
        assert s.max_concurrent_agents == 4
        assert s.max_diff_lines == 5000
        assert s.review_timeout_seconds == 120
        assert s.max_files_per_review == 50
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.log_level == "INFO"
        assert s.debug is False

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "github_token" in field_names
        assert "openai_api_key" in field_names

    def test_secret_str_not_leaked_in_repr(self):
        s = Settings(
            github_token=SecretStr("ghp_super_secret"),
            openai_api_key=SecretStr("sk-super_secret"),
        )
        repr_str = repr(s)
        assert "ghp_super_secret" not in repr_str
        assert "sk-super_secret" not in repr_str
        assert "**********" in repr_str

    def test_secret_str_not_leaked_in_dump(self):
        s = Settings(
            github_token=SecretStr("ghp_super_secret"),
            openai_api_key=SecretStr("sk-super_secret"),
        )
        data = s.model_dump()
        assert data["github_token"] != "ghp_super_secret"
        assert data["openai_api_key"] != "sk-super_secret"

    def test_custom_values(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
            openai_model="gpt-3.5-turbo",
            max_concurrent_agents=8,
            max_diff_lines=10000,
            review_timeout_seconds=300,
            log_level="DEBUG",
            debug=True,
        )
        assert s.openai_model == "gpt-3.5-turbo"
        assert s.max_concurrent_agents == 8
        assert s.max_diff_lines == 10000
        assert s.review_timeout_seconds == 300
        assert s.log_level == "DEBUG"
        assert s.debug is True

    def test_webhook_secret_optional(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
        )
        assert s.github_webhook_secret is None

    def test_webhook_secret_set(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
            github_webhook_secret=SecretStr("whsec_abc123"),
        )
        assert s.github_webhook_secret.get_secret_value() == "whsec_abc123"

    def test_from_env_vars(self):
        with patch.dict(os.environ, VALID_ENV, clear=False):
            s = Settings(_env_file=None)
            assert s.github_token.get_secret_value() == "ghp_test_token_123"
            assert s.openai_api_key.get_secret_value() == "sk-test_key_456"

    def test_env_prefix(self):
        """Ensure only LINTWISE_ prefixed vars are read."""
        env = {
            "LINTWISE_GITHUB_TOKEN": "ghp_prefixed",
            "LINTWISE_OPENAI_API_KEY": "sk-prefixed",
            "GITHUB_TOKEN": "ghp_no_prefix",  # Should NOT be picked up
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings(_env_file=None)
            assert s.github_token.get_secret_value() == "ghp_prefixed"

    def test_temperature_float(self):
        s = Settings(
            github_token=SecretStr("ghp_test"),
            openai_api_key=SecretStr("sk-test"),
            openai_temperature=0.7,
        )
        assert s.openai_temperature == 0.7


class TestGetSettings:
    """Tests for the get_settings factory."""

    def test_returns_settings_instance(self):
        with patch.dict(os.environ, VALID_ENV, clear=False):
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_raises_without_required_env(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                get_settings()
