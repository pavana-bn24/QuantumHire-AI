"""Milestone 3 - JWT auth (login, /me, protected mutations)."""

from app.core.constants import COLLECTION_USERS
from app.db.mongo import get_collection

DEMO = {"email": "recruiter@quantumhire.ai", "password": "quantumhire"}
MISSING_OBJECT_ID = "000000000000000000000000"


def test_login_returns_jwt_and_user(client):
    response = client.post("/api/auth/login", json=DEMO)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20
    assert body["user"]["email"] == DEMO["email"]
    assert body["user"]["role"] == "recruiter"


def test_login_wrong_password_returns_401(client, raw_client):
    response = raw_client.post("/api/auth/login", json={**DEMO, "password": "wrong-password"})

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_unknown_user_returns_401(client, raw_client):
    response = raw_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    assert response.status_code == 401


def test_me_returns_current_user(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == DEMO["email"]


def test_me_without_token_returns_401(raw_client):
    response = raw_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated. Sign in to obtain a bearer token."


def test_mutations_reject_missing_token(raw_client):
    """Every protected mutation 401s before touching the database."""
    cases = [
        ("POST", "/api/candidates", {"name": "No Auth", "email": "noauth@example.com"}),
        ("POST", "/api/roles", {"title": "No Auth Role"}),
        ("PATCH", f"/api/candidates/{MISSING_OBJECT_ID}/stage?stage=Interview", None),
        ("POST", f"/api/candidates/{MISSING_OBJECT_ID}/evaluate", {}),
        ("POST", f"/api/candidates/{MISSING_OBJECT_ID}/generate-test", {}),
        ("POST", "/api/agents/invoke", {"tool": "get_role_requirements", "arguments": {}}),
    ]

    for method, url, payload in cases:
        response = raw_client.request(method, url, json=payload)
        assert response.status_code == 401, f"{method} {url} -> {response.status_code}"


def test_mutations_reject_garbage_token(raw_client):
    response = raw_client.post(
        "/api/candidates",
        json={"name": "Bad Token", "email": "badtoken@example.com"},
        headers={"Authorization": "Bearer not.a.real.token"},
    )

    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_seeded_user_password_is_hashed(client):
    """The users collection stores a PBKDF2 hash, never plaintext."""
    document = get_collection(COLLECTION_USERS).find_one({"email": DEMO["email"]})

    assert document is not None
    assert document["password_hash"].startswith("pbkdf2_sha256$")
    assert DEMO["password"] not in document["password_hash"]


def test_seed_resyncs_admin_password_from_env(client, raw_client):
    """SEED_ADMIN_* stays authoritative: a stale hash is rotated on startup.

    Without this, a fresh .env on an existing database silently bricks the
    documented demo login.
    """
    from app.db.seed import seed_demo_recruiter
    from app.services.auth import hash_password

    collection = get_collection(COLLECTION_USERS)
    collection.update_one(
        {"email": DEMO["email"]}, {"$set": {"password_hash": hash_password("old-rotated-pw")}}
    )
    try:
        # The documented env password is rejected while the stale hash is in place...
        assert raw_client.post("/api/auth/login", json=DEMO).status_code == 401

        # ...until the seed reconciles the stored hash with the environment.
        assert seed_demo_recruiter() == DEMO["email"]
        response = raw_client.post("/api/auth/login", json=DEMO)
        assert response.status_code == 200, response.text
    finally:
        # Never leave the shared test database with a rotated credential.
        seed_demo_recruiter()

    # Re-running the seed with a matching hash is a no-op (hash unchanged).
    before = collection.find_one({"email": DEMO["email"]})["password_hash"]
    seed_demo_recruiter()
    after = collection.find_one({"email": DEMO["email"]})["password_hash"]
    assert before == after
