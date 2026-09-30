"""Default seed data for QuantumHire AI.

Only reference data lives here: the initial role and a handful of demo
candidates so the dashboard and pipeline are not empty during a demo.
No AI, RAG, resume-parsing or skill-test logic.
"""

from datetime import datetime, timedelta, timezone

from app.core.constants import PipelineStage


def _requirement(key: str, label: str, category: str, weight: int, description: str) -> dict:
    return {
        "key": key,
        "label": label,
        "category": category,
        "weight": weight,
        "description": description,
    }


#: Requirements for the initial role. Weights sum to 100.
AI_FULL_STACK_REQUIREMENTS: list[dict] = [
    _requirement(
        "frontend",
        "Frontend",
        "Engineering",
        9,
        "Component-driven UI work with React and modern state/data patterns.",
    ),
    _requirement(
        "backend",
        "Backend",
        "Engineering",
        9,
        "Python service design, async request handling and clean domain layering.",
    ),
    _requirement(
        "rest_apis",
        "REST APIs",
        "Engineering",
        8,
        "Designing, documenting and versioning REST endpoints with FastAPI/Pydantic.",
    ),
    _requirement(
        "databases",
        "Databases",
        "Data",
        7,
        "Schema design and querying across document and relational stores.",
    ),
    _requirement(
        "authentication",
        "Authentication",
        "Security",
        6,
        "Sessions, tokens, role-based access control and secure credential handling.",
    ),
    _requirement(
        "ai_llm_apis",
        "AI/LLM APIs",
        "AI",
        10,
        "Prompting, structured outputs and streaming against hosted LLM providers.",
    ),
    _requirement(
        "rag",
        "RAG",
        "AI",
        9,
        "Chunking, embeddings, vector search and grounded answer synthesis.",
    ),
    _requirement(
        "agents_tool_calling",
        "Agents/Tool Calling",
        "AI",
        8,
        "Tool schemas, planner/executor loops and safe function invocation.",
    ),
    _requirement(
        "automation",
        "Automation",
        "Platform",
        5,
        "Removing manual recruiter steps through scheduled and event-driven jobs.",
    ),
    _requirement(
        "integrations",
        "Integrations",
        "Platform",
        5,
        "Third-party ATS, email, calendar and webhook connectivity.",
    ),
    _requirement(
        "saas_concepts",
        "SaaS Concepts",
        "Product",
        4,
        "Multi-tenancy, plans, onboarding and product analytics thinking.",
    ),
    _requirement(
        "deployment_devops",
        "Deployment/DevOps",
        "Platform",
        6,
        "Containers, CI/CD pipelines, environment configuration and observability.",
    ),
    _requirement(
        "testing",
        "Testing",
        "Quality",
        6,
        "Unit, integration and end-to-end coverage with reproducible fixtures.",
    ),
    _requirement(
        "security",
        "Security",
        "Security",
        5,
        "OWASP awareness, input validation, secrets management and data privacy.",
    ),
    _requirement(
        "learning_research",
        "Learning/Research",
        "Product",
        3,
        "Independently evaluating new tooling and communicating trade-offs.",
    ),
]

#: The initial role created on first startup.
DEFAULT_ROLES: list[dict] = [
    {
        "title": "AI Full-Stack Developer",
        "slug": "ai-full-stack-developer",
        "department": "Engineering",
        "location": "Remote",
        "employment_type": "Full-time",
        "seniority": "Mid-Senior",
        "status": "active",
        "description": (
            "Own end-to-end delivery of AI-assisted product features: React front ends, "
            "FastAPI services, MongoDB persistence, LLM/RAG pipelines and the automation "
            "that ties them together."
        ),
        "requirements": AI_FULL_STACK_REQUIREMENTS,
    },
]

#: Email prefix used to keep demo records identifiable (and easy to purge).
DEMO_CANDIDATE_PREFIX = "demo.quantumhire+"


def demo_candidates(role_id: str | None, role_title: str) -> list[dict]:
    """Build the demo candidate set, relative to the current time."""
    now = datetime.now(timezone.utc)

    def candidate(
        name: str,
        stage: str,
        email_local: str,
        days_ago: int,
        experience_years: float,
        location: str,
        source: str,
        skills: list[str],
        notes: str,
    ) -> dict:
        created = now - timedelta(days=days_ago)
        return {
            "name": name,
            "email": f"{DEMO_CANDIDATE_PREFIX}{email_local}@example.com",
            "phone": None,
            "role_id": role_id,
            "role_title": role_title,
            "stage": stage,
            "source": source,
            "location": location,
            "experience_years": experience_years,
            "skills": skills,
            "notes": notes,
            "resume_file": None,
            # Filled in by a later milestone (resume parsing + AI evaluation).
            "ai_summary": None,
            "scores": {},
            "created_at": created,
            "updated_at": created,
        }

    return [
        candidate(
            "Aarav Sharma",
            PipelineStage.NEW.value,
            "aarav.sharma",
            1,
            3.5,
            "Bengaluru, IN",
            "LinkedIn",
            ["React", "Node.js", "PostgreSQL", "Docker"],
            "Strong product mindset, shipped an internal RAG assistant.",
        ),
        candidate(
            "Meera Iyer",
            PipelineStage.NEW.value,
            "meera.iyer",
            2,
            2.0,
            "Pune, IN",
            "Referral",
            ["React", "FastAPI", "MongoDB"],
            "Referred by the platform team; full-stack bootcamp graduate.",
        ),
        candidate(
            "Daniel Okafor",
            PipelineStage.NEW.value,
            "daniel.okafor",
            3,
            5.0,
            "Remote (Lagos, NG)",
            "Careers Page",
            ["Python", "FastAPI", "AWS", "LangChain"],
            "Backend-leaning profile, keen on agent tooling.",
        ),
        candidate(
            "Sofia Marchetti",
            PipelineStage.UNDER_REVIEW.value,
            "sofia.marchetti",
            5,
            4.0,
            "Milan, IT",
            "LinkedIn",
            ["React", "TypeScript", "FastAPI", "Docker", "CI/CD"],
            "Screening call complete. Needs a deeper API design check.",
        ),
        candidate(
            "Rahul Verma",
            PipelineStage.UNDER_REVIEW.value,
            "rahul.verma",
            6,
            6.5,
            "Hyderabad, IN",
            "Agency",
            ["Python", "MongoDB", "RAG", "Kubernetes"],
            "Ex-startup lead. Reviewing scope expectations with the hiring manager.",
        ),
        candidate(
            "Priya Nair",
            PipelineStage.SKILL_TEST.value,
            "priya.nair",
            9,
            3.0,
            "Kochi, IN",
            "Referral",
            ["React", "FastAPI", "MongoDB", "PyTest"],
            "Skill test invite sent. Awaiting submission.",
        ),
        candidate(
            "Tom Reinholt",
            PipelineStage.SKILL_TEST.value,
            "tom.reinholt",
            11,
            7.0,
            "Berlin, DE",
            "Careers Page",
            ["TypeScript", "Python", "LLM APIs", "Terraform"],
            "Submission received; pending the automated review step.",
        ),
        candidate(
            "Grace Lin",
            PipelineStage.INTERVIEW.value,
            "grace.lin",
            14,
            5.5,
            "Singapore, SG",
            "LinkedIn",
            ["React", "FastAPI", "RAG", "Agents", "Docker"],
            "Technical panel scheduled with the platform squad.",
        ),
        candidate(
            "Ahmed Farouk",
            PipelineStage.INTERVIEW.value,
            "ahmed.farouk",
            16,
            4.5,
            "Cairo, EG",
            "Agency",
            ["React", "Node.js", "MongoDB", "AWS"],
            "System design round passed; culture round next.",
        ),
        candidate(
            "Elena Petrova",
            PipelineStage.SELECTED.value,
            "elena.petrova",
            24,
            6.0,
            "Remote (Tbilisi, GE)",
            "Referral",
            ["React", "TypeScript", "FastAPI", "RAG", "Agents", "CI/CD"],
            "Offer approved. Handed over to the people team.",
        ),
        candidate(
            "Marcus Bell",
            PipelineStage.REJECTED.value,
            "marcus.bell",
            20,
            1.5,
            "Manchester, UK",
            "Careers Page",
            ["HTML", "CSS", "JavaScript"],
            "Not enough backend or AI exposure for this scope.",
        ),
    ]
