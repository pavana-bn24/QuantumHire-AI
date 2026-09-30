"""Skill-test drafting (milestone 3).

The skill test is drafted **after** the evaluation is approved. It is stored on
the candidate document (``skill_test``), starts as a draft, and only moves the
pipeline stage to ``Skill Test`` when the recruiter approves it.

Providers: ``stub`` builds a deterministic test targeting the evaluation's weak
areas offline; ``openai`` asks the model and validates the JSON. Failures raise
:class:`SkillTestUnavailableError` (503) or :class:`SkillTestFailedError` (502)
- an invalid response is never silently used.
"""

from __future__ import annotations

import logging

from app.ai.base import InvalidProviderOutputError, ProviderError, ProviderUnavailableError
from app.ai.chat import chat_json, validate_structured
from app.ai.factory import get_provider_name
from app.ai.prompts import SKILL_TEST_SYSTEM_PROMPT, build_skill_test_user_prompt
from app.core.constants import (
    EVALUATION_APPROVED,
    RATING_ABSENT,
    RATING_NEEDS_VERIFICATION,
    RATING_PARTIAL,
    SKILL_TEST_DRAFT,
)
from app.core.serialization import utc_now
from app.models import Evaluation, SkillTest, SkillTestQuestion
from app.services.evaluation import _profile_block, _requirements_block
from app.services.knowledge import knowledge_sources_for, search_knowledge

logger = logging.getLogger(__name__)


class SkillTestError(Exception):
    """Base class for skill-test failures with an API-safe message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SkillTestUnavailableError(SkillTestError):
    """No usable AI provider (HTTP 503)."""


class SkillTestFailedError(SkillTestError):
    """Provider ran but produced invalid output (HTTP 502)."""


class SkillTestNotAllowedError(SkillTestError):
    """Preconditions not met (HTTP 409) - e.g. evaluation not approved yet."""


#: Requirement-key -> default question template used by the offline builder.
_QUESTION_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "frontend": (
        "Build a small React component (hooks allowed) that fetches a list from an API, "
        "handles loading/error states and is keyboard accessible. Explain your state design.",
        "coding",
        "Component structure, error handling, accessibility",
    ),
    "backend": (
        "Design and implement a FastAPI service layer for a resource: schemas, validation, "
        "clean separation of routing vs business logic. What would you test?",
        "coding",
        "Layering, validation, testability",
    ),
    "rest_apis": (
        "Review this API design (GET /items, POST /items, PATCH /items/{id}) and propose the "
        "error model, pagination and idempotency rules you would enforce.",
        "knowledge",
        "API conventions, error handling, idempotency",
    ),
    "databases": (
        "You have a candidates collection queried by stage, role_id and free-text name search. "
        "Which indexes do you create and why? Sketch one aggregation you would run.",
        "knowledge",
        "Index design, query planning",
    ),
    "authentication": (
        "Describe how you would implement login for this app: password storage, token issuance, "
        "expiry/refresh and role checks. Where are the common pitfalls?",
        "knowledge",
        "Hashing, JWT lifecycle, authorization checks",
    ),
    "ai_llm_apis": (
        "Write the prompt structure (system vs user) for extracting structured JSON from a "
        "user-supplied document. How do you stop the document from injecting instructions?",
        "coding",
        "Prompt isolation, structured outputs, validation",
    ),
    "rag": (
        "Design a RAG flow over internal docs: chunking, retrieval, prompt assembly and how you "
        "prove answers are grounded in retrieved text. What breaks without citations?",
        "system_design",
        "Chunking, retrieval, grounding/citations",
    ),
    "agents_tool_calling": (
        "Define the JSON schema for a 'get_candidate_profile' tool and describe how you dispatch "
        "tool calls safely, including what happens when tool output is attacker-controlled.",
        "coding",
        "Typed tool schemas, allowlisted dispatch, untrusted output",
    ),
    "automation": (
        "A recruiter approves an evaluation and a skill test must be drafted automatically. "
        "Design the event flow: triggers, idempotency, failure handling.",
        "system_design",
        "Event-driven automation, idempotency, retries",
    ),
    "integrations": (
        "Your webhook consumer receives events from an ATS. How do you secure the endpoint, "
        "verify payloads and handle duplicates/out-of-order delivery?",
        "knowledge",
        "Webhook security, idempotency, ordering",
    ),
    "saas_concepts": (
        "This hiring tool must support multiple companies later. What changes in your data model "
        "and auth design for multi-tenancy?",
        "scenario",
        "Multi-tenancy, data isolation",
    ),
    "deployment_devops": (
        "Describe the CI/CD pipeline for this repo: checks that must pass before deploy, how "
        "secrets and env config are handled, and rollback strategy.",
        "knowledge",
        "CI/CD, secrets, rollback",
    ),
    "testing": (
        "Write the test plan for the resume-upload endpoint: what unit/integration/E2E cases "
        "prove validation, duplicate handling and provider failure paths?",
        "coding",
        "Test layering, fixtures, failure paths",
    ),
    "security": (
        "List the top security issues you would audit in this stack (FastAPI + React + MongoDB) "
        "and the first fix you would ship for each.",
        "knowledge",
        "OWASP awareness, practical remediation",
    ),
    "learning_research": (
        "A new vector database is proposed for this project. Walk through how you would evaluate "
        "it against the current keyword approach and what you would recommend.",
        "scenario",
        "Technical evaluation, trade-off communication",
    ),
}

_DEFAULT_TEMPLATE = (
    "Describe a project where you delivered this requirement end-to-end: your specific "
    "contributions, the trade-offs you made and the measurable outcome.",
    "scenario",
    "Depth of hands-on experience",
)


def _require_approved_evaluation(evaluation: Evaluation | None) -> Evaluation:
    """Skill tests may only target an *approved* evaluation."""
    if evaluation is None:
        raise SkillTestNotAllowedError(
            "Generate and approve an AI evaluation before creating a skill test - "
            "the test must target evidence-based gaps."
        )
    if evaluation.status != EVALUATION_APPROVED:
        raise SkillTestNotAllowedError(
            "The AI evaluation is still a draft. Approve the evaluation first; "
            "skill tests are only drafted from approved evaluations."
        )
    return evaluation


def _weak_areas(evaluation: Evaluation) -> list[str]:
    """Capability keys the test should target, weakest ratings first."""
    wanted = (RATING_ABSENT, RATING_NEEDS_VERIFICATION, RATING_PARTIAL)
    return [a.capability for a in evaluation.assessments if a.rating in wanted]


def build_deterministic_skill_test(
    *,
    candidate_id: str,
    evaluation: Evaluation,
    profile_name: str | None,
    knowledge_sources: list[str] | None = None,
    guidelines: str = "",
) -> SkillTest:
    """Offline test draft targeting the evaluation's weakest areas (stub)."""
    questions: list[SkillTestQuestion] = []
    seen_focus: set[str] = set()

    for key in _weak_areas(evaluation):
        if key in seen_focus:
            continue
        prompt, qtype, sample = _QUESTION_TEMPLATES.get(key, _DEFAULT_TEMPLATE)
        questions.append(SkillTestQuestion(prompt=prompt, type=qtype, focus=key, sample_answer=sample))
        seen_focus.add(key)
        if len(questions) >= 5:
            break

    # Guarantee at least 3 questions: fill from named gaps, then generic depth.
    if len(questions) < 3:
        for gap in evaluation.gaps:
            key = next(
                (a.capability for a in evaluation.assessments if a.label and a.label in gap),
                "backend",
            )
            if key in seen_focus:
                continue
            prompt, qtype, sample = _QUESTION_TEMPLATES.get(key, _DEFAULT_TEMPLATE)
            questions.append(
                SkillTestQuestion(prompt=prompt, type=qtype, focus=key, sample_answer=sample)
            )
            seen_focus.add(key)
            if len(questions) >= 3:
                break

    while len(questions) < 3:
        prompt, qtype, sample = _DEFAULT_TEMPLATE
        questions.append(
            SkillTestQuestion(prompt=prompt, type=qtype, focus="general", sample_answer=sample)
        )

    role_title = evaluation.role_title or "the role"
    first_name = (profile_name or "").split(" ")[0] if profile_name else ""
    focus_titles = [
        next((a.label for a in evaluation.assessments if a.capability == q.focus), q.focus)
        for q in questions
    ]

    # Ground the draft in the retrieved skill-test guidelines (RAG): cite the
    # sections that were actually retrieved and restate their core rules.
    sources = list(knowledge_sources or [])
    guideline_requirement = (
        "Follow the retrieved skill-test guidelines ("
        + ", ".join(sources[:3])
        + "): keep every task evidence-based, completable within the time limit, "
        "and editable/reviewable by the recruiter before it is approved."
        if sources
        else (
            "Keep every task evidence-based, completable within the time limit, and "
            "editable/reviewable by the recruiter before it is approved."
        )
    )

    instructions = (
        f"Hi {first_name or 'there'} - this short practical test is tailored to the areas we "
        "need to confirm for this role. Answer in writing or with code snippets as appropriate. "
        "Submit your answers to your recruiter within the duration below. Tools and docs are "
        "allowed unless your recruiter says otherwise."
    )

    return SkillTest(
        title=(
            f"{role_title} - Skill Test"
            + (f" for {first_name}" if first_name else "")
        ),
        business_problem=(
            f"Confirm that {first_name or 'the candidate'} can deliver a production-grade slice "
            f"of the {role_title} role end to end: implement a small feature, persist data, "
            "handle errors, test the result, and explain the decisions taken."
        ),
        objective=(
            "Demonstrate hands-on implementation ability on the role's core areas - "
            + ", ".join(focus_titles[:4])
            + " - with particular attention to the gaps recorded in the approved evaluation."
        ),
        requirements=[
            f"Targeted stretch area: {focus_titles[0] if focus_titles else 'general depth'}. "
            "At least one task below must exercise this area end to end.",
            *[
                f"Show working use of {label} in the answers, not just discussion."
                for label in focus_titles[1:4]
            ],
            guideline_requirement,
            "Use only the stack evidenced in the approved profile unless a task explicitly "
            "asks to research a new tool; do not assume unstated expertise.",
            "Keep the work realistic: a focused slice completable within the stated time "
            "limit, not a full product.",
        ],
        technical_requirements=[
            "Runnable code with request validation and error handling.",
            "Any data persisted with the schema/index choices documented.",
            "At least one automated test covering the core behaviour.",
            "A README covering setup, run commands and verification steps.",
        ],
        expected_deliverables=[
            "Source code archive or repository link with run instructions.",
            "README: setup, trade-offs and what was verified.",
            "Written answers to the questions below, with code snippets where relevant.",
        ],
        evaluation_criteria=[
            "Correctness and completeness of the working solution.",
            "Code quality, validation and error handling.",
            "Evidence of the targeted stretch areas in the implementation.",
            "Testing approach and documentation clarity.",
        ],
        time_limit="60 minutes",
        duration_minutes=60,
        instructions=instructions,
        questions=questions,
        status=SKILL_TEST_DRAFT,
        provider=get_provider_name(),
        model="stub-deterministic",
        generated_at=utc_now().isoformat(),
        knowledge_sources=sources,
    )


# --- LLM (openai) builder ---------------------------------------------------


class _LLMSkillTestPayload(SkillTest):
    """Shape the model is asked to return (provenance fields filled server-side)."""


def build_llm_skill_test(
    *,
    candidate_id: str,
    evaluation: Evaluation,
    profile_block: str,
    requirements_block: str,
    knowledge: str = "",
    knowledge_sources: list[str] | None = None,
) -> SkillTest:
    """Ask the model for a skill test and validate the JSON it returns."""
    user_prompt = build_skill_test_user_prompt(
        profile_block=profile_block,
        requirements_block=requirements_block,
        evaluation_summary=(
            f"{evaluation.summary}\nGaps: {', '.join(evaluation.gaps) or 'none'}"
        ),
        role_title=evaluation.role_title,
    )
    if knowledge:
        user_prompt = f"{user_prompt}\n\nRETRIEVED GUIDELINES:\n{knowledge}"

    try:
        raw = chat_json(SKILL_TEST_SYSTEM_PROMPT, user_prompt, purpose="skill test generation")
        payload = validate_structured(_LLMSkillTestPayload, raw, purpose="skill test generation")
    except ProviderUnavailableError as exc:
        raise SkillTestUnavailableError(str(exc)) from exc
    except (InvalidProviderOutputError, ProviderError) as exc:
        logger.warning("LLM skill-test generation failed: %s", exc)
        raise SkillTestFailedError(str(exc)) from exc

    if not payload.questions:
        raise SkillTestFailedError(
            "AI returned a skill test with no questions; rejected rather than sending an empty test."
        )
    if len(payload.questions) < 3:
        raise SkillTestFailedError(
            f"AI returned only {len(payload.questions)} question(s); skill tests need at least 3."
        )

    return SkillTest(
        title=payload.title or f"{evaluation.role_title or 'the role'} - Skill Test",
        business_problem=payload.business_problem,
        objective=payload.objective,
        requirements=list(payload.requirements),
        technical_requirements=list(payload.technical_requirements),
        expected_deliverables=list(payload.expected_deliverables),
        evaluation_criteria=list(payload.evaluation_criteria),
        time_limit=payload.time_limit,
        duration_minutes=payload.duration_minutes,
        instructions=payload.instructions,
        questions=payload.questions,
        status=SKILL_TEST_DRAFT,
        provider=get_provider_name(),
        model=None,  # filled by the caller from settings
        generated_at=utc_now().isoformat(),
        knowledge_sources=list(knowledge_sources or []),
    )


# --- shared entry point ------------------------------------------------------


def generate_skill_test(
    *,
    candidate_id: str,
    evaluation: Evaluation | None,
    profile_name: str | None,
    profile_json: str,
    requirements_json: str,
) -> SkillTest:
    """Draft a skill test for a candidate whose evaluation is already approved."""
    evaluation = _require_approved_evaluation(evaluation)
    provider = get_provider_name()

    # Retrieval (RAG): skill-test guidelines, kept separate from candidate
    # evidence and role requirements. Both providers receive the same chunks.
    chunks = search_knowledge(
        f"{evaluation.role_title or ''} skill test guidelines evaluation criteria approval"
    )
    sources = knowledge_sources_for(chunks)
    guidelines = "\n\n".join(f"[{c.source}#{c.heading}]\n{c.text}" for c in chunks)

    if provider == "stub":
        test = build_deterministic_skill_test(
            candidate_id=candidate_id,
            evaluation=evaluation,
            profile_name=profile_name,
            knowledge_sources=sources,
            guidelines=guidelines,
        )
    elif provider == "openai":
        test = build_llm_skill_test(
            candidate_id=candidate_id,
            evaluation=evaluation,
            profile_block=profile_json,
            requirements_block=requirements_json,
            knowledge=guidelines,
            knowledge_sources=sources,
        )
    else:
        raise SkillTestUnavailableError(
            "AI skill-test generation is disabled. Set LLM_PROVIDER=openai (with LLM_API_KEY) "
            "or LLM_PROVIDER=stub for the offline deterministic generator."
        )

    logger.info(
        "Generated skill test for candidate %s via %s (%s question(s))",
        candidate_id,
        test.provider,
        len(test.questions),
    )
    return test


