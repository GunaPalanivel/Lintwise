"""Shared test fixtures for all Lintwise tests."""

from __future__ import annotations

import pytest

from lintwise.core.models import (
    AgentMetrics,
    FileChange,
    FileStatus,
    HunkRange,
    PRDiff,
    ReviewCategory,
    ReviewComment,
    ReviewResult,
    RiskScore,
    Severity,
)


@pytest.fixture
def sample_hunk() -> HunkRange:
    return HunkRange(
        start_line=10,
        line_count=5,
        content="@@ -10,5 +10,7 @@\n def foo():\n-    return None\n+    return 42\n+    # added line\n",
    )


@pytest.fixture
def sample_file_change(sample_hunk: HunkRange) -> FileChange:
    return FileChange(
        filename="src/utils.py",
        status=FileStatus.MODIFIED,
        patch="@@ -10,5 +10,7 @@\n def foo():\n-    return None\n+    return 42\n",
        additions=2,
        deletions=1,
        language="python",
        hunks=[sample_hunk],
    )


@pytest.fixture
def sample_added_file() -> FileChange:
    return FileChange(
        filename="src/new_module.py",
        status=FileStatus.ADDED,
        patch="@@ -0,0 +1,10 @@\n+def new_func():\n+    pass\n",
        additions=10,
        deletions=0,
        language="python",
    )


@pytest.fixture
def sample_deleted_file() -> FileChange:
    return FileChange(
        filename="old_module.py",
        status=FileStatus.DELETED,
        patch="",
        additions=0,
        deletions=50,
        language="python",
    )


@pytest.fixture
def sample_pr_diff(sample_file_change: FileChange, sample_added_file: FileChange) -> PRDiff:
    return PRDiff(
        repo_owner="testorg",
        repo_name="testrepo",
        pr_number=42,
        title="Fix null return in utils",
        description="This PR fixes the null return value in foo().",
        base_branch="main",
        head_branch="fix/null-return",
        files=[sample_file_change, sample_added_file],
        raw_url="https://github.com/testorg/testrepo/pull/42",
    )


@pytest.fixture
def sample_review_comment() -> ReviewComment:
    return ReviewComment(
        file="src/utils.py",
        line=12,
        severity=Severity.WARNING,
        category=ReviewCategory.LOGIC,
        title="Potential unreachable code after return",
        body="The line after `return 42` will never execute.",
        suggestion="Remove the unreachable line.",
        confidence=0.9,
        agent_name="logic_agent",
    )


@pytest.fixture
def sample_agent_metrics() -> AgentMetrics:
    return AgentMetrics(
        agent_name="logic_agent",
        duration_ms=1500,
        prompt_tokens=800,
        completion_tokens=200,
        files_analyzed=2,
        comments_produced=1,
    )


@pytest.fixture
def sample_review_result(
    sample_pr_diff: PRDiff,
    sample_review_comment: ReviewComment,
    sample_agent_metrics: AgentMetrics,
) -> ReviewResult:
    return ReviewResult(
        pr_diff=sample_pr_diff,
        comments=[sample_review_comment],
        summary="Minor logic issue detected in utils.py.",
        risk_score=RiskScore.LOW,
        agent_metrics=[sample_agent_metrics],
        total_duration_ms=2000,
    )
