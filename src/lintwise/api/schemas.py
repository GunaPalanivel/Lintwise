"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from lintwise.core.models import ReviewComment, RiskScore


class ReviewRequest(BaseModel):
    """Request to review a Pull Request."""

    pr_url: str = Field(
        ...,
        description="Full GitHub PR URL (e.g. https://github.com/owner/repo/pull/42)",
        examples=["https://github.com/octocat/hello-world/pull/1"],
    )


class ManualReviewRequest(BaseModel):
    """Request to review a raw diff paste."""

    diff_text: str = Field(
        ...,
        description="Raw unified diff to analyze",
        min_length=10,
    )
    title: str = Field(
        default="Manual Review",
        description="Title for the review context",
    )
    description: str = Field(
        default="",
        description="Description for context",
    )


class ReviewCommentResponse(BaseModel):
    """API-facing review comment."""

    file: str
    line: int | None = None
    severity: str
    category: str
    title: str
    body: str
    suggestion: str | None = None
    confidence: float


class ReviewResponse(BaseModel):
    """Full review response."""

    status: str = "completed"
    pr_url: str | None = None
    risk_score: str = "low"
    summary: str = ""
    total_comments: int = 0
    comments: list[ReviewCommentResponse] = []
    duration_ms: int = 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    services: dict[str, str] = {}


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str = ""
