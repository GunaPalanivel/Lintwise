"""Comprehensive tests for lintwise.orchestrator.aggregator."""

from __future__ import annotations

import pytest

from lintwise.core.models import ReviewCategory, ReviewComment, RiskScore, Severity
from lintwise.orchestrator.aggregator import (
    aggregate_comments,
    compute_risk_score,
    deduplicate_comments,
    rank_comments,
)


def _comment(
    file: str = "test.py",
    line: int | None = 10,
    severity: str = "warning",
    title: str = "Issue",
    confidence: float = 0.8,
    category: str = "logic",
    agent: str = "test_agent",
) -> ReviewComment:
    return ReviewComment(
        file=file,
        line=line,
        severity=Severity(severity),
        category=ReviewCategory(category),
        title=title,
        body="Description of the issue.",
        confidence=confidence,
        agent_name=agent,
    )


# ── Deduplication ───────────────────────────────────────────────────────────


class TestDeduplicateComments:
    def test_no_duplicates(self):
        comments = [
            _comment(title="Issue A", line=1),
            _comment(title="Issue B", line=2),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 2

    def test_exact_duplicates(self):
        comments = [
            _comment(title="Same issue", line=10, confidence=0.7),
            _comment(title="Same issue", line=10, confidence=0.9),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 1
        assert result[0].confidence == 0.9  # Keeps higher confidence

    def test_case_insensitive_dedup(self):
        comments = [
            _comment(title="Null Check Missing", line=5, confidence=0.6),
            _comment(title="null check missing", line=5, confidence=0.8),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 1

    def test_different_files_not_deduped(self):
        comments = [
            _comment(file="a.py", title="Issue", line=10),
            _comment(file="b.py", title="Issue", line=10),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 2

    def test_different_lines_not_deduped(self):
        comments = [
            _comment(title="Issue", line=10),
            _comment(title="Issue", line=20),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate_comments([]) == []

    def test_single_item(self):
        comments = [_comment()]
        assert len(deduplicate_comments(comments)) == 1

    def test_multiple_duplicates(self):
        comments = [
            _comment(title="A", line=1, confidence=0.3),
            _comment(title="A", line=1, confidence=0.9),
            _comment(title="A", line=1, confidence=0.5),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 1
        assert result[0].confidence == 0.9


# ── Ranking ─────────────────────────────────────────────────────────────────


class TestRankComments:
    def test_severity_order(self):
        comments = [
            _comment(severity="nitpick", title="N"),
            _comment(severity="critical", title="C"),
            _comment(severity="suggestion", title="S"),
            _comment(severity="warning", title="W"),
        ]
        ranked = rank_comments(comments)
        assert ranked[0].severity == Severity.CRITICAL
        assert ranked[1].severity == Severity.WARNING
        assert ranked[2].severity == Severity.SUGGESTION
        assert ranked[3].severity == Severity.NITPICK

    def test_same_severity_by_confidence(self):
        comments = [
            _comment(severity="warning", confidence=0.5, title="Low"),
            _comment(severity="warning", confidence=0.9, title="High"),
        ]
        ranked = rank_comments(comments)
        assert ranked[0].confidence == 0.9

    def test_empty(self):
        assert rank_comments([]) == []


# ── Risk Score ──────────────────────────────────────────────────────────────


class TestComputeRiskScore:
    def test_no_comments_low(self):
        assert compute_risk_score([]) == RiskScore.LOW

    def test_nitpicks_only_low(self):
        comments = [_comment(severity="nitpick") for _ in range(10)]
        assert compute_risk_score(comments) == RiskScore.LOW

    def test_single_critical_medium(self):
        # critical = 10 weight, threshold for medium is >5
        comments = [_comment(severity="critical")]
        assert compute_risk_score(comments) == RiskScore.MEDIUM

    def test_multiple_warnings_medium(self):
        # warning = 3, 3 warnings = 9 > 5 threshold
        comments = [_comment(severity="warning") for _ in range(3)]
        assert compute_risk_score(comments) == RiskScore.MEDIUM

    def test_high_risk(self):
        # Need >15: 2 critical (20) should be HIGH
        comments = [_comment(severity="critical") for _ in range(2)]
        assert compute_risk_score(comments) == RiskScore.HIGH

    def test_critical_risk(self):
        # Need >30: 4 critical (40)
        comments = [_comment(severity="critical") for _ in range(4)]
        assert compute_risk_score(comments) == RiskScore.CRITICAL

    def test_mixed_severities(self):
        comments = [
            _comment(severity="critical"),   # 10
            _comment(severity="warning"),    # 3
            _comment(severity="suggestion"), # 1
            _comment(severity="nitpick"),    # 0
        ]
        # Total: 14, which is > 5 (medium) but ≤ 15, so MEDIUM
        assert compute_risk_score(comments) == RiskScore.MEDIUM


# ── Full Aggregation ────────────────────────────────────────────────────────


class TestAggregateComments:
    def test_full_pipeline(self):
        comments = [
            _comment(severity="critical", title="A", line=1, confidence=0.9),
            _comment(severity="warning", title="B", line=2, confidence=0.5),
            _comment(severity="warning", title="B", line=2, confidence=0.8),  # Duplicate
        ]
        ranked, risk = aggregate_comments(comments)
        assert len(ranked) == 2  # Deduped from 3
        assert ranked[0].severity == Severity.CRITICAL  # Ranked first
        assert risk == RiskScore.MEDIUM  # 10 + 3 = 13

    def test_empty(self):
        ranked, risk = aggregate_comments([])
        assert ranked == []
        assert risk == RiskScore.LOW
