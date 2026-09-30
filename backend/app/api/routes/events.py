"""Workflow event (Activity timeline) endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_database, require_recruiter
from app.core.serialization import parse_object_id
from app.db.mongo import get_collection
from app.core.constants import COLLECTION_CANDIDATES
from app.models import WorkflowEvent
from app.services.workflow import list_events

router = APIRouter(
    prefix="/candidates", tags=["activity"], dependencies=[Depends(require_database)]
)


@router.get(
    "/{candidate_id}/events",
    response_model=list[WorkflowEvent],
    summary="List workflow events for a candidate",
)
def candidate_events(
    candidate_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_recruiter),
) -> list[dict]:
    """Activity timeline (newest first) for one candidate."""
    object_id = parse_object_id(candidate_id)
    exists = (
        get_collection(COLLECTION_CANDIDATES).find_one({"_id": object_id}, {"_id": 1})
        if object_id
        else None
    )
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return list_events(candidate_id, limit=limit)
