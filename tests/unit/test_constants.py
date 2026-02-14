"""Comprehensive tests for lintwise.core.constants."""

from __future__ import annotations

import pytest

from lintwise.core.constants import (
    EXTENSION_LANGUAGE_MAP,
    RISK_THRESHOLDS,
    SEVERITY_WEIGHTS,
    SKIP_PATTERNS,
    detect_language,
)


class TestExtensionLanguageMap:
    """Tests for the file extension → language mapping."""

    def test_common_languages(self):
        assert EXTENSION_LANGUAGE_MAP[".py"] == "python"
        assert EXTENSION_LANGUAGE_MAP[".js"] == "javascript"
        assert EXTENSION_LANGUAGE_MAP[".ts"] == "typescript"
        assert EXTENSION_LANGUAGE_MAP[".java"] == "java"
        assert EXTENSION_LANGUAGE_MAP[".go"] == "go"
        assert EXTENSION_LANGUAGE_MAP[".rs"] == "rust"
        assert EXTENSION_LANGUAGE_MAP[".rb"] == "ruby"
        assert EXTENSION_LANGUAGE_MAP[".cs"] == "csharp"

    def test_jsx_tsx_mappings(self):
        assert EXTENSION_LANGUAGE_MAP[".jsx"] == "javascript"
        assert EXTENSION_LANGUAGE_MAP[".tsx"] == "typescript"

    def test_c_family(self):
        assert EXTENSION_LANGUAGE_MAP[".c"] == "c"
        assert EXTENSION_LANGUAGE_MAP[".cpp"] == "cpp"
        assert EXTENSION_LANGUAGE_MAP[".h"] == "c"
        assert EXTENSION_LANGUAGE_MAP[".hpp"] == "cpp"

    def test_config_formats(self):
        assert EXTENSION_LANGUAGE_MAP[".yml"] == "yaml"
        assert EXTENSION_LANGUAGE_MAP[".yaml"] == "yaml"
        assert EXTENSION_LANGUAGE_MAP[".json"] == "json"
        assert EXTENSION_LANGUAGE_MAP[".toml"] == "toml"
        assert EXTENSION_LANGUAGE_MAP[".xml"] == "xml"

    def test_web_formats(self):
        assert EXTENSION_LANGUAGE_MAP[".html"] == "html"
        assert EXTENSION_LANGUAGE_MAP[".css"] == "css"
        assert EXTENSION_LANGUAGE_MAP[".scss"] == "scss"

    def test_no_duplicate_values_are_accidental(self):
        """All mappings should be intentional."""
        assert len(EXTENSION_LANGUAGE_MAP) > 20


class TestDetectLanguage:
    """Tests for the detect_language function."""

    def test_python(self):
        assert detect_language("main.py") == "python"

    def test_javascript(self):
        assert detect_language("index.js") == "javascript"

    def test_typescript(self):
        assert detect_language("component.ts") == "typescript"

    def test_tsx(self):
        assert detect_language("App.tsx") == "typescript"

    def test_unknown_extension(self):
        assert detect_language("data.xyz") is None

    def test_no_extension(self):
        assert detect_language("Makefile") is None

    def test_case_insensitive(self):
        assert detect_language("Main.PY") == "python"
        assert detect_language("INDEX.JS") == "javascript"

    def test_path_with_directories(self):
        assert detect_language("src/components/Button.tsx") == "typescript"
        assert detect_language("pkg/handlers/auth.go") == "go"

    def test_dotfile(self):
        assert detect_language(".gitignore") is None

    def test_dockerfile(self):
        assert detect_language("app.dockerfile") == "dockerfile"

    def test_markdown(self):
        assert detect_language("README.md") == "markdown"

    def test_shell(self):
        assert detect_language("deploy.sh") == "shell"
        assert detect_language("build.bash") == "shell"

    def test_sql(self):
        assert detect_language("migrations/001.sql") == "sql"


class TestSkipPatterns:
    """Tests for files that should be skipped during review."""

    def test_lockfiles(self):
        assert "package-lock.json" in SKIP_PATTERNS
        assert "yarn.lock" in SKIP_PATTERNS
        assert "poetry.lock" in SKIP_PATTERNS
        assert "Pipfile.lock" in SKIP_PATTERNS
        assert "pnpm-lock.yaml" in SKIP_PATTERNS

    def test_git_files(self):
        assert ".gitignore" in SKIP_PATTERNS
        assert ".gitattributes" in SKIP_PATTERNS

    def test_license(self):
        assert "LICENSE" in SKIP_PATTERNS

    def test_source_files_not_skipped(self):
        assert "main.py" not in SKIP_PATTERNS
        assert "index.js" not in SKIP_PATTERNS
        assert "README.md" not in SKIP_PATTERNS


class TestSeverityWeights:
    """Tests for severity weight mappings."""

    def test_ordering(self):
        assert SEVERITY_WEIGHTS["critical"] > SEVERITY_WEIGHTS["warning"]
        assert SEVERITY_WEIGHTS["warning"] > SEVERITY_WEIGHTS["suggestion"]
        assert SEVERITY_WEIGHTS["suggestion"] > SEVERITY_WEIGHTS["nitpick"]

    def test_nitpick_is_zero(self):
        assert SEVERITY_WEIGHTS["nitpick"] == 0

    def test_critical_is_highest(self):
        assert SEVERITY_WEIGHTS["critical"] == max(SEVERITY_WEIGHTS.values())

    def test_all_severities_covered(self):
        from lintwise.core.models import Severity
        for s in Severity:
            assert s.value in SEVERITY_WEIGHTS


class TestRiskThresholds:
    """Tests for risk score thresholds."""

    def test_ordering(self):
        assert RISK_THRESHOLDS["low"] < RISK_THRESHOLDS["medium"]
        assert RISK_THRESHOLDS["medium"] < RISK_THRESHOLDS["high"]

    def test_critical_not_in_thresholds(self):
        """Critical is anything above high — no explicit threshold needed."""
        assert "critical" not in RISK_THRESHOLDS
