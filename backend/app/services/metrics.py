"""Recruitment metrics used by the dashboard."""

from __future__ import annotations

from app.core.constants import (
    COLLECTION_CANDIDATES,
    COLLECTION_ROLES,
    EVALUATION_APPROVED,
    PIPELINE_STAGES,
    SKILL_TEST_APPROVED,
    PipelineStage,
)
from app.db.mongo import get_collection


def build_dashboard_summary() -> dict:
    """Aggregate the counters shown on the dashboard."""
    candidates = get_collection(COLLECTION_CANDIDATES)
    roles = get_collection(COLLECTION_ROLES)

    counts_by_stage = {
        entry["_id"]: entry["count"]
        for entry in candidates.aggregate([{"$group": {"_id": "$stage", "count": {"$sum": 1}}}])
        if entry.get("_id")
    }

    def count(stage: PipelineStage) -> int:
        return counts_by_stage.get(stage.value, 0)

    # Workflow queues (not stage counts):
    #  - awaiting_review: uploaded resumes whose profile is not approved yet.
    #  - awaiting_skill_test: evaluation approved but skill test not approved.
    awaiting_review = candidates.count_documents(
        {"profile_reviewed": {"$ne": True}, "resume_filename": {"$ne": None}}
    )
    awaiting_skill_test = candidates.count_documents(
        {
            "evaluation.status": EVALUATION_APPROVED,
            "$or": [
                {"skill_test": {"$exists": False}},
                {"skill_test": {"$in": [None]}},
                {"skill_test.status": {"$ne": SKILL_TEST_APPROVED}},
            ],
        }
    )

    return {
        "total_candidates": candidates.estimated_document_count(),
        "under_review": count(PipelineStage.UNDER_REVIEW),
        "skill_tests": count(PipelineStage.SKILL_TEST),
        "interviews": count(PipelineStage.INTERVIEW),
        "selected": count(PipelineStage.SELECTED),
        "rejected": count(PipelineStage.REJECTED),
        "new": count(PipelineStage.NEW),
        "active_roles": roles.count_documents({"status": "active"}),
        "total_roles": roles.estimated_document_count(),
        "awaiting_review": awaiting_review,
        "awaiting_skill_test": awaiting_skill_test,
        "pipeline": [
            {"stage": stage, "count": counts_by_stage.get(stage, 0)} for stage in PIPELINE_STAGES
        ],
    }
