"""Async GitHub API client for fetching PR diffs and posting reviews."""

from __future__ import annotations

import re
from typing import Any

import httpx

from lintwise.core.config import Settings
from lintwise.core.exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubRateLimitError,
    InvalidPRURLError,
    PRNotFoundError,
)
from lintwise.core.logging import get_logger
from lintwise.core.models import PRDiff
from lintwise.github.diff_parser import parse_pr_files
from lintwise.github.schemas import GitHubFile, GitHubPullRequest, GitHubReviewRequest

logger = get_logger(__name__)

# Pattern: https://github.com/{owner}/{repo}/pull/{number}
_PR_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, and PR number from a GitHub PR URL.

    Raises:
        InvalidPRURLError: If the URL doesn't match expected format.
    """
    match = _PR_URL_RE.match(url.strip())
    if not match:
        raise InvalidPRURLError(f"Cannot parse PR URL: {url}")
    return match.group("owner"), match.group("repo"), int(match.group("number"))


class GitHubClient:
    """Async client for the GitHub REST API.

    Uses httpx with connection pooling for efficient async I/O.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.github_api_base.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._settings.github_token.get_secret_value()}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _handle_error(self, response: httpx.Response, context: str = "") -> None:
        """Map HTTP status codes to domain exceptions."""
        if response.is_success:
            return

        status = response.status_code
        detail = f"{context} — HTTP {status}"

        try:
            body = response.json()
            message = body.get("message", "")
            detail = f"{detail}: {message}"
        except Exception:
            pass

        if status == 401:
            raise GitHubAuthError(detail)
        if status == 403 and "rate limit" in detail.lower():
            reset_at = response.headers.get("X-RateLimit-Reset")
            raise GitHubRateLimitError(reset_at=int(reset_at) if reset_at else None)
        if status == 404:
            raise PRNotFoundError(detail)
        raise GitHubError(detail)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an authenticated GET request."""
        client = await self._get_client()
        response = await client.get(path, params=params)
        self._handle_error(response, context=f"GET {path}")
        return response.json()

    async def _post(self, path: str, json: dict[str, Any]) -> Any:
        """Make an authenticated POST request."""
        client = await self._get_client()
        response = await client.post(path, json=json)
        self._handle_error(response, context=f"POST {path}")
        return response.json()

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> GitHubPullRequest:
        """Fetch PR metadata."""
        data = await self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return GitHubPullRequest.model_validate(data)

    async def get_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        per_page: int = 100,
    ) -> list[GitHubFile]:
        """Fetch all files changed in a PR (handles pagination)."""
        all_files: list[GitHubFile] = []
        page = 1

        while True:
            data = await self._get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": per_page, "page": page},
            )

            if not data:
                break

            all_files.extend(GitHubFile.model_validate(f) for f in data)

            if len(data) < per_page:
                break
            page += 1

        return all_files

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> PRDiff:
        """Fetch a complete PRDiff: metadata + parsed files.

        This is the main entry point for the review pipeline.
        """
        logger.info("fetching_pr_diff", owner=owner, repo=repo, pr_number=pr_number)

        # Fetch PR metadata and files in parallel
        pr_data = await self.get_pull_request(owner, repo, pr_number)
        pr_files = await self.get_pr_files(owner, repo, pr_number)

        # Parse files into structured models
        file_dicts = [f.model_dump() for f in pr_files]
        parsed_files, skipped = parse_pr_files(
            file_dicts,
            max_files=self._settings.max_files_per_review,
            max_lines=self._settings.max_diff_lines,
        )

        if skipped:
            logger.info("skipped_files", count=len(skipped), files=skipped[:5])

        return PRDiff(
            repo_owner=owner,
            repo_name=repo,
            pr_number=pr_number,
            title=pr_data.title,
            description=pr_data.body or "",
            base_branch=pr_data.base.ref,
            head_branch=pr_data.head.ref,
            files=parsed_files,
            raw_url=pr_data.html_url,
        )

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review: GitHubReviewRequest,
    ) -> dict[str, Any]:
        """Submit a review with inline comments to a PR."""
        logger.info(
            "posting_review",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            comment_count=len(review.comments),
        )

        return await self._post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=review.model_dump(exclude_none=True),
        )
