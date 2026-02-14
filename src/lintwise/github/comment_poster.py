"""Posts review comments back to GitHub PRs."""

from __future__ import annotations

from lintwise.core.logging import get_logger
from lintwise.core.models import ReviewComment, ReviewResult
from lintwise.github.schemas import GitHubReviewComment, GitHubReviewRequest

logger = get_logger(__name__)


def build_review_body(result: ReviewResult) -> str:
    """Build the top-level review summary body in Markdown."""
    lines = [
        f"## 🔍 Lintwise Review — {result.risk_score.value.upper()} Risk",
        "",
        result.summary or "Analysis complete.",
        "",
        f"**{len(result.comments)} comments** across "
        f"{len(result.pr_diff.files)} files "
        f"({result.total_duration_ms / 1000:.1f}s)",
        "",
    ]

    # Stats breakdown
    stats = result.stats
    sev_parts = [
        f"🔴 {stats['by_severity']['critical']} critical",
        f"🟡 {stats['by_severity']['warning']} warnings",
        f"🔵 {stats['by_severity']['suggestion']} suggestions",
        f"⚪ {stats['by_severity']['nitpick']} nitpicks",
    ]
    lines.append(" | ".join(sev_parts))

    return "\n".join(lines)


def format_inline_comment(comment: ReviewComment) -> str:
    """Format a ReviewComment into a Markdown inline comment body."""
    severity_emoji = {
        "critical": "🔴",
        "warning": "🟡",
        "suggestion": "🔵",
        "nitpick": "⚪",
    }

    emoji = severity_emoji.get(comment.severity.value, "💬")
    lines = [
        f"**{emoji} {comment.severity.value.upper()}** — {comment.title}",
        "",
        comment.body,
    ]

    if comment.suggestion:
        lines.extend([
            "",
            "**Suggested fix:**",
            f"```suggestion",
            comment.suggestion,
            "```",
        ])

    lines.append(f"\n*Confidence: {comment.confidence:.0%} | Agent: {comment.agent_name}*")

    return "\n".join(lines)


def build_review_request(result: ReviewResult) -> GitHubReviewRequest:
    """Convert a ReviewResult into a GitHub review submission payload.

    Only includes comments that have a valid line number for inline placement.
    Comments without line numbers contribute to the summary but aren't posted inline.
    """
    inline_comments: list[GitHubReviewComment] = []
    general_comments: list[str] = []

    for comment in result.comments:
        formatted_body = format_inline_comment(comment)

        if comment.line is not None:
            inline_comments.append(
                GitHubReviewComment(
                    path=comment.file,
                    line=comment.line,
                    body=formatted_body,
                )
            )
        else:
            general_comments.append(f"**{comment.file}**: {formatted_body}")

    # Build the top-level body
    body = build_review_body(result)
    if general_comments:
        body += "\n\n---\n\n### Additional Comments\n\n" + "\n\n".join(general_comments)

    logger.info(
        "built_review_request",
        inline_count=len(inline_comments),
        general_count=len(general_comments),
    )

    return GitHubReviewRequest(
        event="COMMENT",
        body=body,
        comments=inline_comments,
    )
