"""Authentication endpoints (JWT)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_current_user
from app.core.constants import COLLECTION_USERS
from app.core.serialization import parse_object_id, serialize_document
from app.db.mongo import get_collection
from app.models import AuthResponse, LoginRequest, PublicUser
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _public_user(document: dict) -> PublicUser:
    serialized = serialize_document(document) or {}
    return PublicUser(
        id=serialized.get("id", ""),
        email=serialized.get("email", ""),
        name=serialized.get("name", ""),
        role=serialized.get("role", "recruiter"),
    )


@router.post("/login", response_model=AuthResponse, summary="Sign in")
def login(payload: LoginRequest) -> dict:
    """Exchange email/password for a bearer JWT.

    A generic message is returned for unknown e-mail *or* wrong password so the
    endpoint cannot be used to enumerate accounts.
    """
    collection = get_collection(COLLECTION_USERS)
    document = collection.find_one({"email": payload.email.strip().lower()})

    generic = "Invalid email or password."
    if document is None or not verify_password(payload.password, document.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=generic,
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _public_user(document)
    token = create_access_token(
        user_id=user.id, email=user.email, name=user.name, role=user.role
    )
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=PublicUser, summary="Current user")
def me(user: dict = Depends(require_current_user)) -> dict:
    """Return the profile behind the presented bearer token."""
    return user
