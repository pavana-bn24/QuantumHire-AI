# Skill Test Guidelines

How QuantumHire AI drafts practical skill tests for approved candidates.

## Purpose

A skill test validates the *gaps and partially-demonstrated areas* found in the
AI evaluation. It is a short, practical exercise — not a quiz and not a leetcode
gauntlet.

## Structure

Each test contains:

- `title` — role-flavoured, e.g. "AI Full-Stack Developer — Skill Test"
- `duration_minutes` — realistic for the exercise (default 60)
- `instructions` — how to submit, what is graded, what tools are allowed
- `questions` — 3–6 items, each with:
  - `prompt` — the task/question text
  - `type` — `coding` | `system_design` | `scenario` | `knowledge`
  - `focus` — which requirement area it covers (frontend, rag, ...)
  - `sample_answer` — what a strong answer demonstrates (for the reviewer)

## Hard rules

- Every question must map to a role requirement area and, where possible, to a
  specific gap or partially-demonstrated rating from the evaluation.
- Questions must be self-contained and answerable without access to proprietary
  code. Use the candidate's own stated stack when it is present in the approved
  profile.
- **No scores against the candidate** are produced at generation time. The test
  is a draft until the recruiter approves it.
- Edits are always allowed before approval; approval records a workflow event
  and moves the candidate to the Skill Test stage.

## Failure handling

- If the AI provider is unavailable, generation fails with a clear error and the
  recruiter can retry or write the test manually. A partial/invalid response is
  rejected, never silently used.
