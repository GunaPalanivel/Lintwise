"""Result aggregation — deduplicate, rank, and compute risk score."""

from __future__ import annotations

from lintwise.core.constants import RISK_THRESHOLDS, SEVERITY_WEIGHTS
from lintwise.core.logging import get_logger
from lintwise.core.models import ReviewComment, RiskScore

logger = get_logger(__name__)


def deduplicate_comments(comments: list[ReviewComment]) -> list[ReviewComment]:
    """Remove duplicate comments that flag the same issue at the same location.

    Deduplication criteria:
    - Same file + same line + similar title (case-insensitive)
    - When duplicates exist, keep the one with highest confidence
    """
    seen: dict[str, ReviewComment] = {}

    for comment in comments:
        # Build dedup key
        key = f"{comment.file}:{comment.line}:{comment.title.lower().strip()}"

        if key in seen:
            # Keep higher confidence
            if comment.confidence > seen[key].confidence:
                seen[key] = comment
        else:
            seen[key] = comment

    deduped = list(seen.values())
    removed = len(comments) - len(deduped)
    if removed:
        logger.info("deduplicated_comments", removed=removed, remaining=len(deduped))

    return deduped


def rank_comments(comments: list[ReviewComment]) -> list[ReviewComment]:
    """Sort comments by severity (critical first), then by confidence."""
    severity_order = {"critical": 0, "warning": 1, "suggestion": 2, "nitpick": 3}

    return sorted(
        comments,
        key=lambda c: (severity_order.get(c.severity.value, 99), -c.confidence),
    )


def compute_risk_score(comments: list[ReviewComment]) -> RiskScore:
    """Compute overall PR risk score from weighted comment severities."""
    total_weight = sum(
        SEVERITY_WEIGHTS.get(c.severity.value, 0) for c in comments
    )

    if total_weight > RISK_THRESHOLDS["high"]:
        return RiskScore.CRITICAL
    if total_weight > RISK_THRESHOLDS["medium"]:
        return RiskScore.HIGH
    if total_weight > RISK_THRESHOLDS["low"]:
        return RiskScore.MEDIUM
    return RiskScore.LOW


def aggregate_comments(comments: list[ReviewComment]) -> tuple[list[ReviewComment], RiskScore]:
    """Full aggregation pipeline: deduplicate → rank → compute risk.

    Returns:
        Tuple of (ranked comments, risk score).
    """
    deduped = deduplicate_comments(comments)
    ranked = rank_comments(deduped)
    risk = compute_risk_score(ranked)
    return ranked, risk
