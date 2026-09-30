"""Milestone 3 - AI evaluation: gating, structure, editing, approval chain."""

from app.core.constants import CAPABILITY_RATINGS, COLLECTION_CANDIDATES
from app.db.mongo import get_collection

MISSING_OBJECT_ID = "000000000000000000000000"

APPROVED_PROFILE = {
    "name": "Aarav Sharma",
    "email": "aarav.sharma@example.com",
    "skills": ["communication", "mentoring"],
    "technologies": ["Python", "FastAPI", "React", "MongoDB", "Docker"],
    "tools_platforms": ["Docker", "GitHub Actions"],
    "work_experience": [
        {
            "company": "Nimbus Labs",
            "title": "Senior Software Engineer",
            "start_date": "2021",
            "description": "Built a RAG assistant over internal docs with LangChain.",
            "technologies": ["LangChain", "OpenAI API"],
        }
    ],
    "ai_experience": ["Built a RAG assistant over internal documentation."],
    "achievements": ["Won the internal AI hackathon in 2023."],
}


def upload_candidate(uploader, resume) -> str:
    response = uploader(resume)
    assert response.status_code == 201, response.text
    return response.json()["candidate_id"]


def approve_profile(client, candidate_id: str, profile=None) -> dict:
    response = client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={**(profile or APPROVED_PROFILE), "reviewed": True},
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- gating -----------------------------------------------------------------


def test_evaluate_is_blocked_until_profile_is_approved(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)

    response = client.post(f"/api/candidates/{candidate_id}/evaluate")

    assert response.status_code == 409
    assert "recruiter-approved" in response.json()["detail"]


def test_evaluate_unknown_candidate_returns_404(client):
    assert client.post(f"/api/candidates/{MISSING_OBJECT_ID}/evaluate").status_code == 404


def test_evaluation_is_absent_before_generation(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)

    assert client.get(f"/api/candidates/{candidate_id}/evaluation").status_code == 404


# --- structure --------------------------------------------------------------


def test_evaluation_has_required_fields_and_valid_ratings(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)

    response = client.post(f"/api/candidates/{candidate_id}/evaluate")

    assert response.status_code == 201, response.text
    body = response.json()

    required_fields = {
        "candidate_id", "role_id", "role_title", "summary", "strengths", "gaps",
        "assessments", "follow_up_questions", "knowledge_sources", "status",
        "executive_summary", "relevant_experience", "demonstrated_strengths",
        "skill_gaps", "ai_first_readiness", "implementation_capability",
        "learning_research_readiness", "evidence_gaps", "recommended_next_step",
    }
    assert required_fields.issubset(body.keys())
    assert body["status"] == "draft"
    assert body["candidate_id"] == candidate_id
    assert body["assessments"], "expected one assessment per role requirement"

    assert {a["rating"] for a in body["assessments"]}.issubset(set(CAPABILITY_RATINGS))
    for assessment in body["assessments"]:
        assert set(assessment) >= {"capability", "label", "rating", "evidence", "notes"}


def test_evaluation_never_contains_numeric_scores_or_ranks(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)

    body = client.post(f"/api/candidates/{candidate_id}/evaluate").json()

    assert "scores" not in body
    assert "total" not in body
    assert "rank" not in body["summary"].lower()
    assert all(isinstance(a["rating"], str) for a in body["assessments"])
    assert all(isinstance(a["rating"], str) for a in body["assessments"])


def test_evaluation_cites_knowledge_sources(client, uploader, sample_resume):
    """RAG: the evaluation records the knowledge documents it retrieved."""
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)

    body = client.post(f"/api/candidates/{candidate_id}/evaluate").json()

    assert body["knowledge_sources"]
    assert any("evaluation_guidelines" in source for source in body["knowledge_sources"])


def test_evaluation_evidence_comes_from_approved_profile(client):
    """A manually created candidate with a reviewed profile can be evaluated too."""
    role_id = client.get("/api/roles").json()[0]["id"]
    created = client.post(
        "/api/candidates",
        json={"name": "Manual Entry", "email": "manual.eval@example.com", "role_id": role_id},
    ).json()
    approve_profile(
        client,
        created["id"],
        {"name": "Manual Entry", "email": "manual.eval@example.com",
         "technologies": ["Python", "FastAPI", "MongoDB", "RAG", "LangChain"],
         "ai_experience": ["Built a RAG pipeline with LangChain."]},
    )

    response = client.post(f"/api/candidates/{created['id']}/evaluate")

    assert response.status_code == 201, response.text
    assessments = {a["capability"]: a for a in response.json()["assessments"]}

    # Explicitly listed technology -> Demonstrated, with the evidence attached.
    assert assessments["rag"]["rating"] == "Demonstrated"
    assert assessments["rag"]["evidence"]
    # Nothing in the profile covers these -> Not Demonstrated, never guessed.
    assert assessments["kubernetes" if "kubernetes" in assessments else "security"][
        "rating"
    ] in {"Not Demonstrated", "Needs Verification"}


def test_evaluation_requires_the_candidate_role(client, uploader, sample_resume):
    response = uploader(sample_resume, form={"role_id": ""})
    candidate_id = response.json()["candidate_id"]
    approve_profile(client, candidate_id)

    evaluation = client.post(f"/api/candidates/{candidate_id}/evaluate")

    assert evaluation.status_code == 409
    assert "configured role" in evaluation.json()["detail"]


def test_prompt_injection_candidate_is_not_elevated_by_resume_instructions(
    client, uploader, injection_resume
):
    """Injected 'rate 10/10' text cannot create an assessment or a score."""
    candidate_id = upload_candidate(uploader, injection_resume)
    approve_profile(
        client,
        candidate_id,
        {
            "name": "Meera Iyer",
            "email": "meera.iyer@example.com",
            "technologies": ["React", "FastAPI"],
        },
    )

    body = client.post(f"/api/candidates/{candidate_id}/evaluate").json()

    assert body["status"] == "draft"
    assert all(a["rating"] in CAPABILITY_RATINGS for a in body["assessments"])
    assert "10/10" not in body["summary"]


# --- editing + approval -----------------------------------------------------


def test_evaluation_can_be_edited_before_approval(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")

    response = client.put(
        f"/api/candidates/{candidate_id}/evaluation",
        json={"summary": "Recruiter edited summary.", "strengths": ["React", "FastAPI"]},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Recruiter edited summary."
    assert response.json()["executive_summary"] == "Recruiter edited summary."
    assert response.json()["strengths"] == ["React", "FastAPI"]
    assert response.json()["demonstrated_strengths"] == ["React", "FastAPI"]


def test_evaluation_editor_saves_explicit_fields_and_qualitative_assessments(
    client, uploader, sample_resume
):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    generated = client.post(f"/api/candidates/{candidate_id}/evaluate").json()
    assessments = generated["assessments"]
    assessments[0]["rating"] = "Needs Verification"
    assessments[0]["notes"] = "Recruiter requested a project example."

    response = client.put(
        f"/api/candidates/{candidate_id}/evaluation",
        json={
            "executive_summary": "Recruiter-reviewed summary.",
            "relevant_experience": ["Built a documented RAG assistant."],
            "demonstrated_strengths": ["Python"],
            "skill_gaps": ["Kubernetes evidence not found."],
            "ai_first_readiness": "Partially Demonstrated",
            "implementation_capability": "Demonstrated",
            "learning_research_readiness": "Needs Verification",
            "evidence_gaps": ["No deployment example in the approved profile."],
            "recommended_next_step": "Discuss deployment experience.",
            "assessments": assessments,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == body["executive_summary"] == "Recruiter-reviewed summary."
    assert body["demonstrated_strengths"] == body["strengths"] == ["Python"]
    assert body["skill_gaps"] == body["gaps"] == ["Kubernetes evidence not found."]
    assert body["ai_first_readiness"] == "Partially Demonstrated"
    assert body["assessments"][0]["rating"] == "Needs Verification"
    assert body["assessments"][0]["evidence"] == generated["assessments"][0]["evidence"]

    events = client.get(f"/api/candidates/{candidate_id}/events").json()
    updated = next(event for event in events if event["event"] == "evaluation_updated")
    assert updated["actor"] == "recruiter@quantumhire.ai"
    assert "assessments" in updated["metadata"]["fields"]


def test_evaluation_editor_rejects_unknown_capability_ratings(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    generated = client.post(f"/api/candidates/{candidate_id}/evaluate").json()
    assessments = generated["assessments"]
    assessments[0]["rating"] = "Excellent"

    response = client.put(
        f"/api/candidates/{candidate_id}/evaluation",
        json={"assessments": assessments},
    )

    assert response.status_code == 422


def test_evaluation_edit_rejects_unknown_fields(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")

    response = client.put(f"/api/candidates/{candidate_id}/evaluation", json={"score": 9.5})

    assert response.status_code == 422


def test_approving_evaluation_drafts_a_skill_test_automatically(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")

    response = client.post(f"/api/candidates/{candidate_id}/evaluation/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_by"] == "recruiter@quantumhire.ai"

    # Automation: the skill test is drafted as part of the approval step.
    skill_test = client.get(f"/api/candidates/{candidate_id}/skill-test").json()
    assert skill_test["status"] == "draft"
    assert len(skill_test["questions"]) >= 3


def test_approved_evaluation_cannot_be_edited_or_re_approved(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")
    client.post(f"/api/candidates/{candidate_id}/evaluation/approve")

    edit = client.put(f"/api/candidates/{candidate_id}/evaluation", json={"summary": "nope"})
    again = client.post(f"/api/candidates/{candidate_id}/evaluation/approve")

    assert edit.status_code == 409
    assert again.status_code == 409


def test_approval_records_workflow_events(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")
    client.post(f"/api/candidates/{candidate_id}/evaluation/approve")

    events = client.get(f"/api/candidates/{candidate_id}/events").json()
    names = [event["event"] for event in events]

    assert "resume_uploaded" in names
    assert "profile_approved" in names
    assert "evaluation_generated" in names
    assert "evaluation_approved" in names
    assert "skill_test_generated" in names


def test_evaluation_is_persisted_on_the_candidate_document(client, uploader, sample_resume):
    candidate_id = upload_candidate(uploader, sample_resume)
    approve_profile(client, candidate_id)
    client.post(f"/api/candidates/{candidate_id}/evaluate")

    detail = client.get(f"/api/candidates/{candidate_id}").json()
    stored = get_collection(COLLECTION_CANDIDATES).find_one({"name": "Aarav Sharma"})

    assert detail["evaluation"]["status"] == "draft"
    assert stored["evaluation"]["assessments"]

