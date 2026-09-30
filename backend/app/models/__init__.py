"""Pydantic models shared by the API layer (request/response schemas)."""

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import (
    CAPABILITY_RATINGS,
    EVALUATION_DRAFT,
    PIPELINE_STAGES,
    SKILL_TEST_DRAFT,
)
from app.models.profile import (
    CandidateProfile,
    EducationEntry,
    ProjectEntry,
    ResumeMetadata,
    WorkExperienceEntry,
)

__all__ = [
    "AuthResponse",
    "Candidate",
    "CandidateCreate",
    "CandidateDetail",
    "CandidateProfile",
    "CapabilityAssessment",
    "DatabaseHealthResponse",
    "DashboardSummary",
    "EducationEntry",
    "Evaluation",
    "EvaluationCreate",
    "EvaluationUpdate",
    "HealthResponse",
    "KnowledgeChunk",
    "KnowledgeSearchResponse",
    "LoginRequest",
    "PipelineStageCount",
    "ProfileUpdateRequest",
    "ProjectEntry",
    "PublicUser",
    "Requirement",
    "RequirementBase",
    "ResumeExtractionInfo",
    "ResumeMetadata",
    "ResumeUploadResponse",
    "Role",
    "RoleCreate",
    "SkillTest",
    "SkillTestCreate",
    "SkillTestQuestion",
    "SkillTestUpdate",
    "WorkflowEvent",
    "WorkExperienceEntry",
]


class HealthResponse(BaseModel):
    """Response returned by ``GET /api/health``."""

    status: str = "ok"


class DatabaseHealthResponse(BaseModel):
    """Response returned by ``GET /api/health/db``."""

    status: str
    database: str
    connected: bool


class RequirementBase(BaseModel):
    """A single hiring requirement for a role."""

    key: str = Field(..., description="Stable machine-readable identifier")
    label: str = Field(..., description="Human readable requirement name")
    category: str = Field(..., description="Grouping used for reporting")
    weight: int = Field(0, ge=0, le=100, description="Relative importance for scoring")
    description: str = Field("", description="What this requirement covers")


class Requirement(RequirementBase):
    """Requirement as returned by the API."""


class RoleBase(BaseModel):
    """Fields shared by role create/read models."""

    title: str = Field(..., min_length=2, max_length=120)
    department: str = "Engineering"
    location: str = "Remote"
    employment_type: str = "Full-time"
    seniority: str = "Mid-Senior"
    status: str = "active"
    description: str = ""
    requirements: list[Requirement] = Field(default_factory=list)


class RoleCreate(RoleBase):
    """Payload for ``POST /api/roles``."""


class Role(RoleBase):
    """Role returned by the API."""

    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CandidateCreate(BaseModel):
    """Payload for ``POST /api/candidates``."""

    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., description="Candidate email address")
    role_id: str | None = None
    role_title: str | None = None
    stage: str = Field(default=PIPELINE_STAGES[0])
    source: str = "Direct"
    location: str | None = None
    experience_years: float | None = Field(default=None, ge=0, le=60)
    skills: list[str] = Field(default_factory=list)
    notes: str | None = None


class Candidate(CandidateCreate):
    """Candidate returned by the API (list view).

    Resume-related fields are additive: candidates created before milestone 2
    (and seeded demo rows) simply report ``has_resume=False``.
    """

    model_config = ConfigDict(extra="ignore")

    # A resume upload may not state an e-mail address at all.
    email: str | None = None

    id: str
    created_at: str | None = None
    updated_at: str | None = None
    ai_summary: str | None = None
    scores: dict[str, Any] = Field(default_factory=dict)

    # --- resume evidence (milestone 2) -------------------------------------
    has_resume: bool = False
    resume_filename: str | None = None
    profile_reviewed: bool = False
    extracted_profile: CandidateProfile | None = None


class CandidateDetail(Candidate):
    """Candidate returned by the detail endpoint, including the raw evidence."""

    resume_text: str | None = None
    resume_content_type: str | None = None
    resume_size_bytes: int | None = None
    resume_sha256: str | None = None
    resume_page_count: int | None = None
    resume_char_count: int | None = None
    resume_word_count: int | None = None
    uploaded_at: str | None = None
    extracted_at: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
    profile_reviewed_at: str | None = None
    #: Milestone 3: AI evaluation + skill test live on the candidate document.
    evaluation: "Evaluation | None" = None
    skill_test: "SkillTest | None" = None


class ResumeExtractionInfo(BaseModel):
    """Diagnostics about how a profile was produced."""

    provider: str
    model: str
    page_count: int
    char_count: int
    word_count: int
    warnings: list[str] = Field(default_factory=list)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    extracted_at: str


class ResumeUploadResponse(BaseModel):
    """Response of ``POST /api/candidates/upload``."""

    candidate_id: str
    candidate: CandidateDetail
    extracted_profile: CandidateProfile
    extraction: ResumeExtractionInfo


class ProfileUpdateRequest(CandidateProfile):
    """Payload for ``PUT /api/candidates/{id}/profile``.

    Contract (mirrors ``frontend/src/constants/profile.js``): every profile
    field is sent **flat at the top level** next to ``reviewed`` - e.g.
    ``{name, email, skills, ..., reviewed: true}``.

    Unknown keys are rejected with a 422 instead of being silently dropped.
    ``CandidateProfile`` ignores extras so provider output can carry junk keys,
    but a *recruiter edit* that misspells a field (or nests the profile under
    ``extracted_profile``) must fail loudly - otherwise the endpoint would
    quietly overwrite the extracted evidence with an empty profile.
    """

    model_config = ConfigDict(extra="forbid")

    reviewed: bool = Field(
        default=True,
        description="Set to true to approve the profile as candidate evidence",
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_nested_profile_payload(cls, data: Any) -> Any:
        if isinstance(data, dict) and "extracted_profile" in data:
            raise ValueError(
                "Profile fields must be sent flat at the top level "
                "(name, email, skills, ...), not nested under 'extracted_profile'."
            )
        return data


class PipelineStageCount(BaseModel):
    """Candidate count for a single pipeline stage."""

    stage: str
    count: int


class DashboardSummary(BaseModel):
    """Aggregated metrics powering the dashboard."""

    total_candidates: int
    under_review: int
    skill_tests: int
    interviews: int
    selected: int
    rejected: int
    new: int
    active_roles: int
    total_roles: int
    #: Workflow queues (not stage counts): profiles awaiting recruiter approval
    #: and approved profiles whose skill test has not been approved yet.
    awaiting_review: int = 0
    awaiting_skill_test: int = 0
    pipeline: list[PipelineStageCount] = Field(default_factory=list)


# --- Milestone 3: AI evaluation -------------------------------------------


class CapabilityAssessment(BaseModel):
    """One role requirement assessed against approved evidence.

    ``rating`` is restricted to the four-value qualitative scale - numeric
    scores are deliberately not part of the contract.
    """

    model_config = ConfigDict(extra="ignore")

    capability: str = Field(..., description="Stable requirement key (e.g. 'rag')")
    label: str = Field("", description="Human readable requirement name")
    category: str = Field("", description="Grouping used for reporting")
    rating: str = Field(..., description="One of CAPABILITY_RATINGS")
    evidence: list[str] = Field(default_factory=list, description="Approved-profile evidence quotes")
    notes: str = ""

    @model_validator(mode="after")
    def _validate_rating(self) -> "CapabilityAssessment":
        if self.rating not in CAPABILITY_RATINGS:
            raise ValueError(
                f"rating must be one of: {', '.join(CAPABILITY_RATINGS)} (got '{self.rating}')"
            )
        return self


class EvaluationCreate(BaseModel):
    """Payload for ``POST /api/candidates/{id}/evaluate`` (server fills evidence)."""


class Evaluation(BaseModel):
    """Structured AI evaluation - ten top-level fields.

    1 candidate_id, 2 role_id, 3 role_title, 4 summary, 5 strengths, 6 gaps,
    7 assessments, 8 follow_up_questions, 9 knowledge_sources, 10 status.
    """

    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    role_id: str | None = None
    role_title: str | None = None
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    # Explicit capability-oriented contract used by the recruiter workspace.
    # Legacy fields above remain available for existing clients.
    executive_summary: str = ""
    relevant_experience: list[str] = Field(default_factory=list)
    demonstrated_strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    ai_first_readiness: str = ""
    implementation_capability: str = ""
    learning_research_readiness: str = ""
    evidence_gaps: list[str] = Field(default_factory=list)
    recommended_next_step: str = ""
    assessments: list[CapabilityAssessment] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)
    status: str = EVALUATION_DRAFT
    # Provenance metadata (kept out of the ten-field contract).
    provider: str | None = None
    model: str | None = None
    generated_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None


class EvaluationUpdate(BaseModel):
    """Recruiter edits applied to a draft evaluation before approval."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str | None = None
    summary: str | None = None
    relevant_experience: list[str] | None = None
    demonstrated_strengths: list[str] | None = None
    strengths: list[str] | None = None
    skill_gaps: list[str] | None = None
    gaps: list[str] | None = None
    ai_first_readiness: str | None = None
    implementation_capability: str | None = None
    learning_research_readiness: str | None = None
    evidence_gaps: list[str] | None = None
    recommended_next_step: str | None = None
    assessments: list[CapabilityAssessment] | None = None
    follow_up_questions: list[str] | None = None


# --- Milestone 3: skill tests ----------------------------------------------


class SkillTestQuestion(BaseModel):
    """A single skill-test question (recruiter-editable)."""

    model_config = ConfigDict(extra="ignore")

    prompt: str = Field(..., min_length=1)
    type: str = Field(default="coding", description="coding | system_design | scenario | knowledge")
    focus: str = Field("", description="Requirement key this question targets")
    sample_answer: str = ""


class SkillTestBase(BaseModel):
    """Fields shared by create/update/read skill-test models.

    The assignment brief fields (business problem, objective, requirements,
    technical requirements, deliverables, evaluation criteria, time limit)
    are additive: legacy/LLM-generated payloads that only carry
    title/instructions/questions still validate.
    """

    title: str = Field(default="", max_length=200)
    business_problem: str = ""
    objective: str = ""
    requirements: list[str] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    expected_deliverables: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    time_limit: str = ""
    duration_minutes: int = Field(default=60, ge=5, le=480)
    instructions: str = ""
    questions: list[SkillTestQuestion] = Field(default_factory=list)


class SkillTestCreate(SkillTestBase):
    """Payload the AI (or recruiter) uses when drafting a test."""


class SkillTestUpdate(SkillTestCreate):
    """Recruiter edits before approval; unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")


class SkillTest(SkillTestBase):
    """Skill test stored on the candidate document."""

    model_config = ConfigDict(extra="ignore")

    skill_test_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = SKILL_TEST_DRAFT
    provider: str | None = None
    model: str | None = None
    generated_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None
    #: ``source#heading`` citations of the retrieved skill-test guidelines.
    knowledge_sources: list[str] = Field(default_factory=list)


# --- Milestone 3: workflow events ------------------------------------------


class WorkflowEvent(BaseModel):
    """Append-only record of an automation trigger."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    candidate_id: str
    event: str
    actor: str = "system"
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Milestone 3: auth ------------------------------------------------------


class LoginRequest(BaseModel):
    """Payload for ``POST /api/auth/login``."""

    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class PublicUser(BaseModel):
    """User shape safe to return from auth endpoints."""

    id: str = ""
    email: str
    name: str = ""
    role: str = "recruiter"


class AuthResponse(BaseModel):
    """JWT login response."""

    access_token: str
    token_type: str = "bearer"
    user: PublicUser


# --- Milestone 3: knowledge retrieval (RAG) --------------------------------


class KnowledgeChunk(BaseModel):
    """A retrieved knowledge snippet returned to the caller / LLM prompt."""

    source: str
    heading: str
    text: str
    score: float = 0.0


class KnowledgeSearchResponse(BaseModel):
    """Response of ``GET /api/knowledge/search``."""

    query: str
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
