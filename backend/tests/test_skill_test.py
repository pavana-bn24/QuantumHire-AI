"""Milestone 3 - skill test: gating, editing, approval, stage + webhook."""

MISSING_OBJECT_ID = "000000000000000000000000"

APPROVED_PROFILE = {
    "name": "Priya Nair",
    "email": "priya.nair@example.com",
    "skills": ["communication"],
    "technologies": ["React", "FastAPI", "MongoDB"],
    "ai_experience": ["Built a RAG assistant with LangChain."],
}


def ready_candidate(client, uploader, sample_resume) -> str:
    """Upload -> approve profile -> evaluate -> approve evaluation (skill test drafted)."""
    candidate_id = uploader(sample_resume).json()["candidate_id"]
    client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={**APPROVED_PROFILE, "email": "priya.nair@example.com", "reviewed": True},
    )
    client.post(f"/api/candidates/{candidate_id}/evaluate")
    client.post(f"/api/candidates/{candidate_id}/evaluation/approve")
    return candidate_id


# --- gating -----------------------------------------------------------------


def test_skill_test_requires_an_approved_evaluation(client, uploader, sample_resume):
    """Generating a test before the evaluation is approved is a 409."""
    candidate_id = uploader(sample_resume).json()["candidate_id"]
    client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={**APPROVED_PROFILE, "email": "priya.nair@example.com", "reviewed": True},
    )
    client.post(f"/api/candidates/{candidate_id}/evaluate")  # draft, not approved

    response = client.post(f"/api/candidates/{candidate_id}/generate-test")

    assert response.status_code == 409
    assert "Approve the evaluation first" in response.json()["detail"]


def test_skill_test_requires_any_evaluation(client):
    created = client.post(
        "/api/candidates", json={"name": "No Eval", "email": "no.eval@example.com"}
    ).json()

    response = client.post(f"/api/candidates/{created['id']}/generate-test")

    assert response.status_code == 409


def test_skill_test_absent_before_generation(client, uploader, sample_resume):
    candidate_id = uploader(sample_resume).json()["candidate_id"]

    assert client.get(f"/api/candidates/{candidate_id}/skill-test").status_code == 404


# --- generation + editing ---------------------------------------------------


def test_generated_skill_test_has_questions_and_draft_status(client, uploader, sample_resume):
    candidate_id = ready_candidate(client, uploader, sample_resume)

    # Approval already drafted one; a manual regeneration must still work.
    response = client.post(f"/api/candidates/{candidate_id}/generate-test")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert 3 <= len(body["questions"]) <= 6
    assert all(q["prompt"] for q in body["questions"])
    assert all(q["focus"] for q in body["questions"])


def test_skill_test_targets_the_evaluation_gaps(client, uploader, sample_resume):
    candidate_id = ready_candidate(client, uploader, sample_resume)

    evaluation = client.get(f"/api/candidates/{candidate_id}/evaluation").json()
    skill_test = client.get(f"/api/candidates/{candidate_id}/skill-test").json()

    weak = {
        a["capability"]
        for a in evaluation["assessments"]
        if a["rating"] in {"Not Demonstrated", "Partially Demonstrated", "Needs Verification"}
    }
    focused = {q["focus"] for q in skill_test["questions"]}
    assert focused & weak, "questions should target at least one weak area"



def test_recruiter_can_edit_the_draft_skill_test(client, uploader, sample_resume):
    candidate_id = ready_candidate(client, uploader, sample_resume)

    response = client.put(
        f"/api/candidates/{candidate_id}/skill-test",
        json={
            "title": "Edited Skill Test",
            "duration_minutes": 45,
            "instructions": "Answer in a single markdown file.",
            "questions": [
                {"prompt": "Explain indexing strategy", "type": "knowledge", "focus": "databases"},
                {"prompt": "Design a RAG flow", "type": "system_design", "focus": "rag"},
                {"prompt": "Outline your API error model", "type": "knowledge", "focus": "rest_apis"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Edited Skill Test"
    assert body["duration_minutes"] == 45
    assert len(body["questions"]) == 3
    assert body["status"] == "draft"
    events = client.get(f"/api/candidates/{candidate_id}/events").json()
    assert any(event["event"] == "skill_test_updated" for event in events)


def test_skill_test_edit_rejects_unknown_keys_and_empty_questions(client, uploader, sample_resume):
    candidate_id = ready_candidate(client, uploader, sample_resume)

    unknown = client.put(f"/api/candidates/{candidate_id}/skill-test", json={"score": 90})
    empty = client.put(f"/api/candidates/{candidate_id}/skill-test", json={"questions": []})

    assert unknown.status_code == 422
    assert empty.status_code == 422


# --- approval ---------------------------------------------------------------


def test_approving_skill_test_moves_candidate_to_skill_test_stage(client, uploader, sample_resume):
    candidate_id = ready_candidate(client, uploader, sample_resume)

    response = client.post(f"/api/candidates/{candidate_id}/skill-test/approve")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    assert response.json()["approved_by"] == "recruiter@quantumhire.ai"

    detail = client.get(f"/api/candidates/{candidate_id}").json()
    assert detail["stage"] == "Skill Test"
    assert detail["skill_test"]["status"] == "approved"


def test_skill_test_approval_fires_a_webhook_event(client, uploader, sample_resume):
    """No EXTERNAL_WEBHOOK_URL in tests -> delivery is simulated, never blocking."""
    candidate_id = ready_candidate(client, uploader, sample_resume)
    client.post(f"/api/candidates/{candidate_id}/skill-test/approve")

    events = client.get(f"/api/candidates/{candidate_id}/events").json()
    webhook_events = [e for e in events if e["event"].startswith("webhook_")]

    assert webhook_events, "expected a webhook workflow event after approval"
    metadata = webhook_events[0]["metadata"]
    assert metadata["delivery"] in {"simulated", "delivered", "failed"}
    if metadata["delivery"] == "simulated":
        assert webhook_events[0]["event"] == "webhook_simulated"
    elif metadata["delivery"] == "failed":
        assert webhook_events[0]["event"] == "webhook_failed"
    assert metadata["event"] == "skill_test_approved"
    assert set(metadata["payload"]) >= {
        "candidate_id", "candidate_name", "role", "stage", "skill_test_id", "timestamp",
    }
    assert metadata["payload"]["stage"] == "Skill Test"


def test_approved_skill_test_is_locked_and_cannot_be_approved_twice(
    client, uploader, sample_resume
):
    candidate_id = ready_candidate(client, uploader, sample_resume)
    client.post(f"/api/candidates/{candidate_id}/skill-test/approve")

    edit = client.put(f"/api/candidates/{candidate_id}/skill-test", json={"title": "Too late"})
    again = client.post(f"/api/candidates/{candidate_id}/skill-test/approve")

    assert edit.status_code == 409
    assert again.status_code == 409


def test_approve_skill_test_without_a_test_returns_404(client):
    created = client.post(
        "/api/candidates", json={"name": "No Test", "email": "no.test@example.com"}
    ).json()

    assert client.post(f"/api/candidates/{created['id']}/skill-test/approve").status_code == 404


def test_approve_skill_test_unknown_candidate_returns_404(client):
    response = client.post(f"/api/candidates/{MISSING_OBJECT_ID}/skill-test/approve")

    assert response.status_code == 404
