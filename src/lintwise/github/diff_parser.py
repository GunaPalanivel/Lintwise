"""Unified diff parser — converts raw patch text to structured FileChange models."""

from __future__ import annotations

import re

from lintwise.core.constants import SKIP_PATTERNS, detect_language
from lintwise.core.models import FileChange, FileStatus, HunkRange

# Matches: @@ -10,5 +12,7 @@ optional context
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$",
    re.MULTILINE,
)


def parse_patch(filename: str, patch: str, status: str = "modified") -> FileChange:
    """Parse a single file's patch text into a FileChange model.

    Args:
        filename: Path of the file in the repo.
        patch: Raw unified diff patch string (from GitHub API).
        status: One of 'added', 'modified', 'removed', 'renamed'.

    Returns:
        Structured FileChange with hunks, line counts, and detected language.
    """
    # Normalise GitHub's "removed" → our "deleted"
    status_map = {"removed": "deleted"}
    normalised = status_map.get(status, status)

    hunks: list[HunkRange] = []
    additions = 0
    deletions = 0

    if patch:
        for match in _HUNK_HEADER_RE.finditer(patch):
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1

            # Extract the hunk body: everything from this @@ to next @@ or end
            hunk_start = match.end()
            next_match = _HUNK_HEADER_RE.search(patch, hunk_start)
            hunk_body = patch[hunk_start : next_match.start()] if next_match else patch[hunk_start:]

            hunks.append(
                HunkRange(
                    start_line=new_start,
                    line_count=new_count,
                    content=hunk_body.strip(),
                )
            )

        # Count additions/deletions from the patch lines
        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

    return FileChange(
        filename=filename,
        status=FileStatus(normalised),
        patch=patch,
        additions=additions,
        deletions=deletions,
        language=detect_language(filename),
        hunks=hunks,
    )


def should_skip_file(filename: str) -> bool:
    """Check if a file should be excluded from review."""
    import os

    basename = os.path.basename(filename)
    return basename in SKIP_PATTERNS


def parse_pr_files(
    files: list[dict],
    max_files: int = 50,
    max_lines: int = 5000,
) -> tuple[list[FileChange], list[str]]:
    """Parse a list of GitHub file dicts into FileChange models.

    Args:
        files: Raw file dicts from GitHub API (GET /pulls/{n}/files).
        max_files: Maximum number of files to include.
        max_lines: Maximum total diff lines before truncation.

    Returns:
        Tuple of (parsed FileChange list, list of skipped file names).
    """
    parsed: list[FileChange] = []
    skipped: list[str] = []
    total_lines = 0

    for f in files:
        filename = f.get("filename", "")

        # Skip non-substantive files
        if should_skip_file(filename):
            skipped.append(filename)
            continue

        # Skip files without patches (binary, etc.)
        patch = f.get("patch", "") or ""
        if not patch:
            skipped.append(filename)
            continue

        # Enforce diff-size limit
        patch_lines = patch.count("\n") + 1
        if total_lines + patch_lines > max_lines:
            skipped.append(filename)
            continue

        total_lines += patch_lines

        file_change = parse_patch(
            filename=filename,
            patch=patch,
            status=f.get("status", "modified"),
        )
        parsed.append(file_change)

        if len(parsed) >= max_files:
            break

    return parsed, skipped
