"""Shared FastAPI dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import COLLECTION_USERS
from app.core.serialization import parse_object_id
from app.db.mongo import get_collection, ping_database
from app.services.auth import AuthError, decode_access_token

#: Reusable HTTP bearer scheme (API docs show the "Authorize" button).
bearer_scheme = HTTPBearer(auto_error=False)


def require_database() -> None:
    """Guard data endpoints so they fail clearly when MongoDB is down."""
    if not ping_database():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Check MONGODB_URI and that MongoDB is running.",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Resolve the authenticated recruiter from the ``Authorization: Bearer`` JWT.

    Raises 401 when the token is missing, invalid, expired, or the user account
    has been removed since the token was issued.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Sign in to obtain a bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = claims.get("sub")
    object_id = parse_object_id(str(user_id)) if user_id else None
    document = (
        get_collection(COLLECTION_USERS).find_one({"_id": object_id}) if object_id else None
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": str(document["_id"]),
        "email": document.get("email", claims.get("email", "")),
        "name": document.get("name", claims.get("name", "")),
        "role": document.get("role", claims.get("role", "recruiter")),
    }


#: Dependency aliases used on protected mutation routes.
require_recruiter = get_current_user
require_current_user = get_current_user

