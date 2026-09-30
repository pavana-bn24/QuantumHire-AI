"""Candidate endpoints.

Milestone 2 adds the resume pipeline on top of the existing CRUD surface:

* ``POST /api/candidates/upload``       - PDF -> text -> structured profile
* ``GET  /api/candidates/{id}``         - now returns the extracted evidence
* ``PUT  /api/candidates/{id}/profile`` - recruiter-reviewed/approved profile

Uploaded bytes are never written to disk and never served back, so resumes are
not publicly reachable. AI evaluation, RAG and skill-test generation remain out
of scope for this milestone.
"""

import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pymongo.errors import DuplicateKeyError

from app.api.deps import require_database, require_recruiter
from app.core.constants import COLLECTION_CANDIDATES, COLLECTION_ROLES, PIPELINE_STAGES, PipelineStage
from app.core.serialization import parse_object_id, serialize_document, utc_now
from app.db.mongo import get_collection
from app.models import (
    Candidate,
    CandidateCreate,
    CandidateDetail,
    CandidateProfile,
    ProfileUpdateRequest,
    ResumeExtractionInfo,
    ResumeUploadResponse,
)
from app.services.candidates import (
    build_resume_candidate_document,
    duplicate_message,
    find_duplicate,
    normalize_email,
    profile_top_level_fields,
)
from app.services.extraction import (
    ExtractionFailedError,
    ExtractionUnavailableError,
    extract_candidate_profile,
)
from app.services.resume import (
    ResumeError,
    content_hash,
    detect_prompt_injection,
    extract_text_from_pdf,
    validate_resume_upload,
)
from app.services.workflow import (
    EVENT_CANDIDATE_CREATED,
    EVENT_PROFILE_APPROVED,
    EVENT_RESUME_UPLOADED,
    EVENT_STAGE_CHANGED,
    record_event,
)

router = APIRouter(
    prefix="/candidates", tags=["candidates"], dependencies=[Depends(require_database)]
)


def candidate_response(document: dict, *, detail: bool = False) -> dict:
    """Serialise a candidate document, deriving UI-friendly derived fields.

    ``has_resume`` lets the list view show a resume badge without shipping the
    full extracted text in list responses.
    """
    data = serialize_document(document) or {}
    data["has_resume"] = bool(document.get("resume_filename") or document.get("resume_text"))
    data["profile_reviewed"] = bool(document.get("profile_reviewed"))

    if not detail:
        data.pop("resume_text", None)

    return data


def _ensure_known_stage(stage: str) -> None:
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown stage '{stage}'. Expected one of: {', '.join(PIPELINE_STAGES)}",
        )


@router.get("", response_model=list[Candidate], summary="List candidates")
def list_candidates(
    stage: str | None = Query(default=None, description="Filter by pipeline stage"),
    role_id: str | None = Query(default=None, description="Filter by role id"),
    search: str | None = Query(default=None, description="Case-insensitive name/skill search"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    user: dict = Depends(require_recruiter),
) -> list[dict]:
    """Return candidates filtered by stage, role or free-text search."""
    query: dict = {}

    if stage:
        _ensure_known_stage(stage)
        query["stage"] = stage

    if role_id:
        query["role_id"] = role_id

    if search:
        pattern = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}},
            {"skills": {"$regex": pattern, "$options": "i"}},
        ]

    # resume_text is large and only needed on the detail view.
    documents = (
        get_collection(COLLECTION_CANDIDATES)
        .find(query, {"resume_text": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [candidate_response(document) for document in documents]


def _resume_error_response(exc: ResumeError) -> HTTPException:
    """Turn a resume failure into a clear HTTP error (message + machine code)."""
    return HTTPException(
        status_code=exc.http_status,
        detail=exc.message,
        headers={"X-Error-Code": exc.code},
    )


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF resume and extract a structured profile",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume (text-based)"),
    role_id: str | None = Form(default=None, description="Optional role to attach the candidate to"),
    stage: str = Form(default=PIPELINE_STAGES[0], description="Initial pipeline stage"),
    source: str = Form(default="Resume Upload"),
    user: dict = Depends(require_recruiter),
) -> dict:
    """Validate -> extract text -> structure profile -> create candidate.

    The uploaded bytes stay in memory: nothing is written to disk or exposed via a
    static route. Only the extracted text and the structured profile are stored.

    Errors are explicit rather than silent: 415 for a non-PDF, 413 when too large,
    422 for corrupt/scanned/empty PDFs, 409 for duplicates, 503/502 when the AI
    provider is unavailable or fails.
    """
    _ensure_known_stage(stage)
    data = await file.read()

    try:
        resume_filename = validate_resume_upload(file.filename, file.content_type, data)
        resume = extract_text_from_pdf(data)
    except ResumeError as exc:
        raise _resume_error_response(exc) from exc

    injection_flags = detect_prompt_injection(resume.text)

    try:
        extraction = extract_candidate_profile(resume.text)
    except ExtractionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        ) from exc
    except ExtractionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        ) from exc

    resume_sha256 = content_hash(data)
    reason, existing = find_duplicate(extraction.profile.email, resume_sha256)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=duplicate_message(reason, existing)
        )

    role_title: str | None = None
    linked_role_id: str | None = None
    if role_id:
        role_object_id = parse_object_id(role_id)
        role = (
            get_collection(COLLECTION_ROLES).find_one({"_id": role_object_id})
            if role_object_id
            else None
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_id}' was not found, so the resume was not imported.",
            )
        role_title = role.get("title")
        linked_role_id = str(role["_id"])

    warnings = list(extraction.warnings)
    if injection_flags:
        warnings.append(
            "Possible prompt injection was detected in the resume text and ignored "
            f"(treated as untrusted data): {', '.join(injection_flags)}. "
            "Verify the extracted profile manually before approving."
        )

    document = build_resume_candidate_document(
        profile=extraction.profile,
        resume=resume,
        resume_filename=resume_filename,
        resume_content_type=file.content_type,
        resume_size_bytes=len(data),
        resume_sha256=resume_sha256,
        role_id=linked_role_id,
        role_title=role_title,
        stage=stage,
        source=source,
        provider=extraction.provider,
        model=extraction.model,
        warnings=warnings,
    )

    try:
        inserted = get_collection(COLLECTION_CANDIDATES).insert_one(document)
    except DuplicateKeyError as exc:  # race between the check and the insert
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A candidate with the same email or resume was created moments ago.",
        ) from exc

    document["_id"] = inserted.inserted_id
    candidate_id = str(inserted.inserted_id)

    # Automation: a fresh upload lands in the recruiter's review queue.
    record_event(
        candidate_id,
        EVENT_RESUME_UPLOADED,
        actor=user["email"],
        metadata={
            "filename": resume_filename,
            "stage": stage,
            "role_id": linked_role_id,
            "triggered_by": "upload",
        },
    )

    return {
        "candidate_id": candidate_id,
        "candidate": candidate_response(document, detail=True),
        "extracted_profile": extraction.profile,
        "extraction": ResumeExtractionInfo(
            provider=extraction.provider,
            model=extraction.model,
            page_count=resume.page_count,
            char_count=resume.char_count,
            word_count=resume.word_count,
            warnings=warnings,
            prompt_injection_flags=injection_flags,
            extracted_at=document["extracted_at"].isoformat(),
        ),
    }


@router.get("/{candidate_id}", response_model=CandidateDetail, summary="Get a candidate")
def get_candidate(candidate_id: str, user: dict = Depends(require_recruiter)) -> dict:
    """Return a single candidate, including the extracted resume evidence."""
    object_id = parse_object_id(candidate_id)
    document = (
        get_collection(COLLECTION_CANDIDATES).find_one({"_id": object_id})
        if object_id
        else None
    )

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    return candidate_response(document, detail=True)


@router.put(
    "/{candidate_id}/profile",
    response_model=CandidateDetail,
    summary="Save the recruiter-reviewed candidate profile",
)
def update_candidate_profile(
    candidate_id: str,
    payload: ProfileUpdateRequest,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Persist the reviewed/edited profile and mark the evidence as approved.

    Until this is called with ``reviewed=true`` the candidate's profile is only a
    machine suggestion - it is not treated as approved evidence.
    """
    object_id = parse_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid candidate id")

    collection = get_collection(COLLECTION_CANDIDATES)
    existing = collection.find_one({"_id": object_id})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    profile_payload = payload.model_dump(exclude={"reviewed"})
    profile = CandidateProfile.model_validate(profile_payload)

    updates: dict = {
        "extracted_profile": profile.model_dump(),
        "profile_reviewed": payload.reviewed,
        "profile_reviewed_at": utc_now() if payload.reviewed else None,
        "profile_updated_at": utc_now(),
        "updated_at": utc_now(),
    }
    updates.update(profile_top_level_fields(profile))

    # Automation: approving the profile moves a brand-new candidate into the
    # review stage so they leave the "New" backlog automatically.
    previously_reviewed = bool(existing.get("profile_reviewed"))
    previous_stage = existing.get("stage")
    if payload.reviewed and not previously_reviewed and previous_stage == PipelineStage.NEW.value:
        updates["stage"] = PipelineStage.UNDER_REVIEW.value

    # Guard the unique e-mail index before writing.
    normalized_email = normalize_email(profile.email)
    if normalized_email:
        clash = collection.find_one({"email": normalized_email, "_id": {"$ne": object_id}})
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Email '{normalized_email}' already belongs to another candidate "
                    f"({clash.get('name')}, id: {clash.get('_id')}). Merge or remove that "
                    "record before approving this profile."
                ),
            )

    updated = None
    try:
        updated = collection.find_one_and_update(
            {"_id": object_id}, {"$set": updates}, return_document=True
        )
    except DuplicateKeyError as exc:  # raced with another write on the unique e-mail index
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Another candidate already uses '{normalized_email}'. Merge or remove "
                "that record before approving this profile."
            ),
        ) from exc

    if updated is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    if payload.reviewed and not previously_reviewed:
        record_event(
            candidate_id,
            EVENT_PROFILE_APPROVED,
            actor=user["email"],
            metadata={
                "stage": updates.get("stage", previous_stage),
                "triggered_by": "recruiter",
            },
        )

    return candidate_response(updated, detail=True)


@router.post(
    "", response_model=Candidate, status_code=status.HTTP_201_CREATED, summary="Create a candidate"
)
def create_candidate(payload: CandidateCreate, user: dict = Depends(require_recruiter)) -> dict:
    """Add a candidate to the pipeline (defaults to the 'New' stage)."""
    if payload.stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown stage '{payload.stage}'. Expected one of: {', '.join(PIPELINE_STAGES)}",
        )

    # Normalise first: "  User@X.com " and "user@x.com" must be the same person.
    normalized_email = normalize_email(payload.email)
    if normalized_email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty email address is required to create a candidate.",
        )

    now = utc_now()
    document = {
        **payload.model_dump(),
        "email": normalized_email,
        "phone": None,
        "resume_file": None,
        "ai_summary": None,
        "scores": {},
        "created_at": now,
        "updated_at": now,
    }

    collection = get_collection(COLLECTION_CANDIDATES)
    if collection.find_one({"email": normalized_email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A candidate with email '{normalized_email}' already exists",
        )

    try:
        result = collection.insert_one(document)
    except DuplicateKeyError as exc:  # raced between the check and the insert
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A candidate with email '{normalized_email}' already exists",
        ) from exc

    document["_id"] = result.inserted_id
    record_event(
        str(result.inserted_id),
        EVENT_CANDIDATE_CREATED,
        actor=user["email"],
        metadata={"stage": document.get("stage"), "source": document.get("source")},
    )
    return candidate_response(document)


@router.patch("/{candidate_id}/stage", response_model=Candidate, summary="Move a candidate")
def update_candidate_stage(
    candidate_id: str,
    stage: str = Query(..., description="Target pipeline stage"),
    user: dict = Depends(require_recruiter),
) -> dict:
    """Move a candidate to another pipeline stage."""
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown stage '{stage}'. Expected one of: {', '.join(PIPELINE_STAGES)}",
        )

    object_id = parse_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid candidate id")

    collection = get_collection(COLLECTION_CANDIDATES)
    existing = collection.find_one({"_id": object_id})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    previous_stage = existing.get("stage")
    result = collection.find_one_and_update(
        {"_id": object_id},
        {"$set": {"stage": stage, "updated_at": utc_now()}},
        return_document=True,
    )

    if previous_stage != stage:
        record_event(
            candidate_id,
            EVENT_STAGE_CHANGED,
            actor=user["email"],
            metadata={"from": previous_stage, "to": stage, "triggered_by": "recruiter"},
        )

    return serialize_document(result)
