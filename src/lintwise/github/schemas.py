"""Pydantic models for GitHub API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    login: str
    avatar_url: str = ""


class GitHubPRHead(BaseModel):
    ref: str
    sha: str


class GitHubPRBase(BaseModel):
    ref: str
    sha: str


class GitHubPullRequest(BaseModel):
    """Subset of GitHub's PR response we actually need."""

    number: int
    title: str
    body: str | None = None
    state: str = "open"
    head: GitHubPRHead
    base: GitHubPRBase
    user: GitHubUser | None = None
    html_url: str = ""
    diff_url: str = ""


class GitHubFile(BaseModel):
    """A file entry from GitHub's GET /pulls/{number}/files endpoint."""

    filename: str
    status: str  # "added", "modified", "removed", "renamed"
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None
    previous_filename: str | None = None
    sha: str = ""


class GitHubReviewComment(BaseModel):
    """Payload for creating an inline PR review comment."""

    path: str
    line: int | None = None
    side: str = "RIGHT"
    body: str


class GitHubReviewRequest(BaseModel):
    """Payload for submitting a full PR review."""

    event: str = "COMMENT"  # APPROVE, REQUEST_CHANGES, COMMENT
    body: str = ""
    comments: list[GitHubReviewComment] = Field(default_factory=list)


class WebhookEvent(BaseModel):
    """Parsed GitHub webhook event."""

    action: str
    sender: str = ""
    repo_owner: str = ""
    repo_name: str = ""
    pr_number: int = 0
