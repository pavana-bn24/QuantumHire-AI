"""Integration endpoints: outbound dispatch status + inbound webhook receiver.

Inbound: ``POST /api/integrations/recruitment-webhook`` accepts an event from
an external system (ATS, scheduler, etc.), validates it, records it on the
candidate timeline when a ``candidate_id`` is supplied, and answers 202.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import require_database, require_recruiter
from app.core.config import settings
from app.services.webhooks import dispatch_webhook
from app.services.workflow import EVENT_WEBHOOK_DELIVERED, EVENT_WEBHOOK_FAILED, record_event

router = APIRouter(
    prefix="/integrations", tags=["integrations"], dependencies=[Depends(require_database)]
)


class InboundWebhookPayload(BaseModel):
    """Event delivered by an external recruitment system."""

    model_config = ConfigDict(extra="forbid")

    event: str = Field(..., min_length=3, max_length=100, description="Event name")
    candidate_id: str | None = Field(default=None, description="Candidate to attach the event to")
    source: str = Field(default="external", description="Producing system")
    data: dict = Field(default_factory=dict)


@router.get("/webhook-config", summary="Outbound webhook configuration")
def webhook_config() -> dict:
    """Whether an outbound webhook URL is configured (never exposes the URL)."""
    url = (settings.external_webhook_url or "").strip()
    return {"configured": bool(url), "timeout_seconds": settings.webhook_timeout_seconds}


@router.post(
    "/recruitment-webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive an external recruitment event",
)
def receive_webhook(payload: InboundWebhookPayload) -> dict:
    """Validate and record an inbound event (202 Accepted)."""
    metadata = {"source": payload.source, "event": payload.event, **payload.data}

    if payload.candidate_id:
        record_event(
            payload.candidate_id,
            f"external_{payload.event}",
            actor=payload.source,
            metadata=metadata,
        )

    return {
        "accepted": True,
        "event": payload.event,
        "source": payload.source,
        "recorded_for": payload.candidate_id,
    }


@router.post("/webhook/test", summary="Send a test outbound webhook")
def test_webhook(user: dict = Depends(require_recruiter)) -> dict:
    """Fire a simulated ping at the configured outbound webhook URL."""
    report = dispatch_webhook("test_ping", {"requested_by": user["email"]})
    return {"event": "test_ping", **report}
