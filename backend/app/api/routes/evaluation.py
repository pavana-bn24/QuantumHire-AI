"""AI evaluation endpoints (milestone 3).

Flow: profile approved -> ``POST .../evaluate`` (draft) -> recruiter edits ->
``POST .../evaluation/approve`` -> automation drafts a skill test.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_recruiter
from app.core.constants import (
    COLLECTION_CANDIDATES,
    COLLECTION_ROLES,
    EVALUATION_APPROVED,
)
from app.core.serialization import parse_object_id, serialize_document, utc_now
from app.db.mongo import get_collection
from app.models import Evaluation, EvaluationUpdate, Requirement
from app.services.evaluation import (
    EvaluationFailedError,
    EvaluationNotAllowedError,
    EvaluationUnavailableError,
    generate_evaluation,
)
from app.services.workflow import (
    EVENT_EVALUATION_APPROVED,
    EVENT_EVALUATION_GENERATED,
    EVENT_EVALUATION_UPDATED,
    record_event,
)

router = APIRouter(prefix="/candidates", tags=["evaluation"])


def _candidate_or_404(candidate_id: str) -> dict:
    object_id = parse_object_id(candidate_id)
    document = (
        get_collection(COLLECTION_CANDIDATES).find_one({"_id": object_id})
        if object_id
        else None
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return document


def _requirements_for(document: dict) -> tuple[list[Requirement], str, str]:
    """Load requirements for the candidate's explicitly configured role."""
    role = None
    role_id = document.get("role_id")
    if role_id:
        object_id = parse_object_id(role_id)
        role = (
            get_collection(COLLECTION_ROLES).find_one({"_id": object_id}) if object_id else None
        )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This candidate has no valid configured role, so the candidate cannot be "
                "evaluated. Assign an existing role first."
            ),
        )

    # Mongo returns raw dicts; validate so the services get typed requirements.
    requirements = [
        Requirement.model_validate(entry) for entry in (role.get("requirements") or [])
    ]
    return requirements, str(role["_id"]), role.get("title")


def run_evaluation_for_candidate(candidate_id: str, *, actor: str) -> dict:
    """Shared entry point used by the HTTP endpoint and the evaluate tool.

    Validates gates (profile approved, role exists), generates the draft
    evaluation, stores it on the candidate document and records the event.
    """
    document = _candidate_or_404(candidate_id)

    from app.models import CandidateProfile

    profile_raw = document.get("extracted_profile")
    if not document.get("profile_reviewed") or profile_raw is None:
        raise EvaluationNotAllowedError(
            "The profile must be recruiter-approved before AI evaluation. "
            "Review and save the profile with reviewed=true first."
        )

    profile = CandidateProfile.model_validate(profile_raw)
    requirements, role_id, role_title = _requirements_for(document)

    # Retrieval query: the candidate's own context **plus** the evaluation policy
    # terms, so the guidelines document is always among the retrieved sources.
    candidate_terms = " ".join(
        filter(None, [document.get("name"), role_title, " ".join(document.get("skills") or [])])
    )
    query = (
        f"{candidate_terms} evaluation rating demonstrated verification evidence guidelines"
    ).strip()

    try:
        evaluation = generate_evaluation(
            candidate_id=candidate_id,
            profile=profile,
            requirements=requirements,
            role_id=role_id,
            role_title=role_title,
            query=query or "evaluation guidelines",
        )
    except EvaluationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        ) from exc
    except EvaluationFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        ) from exc

    payload = evaluation.model_dump()
    get_collection(COLLECTION_CANDIDATES).update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {"evaluation": payload, "updated_at": utc_now()}},
    )
    record_event(
        candidate_id,
        EVENT_EVALUATION_GENERATED,
        actor=actor,
        metadata={
            "provider": evaluation.provider,
            "assessments": len(evaluation.assessments),
            "triggered_by": "recruiter",
        },
    )
    return payload


@router.post(
    "/{candidate_id}/evaluate",
    response_model=Evaluation,
    status_code=status.HTTP_201_CREATED,
    summary="Run the AI evaluation (draft)",
)
def evaluate_candidate(
    candidate_id: str,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Generate and store a draft evaluation.

    409 until the profile is approved, 503 when no AI provider is configured,
    502 when the provider returns invalid structured output.
    """
    try:
        return run_evaluation_for_candidate(candidate_id, actor=user["email"])
    except EvaluationNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.get("/{candidate_id}/evaluation", response_model=Evaluation, summary="Get the evaluation")
def get_evaluation(candidate_id: str, user: dict = Depends(require_recruiter)) -> dict:
    """Return the stored evaluation (404 when none exists yet)."""
    document = _candidate_or_404(candidate_id)
    evaluation = document.get("evaluation")
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation exists for this candidate yet.",
        )
    return evaluation


@router.put(
    "/{candidate_id}/evaluation",
    response_model=Evaluation,
    summary="Edit the draft evaluation",
)
def update_evaluation(
    candidate_id: str,
    payload: EvaluationUpdate,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Apply recruiter edits to narrative fields (drafts only, never re-scores)."""
    document = _candidate_or_404(candidate_id)
    evaluation = document.get("evaluation")
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation exists for this candidate yet.",
        )
    if evaluation.get("status") == EVALUATION_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The evaluation is already approved and cannot be edited.",
        )

    updates = payload.model_dump(exclude_none=True)
    # Keep the legacy fields in sync for existing clients while the recruiter
    # workspace edits the explicit evidence-grounded contract.
    for legacy, explicit in (
        ("summary", "executive_summary"),
        ("strengths", "demonstrated_strengths"),
        ("gaps", "skill_gaps"),
    ):
        if explicit in updates:
            updates[legacy] = updates[explicit]
        elif legacy in updates:
            updates[explicit] = updates[legacy]
    if not updates:
        return evaluation

    evaluation.update(updates)
    get_collection(COLLECTION_CANDIDATES).update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {"evaluation": evaluation, "updated_at": utc_now()}},
    )
    record_event(
        candidate_id,
        EVENT_EVALUATION_UPDATED,
        actor=user["email"],
        metadata={"fields": sorted(payload.model_dump(exclude_none=True))},
    )
    return evaluation


@router.post(
    "/{candidate_id}/evaluation/approve",
    response_model=Evaluation,
    summary="Approve the evaluation (triggers skill-test draft)",
)
def approve_evaluation(
    candidate_id: str,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Approve the draft evaluation and (automation) draft the skill test.

    The skill-test draft is best-effort: approval succeeds even when generation
    fails, and the failure is reported in the workflow event metadata.
    """
    document = _candidate_or_404(candidate_id)
    evaluation = document.get("evaluation")
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation exists for this candidate yet. Run the evaluation first.",
        )
    if evaluation.get("status") == EVALUATION_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The evaluation is already approved.",
        )

    evaluation["status"] = EVALUATION_APPROVED
    evaluation["approved_at"] = utc_now().isoformat()
    evaluation["approved_by"] = user["email"]

    get_collection(COLLECTION_CANDIDATES).update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {"evaluation": evaluation, "updated_at": utc_now()}},
    )
    record_event(
        candidate_id,
        EVENT_EVALUATION_APPROVED,
        actor=user["email"],
        metadata={"assessments": len(evaluation.get("assessments", []))},
    )

    # Automation: draft the skill test right after approval (best effort).
    from app.services.skill_tests import SkillTestError
    from app.api.routes.skill_tests import maybe_generate_skill_test

    try:
        maybe_generate_skill_test(candidate_id, actor=user["email"])
    except SkillTestError as exc:
        record_event(
            candidate_id,
            "skill_test_generation_failed",
            actor="system",
            metadata={"reason": exc.message, "triggered_by": "evaluation_approved"},
        )

    return evaluation
