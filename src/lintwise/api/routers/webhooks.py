"""Webhook endpoint — receives GitHub events."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lintwise.api.schemas import ErrorResponse
from lintwise.core.config import Settings
from lintwise.core.logging import get_logger
from lintwise.github.webhook import parse_webhook_event, verify_signature

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

_settings: Settings | None = None


def configure_webhook_router(settings: Settings) -> None:
    """Inject settings dependency."""
    global _settings
    _settings = settings


@router.post("/github", status_code=202)
async def github_webhook(request: Request):
    """Receive and validate GitHub webhook events.

    Currently handles pull_request events (opened, synchronize, reopened).
    Returns 202 Accepted for valid events.
    """
    # Read raw body for signature verification
    body = await request.body()

    # Verify webhook signature if secret is configured
    if _settings and _settings.github_webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        secret = _settings.github_webhook_secret.get_secret_value()

        if not verify_signature(body, signature, secret):
            logger.warning("webhook_signature_invalid")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the event
    event_type = request.headers.get("X-GitHub-Event", "")

    import json

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = parse_webhook_event(event_type, payload)

    if event is None:
        logger.info("webhook_ignored", event_type=event_type)
        return {"status": "ignored", "message": "Event type not actionable"}

    logger.info(
        "webhook_received",
        action=event.action,
        repo=f"{event.repo_owner}/{event.repo_name}",
        pr=event.pr_number,
        sender=event.sender,
    )

    # In a production system, this would enqueue an async job.
    # For the prototype, we acknowledge and log.
    return {
        "status": "accepted",
        "pr": f"{event.repo_owner}/{event.repo_name}#{event.pr_number}",
        "action": event.action,
    }
