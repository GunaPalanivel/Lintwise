"""Comprehensive tests for lintwise.github.comment_poster."""

from __future__ import annotations

import pytest

from lintwise.core.models import (
    PRDiff,
    ReviewCategory,
    ReviewComment,
    ReviewResult,
    RiskScore,
    Severity,
)
from lintwise.github.comment_poster import (
    build_review_body,
    build_review_request,
    format_inline_comment,
)


@pytest.fixture
def pr_diff() -> PRDiff:
    return PRDiff(repo_owner="o", repo_name="r", pr_number=1)


@pytest.fixture
def critical_comment() -> ReviewComment:
    return ReviewComment(
        file="auth.py",
        line=42,
        severity=Severity.CRITICAL,
        category=ReviewCategory.SECURITY,
        title="SQL injection vulnerability",
        body="User input is directly interpolated into an SQL query.",
        suggestion='cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
        confidence=0.95,
        agent_name="security_agent",
    )


@pytest.fixture
def warning_comment() -> ReviewComment:
    return ReviewComment(
        file="utils.py",
        line=10,
        severity=Severity.WARNING,
        category=ReviewCategory.LOGIC,
        title="Possible null dereference",
        body="Variable `data` could be None here.",
        confidence=0.8,
        agent_name="logic_agent",
    )


@pytest.fixture
def no_line_comment() -> ReviewComment:
    return ReviewComment(
        file="config.py",
        severity=Severity.SUGGESTION,
        category=ReviewCategory.READABILITY,
        title="Consider adding docstring",
        body="This module lacks a module-level docstring.",
        confidence=0.6,
        agent_name="readability_agent",
    )


class TestFormatInlineComment:
    def test_critical_with_suggestion(self, critical_comment: ReviewComment):
        body = format_inline_comment(critical_comment)
        assert "🔴" in body
        assert "CRITICAL" in body
        assert "SQL injection" in body
        assert "```suggestion" in body
        assert "cursor.execute" in body
        assert "95%" in body
        assert "security_agent" in body

    def test_warning_without_suggestion(self, warning_comment: ReviewComment):
        body = format_inline_comment(warning_comment)
        assert "🟡" in body
        assert "WARNING" in body
        assert "```suggestion" not in body

    def test_suggestion_severity(self):
        rc = ReviewComment(
            file="t.py", severity=Severity.SUGGESTION, category=ReviewCategory.PERFORMANCE,
            title="Use generator", body="Save memory.", confidence=0.7, agent_name="perf",
        )
        body = format_inline_comment(rc)
        assert "🔵" in body
        assert "SUGGESTION" in body

    def test_nitpick_severity(self):
        rc = ReviewComment(
            file="t.py", severity=Severity.NITPICK, category=ReviewCategory.READABILITY,
            title="Trailing whitespace", body="Minor.", confidence=0.5, agent_name="read",
        )
        body = format_inline_comment(rc)
        assert "⚪" in body
        assert "NITPICK" in body


class TestBuildReviewBody:
    def test_contains_risk_score(self, pr_diff: PRDiff, critical_comment: ReviewComment):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[critical_comment],
            risk_score=RiskScore.HIGH,
            summary="Major issues found.",
            total_duration_ms=3000,
        )
        body = build_review_body(result)
        assert "HIGH Risk" in body
        assert "1 comments" in body
        assert "3.0s" in body

    def test_severity_breakdown(self, pr_diff: PRDiff, critical_comment: ReviewComment, warning_comment: ReviewComment):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[critical_comment, warning_comment],
            risk_score=RiskScore.MEDIUM,
        )
        body = build_review_body(result)
        assert "1 critical" in body
        assert "1 warnings" in body

    def test_empty_comments(self, pr_diff: PRDiff):
        result = ReviewResult(
            pr_diff=pr_diff,
            summary="All good!",
        )
        body = build_review_body(result)
        assert "0 comments" in body
        assert "LOW Risk" in body

    def test_custom_summary(self, pr_diff: PRDiff):
        result = ReviewResult(
            pr_diff=pr_diff,
            summary="Custom summary text here.",
        )
        body = build_review_body(result)
        assert "Custom summary text here." in body


class TestBuildReviewRequest:
    def test_inline_and_general_comments(
        self, pr_diff: PRDiff, critical_comment: ReviewComment, no_line_comment: ReviewComment
    ):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[critical_comment, no_line_comment],
        )
        request = build_review_request(result)
        assert request.event == "COMMENT"
        # critical_comment has line=42 → inline
        assert len(request.comments) == 1
        assert request.comments[0].path == "auth.py"
        assert request.comments[0].line == 42
        # no_line_comment has no line → goes into body
        assert "Additional Comments" in request.body

    def test_all_inline(self, pr_diff: PRDiff, critical_comment: ReviewComment, warning_comment: ReviewComment):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[critical_comment, warning_comment],
        )
        request = build_review_request(result)
        assert len(request.comments) == 2
        assert "Additional Comments" not in request.body

    def test_all_general(self, pr_diff: PRDiff, no_line_comment: ReviewComment):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[no_line_comment],
        )
        request = build_review_request(result)
        assert len(request.comments) == 0
        assert "Additional Comments" in request.body

    def test_empty_result(self, pr_diff: PRDiff):
        result = ReviewResult(pr_diff=pr_diff)
        request = build_review_request(result)
        assert len(request.comments) == 0
        assert "0 comments" in request.body

    def test_review_body_included(self, pr_diff: PRDiff, critical_comment: ReviewComment):
        result = ReviewResult(
            pr_diff=pr_diff,
            comments=[critical_comment],
            summary="Security issue found.",
            risk_score=RiskScore.CRITICAL,
        )
        request = build_review_request(result)
        assert "CRITICAL Risk" in request.body
        assert "Security issue found." in request.body
