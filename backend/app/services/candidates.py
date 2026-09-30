"""Candidate persistence helpers: duplicate detection and document building."""

from __future__ import annotations

from app.core.constants import COLLECTION_CANDIDATES
from app.core.serialization import utc_now
from app.db.mongo import get_collection
from app.models.profile import CandidateProfile
from app.services.resume import PdfTextResult

DUPLICATE_EMAIL = "email"
DUPLICATE_RESUME_FILE = "resume_file"


def normalize_email(value: str | None) -> str | None:
    """Lower-case and trim an e-mail address."""
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def find_duplicate(
    email: str | None = None, resume_sha256: str | None = None
) -> tuple[str | None, dict | None]:
    """Look for an existing candidate by e-mail, then by exact resume content.

    Returns ``(reason, document)`` - ``(None, None)`` when the candidate is new.
    """
    collection = get_collection(COLLECTION_CANDIDATES)

    normalized = normalize_email(email)
    if normalized:
        existing = collection.find_one({"email": normalized})
        if existing:
            return DUPLICATE_EMAIL, existing

    if resume_sha256:
        existing = collection.find_one({"resume_sha256": resume_sha256})
        if existing:
            return DUPLICATE_RESUME_FILE, existing

    return None, None


def duplicate_message(reason: str, existing: dict) -> str:
    """Human-readable 409 explanation, including how to reach the existing record."""
    candidate_id = str(existing.get("_id", ""))
    name = existing.get("name") or "an existing candidate"
    stage = existing.get("stage") or "unknown stage"

    if reason == DUPLICATE_RESUME_FILE:
        return (
            f"This exact resume file was already uploaded for {name} (id: {candidate_id}, "
            f"stage: {stage}). Open that candidate instead of creating a duplicate."
        )

    return (
        f"A candidate with this email already exists: {name} (id: {candidate_id}, "
        f"stage: {stage}). Update that record instead of creating a duplicate."
    )


def profile_top_level_fields(profile: CandidateProfile) -> dict:
    """Top-level candidate fields derived from the approved/extracted profile.

    Only the fields the existing candidate form already exposes are mirrored here
    so the rest of the app (list, dashboard, filters) keeps working unchanged.
    """
    fields: dict = {}

    if profile.name:
        fields["name"] = profile.name
    email = normalize_email(profile.email)
    if email:
        fields["email"] = email
    if profile.phone:
        fields["phone"] = profile.phone

    # Skills drive the existing search/filter UI.
    merged: list[str] = []
    for value in [*profile.skills, *profile.technologies]:
        if value and value not in merged:
            merged.append(value)
    if merged:
        fields["skills"] = merged

    return fields


def build_resume_candidate_document(
    *,
    profile: CandidateProfile,
    resume: PdfTextResult,
    resume_filename: str,
    resume_content_type: str | None,
    resume_size_bytes: int,
    resume_sha256: str,
    role_id: str | None,
    role_title: str | None,
    stage: str,
    source: str,
    provider: str,
    model: str,
    warnings: list[str],
) -> dict:
    """Assemble the MongoDB document for a newly uploaded resume candidate.

    Existing seeded candidates are unaffected: all resume fields are additive and
    every reader defaults them when absent.
    """
    now = utc_now()
    document = {
        "name": profile.name or resume_filename.rsplit(".", 1)[0] or "Unnamed Candidate",
        "phone": profile.phone,
        "role_id": role_id,
        "role_title": role_title,
        "stage": stage,
        "source": source,
        "location": None,
        "experience_years": None,
        "skills": profile_top_level_fields(profile).get("skills", []),
        "notes": None,
        # --- resume evidence (milestone 2) ---------------------------------
        "resume_filename": resume_filename,
        "resume_text": resume.text,
        "resume_content_type": resume_content_type,
        "resume_size_bytes": resume_size_bytes,
        "resume_sha256": resume_sha256,
        "resume_page_count": resume.page_count,
        "resume_char_count": resume.char_count,
        "resume_word_count": resume.word_count,
        "uploaded_at": now,
        "extracted_at": now,
        "extracted_profile": profile.model_dump(),
        "original_extracted_profile": profile.model_dump(),
        "ai_provider": provider,
        "ai_model": model,
        "extraction_warnings": warnings,
        # A recruiter must explicitly approve before this counts as evidence.
        "profile_reviewed": False,
        "profile_reviewed_at": None,
        # --- reserved for milestone 3 (evaluation / RAG / skill tests) ------
        "ai_summary": None,
        "scores": {},
        "created_at": now,
        "updated_at": now,
    }

    # Email is optional on uploads. The field is omitted entirely (rather than set
    # to null/"") so the sparse unique index still allows several candidates whose
    # resume did not state an address.
    email = normalize_email(profile.email)
    if email:
        document["email"] = email

    return document
