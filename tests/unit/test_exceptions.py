"""Comprehensive tests for lintwise.core.exceptions — domain exception hierarchy."""

from __future__ import annotations

import pytest

from lintwise.core.exceptions import (
    AgentTimeoutError,
    DiffTooLargeError,
    GitHubAuthError,
    GitHubError,
    GitHubRateLimitError,
    InvalidPRURLError,
    LLMContextOverflowError,
    LLMError,
    LLMRateLimitError,
    LLMResponseParseError,
    LintwiseError,
    PipelineError,
    PRNotFoundError,
    ValidationError,
)


class TestLintwiseError:
    """Tests for the base exception."""

    def test_basic_creation(self):
        err = LintwiseError("something failed")
        assert str(err) == "something failed"
        assert err.detail == "something failed"

    def test_with_detail(self):
        err = LintwiseError("msg", detail="extra detail")
        assert str(err) == "msg"
        assert err.detail == "extra detail"

    def test_empty_message(self):
        err = LintwiseError()
        assert str(err) == ""
        assert err.detail == ""

    def test_is_exception(self):
        assert issubclass(LintwiseError, Exception)

    def test_catchable_as_exception(self):
        with pytest.raises(Exception):
            raise LintwiseError("test")


class TestGitHubExceptions:
    """Tests for GitHub-related exceptions."""

    def test_github_error_hierarchy(self):
        assert issubclass(GitHubError, LintwiseError)
        assert issubclass(GitHubAuthError, GitHubError)
        assert issubclass(GitHubRateLimitError, GitHubError)
        assert issubclass(PRNotFoundError, GitHubError)

    def test_github_error(self):
        err = GitHubError("API failed")
        assert str(err) == "API failed"
        with pytest.raises(LintwiseError):
            raise err

    def test_github_auth_error(self):
        err = GitHubAuthError("Bad token")
        assert isinstance(err, GitHubError)
        assert isinstance(err, LintwiseError)

    def test_rate_limit_error(self):
        err = GitHubRateLimitError(reset_at=1700000000)
        assert err.reset_at == 1700000000
        assert "rate limit" in str(err).lower()
        assert "1700000000" in err.detail

    def test_rate_limit_error_no_reset(self):
        err = GitHubRateLimitError()
        assert err.reset_at is None

    def test_pr_not_found(self):
        err = PRNotFoundError("PR #999 not found")
        assert isinstance(err, GitHubError)

    def test_catch_github_errors_broadly(self):
        """All GitHub errors should be catchable as GitHubError."""
        errors = [
            GitHubError("e1"),
            GitHubAuthError("e2"),
            GitHubRateLimitError(reset_at=0),
            PRNotFoundError("e4"),
        ]
        for err in errors:
            with pytest.raises(GitHubError):
                raise err


class TestLLMExceptions:
    """Tests for LLM-related exceptions."""

    def test_llm_error_hierarchy(self):
        assert issubclass(LLMError, LintwiseError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMContextOverflowError, LLMError)
        assert issubclass(LLMResponseParseError, LLMError)

    def test_llm_error(self):
        err = LLMError("OpenAI unavailable")
        assert str(err) == "OpenAI unavailable"

    def test_rate_limit(self):
        err = LLMRateLimitError("Too many requests")
        assert isinstance(err, LLMError)

    def test_context_overflow(self):
        err = LLMContextOverflowError("Input too long: 200k tokens")
        assert isinstance(err, LLMError)

    def test_response_parse(self):
        err = LLMResponseParseError("Invalid JSON in response")
        assert isinstance(err, LLMError)

    def test_catch_llm_errors_broadly(self):
        errors = [
            LLMError("e1"),
            LLMRateLimitError("e2"),
            LLMContextOverflowError("e3"),
            LLMResponseParseError("e4"),
        ]
        for err in errors:
            with pytest.raises(LLMError):
                raise err


class TestPipelineExceptions:
    """Tests for pipeline-related exceptions."""

    def test_pipeline_error_hierarchy(self):
        assert issubclass(PipelineError, LintwiseError)
        assert issubclass(AgentTimeoutError, PipelineError)
        assert issubclass(DiffTooLargeError, PipelineError)

    def test_agent_timeout(self):
        err = AgentTimeoutError("logic_agent timed out after 120s")
        assert isinstance(err, PipelineError)

    def test_diff_too_large(self):
        err = DiffTooLargeError("Diff has 10000 lines, max is 5000")
        assert isinstance(err, PipelineError)


class TestValidationExceptions:
    """Tests for validation-related exceptions."""

    def test_validation_error_hierarchy(self):
        assert issubclass(ValidationError, LintwiseError)
        assert issubclass(InvalidPRURLError, ValidationError)

    def test_invalid_pr_url(self):
        err = InvalidPRURLError("Cannot parse: https://not-github.com/foo")
        assert isinstance(err, ValidationError)
        assert isinstance(err, LintwiseError)


class TestExceptionCatchAllHierarchy:
    """Verify that catching LintwiseError catches ALL domain exceptions."""

    def test_all_exceptions_caught_by_base(self):
        all_exceptions = [
            LintwiseError("base"),
            GitHubError("gh"),
            GitHubAuthError("auth"),
            GitHubRateLimitError(reset_at=0),
            PRNotFoundError("pr"),
            LLMError("llm"),
            LLMRateLimitError("rate"),
            LLMContextOverflowError("ctx"),
            LLMResponseParseError("parse"),
            PipelineError("pipe"),
            AgentTimeoutError("timeout"),
            DiffTooLargeError("large"),
            ValidationError("val"),
            InvalidPRURLError("url"),
        ]
        for err in all_exceptions:
            with pytest.raises(LintwiseError):
                raise err
