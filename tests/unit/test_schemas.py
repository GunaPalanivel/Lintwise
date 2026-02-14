"""Comprehensive tests for lintwise.github.schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lintwise.github.schemas import (
    GitHubFile,
    GitHubPRBase,
    GitHubPRHead,
    GitHubPullRequest,
    GitHubReviewComment,
    GitHubReviewRequest,
    GitHubUser,
    WebhookEvent,
)


class TestGitHubUser:
    def test_creation(self):
        user = GitHubUser(login="octocat")
        assert user.login == "octocat"
        assert user.avatar_url == ""

    def test_with_avatar(self):
        user = GitHubUser(login="octocat", avatar_url="https://example.com/avatar.png")
        assert user.avatar_url == "https://example.com/avatar.png"


class TestGitHubPRHead:
    def test_creation(self):
        head = GitHubPRHead(ref="feature-branch", sha="abc123def456")
        assert head.ref == "feature-branch"
        assert head.sha == "abc123def456"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            GitHubPRHead(ref="branch")


class TestGitHubPullRequest:
    def test_creation(self):
        pr = GitHubPullRequest(
            number=42,
            title="Test PR",
            head=GitHubPRHead(ref="feature", sha="abc"),
            base=GitHubPRBase(ref="main", sha="def"),
        )
        assert pr.number == 42
        assert pr.title == "Test PR"
        assert pr.state == "open"

    def test_defaults(self):
        pr = GitHubPullRequest(
            number=1,
            title="T",
            head=GitHubPRHead(ref="f", sha="a"),
            base=GitHubPRBase(ref="m", sha="b"),
        )
        assert pr.body is None
        assert pr.state == "open"
        assert pr.user is None
        assert pr.html_url == ""
        assert pr.diff_url == ""

    def test_roundtrip(self):
        pr = GitHubPullRequest(
            number=42,
            title="Test",
            body="Description",
            head=GitHubPRHead(ref="f", sha="a"),
            base=GitHubPRBase(ref="m", sha="b"),
        )
        data = pr.model_dump()
        restored = GitHubPullRequest.model_validate(data)
        assert restored.number == 42
        assert restored.body == "Description"


class TestGitHubFile:
    def test_creation(self):
        f = GitHubFile(filename="main.py", status="modified")
        assert f.filename == "main.py"
        assert f.status == "modified"

    def test_defaults(self):
        f = GitHubFile(filename="t.py", status="added")
        assert f.additions == 0
        assert f.deletions == 0
        assert f.changes == 0
        assert f.patch is None
        assert f.previous_filename is None
        assert f.sha == ""

    def test_with_patch(self):
        f = GitHubFile(
            filename="t.py",
            status="modified",
            patch="@@ -1,3 +1,4 @@\n+new line",
            additions=1,
        )
        assert f.patch is not None
        assert f.additions == 1

    def test_renamed(self):
        f = GitHubFile(
            filename="new_name.py",
            status="renamed",
            previous_filename="old_name.py",
        )
        assert f.previous_filename == "old_name.py"


class TestGitHubReviewComment:
    def test_creation(self):
        c = GitHubReviewComment(path="main.py", body="Fix this")
        assert c.path == "main.py"
        assert c.body == "Fix this"
        assert c.line is None
        assert c.side == "RIGHT"

    def test_with_line(self):
        c = GitHubReviewComment(path="main.py", line=42, body="Issue here")
        assert c.line == 42


class TestGitHubReviewRequest:
    def test_defaults(self):
        r = GitHubReviewRequest()
        assert r.event == "COMMENT"
        assert r.body == ""
        assert r.comments == []

    def test_with_comments(self):
        r = GitHubReviewRequest(
            event="REQUEST_CHANGES",
            body="Please fix these issues.",
            comments=[
                GitHubReviewComment(path="a.py", line=1, body="Fix A"),
                GitHubReviewComment(path="b.py", line=2, body="Fix B"),
            ],
        )
        assert len(r.comments) == 2
        assert r.event == "REQUEST_CHANGES"


class TestWebhookEvent:
    def test_creation(self):
        e = WebhookEvent(action="opened")
        assert e.action == "opened"
        assert e.sender == ""
        assert e.repo_owner == ""
        assert e.repo_name == ""
        assert e.pr_number == 0

    def test_full(self):
        e = WebhookEvent(
            action="synchronize",
            sender="octocat",
            repo_owner="org",
            repo_name="repo",
            pr_number=99,
        )
        assert e.sender == "octocat"
        assert e.pr_number == 99
