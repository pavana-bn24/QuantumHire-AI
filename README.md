# QuantumHire AI

A recruiter workspace built around **one** end-to-end recruitment workflow:

```
CREATE JOB ROLE
      ↓
UPLOAD RESUME
      ↓
EXTRACT CANDIDATE INFORMATION
      ↓
AI EVALUATION
      ↓
STRENGTHS & GAPS
      ↓
RECOMMENDED NEXT STEP
      ↓
PERSONALISED SKILL TEST
      ↓
RECRUITER REVIEW / EDIT
      ↓
RECRUITER APPROVAL
      ↓
CANDIDATE STATUS UPDATED  →  Skill Test
```

Every step follows the same path: **button → frontend API request → backend business
logic → MongoDB → response → UI update**. The AI provider is the offline `stub` by
default: it drafts evaluation and skill-test content dynamically from the actual
candidate profile, the actual role requirements and the local knowledge base (RAG).
Nothing is approved until a recruiter presses the corresponding button, AI never
selects or rejects candidates, and no paid AI API key is required.

## Features

- **Create Job Role** - persisted roles with a required-skills matrix (Frontend, Backend,
  APIs, Databases, Authentication, AI/LLM APIs, RAG, Agents/Tool Calling, Automation,
  Integrations, SaaS, Deployment/DevOps, Testing, Security, Learning/Research).
  The **AI Full-Stack Developer** example role is seeded on first startup.
- **PDF resume upload** - PyMuPDF text extraction, structured candidate profile, duplicate
  detection, prompt-injection fencing; files are processed in memory only.
- **Candidate profile review** - every extracted field editable, save persists to MongoDB,
  approval gates the rest of the workflow.
- **AI evaluation** - executive summary, relevant experience, demonstrated strengths,
  skill gaps, AI-first readiness, implementation capability, learning/research readiness,
  evidence gaps and a recommended next step. No scores, no rankings.
- **Personalised skill test** - generated from this candidate's approved evaluation
  (strengths + gaps), the role's requirements and retrieved knowledge guidelines;
  fully editable, save-draft persists.
- **Human approvals** - profile → recommendation → skill test; each gate is enforced in
  the backend (409 when skipped) and each approval is an explicit recruiter action.
- **Candidate status** - `New → Under Review → Skill Test → Interview → Selected/Rejected`;
  approval moves the candidate to **Skill Test** and records a `stage_changed` event.
- **Activity timeline** - real persisted workflow events (resume uploaded, profile
  approved, evaluation generated/approved, skill test generated/updated/approved,
  stage changed, webhook delivered/simulated).
- **Dashboard** - live MongoDB counters (totals, stage counts, workflow queues,
  role-wise candidate counts).
- **Agent tools** - `get_candidate_profile`, `get_role_requirements`,
  `get_recruitment_guidelines`, `evaluate_candidate`, `generate_skill_test`,
  `update_candidate_status` execute real backend operations; the stage-changing tool is
  blocked for AI callers (403).

---

## Stack

| Layer    | Technology                                                        |
| -------- | ----------------------------------------------------------------- |
| Frontend | React 18, Vite 6, Tailwind CSS 3, React Router 6, Axios, Lucide   |
| Backend  | Python 3.12+, FastAPI, Pydantic v2, PyMongo, PyMuPDF, httpx        |
| Database | MongoDB                                                            |

Frontend and backend are fully separated; they only communicate over REST.

---

## Project structure

```
QuantumHire-AI-main/
|-- backend/
|   |-- requirements.txt / requirements-dev.txt / pytest.ini
|   |-- .env.example            # copy to .env (never commit .env)
|   |-- knowledge/              # local RAG knowledge base (*.md)
|   |   |-- ai_fullstack_requirements.md
|   |   |-- evaluation_guidelines.md
|   |   |-- skill_test_guidelines.md
|   |   `-- hiring_workflow.md
|   |-- scripts/
|   |   |-- generate_sample_resume.py   # writes a demo resume PDF
|   |   `-- diag_e2e.py                 # live pipeline diagnostic sweep
|   |-- sample_data/            # generated demo resume
|   |-- tests/                  # pytest suite (isolated test database)
|   `-- app/
|       |-- main.py             # FastAPI app + lifespan (Mongo, seeding, CORS)
|       |-- core/               # config.py, constants.py, serialization.py
|       |-- db/                 # mongo.py, seed.py, seed_data.py
|       |-- models/             # API schemas + structured profile models
|       |-- ai/                 # provider interface, prompts, stub/openai providers
|       |-- services/           # resume, extraction, evaluation, skill_tests,
|       |                       # knowledge (RAG), workflow, webhooks, tools, metrics
|       `-- api/                # router, deps (JWT auth), routes/*
`-- frontend/
    |-- .env.example
    `-- src/
        |-- api/                # client.js (axios + JWT), quantumhire.js (helpers)
        |-- components/
        |   |-- layout/         # AppLayout, Sidebar, Topbar
        |   |-- ui/             # StatCard, StageBadge, PipelineBoard, ...
        |   |-- candidate/      # ProfileForm, EvaluationTab, SkillTestTab, fields
        |   `-- upload/         # ResumeUploadDialog
        |-- constants/          # pipeline.js, profile.js (section schema)
        |-- context/            # AuthContext (real JWT session)
        |-- hooks/              # useApiResource
        `-- pages/              # Login, Dashboard, Roles, Candidates,
                                # CandidateDetail, NotFound
```

---

## Setup

### Prerequisites

- Python 3.12+ with MongoDB running locally (or a `MONGODB_URI` to a reachable cluster)
- Node.js 18+ for the frontend

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env              # Windows: copy .env.example .env
```

Set `MONGODB_URI`, `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, and a long random
`JWT_SECRET` in `backend/.env`. The seeded recruiter login comes from those two
variables - there are intentionally no hardcoded credentials anywhere in the source.
The app defaults to `LLM_PROVIDER=stub` (no API key needed), seeds the **AI Full-Stack
Developer** role, and reports webhooks as `webhook_simulated` unless
`EXTERNAL_WEBHOOK_URL` is configured.

Run the API (port 8000):

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5000  (add --port 5175 etc.)
```

The dev server proxies `/api` to `http://127.0.0.1:8000`, so open the Vite URL, sign in
with the seeded recruiter account, and the whole workflow is available. API docs:
`http://localhost:8000/docs`.

Alternatively, from the project root: `bash run-dev.sh` starts both processes.

#### Generate a demo resume PDF

```bash
cd backend
python scripts/generate_sample_resume.py
# -> backend/sample_data/sample_resume.pdf
```

### Tests and builds

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
npm --prefix frontend run build
```

Tests use the offline `stub` provider and an isolated `quantumhire_test` database. They use
MongoDB if available, otherwise `mongomock`; the running app itself still requires the
configured MongoDB service. No LLM API key is needed.

### Optional: reseed manually

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.seed
```

---

## API surface

| Method | Path                              | Purpose                                    |
| ------ | --------------------------------- | ------------------------------------------ |
| GET    | `/`                               | Service banner                              |
| GET    | `/api/health`                     | `{"status": "ok"}`                          |
| GET    | `/api/health/db`                  | MongoDB reachability                        |
| GET    | `/api/roles`                      | List roles                                  |
| GET    | `/api/roles/{id}`                 | Single role                                 |
| POST   | `/api/roles`                      | Create a role                               |
| GET    | `/api/candidates`                 | List (`stage`, `role_id`, `search`, `limit`) |
| GET    | `/api/candidates/{id}`            | Candidate + resume evidence + profile        |
| POST   | `/api/candidates`                 | Create a candidate manually                  |
| **POST** | **`/api/candidates/upload`**    | **Upload a PDF resume → text → structured profile** |
| **PUT**  | **`/api/candidates/{id}/profile`** | **Save the recruiter-reviewed/approved profile** |
| PATCH  | `/api/candidates/{id}/stage?stage=` | Move a candidate between stages           |
| POST   | `/api/candidates/{id}/evaluate`   | Draft a qualitative evaluation for its role |
| PUT/POST | `/api/candidates/{id}/evaluation` | Edit or explicitly approve the evaluation |
| POST   | `/api/candidates/{id}/generate-test` | Draft a skill test from approved evidence |
| PUT/POST | `/api/candidates/{id}/skill-test` | Edit or approve the skill test             |
| GET    | `/api/candidates/{id}/events`     | Recruiter activity and integration history |
| POST   | `/api/agents/invoke`              | Execute an allowlisted application operation |
| GET    | `/api/knowledge/search`           | Retrieve cited recruitment guidance        |
| GET    | `/api/dashboard/summary`          | Dashboard counters + pipeline breakdown     |

Pipeline stages: `New` → `Under Review` → `Skill Test` → `Interview` → `Selected` / `Rejected`.

---

## Recruiter demo flow

1. **Create Job Role** - Dashboard → *Create Job Role*, enter the title, description and
   required skills, save (persisted via `POST /api/roles`), or select the seeded
   **AI Full-Stack Developer** role.
2. **Upload Resume** - Roles → *Upload resume* (or Candidates → *Upload Resume*), pick the
   role and a PDF; the backend extracts and structures the profile, then opens the
   candidate page.
3. **Extract Candidate Information** - review the extracted fields under
   *Resume / Profile* (stage: **Under Review**); edit anything, *Save Candidate Profile*
   persists and approves it.
4. **AI Evaluation** - *Generate AI Evaluation*; the backend combines the approved
   profile, the role's requirements and retrieved knowledge. Review evidence, readiness
   fields, strengths and gaps. There is no overall score or candidate ranking.
5. **Strengths & Gaps** - shown prominently in the evaluation; missing evidence is
   reported as *Not Demonstrated* / *Needs Verification*, never invented.
6. **Recommended Next Step** - shown for review; it is a recommendation only.
7. **Approve Recommendation** - unlocks the skill test (the backend rejects attempts
   before this approval with 409).
8. **Personalised Skill Test** - *Generate Personalised Skill Test*; the draft targets
   this candidate's weak areas against the role's requirements and cites the retrieved
   guidelines.
9. **Review / Edit** - edit title, problem, instructions, tasks, time limit,
   deliverables and criteria; *Save Draft* persists to MongoDB (survives refresh).
10. **Approve & Move to Skill Test** - persists approval, moves the candidate to
    **Skill Test**, records `skill_test_approved` + `stage_changed` events and dispatches
    a webhook (simulated unless `EXTERNAL_WEBHOOK_URL` is set). The dashboard counters
    update immediately.

AI tools cannot move candidates between pipeline stages. Recruiters move candidates with
the authenticated stage controls; entry into Skill Test specifically requires explicit test
approval. AI never selects or rejects candidates.

## Resume and evaluation pipeline

```
Upload PDF → Extract Profile → Recruiter Review/Edit → Approve Profile
           → Role-specific Evaluation → Recruiter Approval → Draft Skill Test
           → Recruiter Edit/Approval → Skill Test stage + webhook event
```

**Upload** (`multipart/form-data`: `file`, optional `role_id`, `stage`, `source`). The
frontend selects an active role by default; a candidate without a valid role cannot be
evaluated or receive a generated skill test.

| Failure                              | Status | Error code        |
| ------------------------------------ | ------ | ----------------- |
| empty file / no file part             | 400 / 422 | `empty_upload` |
| not a PDF (extension, MIME or magic bytes) | 415 | `unsupported_file_type` |
| over `MAX_RESUME_SIZE_MB`             | 413    | `resume_too_large` |
| corrupted / unreadable PDF            | 422    | `corrupt_pdf`     |
| password protected                    | 422    | `encrypted_pdf`   |
| no pages                              | 422    | `empty_pdf`       |
| scanned / image-only (no usable text) | 422    | `scanned_pdf`     |
| duplicate e-mail or identical resume  | 409    | –                 |
| AI provider not configured            | 503    | –                 |
| AI provider failed / invalid output   | 502    | –                 |

**Structured profile fields** (`app/models/profile.py`): `name`, `email`, `phone`,
`skills[]`, `technologies[]`, `work_experience[]`, `projects[]`, `education[]`,
`ai_experience[]`, `development_experience[]`, `tools_platforms[]`, `achievements[]`.
Anything the resume does not state comes back as `null` or `[]` - never invented.

**Stored on the candidate document:** `resume_filename`, `resume_text`, `extracted_profile`,
`original_extracted_profile` (audit copy), `profile_reviewed`, `profile_reviewed_at`,
plus `resume_sha256`, `resume_page_count/char_count/word_count`, `uploaded_at`,
`extracted_at`, `ai_provider`, `ai_model`, `extraction_warnings`.

**Evidence discipline & prompt-injection defence**

* Resume text is **untrusted data**: it is fenced between
  `<<<BEGIN_UNTRUSTED_RESUME_DATA>>>` / `<<<END_UNTRUSTED_RESUME_DATA>>>` markers in the
  *user* message and never concatenated into the system prompt.
* The system prompt forbids inference, requires `null`/`[]` for absent facts and demands
  JSON-only output that is then validated with Pydantic. Invalid output is rejected
  (502) rather than saved.
* Instruction-like resume content is detected and surfaced as a warning for the recruiter
  (it is never obeyed).
* Nothing is approved until a recruiter presses **Save Candidate Profile**
  (`profile_reviewed = true`, `profile_reviewed_at` recorded).

**Privacy:** the uploaded bytes are processed in memory only - they are never written to
disk and never served by a static route. Only the extracted text is persisted.

---

## RAG / knowledge base

Four local markdown files in `backend/knowledge/` provide the recruitment knowledge:
`ai_fullstack_requirements.md`, `evaluation_guidelines.md`, `skill_test_guidelines.md`
and `hiring_workflow.md`. They are split per heading, cached, and matched with a
lightweight keyword scorer (no embeddings, no vector database). Retrieved sections are:

- cited in the evaluation as `knowledge_sources` (`source.md#Heading`), and
- passed into skill-test generation, which cites the guidelines it actually retrieved.

Candidate evidence, role requirements and knowledge-base content stay separate inputs -
the knowledge base is never treated as facts about a candidate, and retrieval results are
never invented.

---

## Security

- **Authentication** - JWT bearer tokens from `POST /api/auth/login` (PBKDF2-hashed
  passwords seeded from `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`). Candidate, dashboard,
  evaluation, skill-test, event and role-creation endpoints require a valid token (401
  otherwise); mutations require the recruiter role.
- **Secrets** - every secret (`JWT_SECRET`, `MONGODB_URI`, `LLM_API_KEY`) is read from
  environment variables. `.env` is gitignored; no keys or passwords live in the source
  tree or in this README.
- **Resume handling** - uploaded bytes are validated (magic bytes, size, encryption,
  page/text checks), processed in memory only, and never served back. Resume text is
  fenced as untrusted data in prompts, instruction-like content is flagged for the
  recruiter, and model output is schema-validated (invalid output is rejected with 502,
  never saved).
- **AI containment** - agent tools are allowlisted; `update_candidate_status` refuses AI
  callers (403), and every approval/stage change is a separate authenticated recruiter
  action recorded in the activity log.

---

## Configuration

All secrets and connection strings come from environment variables (`.env`), never from source.

| Variable                       | Default                                  |
| ------------------------------ | ---------------------------------------- |
| `MONGODB_URI`                  | `mongodb://127.0.0.1:27017`              |
| `MONGODB_DB_NAME`              | `quantumhire`                            |
| `CORS_ORIGINS`                 | `http://localhost:5000,http://127.0.0.1:5000` |
| `SEED_ON_STARTUP`              | `true`                                   |
| `MAX_RESUME_SIZE_MB`           | `10`                                     |
| `RESUME_MIN_CHARS`             | `80` (below this the PDF is treated as scanned) |
| `LLM_PROVIDER`                 | `stub` - `none` / `stub` / `openai`       |
| `LLM_API_KEY`                  | *(empty)* - never hardcoded, never committed |
| `LLM_MODEL`                    | `gpt-4o-mini`                            |
| `LLM_BASE_URL`                 | `https://api.openai.com/v1` (any compatible gateway) |
| `LLM_TIMEOUT_SECONDS`          | `90`                                     |
| `SEED_ADMIN_EMAIL`             | *(empty; set in Replit Secrets)*         |
| `SEED_ADMIN_PASSWORD`          | *(empty; set in Replit Secrets)*         |
| `JWT_SECRET` / `SESSION_SECRET`| required signing secret                  |
| `EXTERNAL_WEBHOOK_URL`         | *(empty; webhook is simulated)*          |
| `VITE_API_BASE_URL` (frontend) | *(empty; same-origin `/api` proxy)*      |

### AI provider selection

The extraction provider is chosen purely by environment configuration:

| `LLM_PROVIDER` | Behaviour |
| -------------- | --------- |
| `none`         | Uploads fail with a clear **503** ("AI extraction is disabled…"). Nothing is invented. |
| `stub`         | Offline, deterministic, rule-based extractor (default). Every value is a regex/keyword match against the resume text, so it still cannot fabricate evidence. No key, no network. |
| `openai`       | Real LLM extraction against any OpenAI-compatible `/chat/completions` endpoint. Requires `LLM_API_KEY`. |

Both providers implement the same `LLMProvider` interface (`app/ai/base.py`), so switching is a
one-line env change. Add a new vendor by implementing that interface and registering it in
`app/ai/factory.py`.

---

## Known limitations

* MongoDB is required by the running app. The in-memory Mongo-compatible fallback is for
  tests only; it is not a replacement database for development or production.
* The `stub` provider is keyword/rule based: it is intentionally conservative, but a
  keyword can still match a word used in a non-skill context (e.g. "documentation" in
  "internal documentation"). That is exactly what the recruiter review step is for - and
  why a real LLM provider is one env var away.
* Knowledge retrieval uses local keyword matching, not embeddings or a hosted vector DB.
* Candidate evaluations and tests are drafts until a recruiter reviews and approves them.
  The prototype does not rank, select, or reject candidates.
* Resume files are not retained (text only), so "download original resume" is not offered.
* Uploads are processed synchronously; large PDFs or slow providers block the request
  (a background job queue is a later concern).
