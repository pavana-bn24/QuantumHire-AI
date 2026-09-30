"""Milestone 2 - resume upload, PDF extraction, structuring and duplicates."""

from app.core.constants import COLLECTION_CANDIDATES
from app.core.config import settings
from app.db.mongo import get_collection

UPLOAD_URL = "/api/candidates/upload"


def candidate_count() -> int:
    return get_collection(COLLECTION_CANDIDATES).count_documents({})


# --- baseline -------------------------------------------------------------


def test_health_endpoint_still_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- happy path -----------------------------------------------------------


def test_valid_pdf_upload_creates_candidate_with_grounded_profile(client, uploader, sample_resume):
    response = uploader(sample_resume)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["candidate_id"]

    profile = body["extracted_profile"]
    assert profile["name"] == "Aarav Sharma"
    assert profile["email"] == "aarav.sharma@example.com"
    assert profile["phone"]
    assert "Python" in profile["technologies"]
    assert "React" in profile["technologies"]
    assert "communication" in profile["skills"]
    assert profile["work_experience"]
    assert profile["education"]
    assert profile["ai_experience"]

    # Evidence discipline: nothing that is absent from the resume may appear.
    for absent in ("Kubernetes", "PyTorch", "Rust", "Terraform"):
        assert absent not in profile["technologies"]

    assert body["extraction"]["provider"] == "stub"
    assert body["extraction"]["page_count"] == 1
    assert body["extraction"]["char_count"] > settings.resume_min_chars

    candidate = body["candidate"]
    assert candidate["resume_filename"] == "aarav-sharma.pdf"
    assert candidate["has_resume"] is True
    assert candidate["profile_reviewed"] is False
    assert candidate["stage"] == "New"


def test_upload_persists_resume_evidence(client, uploader, sample_resume):
    response = uploader(sample_resume)
    assert response.status_code == 201

    stored = get_collection(COLLECTION_CANDIDATES).find_one({})
    assert "aarav.sharma@example.com" in stored["resume_text"]
    assert stored["resume_filename"] == "aarav-sharma.pdf"
    assert stored["uploaded_at"] is not None
    assert stored["extracted_at"] is not None
    assert stored["profile_reviewed"] is False
    assert stored["extracted_profile"]["email"] == "aarav.sharma@example.com"
    assert stored["original_extracted_profile"]["name"] == "Aarav Sharma"
    assert stored["resume_sha256"]
    assert stored["stage"] == "New"


def test_upload_links_candidate_to_role(client, uploader, sample_resume):
    role = client.get("/api/roles").json()[0]

    response = uploader(sample_resume, form={"role_id": role["id"], "stage": "Under Review"})
    assert response.status_code == 201, response.text

    candidate = response.json()["candidate"]
    assert candidate["role_id"] == role["id"]
    assert candidate["role_title"] == role["title"]
    assert candidate["stage"] == "Under Review"


# --- validation failures --------------------------------------------------


def test_non_pdf_extension_is_rejected(client, uploader):
    response = uploader(b"name,email\nAarav,a@example.com\n", filename="resume.txt",
                        content_type="text/plain")

    assert response.status_code == 415
    assert ".txt" in response.json()["detail"]
    assert candidate_count() == 0


def test_pdf_extension_with_non_pdf_content_is_rejected(client, uploader):
    response = uploader(b"this is definitely not a pdf", filename="resume.pdf")

    assert response.status_code == 415
    assert "%PDF-" in response.json()["detail"]
    assert candidate_count() == 0


def test_unsupported_mime_type_is_rejected(client, uploader, sample_resume):
    response = uploader(sample_resume, content_type="image/png")

    assert response.status_code == 415
    assert "image/png" in response.json()["detail"]
    assert candidate_count() == 0


def test_oversize_resume_is_rejected(client, uploader, monkeypatch):
    monkeypatch.setattr(settings, "max_resume_size_mb", 1)
    oversized = b"%PDF-1.7\n" + b"0" * (1_100_000)

    response = uploader(oversized)

    assert response.status_code == 413
    assert "limit" in response.json()["detail"].lower()
    assert candidate_count() == 0


def test_empty_upload_is_rejected(client, uploader):
    response = uploader(b"")

    assert response.status_code == 400
    assert candidate_count() == 0


def test_missing_file_field_returns_422(client):
    response = client.post(UPLOAD_URL, data={"stage": "New"})
    assert response.status_code == 422


def test_unknown_stage_is_rejected(client, uploader, sample_resume):
    response = uploader(sample_resume, form={"stage": "Nonsense"})

    assert response.status_code == 422
    assert candidate_count() == 0


# --- PDF integrity failures ----------------------------------------------


def test_corrupt_pdf_is_rejected(client, uploader):
    response = uploader(b"%PDF-1.7\nthis body is not a real pdf at all")

    assert response.status_code == 422
    assert response.headers.get("X-Error-Code") == "corrupt_pdf"
    assert "corrupt" in response.json()["detail"].lower()
    assert candidate_count() == 0


def test_scanned_or_empty_pdf_is_rejected(client, uploader, blank_pdf_bytes):
    response = uploader(blank_pdf_bytes())

    assert response.status_code == 422
    assert response.headers.get("X-Error-Code") == "scanned_pdf"
    assert "scanned" in response.json()["detail"].lower()
    assert candidate_count() == 0


def test_text_poor_pdf_is_rejected(client, uploader, pdf_bytes):
    response = uploader(pdf_bytes(["Hi"]))

    assert response.status_code == 422
    assert candidate_count() == 0


# --- duplicate detection --------------------------------------------------


def test_duplicate_email_returns_409_and_creates_no_second_candidate(client, uploader, sample_resume):
    first = uploader(sample_resume)
    assert first.status_code == 201

    second = uploader(sample_resume)

    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]
    assert first.json()["candidate_id"] in second.json()["detail"]
    assert candidate_count() == 1


def test_same_resume_file_without_email_returns_409(client, uploader, pdf_bytes):
    resume = pdf_bytes(
        [
            "Priya Nair",
            "Technologies: React, FastAPI, MongoDB",
            "Built an internal analytics dashboard with React and FastAPI.",
        ]
    )

    first = uploader(resume, filename="priya.pdf")
    assert first.status_code == 201, first.text
    assert first.json()["extracted_profile"]["email"] is None

    second = uploader(resume, filename="priya-copy.pdf")

    assert second.status_code == 409
    assert "resume" in second.json()["detail"].lower()
    assert candidate_count() == 1


# --- prompt injection -----------------------------------------------------


def test_prompt_injection_is_flagged_but_never_obeyed(client, uploader, injection_resume):
    response = uploader(injection_resume)

    assert response.status_code == 201, response.text
    extraction = response.json()["extraction"]

    assert extraction["prompt_injection_flags"], "injection text should be flagged"
    assert any("injection" in warning.lower() for warning in extraction["warnings"])

    profile = response.json()["extracted_profile"]
    assert profile["name"] == "Meera Iyer"
    # Only the technologies actually listed may appear - no invented extras.
    assert set(profile["technologies"]) <= {"React", "FastAPI"}
    assert profile["technologies"]
    assert profile["achievements"] == []


# --- provider failures ----------------------------------------------------


def test_provider_disabled_returns_503(client, uploader, sample_resume, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "none")

    response = uploader(sample_resume)

    assert response.status_code == 503
    assert "LLM_PROVIDER" in response.json()["detail"]
    assert candidate_count() == 0


def test_provider_failure_returns_502(client, uploader, sample_resume, monkeypatch):
    from app.ai.base import ProviderError
    from app.services import extraction as extraction_service

    class BrokenProvider:
        name = "broken"
        model = "broken-1"

        def extract_profile(self, resume_text):  # noqa: ARG002
            raise ProviderError("simulated upstream outage")

    monkeypatch.setattr(extraction_service, "get_provider", lambda: BrokenProvider())

    response = uploader(sample_resume)

    assert response.status_code == 502
    assert "simulated upstream outage" in response.json()["detail"]
    assert candidate_count() == 0


def test_unknown_role_returns_404(client, uploader, sample_resume):
    response = uploader(sample_resume, form={"role_id": "000000000000000000000000"})

    assert response.status_code == 404
    assert candidate_count() == 0
