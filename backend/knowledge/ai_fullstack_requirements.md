# AI Full-Stack Developer — Role Requirements

This document is the authoritative requirement definition used by AI evaluation,
skill-test generation and retrieval-augmented prompts.

## Scope

The role owns end-to-end delivery of AI-assisted product features: React front
ends, FastAPI services, MongoDB persistence, LLM/RAG pipelines and the
automation that ties them together.

## Requirement areas

| Key | Area | What "good" looks like |
| --- | --- | --- |
| frontend | Frontend | Component-driven React UI, routing, state/data patterns, accessible forms |
| backend | Backend | Python services, async request handling, clean layering, validation |
| rest_apis | REST APIs | Versioned FastAPI endpoints, clear errors, request/response schemas |
| databases | Databases | Document modelling in MongoDB, indexing, query planning basics |
| authentication | Authentication | Tokens/sessions, password hashing, role-based access control |
| ai_llm_apis | AI/LLM APIs | Prompt design, structured outputs, provider failover, cost control |
| rag | RAG | Chunking, keyword/embedding retrieval, grounded synthesis with citations |
| agents_tool_calling | Agents/Tool calling | Typed tool schemas, allowlisted dispatch, safe untrusted-data isolation |
| automation | Automation | Event-driven recruiter workflows, scheduled jobs, idempotent steps |
| integrations | Integrations | Webhooks in/out, third-party ATS/email/calendar connectivity |
| saas_concepts | SaaS concepts | Multi-tenancy thinking, plans, onboarding, product analytics |
| deployment_devops | Deployment/DevOps | Containers, CI/CD, environment config, observability |
| testing | Testing | Unit/integration/E2E coverage, fixtures, reproducible runs |
| security | Security | Input validation, secrets management, OWASP awareness, data privacy |
| learning_research | Learning/Research | Independent tool evaluation and clear trade-off communication |

## Evaluation policy

- Every assessment must cite evidence from the recruiter-approved profile only.
- Ratings use the four-value scale defined in `evaluation_guidelines.md`.
- No numeric scores, no candidate ranking, no invented evidence.
- Missing evidence is reported as a gap, never guessed.

## Skill-test policy

Tests must cover the weakest validated areas first and be reviewable/editable by
the recruiter before they are approved and sent. See `skill_test_guidelines.md`.
