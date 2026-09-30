"""AI candidate evaluation (milestone 3).

Contract highlights
-------------------
* Evaluation is **gated**: the recruiter must have approved the profile first
  (``profile_reviewed == true``), otherwise :class:`EvaluationNotAllowedError`.
* Output is the structured ten-field :class:`Evaluation` with the four-value
  qualitative rating scale - **no numeric scores, no ranking, ever**.
* Two providers: ``stub`` builds a deterministic, evidence-grounded evaluation
  offline (tests/demos), ``openai`` asks the model and validates its JSON.
  Anything else raises :class:`EvaluationUnavailableError`.
* Retrieved knowledge (RAG) chunks are cited in ``knowledge_sources``.
"""

from __future__ import annotations

import json
import logging
import re

from app.ai.base import InvalidProviderOutputError, ProviderError, ProviderUnavailableError
from app.ai.chat import chat_json, validate_structured
from app.ai.factory import get_provider_name
from app.ai.prompts import (
    EVALUATION_SYSTEM_PROMPT,
    build_evaluation_user_prompt,
)
from app.core.constants import (
    CAPABILITY_RATINGS,
    EVALUATION_DRAFT,
    RATING_ABSENT,
    RATING_DEMONSTRATED,
    RATING_NEEDS_VERIFICATION,
    RATING_PARTIAL,
)
from app.core.serialization import utc_now
from app.models import (
    CapabilityAssessment,
    CandidateProfile,
    Evaluation,
    Requirement,
)
from app.services.knowledge import knowledge_sources_for, search_knowledge

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Base class for evaluation failures with an API-safe message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvaluationUnavailableError(EvaluationError):
    """No usable AI provider is configured (HTTP 503)."""


class EvaluationFailedError(EvaluationError):
    """Provider ran but failed or returned invalid structured output (HTTP 502)."""


class EvaluationNotAllowedError(EvaluationError):
    """Preconditions for evaluating are not met (HTTP 409)."""


# --- deterministic (stub) builder -------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9+#.]{2,}")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "has", "have",
    "not", "but", "its", "into", "you", "your", "all", "any", "can", "may",
    "should", "must", "will", "would", "work", "working", "experience",
    "strong", "good", "well", "using", "used", "use", "etc", "able",
}


def _capability_status(assessments: list[CapabilityAssessment], terms: tuple[str, ...]) -> str:
    """Summarise matching requirements without turning missing evidence into a claim."""
    matches = [a.rating for a in assessments if any(
        term in f"{a.capability} {a.label} {a.category}".lower() for term in terms
    )]
    if not matches:
        return RATING_NEEDS_VERIFICATION
    for rating in (RATING_DEMONSTRATED, RATING_PARTIAL, RATING_NEEDS_VERIFICATION, RATING_ABSENT):
        if rating in matches:
            return rating
    return RATING_NEEDS_VERIFICATION


def _explicit_fields(
    profile: CandidateProfile,
    assessments: list[CapabilityAssessment],
    strengths: list[str],
    gaps: list[str],
    summary: str,
) -> dict:
    experience = [
        " ".join(filter(None, [entry.title, entry.company, entry.description]))
        for entry in profile.work_experience
    ]
    return {
        "executive_summary": summary,
        "relevant_experience": [item for item in experience if item],
        "demonstrated_strengths": list(dict.fromkeys(strengths)),
        "skill_gaps": list(dict.fromkeys(gaps)),
        "ai_first_readiness": _capability_status(assessments, ("ai", "llm", "rag")),
        "implementation_capability": _capability_status(
            assessments, ("backend", "frontend", "api", "database", "development")
        ),
        "learning_research_readiness": _capability_status(
            assessments, ("learning", "research", "communication")
        ),
        "evidence_gaps": [
            f"{a.label}: evidence is not present in the approved profile."
            for a in assessments if a.rating == RATING_ABSENT
        ],
        "recommended_next_step": (
            "Use the personalized skill test to verify the recorded gaps and any "
            "Needs Verification areas before making a hiring decision."
        ),
    }


def _requirement_tokens(requirement: Requirement) -> set[str]:
    """Searchable tokens for a requirement (key + label + description)."""
    text = f"{requirement.key} {requirement.label} {requirement.description}".lower()
    text = text.replace("_", " ").replace("-", " ")
    return {t for t in _WORD_RE.findall(text) if t not in _STOPWORDS}


def _profile_evidence(profile: CandidateProfile) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split profile evidence into (strong, weak) ``(source, quote)`` pairs.

    Strong = explicitly listed facts (skills/technologies/tooling).
    Weak   = narrative claims (experience/projects/achievements).
    """
    strong: list[tuple[str, str]] = []
    weak: list[tuple[str, str]] = []

    for value in [*profile.skills, *profile.technologies, *profile.tools_platforms]:
        if value:
            strong.append((value.lower(), value))
    for value in [*profile.ai_experience, *profile.development_experience]:
        if value:
            weak.append((value.lower(), value))
    for entry in profile.work_experience:
        parts = [p for p in [entry.title, entry.company, entry.description, ", ".join(entry.technologies)] if p]
        if parts:
            weak.append((" ".join(parts).lower(), " ".join(parts)))
    for entry in profile.projects:
        parts = [p for p in [entry.name, entry.description, ", ".join(entry.technologies)] if p]
        if parts:
            weak.append((" ".join(parts).lower(), " ".join(parts)))
    for value in profile.achievements:
        if value:
            weak.append((value.lower(), value))

    return strong, weak




def build_deterministic_evaluation(
    *,
    candidate_id: str,
    profile: CandidateProfile,
    requirements: list[Requirement],
    role_id: str | None,
    role_title: str | None,
    knowledge_sources: list[str],
) -> Evaluation:
    """Evidence-grounded evaluation built without any LLM (offline ``stub``)."""
    strong, weak = _profile_evidence(profile)
    achievement_sources = {a.lower() for a in profile.achievements if a}

    assessments: list[CapabilityAssessment] = []
    strengths: list[str] = []
    gaps: list[str] = []
    follow_ups: list[str] = []
    partial_labels: list[str] = []

    for requirement in requirements:
        tokens = _requirement_tokens(requirement)
        if not tokens:
            continue

        strong_hits = [q for (s, q) in strong if _match(tokens, s)]
        weak_hits = [(q, s) for (s, q) in weak if _match(tokens, s)]
        # Achievements are self-claimed: they never count as demonstrated evidence.
        narrative_hits = [q for q, s in weak_hits if s not in achievement_sources]
        claim_only_hits = [q for q, s in weak_hits if s in achievement_sources]

        evidence: list[str] = []
        if strong_hits:
            rating = RATING_DEMONSTRATED
            evidence = [_quote(q) for q in strong_hits[:3]] + [_quote(q) for q in narrative_hits[:2]]
            strengths.append(requirement.label)
        elif narrative_hits:
            rating = RATING_PARTIAL
            evidence = [_quote(q) for q in narrative_hits[:3]]
            partial_labels.append(requirement.label)
        elif claim_only_hits:
            rating = RATING_NEEDS_VERIFICATION
            evidence = [_quote(q) for q in claim_only_hits[:2]]
            gaps.append(f"{requirement.label} (self-claimed only - needs verification)")
        else:
            rating = RATING_ABSENT
            gaps.append(requirement.label)

        note = ""
        if profile.is_empty():
            rating = RATING_ABSENT
            evidence = []
            note = "No approved profile evidence available."

        assessments.append(
            CapabilityAssessment(
                capability=requirement.key,
                label=requirement.label,
                category=requirement.category,
                rating=rating,
                evidence=list(dict.fromkeys(evidence)),
                notes=note,
            )
        )

    for label in partial_labels[:4]:
        follow_ups.append(f"Can you walk through your hands-on work related to {label}?")
    for assessment in assessments:
        if assessment.rating == RATING_NEEDS_VERIFICATION:
            follow_ups.append(
                f"What concrete results can you show for {assessment.label} "
                "(projects, links, references)?"
            )

    demonstrated = [a.label for a in assessments if a.rating == RATING_DEMONSTRATED]
    summary = (
        f"Evidence-based evaluation against {role_title or 'the role requirements'}. "
        f"Approved profile explicitly covers: "
        f"{', '.join(demonstrated) if demonstrated else 'no requirement areas yet'}. "
        f"Main gaps: {', '.join(gaps) if gaps else 'none found'}. "
        "All ratings cite recruiter-approved evidence only; ambiguous items are marked "
        "Needs Verification for interview follow-up."
    )

    explicit = _explicit_fields(profile, assessments, strengths, gaps, summary)
    return Evaluation(
        candidate_id=candidate_id,
        role_id=role_id,
        role_title=role_title,
        summary=summary,
        strengths=list(dict.fromkeys(strengths)),
        gaps=list(dict.fromkeys(gaps)),
        **explicit,
        assessments=assessments,
        follow_up_questions=list(dict.fromkeys(follow_ups))[:6],
        knowledge_sources=knowledge_sources,
        status=EVALUATION_DRAFT,
        provider=get_provider_name(),
        model="stub-deterministic",
        generated_at=utc_now().isoformat(),
    )


# --- LLM (openai) builder ---------------------------------------------------


def _requirements_block(requirements: list[Requirement]) -> str:
    return "\n".join(
        f"- {r.key} | {r.label} | {r.category} | {r.description}" for r in requirements
    ) or "(no requirements defined for this role)"


def _knowledge_block(chunks) -> str:
    if not chunks:
        return "(no additional knowledge retrieved)"
    return "\n\n".join(f"[{c.source}#{c.heading}]\n{c.text}" for c in chunks)


def _profile_block(profile: CandidateProfile) -> str:
    return json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)


class _LLMPayload(Evaluation):
    """Shape the model is asked to return (identity fields are filled server-side)."""

    candidate_id: str = ""  # type: ignore[assignment]


def build_llm_evaluation(
    *,
    candidate_id: str,
    profile: CandidateProfile,
    requirements: list[Requirement],
    role_id: str | None,
    role_title: str | None,
    chunks,
) -> Evaluation:
    """Ask the configured model for an evaluation and validate its JSON."""
    user_prompt = build_evaluation_user_prompt(
        profile_block=_profile_block(profile),
        requirements_block=_requirements_block(requirements),
        knowledge_block=_knowledge_block(chunks),
        role_title=role_title,
    )

    try:
        raw = chat_json(EVALUATION_SYSTEM_PROMPT, user_prompt, purpose="candidate evaluation")
        payload = validate_structured(_LLMPayload, raw, purpose="candidate evaluation")
    except ProviderUnavailableError as exc:
        raise EvaluationUnavailableError(str(exc)) from exc
    except (InvalidProviderOutputError, ProviderError) as exc:
        logger.warning("LLM evaluation failed: %s", exc)
        raise EvaluationFailedError(str(exc)) from exc

    # Reject any rating the model invented instead of the four-value scale.
    for assessment in payload.assessments:
        if assessment.rating not in CAPABILITY_RATINGS:
            raise EvaluationFailedError(
                f"AI returned rating '{assessment.rating}' which is not one of the four "
                "allowed values; the evaluation was rejected rather than guessed."
            )

    explicit = _explicit_fields(profile, payload.assessments, payload.strengths, payload.gaps, payload.summary)
    return Evaluation(
        candidate_id=candidate_id,
        role_id=role_id,
        role_title=role_title,
        summary=payload.summary,
        strengths=payload.strengths,
        gaps=payload.gaps,
        **explicit,
        assessments=payload.assessments,
        follow_up_questions=payload.follow_up_questions,
        knowledge_sources=knowledge_sources_for(list(chunks)),
        status=EVALUATION_DRAFT,
        provider=get_provider_name(),
        model=None,  # filled by the caller from settings
        generated_at=utc_now().isoformat(),
    )


# --- shared entry point ------------------------------------------------------


def generate_evaluation(
    *,
    candidate_id: str,
    profile: CandidateProfile,
    requirements: list[Requirement],
    role_id: str | None,
    role_title: str | None,
    query: str,
) -> Evaluation:
    """Retrieve knowledge, then build the evaluation with the configured provider."""
    chunks = search_knowledge(query)
    provider = get_provider_name()

    if provider == "stub":
        evaluation = build_deterministic_evaluation(
            candidate_id=candidate_id,
            profile=profile,
            requirements=requirements,
            role_id=role_id,
            role_title=role_title,
            knowledge_sources=knowledge_sources_for(chunks),
        )
    elif provider == "openai":
        evaluation = build_llm_evaluation(
            candidate_id=candidate_id,
            profile=profile,
            requirements=requirements,
            role_id=role_id,
            role_title=role_title,
            chunks=chunks,
        )
    else:
        raise EvaluationUnavailableError(
            "AI evaluation is disabled. Set LLM_PROVIDER=openai (with LLM_API_KEY) or "
            "LLM_PROVIDER=stub for the offline deterministic evaluator."
        )

    logger.info(
        "Generated evaluation for candidate %s via %s (%s assessment(s))",
        candidate_id,
        evaluation.provider,
        len(evaluation.assessments),
    )
    return evaluation


def _match(tokens: set[str], haystack: str) -> int:
    """How many requirement tokens appear as substrings of ``haystack``."""
    return sum(1 for token in tokens if token in haystack)


def _quote(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"