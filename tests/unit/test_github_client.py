"""Comprehensive tests for lintwise.github.client — URL parsing and error handling."""

from __future__ import annotations

import pytest

from lintwise.core.exceptions import InvalidPRURLError
from lintwise.github.client import parse_pr_url


class TestParsePRUrl:
    def test_standard_url(self):
        owner, repo, num = parse_pr_url("https://github.com/octocat/hello-world/pull/42")
        assert owner == "octocat"
        assert repo == "hello-world"
        assert num == 42

    def test_url_with_trailing_slashes(self):
        owner, repo, num = parse_pr_url("https://github.com/org/repo/pull/1  ")
        assert owner == "org"
        assert repo == "repo"
        assert num == 1

    def test_url_with_http(self):
        owner, repo, num = parse_pr_url("http://github.com/org/repo/pull/99")
        assert owner == "org"
        assert num == 99

    def test_large_pr_number(self):
        owner, repo, num = parse_pr_url("https://github.com/org/repo/pull/99999")
        assert num == 99999

    def test_invalid_url_no_pull(self):
        with pytest.raises(InvalidPRURLError):
            parse_pr_url("https://github.com/org/repo/issues/1")

    def test_invalid_url_not_github(self):
        with pytest.raises(InvalidPRURLError):
            parse_pr_url("https://gitlab.com/org/repo/pull/1")

    def test_invalid_url_empty(self):
        with pytest.raises(InvalidPRURLError):
            parse_pr_url("")

    def test_invalid_url_random_text(self):
        with pytest.raises(InvalidPRURLError):
            parse_pr_url("not a url at all")

    def test_invalid_url_missing_number(self):
        with pytest.raises(InvalidPRURLError):
            parse_pr_url("https://github.com/org/repo/pull/")

    def test_hyphenated_names(self):
        owner, repo, num = parse_pr_url(
            "https://github.com/my-org/my-awesome-repo/pull/123"
        )
        assert owner == "my-org"
        assert repo == "my-awesome-repo"
        assert num == 123

    def test_underscored_names(self):
        owner, repo, num = parse_pr_url(
            "https://github.com/my_org/my_repo/pull/5"
        )
        assert owner == "my_org"
        assert repo == "my_repo"
