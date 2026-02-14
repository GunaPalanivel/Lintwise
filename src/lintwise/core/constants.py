"""Constants and mappings used across the application."""

from __future__ import annotations

# ── Language Detection (extension → language name) ───────────────────────────

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".md": "markdown",
    ".dockerfile": "dockerfile",
}

# Files to skip during review (non-substantive changes)
SKIP_PATTERNS: set[str] = {
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pnpm-lock.yaml",
    ".gitignore",
    ".gitattributes",
    "LICENSE",
}

# Maximum tokens to allocate per agent per file analysis
MAX_TOKENS_PER_ANALYSIS: int = 4000

# Review severity weights for risk score computation
SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 10,
    "warning": 3,
    "suggestion": 1,
    "nitpick": 0,
}

# Risk score thresholds (total weighted severity)
RISK_THRESHOLDS: dict[str, int] = {
    "low": 5,
    "medium": 15,
    "high": 30,
    # Above 30 → critical
}


def detect_language(filename: str) -> str | None:
    """Detect programming language from file extension."""
    import os

    _, ext = os.path.splitext(filename.lower())
    return EXTENSION_LANGUAGE_MAP.get(ext)
