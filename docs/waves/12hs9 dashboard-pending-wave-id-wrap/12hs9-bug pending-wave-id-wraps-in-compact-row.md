# Dashboard: Pending Wave ID Wraps in Compact Row

Change ID: `12hs9-bug pending-wave-id-wraps-in-compact-row`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-10
Wave: `12hs9 dashboard-pending-wave-id-wrap`

## Rationale

In `.pending-wave-row`, the wave ID element (`.open-wave-id`) has no `white-space: nowrap`, so long wave IDs (e.g. `"00000 wave-zero-plans-and-specs"`) wrap to a second line. The `.pending-wave-title` then appears to float beside the second line of the ID, giving the row a false two-column appearance and distorting the outer two-column content-grid layout visually.

## Requirements

1. The wave ID in a `.pending-wave-row` must not wrap to a second line regardless of ID length.
2. If the wave ID is too long to fit, it must truncate with an ellipsis rather than wrapping.
3. The title retains its existing ellipsis truncation behavior.

## Scope

**Problem statement:** `.open-wave-id` lacks `white-space: nowrap` when used in `.pending-wave-left`, causing multi-line wrap on long IDs.

**In scope:**

- Add scoped CSS to prevent `.open-wave-id` from wrapping inside `.pending-wave-left`.

**Out of scope:**

- Layout changes to `.open-wave-card` (active wave cards, which have different layout needs).
- Any JS changes.

## Acceptance Criteria

- AC-1: A pending wave row with a long wave ID (≥ 30 chars) renders the ID on a single line without wrapping.
- AC-2: If the ID is too long, it truncates with `…` rather than overflowing.
- AC-3: The `.pending-wave-title` still truncates with ellipsis as before.

## Tasks

- Add `.pending-wave-left .open-wave-id { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex-shrink: 1; }` to `dashboard.css`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| css-fix    | implementer | — | Single CSS rule addition |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to dashboard CSS, no boundary or flow impact.

## AC Priority

| AC   | Priority | Rationale |
|------|----------|-----------|
| AC-1 | required | Core layout correctness |
| AC-2 | required | Prevents overflow |
| AC-3 | important | Existing behavior must be preserved |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-10 | Change doc created; root cause identified in `.open-wave-id` CSS | Code review |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-10 | Scoped to `.pending-wave-left .open-wave-id` only | `.open-wave-id` in active wave cards may wrap intentionally | Global `nowrap` on `.open-wave-id` |

## Risks

| Risk | Mitigation |
|------|------------|
| Very long IDs clipped entirely if title takes all space | `flex-shrink: 1; min-width: 0` on ID allows title to share space |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
