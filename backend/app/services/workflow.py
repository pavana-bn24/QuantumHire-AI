"""Workflow event log: append-only automation trace per candidate.

Every automation trigger (upload, approvals, stage moves, webhook deliveries)
records a :class:`WorkflowEvent` here. The Activity tab in the UI reads it via
``GET /api/candidates/{id}/events``.
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from app.core.constants import COLLECTION_WORKFLOW_EVENTS
from app.core.serialization import parse_object_id, serialize_document, utc_now
from app.db.mongo import get_collection

logger = logging.getLogger(__name__)

#: Events the UI and tests rely on; keep names stable.
EVENT_RESUME_UPLOADED = "resume_uploaded"
EVENT_PROFILE_APPROVED = "profile_approved"
EVENT_EVALUATION_GENERATED = "evaluation_generated"
EVENT_EVALUATION_UPDATED = "evaluation_updated"
EVENT_EVALUATION_APPROVED = "evaluation_approved"
EVENT_SKILL_TEST_GENERATED = "skill_test_generated"
EVENT_SKILL_TEST_UPDATED = "skill_test_updated"
EVENT_SKILL_TEST_APPROVED = "skill_test_approved"
EVENT_STAGE_CHANGED = "stage_changed"
EVENT_CANDIDATE_CREATED = "candidate_created"
EVENT_WEBHOOK_DELIVERED = "webhook_delivered"
EVENT_WEBHOOK_SIMULATED = "webhook_simulated"
EVENT_WEBHOOK_FAILED = "webhook_failed"


def record_event(
    candidate_id: str,
    event: str,
    *,
    actor: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Append one workflow event and return the serialised document.

    Failures are logged, never raised: recording history must not break the
    business operation that triggered it.
    """
    document = {
        "candidate_id": candidate_id,
        "event": event,
        "actor": actor,
        "timestamp": utc_now(),
        "metadata": _sanitize(metadata or {}),
    }

    try:
        result = get_collection(COLLECTION_WORKFLOW_EVENTS).insert_one(document)
        document["_id"] = result.inserted_id
    except Exception as exc:  # pragma: no cover - depends on local Mongo
        logger.warning("Failed to record workflow event '%s': %s", event, exc)
        return {"candidate_id": candidate_id, "event": event, "actor": actor,
                "timestamp": document["timestamp"].isoformat(), "metadata": document["metadata"], "id": ""}

    return serialize_document(document) or {}


def list_events(candidate_id: str, limit: int = 100) -> list[dict]:
    """Workflow events for a candidate, newest first."""
    if parse_object_id(candidate_id) is None:
        return []
    documents = (
        get_collection(COLLECTION_WORKFLOW_EVENTS)
        .find({"candidate_id": candidate_id})
        .sort("timestamp", -1)
        .limit(limit)
    )
    return [serialize_document(doc) for doc in documents]


def _sanitize(metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep metadata JSON-safe (ObjectIds -> str, datetimes -> isoformat)."""
    from datetime import datetime

    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, ObjectId):
            clean[key] = str(value)
        elif isinstance(value, datetime):
            clean[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        elif isinstance(value, (list, tuple)):
            clean[key] = [_sanitize_one(item) for item in value]
        elif isinstance(value, dict):
            clean[key] = _sanitize(value)
        else:
            clean[key] = str(value)
    return clean


def _sanitize_one(value: Any) -> Any:
    from datetime import datetime

    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return _sanitize(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
