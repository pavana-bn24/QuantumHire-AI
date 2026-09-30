"""Skill-test endpoints (milestone 3).

Flow: evaluation approved -> ``POST .../generate-test`` (or automatic on
evaluation approval) -> recruiter edits -> ``POST .../skill-test/approve``
which moves the candidate to the Skill Test stage and fires the webhook.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_recruiter
from app.core.constants import (
    COLLECTION_CANDIDATES,
    EVALUATION_APPROVED,
    PipelineStage,
    SKILL_TEST_APPROVED,
    SKILL_TEST_DRAFT,
)
from app.core.serialization import parse_object_id, utc_now
from app.db.mongo import get_collection
from app.models import Requirement, SkillTest, SkillTestUpdate
from app.services.evaluation import Evaluation
from app.services.skill_tests import (
    SkillTestFailedError,
    SkillTestNotAllowedError,
    SkillTestUnavailableError,
    generate_skill_test,
)
from app.services.webhooks import dispatch_webhook
from app.services.workflow import (
    EVENT_SKILL_TEST_APPROVED,
    EVENT_SKILL_TEST_GENERATED,
    EVENT_STAGE_CHANGED,
    EVENT_WEBHOOK_DELIVERED,
    EVENT_WEBHOOK_FAILED,
    EVENT_WEBHOOK_SIMULATED,
    EVENT_SKILL_TEST_UPDATED,
    record_event,
)

router = APIRouter(prefix="/candidates", tags=["skill-test"])


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


def run_skill_test_generation(candidate_id: str, *, actor: str) -> dict:
    """Shared entry point (HTTP endpoint + generate_skill_test tool).

    Raises the service-layer :class:`SkillTestError` subclasses; callers map
    them to HTTP statuses or record them on the workflow timeline.
    """
    document = _candidate_or_404(candidate_id)

    evaluation_raw = document.get("evaluation")
    evaluation = Evaluation.model_validate(evaluation_raw) if evaluation_raw else None

    requirements: list[Requirement] = []
    role_id = document.get("role_id")
    from app.core.constants import COLLECTION_ROLES
    object_id = parse_object_id(role_id) if role_id else None
    role = get_collection(COLLECTION_ROLES).find_one({"_id": object_id}) if object_id else None
    if role is None:
        raise SkillTestNotAllowedError(
            "This candidate has no valid configured role. Assign an existing role before "
            "generating a skill test."
        )
    requirements = [Requirement.model_validate(entry) for entry in (role.get("requirements") or [])]
    # Keep the role context authoritative even if a recruiter renamed a candidate.
    role_title = role.get("title") or document.get("role_title")

    test = generate_skill_test(
        candidate_id=candidate_id,
        evaluation=evaluation,
        profile_name=document.get("name"),
        profile_json=json.dumps(document.get("extracted_profile") or {}, ensure_ascii=False),
        requirements_json=json.dumps(
            [requirement.model_dump() for requirement in requirements], ensure_ascii=False
        ),
    )
    if role_title and test.title:
        # The provider may use the role title from the approved evaluation; do not
        # overwrite its personalized content, but preserve the authoritative role
        # in the webhook payload through the candidate snapshot below.
        document["role_title"] = role_title

    payload = test.model_dump()
    get_collection(COLLECTION_CANDIDATES).update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {"skill_test": payload, "updated_at": utc_now()}},
    )
    record_event(
        candidate_id,
        EVENT_SKILL_TEST_GENERATED,
        actor=actor,
        metadata={
            "provider": test.provider,
            "questions": len(test.questions),
            "skill_test_id": test.skill_test_id,
            "triggered_by": "recruiter",
        },
    )
    return payload


@router.post(
    "/{candidate_id}/generate-test",
    response_model=SkillTest,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a skill test (draft)",
)
def generate_test(
    candidate_id: str,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Draft a skill test from an *approved* evaluation.

    409 if the evaluation is missing/draft, 503 when no provider is configured,
    502 when the provider returns an invalid test.
    """
    try:
        return run_skill_test_generation(candidate_id, actor=user["email"])
    except SkillTestNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except SkillTestUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except SkillTestFailedError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc


@router.get("/{candidate_id}/skill-test", response_model=SkillTest, summary="Get the skill test")
def get_skill_test(candidate_id: str, user: dict = Depends(require_recruiter)) -> dict:
    """Return the stored skill test (404 when none exists yet)."""
    document = _candidate_or_404(candidate_id)
    skill_test = document.get("skill_test")
    if not skill_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No skill test exists for this candidate yet.",
        )
    return skill_test


@router.put(
    "/{candidate_id}/skill-test",
    response_model=SkillTest,
    summary="Edit the skill test (draft)",
)
def update_skill_test(
    candidate_id: str,
    payload: SkillTestUpdate,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Apply recruiter edits before approval; approved tests are locked."""
    document = _candidate_or_404(candidate_id)
    skill_test = document.get("skill_test")
    if not skill_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No skill test exists for this candidate yet.",
        )
    if skill_test.get("status") == SKILL_TEST_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The skill test is already approved and cannot be edited.",
        )
    if not payload.questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A skill test needs at least one question.",
        )

    skill_test.update(payload.model_dump())
    skill_test["status"] = SKILL_TEST_DRAFT
    get_collection(COLLECTION_CANDIDATES).update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {"skill_test": skill_test, "updated_at": utc_now()}},
    )
    record_event(
        candidate_id,
        EVENT_SKILL_TEST_UPDATED,
        actor=user["email"],
        metadata={"questions": len(skill_test.get("questions", []))},
    )
    return skill_test


@router.post(
    "/{candidate_id}/skill-test/approve",
    response_model=SkillTest,
    summary="Approve the skill test (moves candidate to Skill Test)",
)
def approve_skill_test(
    candidate_id: str,
    user: dict = Depends(require_recruiter),
) -> dict:
    """Approve the test, move the candidate to ``Skill Test`` and fire a webhook."""
    document = _candidate_or_404(candidate_id)
    skill_test = document.get("skill_test")
    if not skill_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No skill test exists for this candidate yet. Generate one first.",
        )
    if skill_test.get("status") == SKILL_TEST_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The skill test is already approved.",
        )

    now = utc_now()
    skill_test.setdefault("skill_test_id", str(uuid4()))
    skill_test["status"] = SKILL_TEST_APPROVED
    skill_test["approved_at"] = now.isoformat()
    skill_test["approved_by"] = user["email"]

    previous_stage = document.get("stage")
    collection = get_collection(COLLECTION_CANDIDATES)
    collection.update_one(
        {"_id": parse_object_id(candidate_id)},
        {"$set": {
            "skill_test": skill_test,
            "stage": PipelineStage.SKILL_TEST.value,
            "updated_at": now,
        }},
    )
    record_event(
        candidate_id,
        EVENT_SKILL_TEST_APPROVED,
        actor=user["email"],
        metadata={
            "questions": len(skill_test.get("questions", [])),
            "stage": PipelineStage.SKILL_TEST.value,
        },
    )
    # Explicit stage-transition activity ("Candidate Stage Updated" in the UI).
    if previous_stage != PipelineStage.SKILL_TEST.value:
        record_event(
            candidate_id,
            EVENT_STAGE_CHANGED,
            actor=user["email"],
            metadata={
                "from": previous_stage,
                "to": PipelineStage.SKILL_TEST.value,
                "triggered_by": "skill_test_approval",
            },
        )

    # Resolve the role from the candidate's configured role, not user-entered
    # narrative, so integrations receive authoritative context.
    role_title = document.get("role_title") or ""
    role_id = document.get("role_id")
    if role_id:
        from app.core.constants import COLLECTION_ROLES
        role_object_id = parse_object_id(role_id)
        role = get_collection(COLLECTION_ROLES).find_one({"_id": role_object_id}) if role_object_id else None
        role_title = (role or {}).get("title") or role_title

    # Outbound integration: never blocks the workflow (simulated when unset).
    webhook_payload = {
        "candidate_id": candidate_id,
        "candidate_name": document.get("name"),
        "role": role_title,
        "stage": PipelineStage.SKILL_TEST.value,
        "skill_test_id": skill_test["skill_test_id"],
        "timestamp": now.isoformat(),
        "approved_by": user["email"],
        "approved_at": skill_test["approved_at"],
    }
    report = dispatch_webhook("skill_test_approved", webhook_payload)
    webhook_event = {
        "delivered": EVENT_WEBHOOK_DELIVERED,
        "simulated": EVENT_WEBHOOK_SIMULATED,
        "failed": EVENT_WEBHOOK_FAILED,
    }.get(report.get("delivery"), EVENT_WEBHOOK_FAILED)
    record_event(
        candidate_id,
        webhook_event,
        actor="system",
        metadata={"event": "skill_test_approved", "payload": webhook_payload, **report},
    )

    return skill_test


def maybe_generate_skill_test(candidate_id: str, *, actor: str) -> dict | None:
    """Generate only when none exists yet (used by evaluation-approval automation)."""
    document = _candidate_or_404(candidate_id)
    if document.get("skill_test"):
        return None
    return run_skill_test_generation(candidate_id, actor=actor)
