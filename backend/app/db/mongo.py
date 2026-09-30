"""MongoDB connection handling built on PyMongo.

A single ``MongoClient`` is created during the FastAPI lifespan and reused for
the whole process. Connection failures are logged but never crash the API, so
``/api/health`` keeps answering even when the database is unavailable.
"""

from __future__ import annotations

import logging

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_connected: bool = False


def connect_to_mongo() -> MongoClient:
    """Create (once) and return the shared ``MongoClient``."""
    global _client, _connected

    if _client is None:
        _client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            tz_aware=True,
        )

    try:
        _client.admin.command("ping")
        _connected = True
        logger.info(
            "Connected to MongoDB database '%s' at %s",
            settings.mongodb_db_name,
            _client.address,
        )
    except PyMongoError as exc:  # pragma: no cover - depends on local Mongo
        _connected = False
        logger.warning("MongoDB is not reachable yet: %s", exc)

    return _client


def close_mongo_connection() -> None:
    """Close the shared client on application shutdown."""
    global _client, _connected

    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")

    _client = None
    _connected = False


def get_client() -> MongoClient:
    """Return the shared client, connecting lazily if needed."""
    if _client is None:
        return connect_to_mongo()
    return _client


def get_database() -> Database:
    """Return the application database."""
    return get_client()[settings.mongodb_db_name]


def get_collection(name: str):
    """Return a collection from the application database."""
    return get_database()[name]


def mongo_is_connected() -> bool:
    """Whether the last ping succeeded."""
    return _connected


def ping_database() -> bool:
    """Actively ping the database; returns ``True`` when reachable."""
    global _connected

    try:
        get_client().admin.command("ping")
        _connected = True
    except PyMongoError as exc:  # pragma: no cover - depends on local Mongo
        _connected = False
        logger.warning("MongoDB ping failed: %s", exc)

    return _connected
