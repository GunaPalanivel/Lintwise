"""Domain models shared across all Lintwise modules.

These Pydantic models define the contract between services.  Every module
communicates through these types — never raw dicts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────


class FileStatus(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NITPICK = "nitpick"


class ReviewCategory(StrEnum):
    LOGIC = "logic"
    READABILITY = "readability"
    PERFORMANCE = "performance"
    SECURITY = "security"


class RiskScore(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── PR / Diff Models ────────────────────────────────────────────────────────


class HunkRange(BaseModel):
    """A single @@ hunk within a file diff."""

    start_line: int
    line_count: int
    content: str


class FileChange(BaseModel):
    """A single file affected by the PR."""

    filename: str
    status: FileStatus
    patch: str = ""
    additions: int = 0
    deletions: int = 0
    language: str | None = None
    hunks: list[HunkRange] = Field(default_factory=list)


class PRDiff(BaseModel):
    """Complete representation of a Pull Request diff."""

    repo_owner: str
    repo_name: str
    pr_number: int
    title: str = ""
    description: str = ""
    base_branch: str = "main"
    head_branch: str = ""
    files: list[FileChange] = Field(default_factory=list)
    raw_url: str | None = None  # Original PR URL


# ── Review Models ────────────────────────────────────────────────────────────


class ReviewComment(BaseModel):
    """A single review finding produced by an analysis agent."""

    file: str
    line: int | None = None
    end_line: int | None = None
    severity: Severity
    category: ReviewCategory
    title: str
    body: str  # Markdown
    suggestion: str | None = None  # Suggested code fix
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    agent_name: str = ""


class AgentMetrics(BaseModel):
    """Telemetry from a single agent run."""

    agent_name: str
    duration_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    files_analyzed: int = 0
    comments_produced: int = 0
    error: str | None = None


class ReviewResult(BaseModel):
    """Final aggregated review output for a PR."""

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    pr_diff: PRDiff
    comments: list[ReviewComment] = Field(default_factory=list)
    summary: str = ""
    risk_score: RiskScore = RiskScore.LOW
    agent_metrics: list[AgentMetrics] = Field(default_factory=list)
    total_duration_ms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def stats(self) -> dict[str, Any]:
        """Quick stats for logging / API response."""
        return {
            "total_comments": len(self.comments),
            "by_severity": {s.value: sum(1 for c in self.comments if c.severity == s) for s in Severity},
            "by_category": {c.value: sum(1 for cm in self.comments if cm.category == c) for c in ReviewCategory},
            "risk_score": self.risk_score.value,
        }
