"""GitHub webhook handler with HMAC-SHA256 signature verification."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from lintwise.core.logging import get_logger
from lintwise.github.schemas import WebhookEvent

logger = get_logger(__name__)

# Events we act on
ACTIONABLE_EVENTS = {
    ("pull_request", "opened"),
    ("pull_request", "synchronize"),
    ("pull_request", "reopened"),
}


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header (e.g. 'sha256=abc...').
        secret: Webhook secret configured in GitHub.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def parse_webhook_event(event_type: str, payload: dict[str, Any]) -> WebhookEvent | None:
    """Parse a webhook payload into a WebhookEvent if actionable.

    Args:
        event_type: Value of X-GitHub-Event header.
        payload: Parsed JSON body.

    Returns:
        WebhookEvent if this is an actionable PR event, None otherwise.
    """
    action = payload.get("action", "")

    if (event_type, action) not in ACTIONABLE_EVENTS:
        logger.debug("ignoring_webhook", event_type=event_type, action=action)
        return None

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    sender = payload.get("sender", {})

    # Extract owner from repo.full_name ("owner/repo")
    full_name = repo.get("full_name", "/")
    parts = full_name.split("/", 1)
    owner = parts[0] if len(parts) >= 1 else ""
    repo_name = parts[1] if len(parts) >= 2 else ""

    event = WebhookEvent(
        action=action,
        sender=sender.get("login", ""),
        repo_owner=owner,
        repo_name=repo_name,
        pr_number=pr.get("number", 0),
    )

    logger.info(
        "actionable_webhook",
        action=action,
        repo=full_name,
        pr_number=event.pr_number,
        sender=event.sender,
    )

    return event
