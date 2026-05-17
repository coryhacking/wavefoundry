# `code_ask` should demote feedback/journal docs without suppressing them

Change ID: `12p3a-bug code-ask-feedback-docs-penalty`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-17
Wave: 12nbr code-intelligence-expansion

## Rationale

`code_ask` should answer implementation questions from the codebase first, but feedback and journal artifacts can still be useful evidence when they are the best or only source of a decision. A hard suppression would hide that context. The current issue is ranking noise: review/journal docs can outrank implementation sources for code questions even when they are only tangentially relevant.

This change adds a soft demotion for feedback, journal, and framework seed artifacts during `code_ask` ranking so implementation sources stay on top while the evidence trail remains discoverable.
The response now also surfaces `partition_applied`, `demotion_count`, `demoted`, `partition_reason`, and `final_rank` so the reordered list is legible instead of looking like a broken ranking.

## Requirements

1. `code_ask` must keep feedback and journal docs searchable.
2. `code_ask` must demote those artifacts, plus framework seed guidance, for implementation-oriented questions.
3. The demotion must be soft, not a hard exclusion.
4. The change must not affect docs search, code search, or other retrieval tools.

## Scope

**Problem statement:** review/journal/seed artifacts can outrank actual code in `code_ask` even when the question is about implementation behavior.

**In scope:**

- `server.py`
- `test_server_tools.py`

**Out of scope:**

- Global docs indexing changes
- Hard exclusion of feedback/journal artifacts
- Changes to other retrieval tools

## Acceptance Criteria

- AC-1: `code_ask` still returns feedback/journal docs when they are the best evidence, and framework seeds remain discoverable when they are the best evidence.
- AC-2: `code_ask` prefers implementation sources over feedback/journal/seed docs for code questions.
- AC-3: The demotion is visible in tests and does not break other question types.
- AC-4: The response surfaces partition metadata (`partition_applied`, `demotion_count`, `demoted`, `partition_reason`, `final_rank`) so the ranking inversion is understandable.
- AC-5: No retrieval tool loses access to the underlying docs or journal content.

## Required Review Lanes

- `qa-reviewer` — required (ranking behavior affects user-facing Q&A)
- `code-reviewer` — required (touches retrieval ordering logic)

## Tasks

- Add a narrow path- and kind-based ranking penalty for feedback/journal/seed artifacts in `code_ask`.
- Keep the penalty soft so those artifacts remain in the candidate set.
- Add regression coverage proving implementation sources outrank feedback and seed docs on code questions.

## Affected Architecture Docs

N/A. This is a retrieval ranking policy tweak.

## AC Priority

| AC   | Priority | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | Preserves discoverability of useful feedback |
| AC-2 | required | Fixes the observed ranking noise |
| AC-3 | important | Proves the policy is scoped and non-breaking |
| AC-4 | required | Makes the reordered list self-explanatory |
| AC-5 | required | Prevents accidental suppression of evidence |
