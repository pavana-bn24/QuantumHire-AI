"""Outbound + inbound recruitment webhooks.

Outbound
--------
``dispatch_webhook(event, payload)`` POSTs JSON to ``EXTERNAL_WEBHOOK_URL``.
When the URL is unset or delivery fails the event is **simulated**: a log line
plus a ``{delivery: "simulated"|"failed"}`` result that callers can persist on
the workflow event. The recruitment workflow never blocks on a third party.

Inbound
-------
``POST /api/integrations/recruitment-webhook`` validates an incoming event and
answers 202; tests use it to prove the integration surface works without any
external service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookDeliveryError(Exception):
    """Outbound webhook delivery failed (message safe for API responses)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def dispatch_webhook(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Deliver ``event``/``payload`` to the configured webhook URL.

    Returns a delivery report::

        {"delivery": "delivered", "status_code": 200}
        {"delivery": "simulated", "reason": "EXTERNAL_WEBHOOK_URL not set"}
        {"delivery": "failed", "reason": "..."}   # never raises
    """
    url = (settings.external_webhook_url or "").strip()
    if not url:
        logger.info("Webhook '%s' simulated (EXTERNAL_WEBHOOK_URL not set): %s", event, payload)
        return {"delivery": "simulated", "reason": "EXTERNAL_WEBHOOK_URL not set"}

    body = {"event": event, "payload": payload}
    try:
        response = httpx.post(url, json=body, timeout=settings.webhook_timeout_seconds)
    except httpx.TimeoutException:
        logger.warning("Webhook '%s' timed out after %ss", event, settings.webhook_timeout_seconds)
        return {"delivery": "failed", "reason": "timeout"}
    except httpx.HTTPError as exc:
        logger.warning("Webhook '%s' unreachable: %s", event, exc)
        return {"delivery": "failed", "reason": f"unreachable: {exc}"}

    if response.status_code >= 400:
        logger.warning("Webhook '%s' returned HTTP %s", event, response.status_code)
        return {"delivery": "failed", "reason": f"HTTP {response.status_code}"}

    return {"delivery": "delivered", "status_code": response.status_code}
