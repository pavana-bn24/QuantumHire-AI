"""Deterministic, offline ``stub`` provider.

Purpose: let the full upload -> extract -> review -> save flow run (and be
tested) without an API key, while still obeying the "evidence only" rule.

It is deliberately **not** a fake/creative generator - every value it returns is
produced by a regex or keyword match against the resume text:

* e-mail / phone / name come from explicit patterns,
* skills, technologies and tools are only reported when the keyword literally
  appears in the resume,
* work experience, education and projects are derived from the actual lines,
* AI/development/achievement bullets are the lines containing relevant cues.

Nothing is inferred, completed or invented, so ``LLM_PROVIDER=stub`` never
fabricates candidate evidence. Use ``LLM_PROVIDER=openai`` for real LLM
extraction through the same interface.
"""

from __future__ import annotations

import re

from app.ai.base import ExtractionResult, LLMProvider
from app.models.profile import CandidateProfile, EducationEntry, ProjectEntry, WorkExperienceEntry

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?){2,3}\d{2,4}")
YEAR_RANGE_RE = re.compile(
    r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current|now)", re.IGNORECASE
)

SKILL_KEYWORDS = [
    "communication", "leadership", "teamwork", "problem solving", "collaboration",
    "mentoring", "code review", "debugging", "time management", "ownership",
    "stakeholder management", "documentation", "agile", "scrum", "kanban",
]

TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "SQL",
    "React", "Next.js", "Vue", "Angular", "Node.js", "FastAPI", "Flask", "Django",
    "Express", "Spring Boot", "Tailwind", "Redux", "GraphQL", "REST", "gRPC",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite",
    "PyTorch", "TensorFlow", "scikit-learn", "Pandas", "NumPy",
    "LangChain", "LlamaIndex", "OpenAI API", "Hugging Face", "Transformers",
    "RAG", "embeddings", "vector database", "Pinecone", "FAISS", "Chroma",
    "prompt engineering", "fine-tuning", "LLM", "NLP", "computer vision",
]

TOOL_KEYWORDS = [
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Ansible",
    "GitHub Actions", "GitLab CI", "Jenkins", "CI/CD", "Linux", "Git", "Nginx",
    "Celery", "RabbitMQ", "Kafka", "Airflow", "Sentry",
    "Grafana", "Prometheus", "Vercel", "Heroku", "Postman", "Swagger",
]

AI_CUES = ("llm", "gpt", "openai", "rag", "embedding", "agent", "langchain", "prompt",
           "fine-tun", "machine learning", "ml model", "nlp", "vector", "anthropic", "gemini")

DEV_CUES = ("develop", "built", "build", "implement", "engineered", "designed", "shipped",
            "migrated", "refactored", "architected", "deployed", "automated", " api",
            "frontend", "backend", "full-stack", "fullstack")

ACHIEVEMENT_CUES = ("award", "won", "winner", "hackathon", "top ", "rank", "medal",
                    "certified", "certification", "scholarship", "recogni", "published",
                    "patent", "increased", "reduced", "improved by", "%")

DEGREE_CUES = ("b.tech", "b.e.", "bachelor", "master", "m.tech", "m.sc", "b.sc",
               "phd", "ph.d", "mba", "bca", "mca", "diploma", "associate degree")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _keyword_present(haystack: str, keyword: str) -> bool:
    """Word-boundary keyword match that tolerates ``.``, ``+``, ``#`` and ``/``."""
    pattern = rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])"
    return re.search(pattern, haystack, re.IGNORECASE) is not None


def _match_any(text: str, keywords: list[str]) -> list[str]:
    """Return the keywords literally present in ``text`` (canonical casing)."""
    return [keyword for keyword in keywords if _keyword_present(text, keyword)]


def _cue_lines(lines: list[str], cues: tuple[str, ...], limit: int = 6) -> list[str]:
    """Return lines containing one of ``cues``, verbatim and de-duplicated."""
    found: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(cue in lowered for cue in cues) and line not in found:
            found.append(line)
        if len(found) >= limit:
            break
    return found


def _guess_name(lines: list[str]) -> str | None:
    """First line that looks like a person's name (2-4 alphabetic words)."""
    for line in lines[:6]:
        if "@" in line or any(char.isdigit() for char in line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(word.replace("-", "").isalpha() for word in words):
            return line
    return None


def _work_experience(lines: list[str]) -> list[WorkExperienceEntry]:
    """Build entries from lines that contain an explicit year range."""
    entries: list[WorkExperienceEntry] = []
    for index, line in enumerate(lines):
        match = YEAR_RANGE_RE.search(line)
        if not match:
            continue

        context = lines[index - 1] if index > 0 else ""
        title, company = None, None
        if " at " in context.lower():
            parts = re.split(r"\s+at\s+", context, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                title, company = parts[0].strip(), parts[1].strip()
            else:
                company = context
        elif " - " in context:
            company, _, title = context.partition(" - ")
        elif context:
            company = context

        entries.append(
            WorkExperienceEntry(
                company=(company or "").strip() or None,
                title=(title or "").strip() or None,
                start_date=match.group(1),
                end_date=match.group(2),
                description=line,
                technologies=_match_any(line, TECH_KEYWORDS),
            )
        )
        if len(entries) >= 5:
            break
    return entries


def _projects(lines: list[str]) -> list[ProjectEntry]:
    """Build entries from lines that explicitly label a project."""
    entries: list[ProjectEntry] = []
    for line in lines:
        lowered = line.lower()
        if not (lowered.startswith("project") or "project:" in lowered):
            continue
        _, _, remainder = line.partition(":")
        name = (remainder or line).strip() or None
        entries.append(
            ProjectEntry(
                name=name,
                description=line,
                technologies=_match_any(line, TECH_KEYWORDS),
            )
        )
        if len(entries) >= 5:
            break
    return entries


def _education(lines: list[str]) -> list[EducationEntry]:
    """Build entries from lines that mention a degree or an institution."""
    institution_cues = ("university", "college", "institute", "school", "academy")
    entries: list[EducationEntry] = []

    for line in lines:
        lowered = line.lower()
        degree = next((cue for cue in DEGREE_CUES if cue in lowered), None)
        has_institution = any(cue in lowered for cue in institution_cues)
        if not degree and not has_institution:
            continue

        match = YEAR_RANGE_RE.search(line)
        entries.append(
            EducationEntry(
                institution=line if has_institution else None,
                degree=line if degree else None,
                start_date=match.group(1) if match else None,
                end_date=match.group(2) if match else None,
            )
        )
        if len(entries) >= 3:
            break
    return entries


class StubProvider(LLMProvider):
    """Offline, deterministic extractor used for demos and tests."""

    name = "stub"

    def __init__(self, model: str = "stub-deterministic") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def extract_profile(self, resume_text: str) -> ExtractionResult:
        """Extract every value strictly from literal matches in the resume."""
        lines = _lines(resume_text)
        email_match = EMAIL_RE.search(resume_text)
        phone_match = PHONE_RE.search(resume_text)

        profile = CandidateProfile(
            name=_guess_name(lines),
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0).strip() if phone_match else None,
            skills=_match_any(resume_text, SKILL_KEYWORDS),
            technologies=_match_any(resume_text, TECH_KEYWORDS),
            work_experience=_work_experience(lines),
            projects=_projects(lines),
            education=_education(lines),
            ai_experience=_cue_lines(lines, AI_CUES),
            development_experience=_cue_lines(lines, DEV_CUES),
            tools_platforms=_match_any(resume_text, TOOL_KEYWORDS),
            achievements=_cue_lines(lines, ACHIEVEMENT_CUES),
        )

        warnings = [
            "Extraction ran with LLM_PROVIDER=stub (offline rule-based extractor). "
            "Set LLM_PROVIDER=openai and LLM_API_KEY for full LLM extraction."
        ]
        if profile.is_empty():
            warnings.append(
                "No structured fields could be grounded in this resume text - "
                "please complete the profile manually."
            )

        return ExtractionResult(
            profile=profile, provider=self.name, model=self._model, warnings=warnings
        )
