"""Milestone 2 - candidate detail evidence + recruiter profile review/approval."""

from app.core.constants import COLLECTION_CANDIDATES
from app.db.mongo import get_collection

MISSING_OBJECT_ID = "000000000000000000000000"


def upload_candidate(uploader, resume) -> str:
    """Upload a resume and return the new candidate id."""
    response = uploader(resume)
    assert response.status_code == 201, response.text
    return response.json()["candidate_id"]


# --- detail endpoint ------------------------------------------------------


def test_detail_returns_extracted_profile_and_resume_text(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)

    response = client.get(f"/api/candidates/{candidate_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == candidate_id
    assert body["has_resume"] is True
    assert body["resume_filename"] == "aarav-sharma.pdf"
    assert body["profile_reviewed"] is False
    assert body["extracted_profile"]["email"] == "aarav.sharma@example.com"
    assert "Aarav Sharma" in body["resume_text"]
    assert body["ai_provider"] == "stub"
    assert body["resume_page_count"] == 1


def test_detail_missing_candidate_returns_404(client):
    response = client.get(f"/api/candidates/{MISSING_OBJECT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"


def test_detail_invalid_candidate_id_returns_404(client):
    response = client.get("/api/candidates/not-an-object-id")

    assert response.status_code == 404


def test_list_omits_resume_text_but_reports_has_resume(client, uploader, sample_resume):
    upload_candidate(uploader, sample_resume)

    response = client.get("/api/candidates")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["has_resume"] is True
    assert "resume_text" not in rows[0]


# --- recruiter review / approval -----------------------------------------


REVIEWED_PROFILE = {
    "name": "Aarav S. Sharma",
    "email": "aarav.sharma@example.com",
    "phone": "+91 98765 43210",
    "skills": ["communication", "mentoring", "system design"],
    "technologies": ["Python", "FastAPI", "React", "MongoDB"],
    "work_experience": [
        {
            "company": "Nimbus Labs",
            "title": "Senior Software Engineer",
            "start_date": "2021",
            "end_date": "Present",
            "description": "Built a RAG assistant over internal docs.",
            "technologies": ["LangChain", "OpenAI API"],
        }
    ],
    "projects": [
        {
            "name": "QuantumHire",
            "description": "Resume parsing service.",
            "technologies": ["FastAPI"],
        }
    ],
    "education": [
        {"institution": "IIT Madras", "degree": "B.Tech", "field_of_study": "Computer Science"}
    ],
    "ai_experience": ["Built a RAG assistant with LangChain."],
    "development_experience": ["Developed React dashboards."],
    "tools_platforms": ["Docker", "GitHub Actions"],
    "achievements": ["Won the internal AI hackathon in 2023."],
}


def test_profile_update_saves_recruiter_edits_and_approves(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)

    response = client.put(
        f"/api/candidates/{candidate_id}/profile", json={**REVIEWED_PROFILE, "reviewed": True}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile_reviewed"] is True
    assert body["profile_reviewed_at"] is not None
    assert body["extracted_profile"]["name"] == "Aarav S. Sharma"
    assert body["extracted_profile"]["skills"] == ["communication", "mentoring", "system design"]
    assert body["extracted_profile"]["work_experience"][0]["company"] == "Nimbus Labs"

    # Top-level fields stay in sync so search, lists and the dashboard keep working.
    assert body["name"] == "Aarav S. Sharma"
    assert "system design" in body["skills"]

    stored = get_collection(COLLECTION_CANDIDATES).find_one({})
    assert stored["profile_reviewed"] is True
    assert stored["extracted_profile"]["achievements"] == ["Won the internal AI hackathon in 2023."]
    # The machine's original extraction is preserved for audit/diffing.
    assert stored["original_extracted_profile"]["skills"] != stored["extracted_profile"]["skills"]


def test_profile_update_missing_candidate_returns_404(client):
    response = client.put(
        f"/api/candidates/{MISSING_OBJECT_ID}/profile",
        json={"name": "Ghost", "skills": [], "technologies": []},
    )

    assert response.status_code == 404


def test_profile_update_duplicate_email_returns_409(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    client.post("/api/candidates", json={"name": "Other Person", "email": "taken@example.com"})

    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"name": "Aarav Sharma", "email": "taken@example.com", "skills": []},
    )

    assert response.status_code == 409
    assert "already belongs to another candidate" in response.json()["detail"]

    from bson import ObjectId

    stored = get_collection(COLLECTION_CANDIDATES).find_one({"_id": ObjectId(candidate_id)})
    assert stored["email"] == "aarav.sharma@example.com"  # unchanged


def test_profile_update_can_withdraw_approval(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    payload = {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "skills": ["communication"],
        "technologies": ["Python"],
    }

    client.put(f"/api/candidates/{candidate_id}/profile", json={**payload, "reviewed": True})
    response = client.put(
        f"/api/candidates/{candidate_id}/profile", json={**payload, "reviewed": False}
    )

    assert response.status_code == 200
    assert response.json()["profile_reviewed"] is False
    assert response.json()["profile_reviewed_at"] is None


def test_profile_update_rejects_invalid_payload(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)

    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"name": "Aarav", "skills": "communication"},
    )

    assert response.status_code == 422


# --- request contract: malformed payloads must fail loudly -----------------


def test_profile_update_rejects_nested_extracted_profile_payload(client, uploader, sample_resume):
    """Regression: a nested payload must 422, not silently wipe the profile.

    The frontend contract is flat (``{...profile, reviewed}``). Before this
    check, ``{"extracted_profile": {...}}`` matched no declared field, was
    dropped by ``extra="ignore"`` and stored an *empty* profile as approved
    evidence - losing the extraction without any error.
    """
    candidate_id = upload_candidate(uploader, sample_resume)
    before = client.get(f"/api/candidates/{candidate_id}").json()["extracted_profile"]

    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"extracted_profile": {"name": "Ghost"}, "reviewed": True},
    )

    assert response.status_code == 422
    assert "flat at the top level" in response.text

    after = client.get(f"/api/candidates/{candidate_id}").json()
    assert after["extracted_profile"] == before  # evidence untouched
    assert after["profile_reviewed"] is False  # not approved either


def test_profile_update_rejects_unknown_fields(client, uploader, sample_resume):
    """Regression: a misspelled key (``full_name``) must not be silently dropped.

    With ``extra="ignore"`` the typo would clear every other profile field and
    save an empty profile as approved evidence.
    """
    candidate_id = upload_candidate(uploader, sample_resume)
    before = client.get(f"/api/candidates/{candidate_id}").json()["extracted_profile"]

    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"full_name": "Aarav", "skills": ["React"]},
    )

    assert response.status_code == 422
    assert "full_name" in response.text

    after = client.get(f"/api/candidates/{candidate_id}").json()
    assert after["extracted_profile"] == before
    assert after["profile_reviewed"] is False


def test_profile_update_still_accepts_the_flat_frontend_payload(client, uploader, sample_resume):
    """The exact shape ProfileForm sends: every profile field flat + ``reviewed``."""
    candidate_id = upload_candidate(uploader, sample_resume)
    payload = {**REVIEWED_PROFILE, "reviewed": True}

    response = client.put(f"/api/candidates/{candidate_id}/profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile_reviewed"] is True
    assert body["extracted_profile"]["name"] == "Aarav S. Sharma"


# --- duplicate e-mail protection on create/update --------------------------


def test_profile_update_duplicate_email_is_case_and_whitespace_insensitive(client, uploader, sample_resume):
    """``TAKEN@Example.COM`` must clash with the stored ``taken@example.com``."""
    candidate_id = upload_candidate(uploader, sample_resume)
    client.post("/api/candidates", json={"name": "Other Person", "email": "taken@example.com"})

    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"name": "Aarav Sharma", "email": "  TAKEN@Example.COM  ", "skills": []},
    )

    assert response.status_code == 409
    assert "already belongs to another candidate" in response.json()["detail"]

    from bson import ObjectId

    stored = get_collection(COLLECTION_CANDIDATES).find_one({"_id": ObjectId(candidate_id)})
    assert stored["email"] == "aarav.sharma@example.com"  # unchanged


def test_create_candidate_duplicate_email_returns_409(client):
    first = client.post("/api/candidates", json={"name": "First Person", "email": "dup@example.com"})
    assert first.status_code == 201

    duplicate = client.post(
        "/api/candidates", json={"name": "Second Person", "email": "  DUP@Example.com  "}
    )

    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]
    # Stored normalised, so later lookups and the unique index agree.
    rows = client.get("/api/candidates").json()
    assert len(rows) == 1
    assert rows[0]["email"] == "dup@example.com"


def test_create_candidate_blank_email_returns_422(client):
    response = client.post("/api/candidates", json={"name": "No Email", "email": "   "})

    assert response.status_code == 422
    assert "email" in response.json()["detail"].lower()


def test_candidate_without_resume_still_works_and_can_be_profiled(client):
    """Regression: manually created candidates predate milestone 2 and must not break."""
    created = client.post(
        "/api/candidates", json={"name": "Manual Entry", "email": "manual@example.com"}
    )
    assert created.status_code == 201
    candidate_id = created.json()["id"]

    detail = client.get(f"/api/candidates/{candidate_id}").json()
    assert detail["has_resume"] is False
    assert detail["extracted_profile"] is None
    assert detail["profile_reviewed"] is False

    reviewed = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={"name": "Manual Entry", "email": "manual@example.com", "skills": ["Excel"]},
    )

    assert reviewed.status_code == 200
    assert reviewed.json()["profile_reviewed"] is True
    assert reviewed.json()["has_resume"] is False
