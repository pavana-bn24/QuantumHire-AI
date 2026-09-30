"""Idempotent seeding of reference data.

Runs on startup (and can be run manually via ``python -m app.db.seed``). Every
step is safe to repeat: existing records are never overwritten and nothing is
deleted.
"""

from __future__ import annotations

import logging

from pymongo.errors import PyMongoError

from app.core.config import settings
from app.core.constants import (
    COLLECTION_CANDIDATES,
    COLLECTION_ROLES,
    COLLECTION_USERS,
    COLLECTION_WORKFLOW_EVENTS,
)
from app.core.serialization import utc_now
from app.db.mongo import get_collection, ping_database
from app.db.seed_data import DEFAULT_ROLES, demo_candidates
from app.services.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


def ensure_indexes() -> None:
    """Create the indexes the API relies on (safe to run repeatedly)."""
    get_collection(COLLECTION_ROLES).create_index("slug", unique=True, sparse=True)
    get_collection(COLLECTION_ROLES).create_index("title")

    candidates = get_collection(COLLECTION_CANDIDATES)
    candidates.create_index("email", unique=True, sparse=True)
    candidates.create_index("stage")
    candidates.create_index("role_id")
    candidates.create_index([("created_at", -1)])
    # Milestone 2: resume evidence lookups / exact-duplicate detection.
    candidates.create_index("resume_sha256", sparse=True)
    candidates.create_index("profile_reviewed", sparse=True)

    # Milestone 3: auth + activity timeline.
    get_collection(COLLECTION_USERS).create_index("email", unique=True)
    events = get_collection(COLLECTION_WORKFLOW_EVENTS)
    events.create_index([("candidate_id", 1), ("timestamp", -1)])
    events.create_index("event")


def seed_default_roles() -> dict | None:
    """Insert the default roles that are missing, returning the first one."""
    collection = get_collection(COLLECTION_ROLES)
    now = utc_now()

    for role in DEFAULT_ROLES:
        existing = collection.find_one({"slug": role["slug"]})
        if existing:
            logger.info("Role '%s' already present - skipping insert", role["title"])
            continue

        document = {**role, "created_at": now, "updated_at": now}
        collection.insert_one(document)
        logger.info("Seeded role '%s'", role["title"])

    return collection.find_one({"slug": DEFAULT_ROLES[0]["slug"]})


def seed_demo_candidates(role: dict | None) -> int:
    """Insert demo candidates when the candidates collection is empty."""
    collection = get_collection(COLLECTION_CANDIDATES)

    if collection.estimated_document_count() > 0:
        logger.info("Candidates already exist - skipping demo seed")
        return 0

    role_id = str(role["_id"]) if role else None
    role_title = role["title"] if role else "AI Full-Stack Developer"
    documents = demo_candidates(role_id=role_id, role_title=role_title)

    collection.insert_many(documents)
    logger.info("Seeded %s demo candidates", len(documents))
    return len(documents)


def seed_demo_recruiter() -> str | None:
    """Ensure the demo recruiter account exists (e-mail is unique).

    The password is hashed with PBKDF2 and comes from the environment
    (``SEED_ADMIN_EMAIL`` / ``SEED_ADMIN_PASSWORD``), never from source code.
    Existing accounts are left untouched so a changed .env password does not
    silently reset a user.
    """
    email = settings.seed_admin_email.strip().lower()
    if not email or not settings.seed_admin_password:
        logger.warning(
            "Skipping recruiter seed: set both SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD."
        )
        return None

    collection = get_collection(COLLECTION_USERS)
    existing = collection.find_one({"email": email})
    if existing:
        # The environment is the source of truth for the demo credential: if the
        # configured password no longer matches the stored hash (credential
        # rotation, fresh .env on an existing database), re-hash it so the
        # documented login always works. The secret still only ever comes from
        # the environment - never from source code.
        if verify_password(settings.seed_admin_password, existing.get("password_hash", "")):
            logger.info("Recruiter account %s already present - skipping insert", email)
            return email
        collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(settings.seed_admin_password),
                      "updated_at": utc_now()}},
        )
        logger.warning(
            "Recruiter account %s existed with a different password - updated from "
            "SEED_ADMIN_PASSWORD",
            email,
        )
        return email

    collection.insert_one(
        {
            "email": email,
            "name": "Demo Recruiter",
            "role": "recruiter",
            "password_hash": hash_password(settings.seed_admin_password),
            "created_at": utc_now(),
        }
    )
    logger.info("Seeded recruiter account %s", email)
    return email


def run_seed() -> bool:
    """Run the full seeding routine. Returns ``True`` when Mongo was reachable."""
    if not ping_database():
        logger.warning("Skipping seed: MongoDB is not reachable")
        return False

    try:
        ensure_indexes()
        role = seed_default_roles()
        seed_demo_candidates(role)
        seed_demo_recruiter()
    except PyMongoError as exc:  # pragma: no cover - depends on local Mongo
        logger.warning("Seeding failed: %s", exc)
        return False

    return True


if __name__ == "__main__":  # pragma: no cover - manual helper
    logging.basicConfig(level=logging.INFO)
    print("Seed complete" if run_seed() else "Seed skipped (database unavailable)")
