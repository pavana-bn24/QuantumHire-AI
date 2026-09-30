"""Small serialisation helpers shared across the API layer."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def to_str_id(value: Any) -> str:
    """Convert a Mongo ``ObjectId`` (or any value) into a JSON-safe string id."""
    if isinstance(value, ObjectId):
        return str(value)
    return "" if value is None else str(value)


def serialize_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a copy of a Mongo document with ``_id`` exposed as ``id``."""
    if document is None:
        return None

    serialized = dict(document)
    raw_id = serialized.pop("_id", None)
    serialized["id"] = to_str_id(raw_id)

    for key, value in list(serialized.items()):
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()

    return serialized


def serialize_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialise a list of Mongo documents."""
    return [serialize_document(document) or {} for document in documents]


def parse_object_id(value: str) -> ObjectId | None:
    """Safely parse a 24-char hex string into an ``ObjectId``."""
    if not value or not ObjectId.is_valid(value):
        return None
    return ObjectId(value)
