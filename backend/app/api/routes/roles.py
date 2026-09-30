"""Role endpoints.

Read paths power the Roles page; the create path exists so new roles can be
added without touching the database by hand.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.api.deps import require_database, require_recruiter
from app.core.constants import COLLECTION_ROLES
from app.core.serialization import parse_object_id, serialize_document, serialize_documents, utc_now
from app.db.mongo import get_collection
from app.models import Role, RoleCreate

router = APIRouter(prefix="/roles", tags=["roles"], dependencies=[Depends(require_database)])


@router.get("", response_model=list[Role], summary="List roles")
def list_roles() -> list[dict]:
    """Return every role, newest first."""
    documents = list(get_collection(COLLECTION_ROLES).find().sort("created_at", -1))
    return serialize_documents(documents)


@router.get("/{role_id}", response_model=Role, summary="Get a role")
def get_role(role_id: str) -> dict:
    """Return a single role by id."""
    object_id = parse_object_id(role_id)
    document = (
        get_collection(COLLECTION_ROLES).find_one({"_id": object_id}) if object_id else None
    )

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return serialize_document(document)


@router.post("", response_model=Role, status_code=status.HTTP_201_CREATED, summary="Create a role")
def create_role(payload: RoleCreate, user: dict = Depends(require_recruiter)) -> dict:
    """Create a role. Titles are unique via the derived slug."""
    now = utc_now()
    slug = payload.title.strip().lower().replace(" ", "-")
    document = {
        **payload.model_dump(),
        "slug": slug,
        "created_at": now,
        "updated_at": now,
    }

    collection = get_collection(COLLECTION_ROLES)
    if collection.find_one({"slug": slug}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A role with the title '{payload.title}' already exists",
        )

    try:
        result = collection.insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Role already exists"
        ) from exc

    document["_id"] = result.inserted_id
    return serialize_document(document)
