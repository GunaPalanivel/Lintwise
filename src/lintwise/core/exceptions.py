"""Domain exception hierarchy.

All exceptions inherit from ``LintwiseError`` so callers can catch broadly
or narrowly as needed.  FastAPI exception handlers map these to HTTP responses.
"""

from __future__ import annotations


class LintwiseError(Exception):
    """Base exception for all Lintwise errors."""

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        self.detail = detail or message
        super().__init__(message)


# ── GitHub ───────────────────────────────────────────────────────────────────


class GitHubError(LintwiseError):
    """Error communicating with the GitHub API."""


class GitHubAuthError(GitHubError):
    """Invalid or expired GitHub token."""


class GitHubRateLimitError(GitHubError):
    """GitHub API rate limit exhausted."""

    def __init__(self, reset_at: int | None = None) -> None:
        self.reset_at = reset_at
        super().__init__("GitHub API rate limit exceeded", detail=f"Resets at {reset_at}")


class PRNotFoundError(GitHubError):
    """The requested PR does not exist or is not accessible."""


# ── LLM ──────────────────────────────────────────────────────────────────────


class LLMError(LintwiseError):
    """Error from the LLM provider."""


class LLMRateLimitError(LLMError):
    """LLM provider rate limit hit."""


class LLMContextOverflowError(LLMError):
    """Input exceeds the model's context window."""


class LLMResponseParseError(LLMError):
    """LLM returned malformed / unparseable output."""


# ── Pipeline ─────────────────────────────────────────────────────────────────


class PipelineError(LintwiseError):
    """Error during agent pipeline execution."""


class AgentTimeoutError(PipelineError):
    """An agent exceeded its execution timeout."""


class DiffTooLargeError(PipelineError):
    """The PR diff exceeds the maximum allowed size."""


# ── Validation ───────────────────────────────────────────────────────────────


class ValidationError(LintwiseError):
    """Input validation failed."""


class InvalidPRURLError(ValidationError):
    """The provided PR URL could not be parsed."""
