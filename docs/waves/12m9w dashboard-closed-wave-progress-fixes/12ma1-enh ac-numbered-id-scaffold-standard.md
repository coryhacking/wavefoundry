# Standard: AC-N Numbered Identifiers in Change Doc Scaffold

Change ID: `12ma1-enh ac-numbered-id-scaffold-standard`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12m9w dashboard-closed-wave-progress-fixes`

## Rationale

Change docs in this project use `- AC-1:`, `- AC-2:` identifiers for acceptance criteria, which creates stable references for the AC Priority table, review comments, and test evidence. The scaffold in `170-plan-feature.prompt.md` still uses a generic `- [Testable outcome]` placeholder, so new change docs require manual renaming. Standardizing the scaffold eliminates that step and makes the AC-N pattern the expected convention for all future change docs. Tasks remain as plain checkboxes — they are implementation-internal and have no cross-reference use case that would benefit from IDs.

## Requirements

1. The `## Acceptance Criteria` scaffold in `170-plan-feature.prompt.md` must use `- AC-1:` / `- AC-2:` as the placeholder format.
2. The `## Tasks` scaffold must remain as plain checkboxes — no task IDs introduced.
3. No other seeds or docs require changes for this scope.

## Scope

**Problem statement:** The plan-feature seed's AC scaffold doesn't match the AC-N convention used in practice, requiring manual fixup on every new change doc.

**In scope:**

- Update `## Acceptance Criteria` example lines in `170-plan-feature.prompt.md` seed.

**Out of scope:**

- Retrofitting existing change docs.
- Adding task IDs.
- Updating other seeds that mention AC format.

## Acceptance Criteria

- AC-1: `170-plan-feature.prompt.md` scaffold shows `- AC-1:` / `- AC-2:` as the AC placeholder format.
- AC-2: `## Tasks` scaffold is unchanged — plain checkboxes only.

## Tasks

- [x] Update `## Acceptance Criteria` placeholder in seed-170.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| seed-update | implementer | — | Single targeted edit to seed-170 |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to scaffold template; no boundary, flow, or test topology changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Core scaffold change |
| AC-2 | required  | Tasks format must not regress |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Seed-170 AC placeholder updated to AC-N format | Reviewed in session |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | No task IDs | Tasks are ephemeral implementation steps with no cross-reference use case | T-N identifiers — more overhead, no AC Priority equivalent |

## Risks

| Risk | Mitigation |
|------|------------|
| Agents generating AC-1/AC-2 mechanically without meaningful content | Existing guidance in seed-170 requires testable, concrete outcomes — unchanged |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
