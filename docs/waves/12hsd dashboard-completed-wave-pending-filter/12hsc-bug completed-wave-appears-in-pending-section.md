# Dashboard: Pending Section Bugs — Completed Filter + Row Layout

Change ID: `12hsc-bug completed-wave-appears-in-pending-section`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-10
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

Three related bugs in the pending wave section:

1. `pendingWaves()` only excludes `"active"` and `"closed"` — waves with `Status: completed` pass through and appear in the Pending section, which is wrong.
2. `.pending-wave-left` uses `flex-direction: row` (default), placing the wave title beside the wave ID instead of below it. This causes the title to visually "kick everything right" and look like a misaligned second column.
3. `.waves-section-label::before` puts the horizontal rule to the LEFT of the label text, pushing "1 PENDING" to the far right. The rule should trail the text on the right.

## Requirements

1. Waves with status `"completed"` must not appear in the Pending section.
2. The wave title must render below the wave ID in the pending row, matching the stacked layout of active wave cards.
3. Transitional waves (`planned`, `ready`, `paused`) must still appear in Pending.

## Scope

**Problem statement:** `pendingWaves()` treats `"completed"` as non-terminal; `.pending-wave-left` stacks ID and title horizontally instead of vertically.

**In scope:**

- Add `"completed"` to the exclusion list in `pendingWaves()` in `dashboard.js`.
- Change `.pending-wave-left` to `flex-direction: column` in `dashboard.css`.

**Out of scope:**

- Redefining the full wave status taxonomy.

## Acceptance Criteria

- AC-1: A wave with `Status: completed` does not appear in the Pending section.
- AC-2: The wave title renders below (not beside) the wave ID in a pending row.
- AC-3: Transitional waves (`planned`, `ready`, `paused`) still appear in Pending.

## Tasks

- Update `pendingWaves()`: exclude `"completed"` alongside `"active"` and `"closed"`.
- Update `.pending-wave-left`: `flex-direction: column; align-items: flex-start; gap: var(--space-1)`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| js-fix | implementer | — | One-line change in `pendingWaves()` |
| css-fix | implementer | — | `.pending-wave-left` column direction |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to dashboard JS filter logic.

## AC Priority

| AC   | Priority | Rationale |
|------|----------|-----------|
| AC-1 | required | Core correctness — completed waves must not appear as pending |
| AC-2 | required | Transitional waves must still show |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-10 | Change doc created; root cause identified in `pendingWaves()` | Code review |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-10 | Extend exclusion list rather than define a TERMINAL_WAVE_STATUSES set | Minimal change; only one extra status to exclude | Define constant set |

## Risks

| Risk | Mitigation |
|------|------------|
| Other terminal status strings missed | Only `completed` observed in the wild; can extend later if needed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
