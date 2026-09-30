"""Authentication: password hashing + JWT issuing/verification.

- Passwords: PBKDF2-HMAC-SHA256 (stdlib, no extra dependency) with a random
  per-user salt, stored as ``pbkdf2_sha256$<iterations>$<salt>$<hash>``.
- Tokens: PyJWT HS256 signed with ``JWT_SECRET`` (from the environment).

The demo recruiter is seeded from ``SEED_ADMIN_EMAIL``/``SEED_ADMIN_PASSWORD``
so the app works out of the box; change both in ``.env`` for anything real.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 100_000


class AuthError(Exception):
    """Authentication failure with an API-safe message (HTTP 401)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# --- password hashing --------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash for ``password``."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash string."""
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


# --- JWT ---------------------------------------------------------------------


def create_access_token(*, user_id: str, email: str, name: str, role: str) -> str:
    """Issue a signed JWT for the user (expiry from ``JWT_EXPIRES_MINUTES``)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT, raising :class:`AuthError` on any failure."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Session expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid or malformed authentication token.") from exc
