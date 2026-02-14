"""Review endpoints — submit PRs for AI-powered code review."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from lintwise.api.schemas import (
    ManualReviewRequest,
    ReviewCommentResponse,
    ReviewRequest,
    ReviewResponse,
)
from lintwise.core.logging import get_logger
from lintwise.core.models import FileChange, FileStatus, PRDiff
from lintwise.github.client import GitHubClient, parse_pr_url
from lintwise.github.diff_parser import parse_pr_files
from lintwise.llm.base import LLMProvider
from lintwise.orchestrator.pipeline import run_review

logger = get_logger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])

# These will be injected at app startup
_github_client: GitHubClient | None = None
_llm_provider: LLMProvider | None = None


def configure_review_router(
    github_client: GitHubClient,
    llm_provider: LLMProvider,
) -> None:
    """Inject dependencies into the review router."""
    global _github_client, _llm_provider
    _github_client = github_client
    _llm_provider = llm_provider


def _to_api_comments(comments) -> list[ReviewCommentResponse]:
    """Convert domain comments to API response format."""
    return [
        ReviewCommentResponse(
            file=c.file,
            line=c.line,
            severity=c.severity.value,
            category=c.category.value,
            title=c.title,
            body=c.body,
            suggestion=c.suggestion,
            confidence=c.confidence,
        )
        for c in comments
    ]


@router.post("/", response_model=ReviewResponse, status_code=200)
async def create_review(request: ReviewRequest) -> ReviewResponse:
    """Submit a GitHub PR URL for AI-powered code review.

    The system will:
    1. Fetch the PR diff from GitHub
    2. Run 4 specialized agents (logic, readability, performance, security)
    3. Aggregate and deduplicate findings
    4. Return a structured review
    """
    if not _github_client or not _llm_provider:
        raise HTTPException(status_code=503, detail="Service not configured")

    # Parse the PR URL
    owner, repo, pr_number = parse_pr_url(request.pr_url)

    # Fetch the PR diff
    pr_diff = await _github_client.get_pr_diff(owner, repo, pr_number)

    # Run the review pipeline
    result = await run_review(pr_diff, _llm_provider)

    return ReviewResponse(
        status="completed",
        pr_url=request.pr_url,
        risk_score=result.risk_score.value,
        summary=result.summary,
        total_comments=len(result.comments),
        comments=_to_api_comments(result.comments),
        duration_ms=result.total_duration_ms,
    )


@router.post("/manual", response_model=ReviewResponse, status_code=200)
async def manual_review(request: ManualReviewRequest) -> ReviewResponse:
    """Submit a raw diff for review (no GitHub required).

    Great for testing or CI/CD integration.
    """
    if not _llm_provider:
        raise HTTPException(status_code=503, detail="Service not configured")

    # Build a synthetic PRDiff from the raw text
    file_change = FileChange(
        filename="manual_input.diff",
        status=FileStatus.MODIFIED,
        patch=request.diff_text,
        additions=request.diff_text.count("\n+"),
        deletions=request.diff_text.count("\n-"),
        language=None,
    )

    pr_diff = PRDiff(
        repo_owner="manual",
        repo_name="review",
        pr_number=0,
        title=request.title,
        description=request.description,
        files=[file_change],
    )

    result = await run_review(pr_diff, _llm_provider)

    return ReviewResponse(
        status="completed",
        risk_score=result.risk_score.value,
        summary=result.summary,
        total_comments=len(result.comments),
        comments=_to_api_comments(result.comments),
        duration_ms=result.total_duration_ms,
    )
