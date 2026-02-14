"""Comprehensive tests for lintwise.github.diff_parser."""

from __future__ import annotations

import pytest

from lintwise.core.models import FileStatus
from lintwise.github.diff_parser import parse_patch, parse_pr_files, should_skip_file


# ── Sample Patches ──────────────────────────────────────────────────────────

SIMPLE_PATCH = """\
@@ -10,5 +10,7 @@ def existing():
     pass
 
 def foo():
-    return None
+    return 42
+    # Extra line
"""

MULTI_HUNK_PATCH = """\
@@ -1,3 +1,4 @@
 import os
+import sys
 
 def a():
@@ -20,4 +21,5 @@ def b():
     pass
 
 def c():
+    # new comment
     return True
"""

ADDITION_ONLY_PATCH = """\
@@ -0,0 +1,5 @@
+def new_function():
+    \"\"\"Docstring.\"\"\"
+    x = 1
+    y = 2
+    return x + y
"""

DELETION_ONLY_PATCH = """\
@@ -1,5 +1,2 @@
-def old_function():
-    x = 1
-    y = 2
-    return x + y
+def old_function():
+    pass
"""

SINGLE_LINE_HUNK = """\
@@ -5 +5 @@ context
-old_line
+new_line
"""


# ── parse_patch ─────────────────────────────────────────────────────────────


class TestParsePatch:
    def test_simple_modification(self):
        fc = parse_patch("src/utils.py", SIMPLE_PATCH, "modified")
        assert fc.filename == "src/utils.py"
        assert fc.status == FileStatus.MODIFIED
        assert fc.additions == 2
        assert fc.deletions == 1
        assert fc.language == "python"
        assert len(fc.hunks) == 1
        assert fc.hunks[0].start_line == 10

    def test_multi_hunk(self):
        fc = parse_patch("main.py", MULTI_HUNK_PATCH, "modified")
        assert len(fc.hunks) == 2
        assert fc.hunks[0].start_line == 1
        assert fc.hunks[1].start_line == 21
        assert fc.additions == 2
        assert fc.deletions == 0

    def test_addition_only(self):
        fc = parse_patch("new_file.py", ADDITION_ONLY_PATCH, "added")
        assert fc.status == FileStatus.ADDED
        assert fc.additions == 5
        assert fc.deletions == 0
        assert len(fc.hunks) == 1
        assert fc.hunks[0].start_line == 1

    def test_deletion_remap(self):
        """GitHub uses 'removed', our model uses 'deleted'."""
        fc = parse_patch("old.py", DELETION_ONLY_PATCH, "removed")
        assert fc.status == FileStatus.DELETED

    def test_empty_patch(self):
        fc = parse_patch("binary.png", "", "modified")
        assert fc.additions == 0
        assert fc.deletions == 0
        assert fc.hunks == []
        assert fc.patch == ""

    def test_language_detection(self):
        assert parse_patch("app.js", SIMPLE_PATCH).language == "javascript"
        assert parse_patch("main.go", SIMPLE_PATCH).language == "go"
        assert parse_patch("Dockerfile", SIMPLE_PATCH).language is None

    def test_single_line_hunk(self):
        fc = parse_patch("config.py", SINGLE_LINE_HUNK, "modified")
        assert len(fc.hunks) == 1
        assert fc.hunks[0].start_line == 5
        assert fc.additions == 1
        assert fc.deletions == 1

    def test_patch_content_preserved(self):
        fc = parse_patch("test.py", SIMPLE_PATCH, "modified")
        assert fc.patch == SIMPLE_PATCH

    def test_renamed_status(self):
        fc = parse_patch("new_name.py", SIMPLE_PATCH, "renamed")
        assert fc.status == FileStatus.RENAMED


# ── should_skip_file ────────────────────────────────────────────────────────


class TestShouldSkipFile:
    def test_lockfiles_skipped(self):
        assert should_skip_file("package-lock.json") is True
        assert should_skip_file("yarn.lock") is True
        assert should_skip_file("poetry.lock") is True

    def test_source_files_not_skipped(self):
        assert should_skip_file("main.py") is False
        assert should_skip_file("index.js") is False
        assert should_skip_file("README.md") is False

    def test_nested_path_uses_basename(self):
        assert should_skip_file("frontend/package-lock.json") is True
        assert should_skip_file("src/main.py") is False

    def test_gitignore_skipped(self):
        assert should_skip_file(".gitignore") is True

    def test_license_skipped(self):
        assert should_skip_file("LICENSE") is True


# ── parse_pr_files ──────────────────────────────────────────────────────────


class TestParsePRFiles:
    def _make_file(self, filename: str, patch: str = SIMPLE_PATCH, status: str = "modified"):
        return {
            "filename": filename,
            "status": status,
            "additions": 2,
            "deletions": 1,
            "changes": 3,
            "patch": patch,
        }

    def test_basic_parsing(self):
        files = [self._make_file("main.py"), self._make_file("utils.py")]
        parsed, skipped = parse_pr_files(files)
        assert len(parsed) == 2
        assert len(skipped) == 0

    def test_skips_lockfiles(self):
        files = [
            self._make_file("main.py"),
            self._make_file("package-lock.json"),
        ]
        parsed, skipped = parse_pr_files(files)
        assert len(parsed) == 1
        assert "package-lock.json" in skipped

    def test_skips_no_patch(self):
        files = [
            self._make_file("main.py"),
            {"filename": "image.png", "status": "added", "patch": None},
        ]
        parsed, skipped = parse_pr_files(files)
        assert len(parsed) == 1
        assert "image.png" in skipped

    def test_skips_empty_patch(self):
        files = [
            self._make_file("main.py"),
            {"filename": "empty.py", "status": "modified", "patch": ""},
        ]
        parsed, skipped = parse_pr_files(files)
        assert len(parsed) == 1
        assert "empty.py" in skipped

    def test_max_files_limit(self):
        files = [self._make_file(f"file_{i}.py") for i in range(100)]
        parsed, skipped = parse_pr_files(files, max_files=5)
        assert len(parsed) == 5

    def test_max_lines_limit(self):
        # Each patch has ~6 lines; with limit of 10, only 1-2 files should fit
        files = [self._make_file(f"file_{i}.py") for i in range(10)]
        parsed, skipped = parse_pr_files(files, max_lines=10)
        assert len(parsed) < 10
        assert len(skipped) > 0

    def test_empty_input(self):
        parsed, skipped = parse_pr_files([])
        assert parsed == []
        assert skipped == []

    def test_all_skipped(self):
        files = [
            self._make_file("package-lock.json"),
            self._make_file("yarn.lock"),
        ]
        parsed, skipped = parse_pr_files(files)
        assert len(parsed) == 0
        assert len(skipped) == 2

    def test_preserves_order(self):
        files = [self._make_file(f"file_{i}.py") for i in range(5)]
        parsed, _ = parse_pr_files(files)
        assert [f.filename for f in parsed] == [f"file_{i}.py" for i in range(5)]
