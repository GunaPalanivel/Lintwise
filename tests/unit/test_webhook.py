"""Comprehensive tests for lintwise.github.webhook."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from lintwise.github.webhook import (
    ACTIONABLE_EVENTS,
    parse_webhook_event,
    verify_signature,
)


# ── Signature Verification ──────────────────────────────────────────────────


class TestVerifySignature:
    SECRET = "test_webhook_secret_123"

    def _sign(self, payload: bytes) -> str:
        sig = hmac.new(self.SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    def test_valid_signature(self):
        payload = b'{"action": "opened"}'
        sig = self._sign(payload)
        assert verify_signature(payload, sig, self.SECRET) is True

    def test_invalid_signature(self):
        payload = b'{"action": "opened"}'
        assert verify_signature(payload, "sha256=invalid_hex", self.SECRET) is False

    def test_tampered_payload(self):
        original = b'{"action": "opened"}'
        sig = self._sign(original)
        tampered = b'{"action": "closed"}'
        assert verify_signature(tampered, sig, self.SECRET) is False

    def test_missing_sha256_prefix(self):
        payload = b'{"action": "opened"}'
        sig = hmac.new(self.SECRET.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_signature(payload, sig, self.SECRET) is False  # No "sha256=" prefix

    def test_wrong_secret(self):
        payload = b'{"action": "opened"}'
        sig = self._sign(payload)
        assert verify_signature(payload, sig, "wrong_secret") is False

    def test_empty_payload(self):
        payload = b""
        sig = self._sign(payload)
        assert verify_signature(payload, sig, self.SECRET) is True

    def test_large_payload(self):
        payload = b"x" * 100_000
        sig = self._sign(payload)
        assert verify_signature(payload, sig, self.SECRET) is True


# ── Webhook Event Parsing ───────────────────────────────────────────────────


def _build_pr_payload(action: str = "opened", pr_number: int = 42) -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": pr_number,
            "title": "Test PR",
            "head": {"ref": "feature", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
        },
        "repository": {
            "full_name": "testorg/testrepo",
            "name": "testrepo",
        },
        "sender": {
            "login": "testuser",
        },
    }


class TestParseWebhookEvent:
    def test_pr_opened(self):
        event = parse_webhook_event("pull_request", _build_pr_payload("opened"))
        assert event is not None
        assert event.action == "opened"
        assert event.repo_owner == "testorg"
        assert event.repo_name == "testrepo"
        assert event.pr_number == 42
        assert event.sender == "testuser"

    def test_pr_synchronize(self):
        event = parse_webhook_event("pull_request", _build_pr_payload("synchronize"))
        assert event is not None
        assert event.action == "synchronize"

    def test_pr_reopened(self):
        event = parse_webhook_event("pull_request", _build_pr_payload("reopened"))
        assert event is not None
        assert event.action == "reopened"

    def test_pr_closed_ignored(self):
        event = parse_webhook_event("pull_request", _build_pr_payload("closed"))
        assert event is None

    def test_pr_edited_ignored(self):
        event = parse_webhook_event("pull_request", _build_pr_payload("edited"))
        assert event is None

    def test_non_pr_event_ignored(self):
        payload = {"action": "created", "issue": {"number": 1}}
        event = parse_webhook_event("issues", payload)
        assert event is None

    def test_push_event_ignored(self):
        payload = {"ref": "refs/heads/main"}
        event = parse_webhook_event("push", payload)
        assert event is None

    def test_missing_fields_handled(self):
        """Gracefully handle payloads with missing nested fields."""
        minimal = {"action": "opened"}
        event = parse_webhook_event("pull_request", minimal)
        assert event is not None
        assert event.pr_number == 0
        assert event.repo_owner == ""

    def test_actionable_events_set(self):
        """Ensure all expected event types are registered."""
        assert ("pull_request", "opened") in ACTIONABLE_EVENTS
        assert ("pull_request", "synchronize") in ACTIONABLE_EVENTS
        assert ("pull_request", "reopened") in ACTIONABLE_EVENTS
        assert len(ACTIONABLE_EVENTS) == 3
