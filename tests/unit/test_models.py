"""Comprehensive tests for lintwise.core.models — all domain Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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


# ── FileStatus Enum ─────────────────────────────────────────────────────────


class TestFileStatus:
    def test_values(self):
        assert FileStatus.ADDED == "added"
        assert FileStatus.MODIFIED == "modified"
        assert FileStatus.DELETED == "deleted"
        assert FileStatus.RENAMED == "renamed"

    def test_all_members(self):
        assert set(FileStatus) == {
            FileStatus.ADDED,
            FileStatus.MODIFIED,
            FileStatus.DELETED,
            FileStatus.RENAMED,
        }


# ── Severity Enum ───────────────────────────────────────────────────────────


class TestSeverity:
    def test_values(self):
        assert Severity.CRITICAL == "critical"
        assert Severity.WARNING == "warning"
        assert Severity.SUGGESTION == "suggestion"
        assert Severity.NITPICK == "nitpick"

    def test_ordering_by_value(self):
        """Severities should be orderable alphabetically (not priority)."""
        severities = sorted(Severity, key=lambda s: s.value)
        assert len(severities) == 4


# ── ReviewCategory Enum ─────────────────────────────────────────────────────


class TestReviewCategory:
    def test_values(self):
        assert ReviewCategory.LOGIC == "logic"
        assert ReviewCategory.READABILITY == "readability"
        assert ReviewCategory.PERFORMANCE == "performance"
        assert ReviewCategory.SECURITY == "security"

    def test_all_categories(self):
        assert len(ReviewCategory) == 4


# ── RiskScore Enum ──────────────────────────────────────────────────────────


class TestRiskScore:
    def test_values(self):
        assert RiskScore.LOW == "low"
        assert RiskScore.MEDIUM == "medium"
        assert RiskScore.HIGH == "high"
        assert RiskScore.CRITICAL == "critical"


# ── HunkRange ───────────────────────────────────────────────────────────────


class TestHunkRange:
    def test_creation(self, sample_hunk: HunkRange):
        assert sample_hunk.start_line == 10
        assert sample_hunk.line_count == 5
        assert "@@ -10,5 +10,7 @@" in sample_hunk.content

    def test_minimal(self):
        hunk = HunkRange(start_line=1, line_count=1, content="+new line\n")
        assert hunk.start_line == 1

    def test_serialization_roundtrip(self, sample_hunk: HunkRange):
        data = sample_hunk.model_dump()
        restored = HunkRange.model_validate(data)
        assert restored == sample_hunk

    def test_json_roundtrip(self, sample_hunk: HunkRange):
        json_str = sample_hunk.model_dump_json()
        restored = HunkRange.model_validate_json(json_str)
        assert restored == sample_hunk


# ── FileChange ──────────────────────────────────────────────────────────────


class TestFileChange:
    def test_creation(self, sample_file_change: FileChange):
        assert sample_file_change.filename == "src/utils.py"
        assert sample_file_change.status == FileStatus.MODIFIED
        assert sample_file_change.additions == 2
        assert sample_file_change.deletions == 1
        assert sample_file_change.language == "python"
        assert len(sample_file_change.hunks) == 1

    def test_defaults(self):
        fc = FileChange(filename="test.py", status=FileStatus.ADDED)
        assert fc.patch == ""
        assert fc.additions == 0
        assert fc.deletions == 0
        assert fc.language is None
        assert fc.hunks == []

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            FileChange(filename="test.py", status="invalid_status")

    def test_all_statuses(self):
        for status in FileStatus:
            fc = FileChange(filename="test.py", status=status)
            assert fc.status == status

    def test_serialization_roundtrip(self, sample_file_change: FileChange):
        data = sample_file_change.model_dump()
        restored = FileChange.model_validate(data)
        assert restored == sample_file_change


# ── PRDiff ──────────────────────────────────────────────────────────────────


class TestPRDiff:
    def test_creation(self, sample_pr_diff: PRDiff):
        assert sample_pr_diff.repo_owner == "testorg"
        assert sample_pr_diff.repo_name == "testrepo"
        assert sample_pr_diff.pr_number == 42
        assert sample_pr_diff.title == "Fix null return in utils"
        assert len(sample_pr_diff.files) == 2
        assert sample_pr_diff.raw_url is not None

    def test_defaults(self):
        pr = PRDiff(repo_owner="o", repo_name="r", pr_number=1)
        assert pr.title == ""
        assert pr.description == ""
        assert pr.base_branch == "main"
        assert pr.head_branch == ""
        assert pr.files == []
        assert pr.raw_url is None

    def test_pr_number_required(self):
        with pytest.raises(ValidationError):
            PRDiff(repo_owner="o", repo_name="r")

    def test_files_list_integrity(self, sample_pr_diff: PRDiff):
        filenames = [f.filename for f in sample_pr_diff.files]
        assert "src/utils.py" in filenames
        assert "src/new_module.py" in filenames

    def test_serialization_roundtrip(self, sample_pr_diff: PRDiff):
        data = sample_pr_diff.model_dump()
        restored = PRDiff.model_validate(data)
        assert restored.pr_number == sample_pr_diff.pr_number
        assert len(restored.files) == len(sample_pr_diff.files)

    def test_json_roundtrip(self, sample_pr_diff: PRDiff):
        json_str = sample_pr_diff.model_dump_json()
        restored = PRDiff.model_validate_json(json_str)
        assert restored.repo_owner == sample_pr_diff.repo_owner


# ── ReviewComment ───────────────────────────────────────────────────────────


class TestReviewComment:
    def test_creation(self, sample_review_comment: ReviewComment):
        assert sample_review_comment.file == "src/utils.py"
        assert sample_review_comment.line == 12
        assert sample_review_comment.severity == Severity.WARNING
        assert sample_review_comment.category == ReviewCategory.LOGIC
        assert sample_review_comment.confidence == 0.9
        assert sample_review_comment.agent_name == "logic_agent"

    def test_defaults(self):
        rc = ReviewComment(
            file="test.py",
            severity=Severity.SUGGESTION,
            category=ReviewCategory.READABILITY,
            title="Test",
            body="Test body",
        )
        assert rc.line is None
        assert rc.end_line is None
        assert rc.suggestion is None
        assert rc.confidence == 0.8
        assert rc.agent_name == ""

    def test_confidence_bounds(self):
        # Valid at boundaries
        rc = ReviewComment(
            file="t.py", severity=Severity.NITPICK, category=ReviewCategory.LOGIC,
            title="T", body="B", confidence=0.0,
        )
        assert rc.confidence == 0.0

        rc = ReviewComment(
            file="t.py", severity=Severity.NITPICK, category=ReviewCategory.LOGIC,
            title="T", body="B", confidence=1.0,
        )
        assert rc.confidence == 1.0

    def test_confidence_out_of_bounds(self):
        with pytest.raises(ValidationError):
            ReviewComment(
                file="t.py", severity=Severity.NITPICK, category=ReviewCategory.LOGIC,
                title="T", body="B", confidence=1.5,
            )

        with pytest.raises(ValidationError):
            ReviewComment(
                file="t.py", severity=Severity.NITPICK, category=ReviewCategory.LOGIC,
                title="T", body="B", confidence=-0.1,
            )

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            ReviewComment(
                file="t.py", severity="blocker", category=ReviewCategory.LOGIC,
                title="T", body="B",
            )

    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            ReviewComment(
                file="t.py", severity=Severity.WARNING, category="style",
                title="T", body="B",
            )

    def test_with_suggestion(self):
        rc = ReviewComment(
            file="t.py", severity=Severity.SUGGESTION, category=ReviewCategory.PERFORMANCE,
            title="Use list comprehension", body="More efficient",
            suggestion="items = [x for x in range(10)]",
        )
        assert rc.suggestion is not None

    def test_serialization_roundtrip(self, sample_review_comment: ReviewComment):
        data = sample_review_comment.model_dump()
        restored = ReviewComment.model_validate(data)
        assert restored == sample_review_comment


# ── AgentMetrics ────────────────────────────────────────────────────────────


class TestAgentMetrics:
    def test_creation(self, sample_agent_metrics: AgentMetrics):
        assert sample_agent_metrics.agent_name == "logic_agent"
        assert sample_agent_metrics.duration_ms == 1500
        assert sample_agent_metrics.prompt_tokens == 800
        assert sample_agent_metrics.completion_tokens == 200
        assert sample_agent_metrics.files_analyzed == 2
        assert sample_agent_metrics.comments_produced == 1
        assert sample_agent_metrics.error is None

    def test_defaults(self):
        am = AgentMetrics(agent_name="test_agent")
        assert am.duration_ms == 0
        assert am.prompt_tokens == 0
        assert am.completion_tokens == 0
        assert am.files_analyzed == 0
        assert am.comments_produced == 0
        assert am.error is None

    def test_with_error(self):
        am = AgentMetrics(agent_name="failed_agent", error="LLM timeout")
        assert am.error == "LLM timeout"

    def test_serialization_roundtrip(self, sample_agent_metrics: AgentMetrics):
        data = sample_agent_metrics.model_dump()
        restored = AgentMetrics.model_validate(data)
        assert restored == sample_agent_metrics


# ── ReviewResult ────────────────────────────────────────────────────────────


class TestReviewResult:
    def test_creation(self, sample_review_result: ReviewResult):
        assert sample_review_result.pr_diff.pr_number == 42
        assert len(sample_review_result.comments) == 1
        assert sample_review_result.risk_score == RiskScore.LOW
        assert len(sample_review_result.agent_metrics) == 1
        assert sample_review_result.total_duration_ms == 2000

    def test_auto_id(self):
        rr = ReviewResult(
            pr_diff=PRDiff(repo_owner="o", repo_name="r", pr_number=1),
        )
        assert len(rr.id) == 12  # hex[:12]

    def test_unique_ids(self):
        ids = set()
        for _ in range(100):
            rr = ReviewResult(
                pr_diff=PRDiff(repo_owner="o", repo_name="r", pr_number=1),
            )
            ids.add(rr.id)
        assert len(ids) == 100  # All unique

    def test_auto_timestamp(self):
        rr = ReviewResult(
            pr_diff=PRDiff(repo_owner="o", repo_name="r", pr_number=1),
        )
        assert isinstance(rr.created_at, datetime)
        assert rr.created_at.tzinfo == timezone.utc

    def test_defaults(self):
        rr = ReviewResult(
            pr_diff=PRDiff(repo_owner="o", repo_name="r", pr_number=1),
        )
        assert rr.comments == []
        assert rr.summary == ""
        assert rr.risk_score == RiskScore.LOW
        assert rr.agent_metrics == []
        assert rr.total_duration_ms == 0

    def test_stats_property(self, sample_review_result: ReviewResult):
        stats = sample_review_result.stats
        assert stats["total_comments"] == 1
        assert stats["by_severity"]["warning"] == 1
        assert stats["by_severity"]["critical"] == 0
        assert stats["by_category"]["logic"] == 1
        assert stats["by_category"]["security"] == 0
        assert stats["risk_score"] == "low"

    def test_stats_empty(self):
        rr = ReviewResult(
            pr_diff=PRDiff(repo_owner="o", repo_name="r", pr_number=1),
        )
        stats = rr.stats
        assert stats["total_comments"] == 0
        assert all(v == 0 for v in stats["by_severity"].values())

    def test_serialization_roundtrip(self, sample_review_result: ReviewResult):
        data = sample_review_result.model_dump()
        restored = ReviewResult.model_validate(data)
        assert restored.id == sample_review_result.id
        assert len(restored.comments) == len(sample_review_result.comments)

    def test_json_roundtrip(self, sample_review_result: ReviewResult):
        json_str = sample_review_result.model_dump_json()
        restored = ReviewResult.model_validate_json(json_str)
        assert restored.pr_diff.pr_number == 42
