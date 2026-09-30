"""Structured candidate profile models.

These models are the *evidence contract* between resume extraction, the recruiter
review screen and any later AI evaluation:

* Every field is optional/empty-by-default so the model can faithfully represent
  "the resume did not state this".
* Nothing is inferred or defaulted to a plausible value - an absent fact must
  round-trip as ``None`` or an empty list.
"""

from pydantic import BaseModel, ConfigDict, Field


class WorkExperienceEntry(BaseModel):
    """One employment record, exactly as supported by the resume."""

    company: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    """One project record."""

    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    link: str | None = None


class EducationEntry(BaseModel):
    """One education record."""

    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CandidateProfile(BaseModel):
    """Structured candidate profile extracted from a resume.

    ``name``/``email``/``phone`` are scalars; everything that can legitimately
    have multiple values is a list.
    """

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None

    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    work_experience: list[WorkExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)

    ai_experience: list[str] = Field(default_factory=list)
    development_experience: list[str] = Field(default_factory=list)
    tools_platforms: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        """True when nothing at all could be grounded in the resume."""
        return not any(
            [
                self.name,
                self.email,
                self.phone,
                self.skills,
                self.technologies,
                self.work_experience,
                self.projects,
                self.education,
                self.ai_experience,
                self.development_experience,
                self.tools_platforms,
                self.achievements,
            ]
        )


class ResumeMetadata(BaseModel):
    """Provenance stored alongside the profile so evidence can be traced."""

    resume_filename: str | None = None
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
    profile_reviewed: bool = False
    profile_reviewed_at: str | None = None
