# Agent Doc Role Metadata Lint and Journal Exemption

Change ID: `12rp6-doc agent-role-metadata-lint`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

The dashboard already uses `Role:` as the inclusion gate for dashboard-visible agent entries, but that gate is only enforced at render time. The repo also has a mixed `docs/agents/` surface: role docs, personas, specialists, journals, and support docs live side by side. That makes it easy to introduce a file that is intended to be an agent entry but omits `Role:`.

This change makes the boundary explicit in validation:

- agent docs that are meant to appear as dashboard entries must declare `Role:`
- journals behave as they do today: if they declare `Role:`, the dashboard shows them in the journal group
- journals are not required to declare `Role:`
- support docs like `README.md`, `session-handoff.md`, and `platform-mapping.md` remain exempt

The goal is to prevent missing-role regressions before they reach the dashboard.

## Requirements

1. Define a repo-wide validation rule for `docs/agents/` that distinguishes agent docs from support docs.
2. Require `Role:` on dashboard-visible agent docs.
3. Require the `Role:` value to match the filename slug for those agent docs.
4. Exempt journal docs from the `Role:` requirement; journals continue to use the current dashboard behavior and do not need a special gate.
5. Exempt support docs such as `README.md`, `session-handoff.md`, and `platform-mapping.md`.
6. Keep the dashboard’s current render-time `Role:` gate as defense in depth.

## Scope

**Problem statement:** Missing `Role:` metadata can currently slip into agent-bearing docs without a validation failure, and journals/support docs risk being conflated with dashboard-visible agent entries.

**In scope:**

- docs validation for `docs/agents/` role metadata
- explicit journal exemption and current dashboard behavior
- slug-match validation for agent docs that do require `Role:`
- tests that prove missing or mismatched role metadata is caught

**Out of scope:**

- changing the dashboard UI layout
- changing how journals are written or distilled
- changing the contents of existing agent docs beyond any metadata needed for validation alignment

## Acceptance Criteria

- AC-1: A dashboard-visible agent doc missing `Role:` fails validation.
- AC-2: A dashboard-visible agent doc with a mismatched `Role:` value fails validation.
- AC-3: A journal doc under `docs/agents/journals/` does not fail validation solely because it lacks `Role:`.
- AC-3b: Journals continue to follow the current dashboard behavior and do not fail validation solely because they lack `Role:`.
- AC-4: Support docs such as `README.md`, `session-handoff.md`, and `platform-mapping.md` remain exempt.
- AC-5: Dashboard rendering still excludes files without `Role:` as a defense-in-depth behavior.

## Tasks

- [x] Define the validation boundary for `docs/agents/` so agent docs, journals, and support docs are handled separately.
- [x] Add a lint or gardener check for missing/mismatched `Role:` on agent docs.
- [x] Add tests covering agent docs, journal docs, and support docs.
- [x] Keep the dashboard’s current `Role:` inclusion gate unchanged unless the validation rule requires a follow-on adjustment.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| role-metadata-lint | implementer | — | Validation rule and tests for agent-doc metadata |

## Serialization Points

- `docs/agents/` role classification must be explicit before validation is enforced.

## Affected Architecture Docs

N/A — this is a validation and docs-surface policy change; no architecture boundary or runtime flow change is expected.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Missing-role regressions must be caught early |
| AC-2 | required | Slug mismatches are the most likely accidental drift |
| AC-3 | required | Journals are durable memory, not agent entries |
| AC-3b | required | Journals should stay hidden unless explicitly requested |
| AC-4 | required | Support docs are intentionally roleless |
| AC-5 | important | Defense in depth keeps the dashboard from regressing silently |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-20 | Change doc admitted into wave `12rnv agent-prompt-harness` from prompt-guidance review. | user request |
| 2026-05-20 | Implemented role-metadata lint for dashboard-visible agent docs with journal exemption and current dashboard behavior preserved. | `docs-lint: ok` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-20 | Treat journals as journal entries that do not need a special validation gate. | Matches current dashboard behavior and avoids conflating journals with generic role docs. | Force journals to carry `Role:` — rejected because it would blur the agent/journal distinction and add an unnecessary gate. |

## Risks

| Risk | Mitigation |
|------|------------|
| Validation accidentally flags journals or support docs | Keep an explicit exemption list and test it |
| Validation is too broad and blocks legitimate future agent docs | Make the allowlist for agent-bearing paths explicit and easy to extend |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
