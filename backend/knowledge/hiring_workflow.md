# Hiring Workflow & Automation

The end-to-end recruiter workflow QuantumHire AI automates.

## Pipeline stages

New → Under Review → Skill Test → Interview → Selected (Rejected as an exit)

## Triggers and automations

| Trigger | Automated action |
| --- | --- |
| Resume uploaded | Candidate created (default stage `New`), workflow event `resume_uploaded`, recruiter sees it under "Awaiting review" |
| Recruiter approves profile | Stage moves to `Under Review`, event `profile_approved` |
| Recruiter runs / approves AI evaluation | Draft evaluation stored (`status draft` → `approved`), event `evaluation_generated` / `evaluation_approved` |
| Evaluation approved | Skill test drafted automatically, events `skill_test_generated` |
| Recruiter approves skill test | Stage moves to `Skill Test`, events `skill_test_approved`, outbound webhook fired |
| Stage moved manually | Event `stage_changed` recorded with actor and timestamps |
| Candidate created via API | Event `candidate_created` recorded |

## Workflow events

Every trigger appends a `WorkflowEvent` document:

```json
{
  "candidate_id": "<id>",
  "event": "profile_approved",
  "actor": "recruiter@quantumhire.ai",
  "timestamp": "2026-01-01T12:00:00Z",
  "metadata": {"stage": "Under Review", "triggered_by": "recruiter"}
}
```

The Activity tab in the UI renders this timeline newest-first.

## Webhooks

Approved skill tests (and other high-value events) POST a JSON payload to
`EXTERNAL_WEBHOOK_URL` when configured. If the URL is missing or delivery
fails, the event is **simulated**: recorded locally with
`"delivery": "simulated"` / `"failed"` so the workflow never blocks on a third
party. Inbound test webhooks can be delivered to
`POST /api/integrations/recruitment-webhook`.

## Role of the recruiter

Automation drafts; the recruiter decides. No candidate advances without an
explicit recruiter approval step, and no numeric candidate score is ever
computed or displayed.
