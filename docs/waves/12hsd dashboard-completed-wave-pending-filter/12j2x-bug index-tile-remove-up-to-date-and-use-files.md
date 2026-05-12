# Dashboard: Simplify Semantic Index Tile Hierarchy

Change ID: `12j2x-bug index-tile-remove-up-to-date-and-use-files`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The Semantic Index tile is over-signaling. Its primary number currently shows a combined files/chunks pair, and it spends a dedicated status line on `Up to date`. That makes the tile busier than necessary. The primary number should simply be the indexed file count, chunk totals should remain secondary context, and the tile should reserve the separate status line for exceptional or active states rather than the normal “current” case.

## Requirements

1. The Semantic Index tile primary number must be the combined indexed file count only.
2. The tile must no longer show `Up to date` as a dedicated status line.
3. Chunk totals may remain as secondary context.
4. Existing click-through behavior must remain unchanged.

## Scope

**Problem statement:** the index tile headline and status hierarchy are too dense for a steady-state dashboard tile.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
  - Change the primary value to files only
  - Suppress the current-state `Up to date` status line
- `.wavefoundry/framework/dashboard/dashboard.css`
  - Keep any necessary supporting styles aligned with the updated structure

**Out of scope:**

- Semantic Index dialog changes
- Index health/build logic changes

## Acceptance Criteria

- AC-1: The Semantic Index tile headline shows only the combined file count.
- AC-2: The tile no longer renders `Up to date`.
- AC-3: Chunk totals remain available as secondary context.
- AC-4: Dashboard verification passes.

## Tasks

- Change the index tile value to combined files only
- Remove the current-state `Up to date` status line
- Preserve chunk totals as secondary context
- Run dashboard verification

## Affected Architecture Docs

N/A — tile hierarchy change only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core user request |
| AC-2 | required | Core user request |
| AC-3 | important | Retains useful supporting context |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to simplify the Semantic Index tile so files are primary and steady-state current status is silent. | Operator request; `dashboard.js` |
| 2026-05-11 | Updated the Semantic Index tile so the headline is now combined indexed files only, chunk totals remain secondary context, and the `Up to date` status line is suppressed in the steady state. | `dashboard.js`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |
| 2026-05-11 | Adjusted the secondary index summary copy to include the word `files` explicitly (`<files> files / <chunks> chunks`) for clearer scanning. | `dashboard.js`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |
| 2026-05-11 | Refined the secondary summary to continue from the primary file count (`files / <chunks> chunks`) and always reserve a blank status row so stale/indexing states do not resize the tile. | `dashboard.js`; `dashboard.css`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Keep chunk totals as secondary context rather than removing them entirely | Chunks remain useful, but they should not compete with the main file count | Remove chunk totals completely (rejected: too much information loss) |

## Risks

| Risk | Mitigation |
|------|------------|
| Removing `Up to date` could hide status completely in the common case | Keep stale/running/failed/not-built states visible on the separate status line |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
