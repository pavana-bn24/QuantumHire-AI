"""Milestone 3 - agent tool calling, RAG search, webhooks and activity events."""

from app.core.constants import COLLECTION_WORKFLOW_EVENTS
from app.db.mongo import get_collection

MISSING_OBJECT_ID = "000000000000000000000000"

APPROVED_PROFILE = {
    "name": "Aarav Sharma",
    "email": "aarav.sharma@example.com",
    "technologies": ["Python", "FastAPI", "React", "MongoDB", "Docker"],
    "ai_experience": ["Built a RAG assistant with LangChain."],
}


def approved_candidate(client, uploader, sample_resume) -> str:
    candidate_id = uploader(sample_resume).json()["candidate_id"]
    client.put(
        f"/api/candidates/{candidate_id}/profile",
        json={**APPROVED_PROFILE, "reviewed": True},
    )
    return candidate_id


def invoke(client, tool: str, arguments: dict | None = None):
    return client.post("/api/agents/invoke", json={"tool": tool, "arguments": arguments or {}})


# --- tool catalog + allowlist ----------------------------------------------


def test_tool_catalog_exposes_the_six_allowlisted_tools(client):
    response = client.get("/api/agents/tools")

    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()}
    assert names == {
        "get_candidate_profile",
        "get_role_requirements",
        "get_recruitment_guidelines",
        "evaluate_candidate",
        "generate_skill_test",
        "update_candidate_status",
    }
    assert all("parameters" in tool for tool in response.json())


def test_unknown_tool_is_rejected(client):
    response = invoke(client, "rm_minus_rf", {"path": "/"})

    assert response.status_code == 400
    assert "Unknown tool" in response.json()["detail"]


def test_tool_missing_required_argument_is_rejected(client):
    response = invoke(client, "get_candidate_profile", {})

    assert response.status_code == 400
    assert "missing required argument" in response.json()["detail"]


# --- read tools -------------------------------------------------------------


def test_get_candidate_profile_marks_output_untrusted(client, uploader, sample_resume):
    candidate_id = uploader(sample_resume).json()["candidate_id"]

    response = invoke(client, "get_candidate_profile", {"candidate_id": candidate_id})

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["candidate_id"] == candidate_id
    assert result["untrusted_data"] is True
    assert "never instructions" in result["note"]


def test_get_candidate_profile_unknown_id_returns_404(client):
    response = invoke(client, "get_candidate_profile", {"candidate_id": MISSING_OBJECT_ID})

    assert response.status_code == 404


def test_get_role_requirements_returns_requirement_keys(client):
    response = invoke(client, "get_role_requirements", {})

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["requirements"]
    assert "key" in result["requirements"][0]



# --- mutating tools ---------------------------------------------------------


def test_ai_tool_cannot_move_candidate_stage(client):
    created = client.post(
        "/api/candidates", json={"name": "Tool Move", "email": "tool.move@example.com"}
    ).json()

    response = invoke(
        client, "update_candidate_status", {"candidate_id": created["id"], "stage": "Interview"}
    )

    assert response.status_code == 403
    assert "cannot move candidates" in response.json()["detail"].lower()

    detail = client.get(f"/api/candidates/{created['id']}").json()
    assert detail["stage"] == "New"


def test_update_candidate_status_rejects_invalid_stage(client):
    created = client.post(
        "/api/candidates", json={"name": "Bad Stage", "email": "bad.stage@example.com"}
    ).json()

    response = invoke(
        client, "update_candidate_status", {"candidate_id": created["id"], "stage": "Hired"}
    )

    assert response.status_code == 400
    assert "Unknown stage" in response.json()["detail"]


def test_evaluate_candidate_tool_respects_the_approval_gate(client, uploader, sample_resume):
    candidate_id = uploader(sample_resume).json()["candidate_id"]

    blocked = invoke(client, "evaluate_candidate", {"candidate_id": candidate_id})
    assert blocked.status_code == 409

    client.put(
        f"/api/candidates/{candidate_id}/profile", json={**APPROVED_PROFILE, "reviewed": True}
    )
    allowed = invoke(client, "evaluate_candidate", {"candidate_id": candidate_id})

    assert allowed.status_code == 200
    assert allowed.json()["result"]["status"] == "draft"


# --- RAG search -------------------------------------------------------------


def test_knowledge_search_returns_ranked_chunks(client):
    response = client.get("/api/knowledge/search", params={"q": "skill test duration"})

    assert response.status_code == 200
    body = response.json()
    assert body["chunks"]
    assert body["chunks"][0]["score"] >= body["chunks"][-1]["score"]
    assert any("skill_test" in source for source in body["sources"])


def test_knowledge_search_with_no_overlap_returns_nothing(client):
    response = client.get("/api/knowledge/search", params={"q": "zzzzqqqq unrelated"})

    assert response.status_code == 200
    assert response.json()["chunks"] == []


def test_knowledge_search_requires_a_query(client):
    assert client.get("/api/knowledge/search", params={"q": "a"}).status_code == 422


# --- webhooks ---------------------------------------------------------------


def test_inbound_webhook_is_accepted_and_recorded(client):
    created = client.post(
        "/api/candidates", json={"name": "Hooked", "email": "hooked@example.com"}
    ).json()

    response = client.post(
        "/api/integrations/recruitment-webhook",
        json={
            "event": "interview_scheduled",
            "candidate_id": created["id"],
            "source": "ats",
            "data": {"when": "2026-01-05"},
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    events = client.get(f"/api/candidates/{created['id']}/events").json()
    assert any(e["event"] == "external_interview_scheduled" for e in events)


def test_inbound_webhook_rejects_unknown_fields(client):
    response = client.post(
        "/api/integrations/recruitment-webhook", json={"event": "x", "bogus": 1}
    )

    assert response.status_code == 422


def test_outbound_webhook_is_simulated_without_a_configured_url(client):
    config = client.get("/api/integrations/webhook-config")
    ping = client.post("/api/integrations/webhook/test")

    assert config.json()["configured"] is False
    assert ping.status_code == 200
    assert ping.json()["delivery"] == "simulated"


# --- activity timeline ------------------------------------------------------


def test_events_are_returned_newest_first(client, uploader, sample_resume):
    candidate_id = approved_candidate(client, uploader, sample_resume)
    client.post(f"/api/candidates/{candidate_id}/evaluate")

    events = client.get(f"/api/candidates/{candidate_id}/events").json()

    assert [e["event"] for e in events][:2] == ["evaluation_generated", "profile_approved"]
    assert all(e["actor"] for e in events)
    assert all(e["timestamp"] for e in events)


def test_events_for_unknown_candidate_returns_404(client):
    assert client.get(f"/api/candidates/{MISSING_OBJECT_ID}/events").status_code == 404


def test_stage_change_event_records_both_stages(client):
    created = client.post(
        "/api/candidates", json={"name": "Mover", "email": "mover@example.com"}
    ).json()

    client.patch(f"/api/candidates/{created['id']}/stage", params={"stage": "Interview"})

    events = client.get(f"/api/candidates/{created['id']}/events").json()
    change = next(e for e in events if e["event"] == "stage_changed")
    assert change["metadata"]["from"] == "New"
    assert change["metadata"]["to"] == "Interview"


def test_candidate_creation_records_an_event(client):
    created = client.post(
        "/api/candidates", json={"name": "Tracked", "email": "tracked@example.com"}
    ).json()

    events = client.get(f"/api/candidates/{created['id']}/events").json()

    assert events[0]["event"] == "candidate_created"
    assert events[0]["actor"] == "recruiter@quantumhire.ai"


def test_workflow_events_are_stored_as_documents(client, uploader, sample_resume):
    """Events are queryable for external analytics (indexed collection)."""
    candidate_id = approved_candidate(client, uploader, sample_resume)

    stored = list(
        get_collection(COLLECTION_WORKFLOW_EVENTS).find({"candidate_id": candidate_id})
    )

    assert stored
    assert all(entry["event"] for entry in stored)


# --- dashboard workflow counters --------------------------------------------


def test_dashboard_counts_awaiting_review(client, uploader, sample_resume):
    """An uploaded, not-yet-approved profile shows up as "Awaiting review"."""
    before = client.get("/api/dashboard/summary").json()["awaiting_review"]

    uploader(sample_resume)

    after = client.get("/api/dashboard/summary").json()
    assert after["awaiting_review"] == before + 1


def test_dashboard_counts_awaiting_skill_test_until_approved(client, uploader, sample_resume):
    candidate_id = approved_candidate(client, uploader, sample_resume)
    client.post(f"/api/candidates/{candidate_id}/evaluate")
    client.post(f"/api/candidates/{candidate_id}/evaluation/approve")

    queued = client.get("/api/dashboard/summary").json()["awaiting_skill_test"]
    assert queued == 1

    client.post(f"/api/candidates/{candidate_id}/skill-test/approve")

    assert client.get("/api/dashboard/summary").json()["awaiting_skill_test"] == 0


def test_get_recruitment_guidelines_returns_cited_chunks(client):
    response = invoke(client, "get_recruitment_guidelines", {"query": "skill test approval"})

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["chunks"]
    assert all("source" in chunk and "heading" in chunk for chunk in result["chunks"])
