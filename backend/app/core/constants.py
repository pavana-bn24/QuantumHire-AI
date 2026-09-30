"""Shared domain constants.

Keeping the pipeline definition in one place means the API, the seed data and
the React UI all agree on the same stages.
"""

from enum import Enum


class PipelineStage(str, Enum):
    """Recruitment pipeline stages, in workflow order."""

    NEW = "New"
    UNDER_REVIEW = "Under Review"
    SKILL_TEST = "Skill Test"
    INTERVIEW = "Interview"
    SELECTED = "Selected"
    REJECTED = "Rejected"


#: Ordered list of every pipeline stage - the single source of truth.
PIPELINE_STAGES: list[str] = [stage.value for stage in PipelineStage]

#: Terminal pipeline stages (no further movement expected).
TERMINAL_STAGES: set[str] = {PipelineStage.SELECTED.value, PipelineStage.REJECTED.value}

#: MongoDB collection names.
COLLECTION_ROLES = "roles"
COLLECTION_CANDIDATES = "candidates"
COLLECTION_WORKFLOW_EVENTS = "workflow_events"
COLLECTION_USERS = "users"

#: The four allowed capability ratings (no numeric scores anywhere).
RATING_DEMONSTRATED = "Demonstrated"
RATING_PARTIAL = "Partially Demonstrated"
RATING_ABSENT = "Not Demonstrated"
RATING_NEEDS_VERIFICATION = "Needs Verification"
CAPABILITY_RATINGS: list[str] = [
    RATING_DEMONSTRATED,
    RATING_PARTIAL,
    RATING_ABSENT,
    RATING_NEEDS_VERIFICATION,
]

#: Evaluation workflow states.
EVALUATION_DRAFT = "draft"
EVALUATION_APPROVED = "approved"

#: Skill-test workflow states.
SKILL_TEST_DRAFT = "draft"
SKILL_TEST_APPROVED = "approved"
