# Dashboard: Restore Colored Line Deltas In Files Tile

Change ID: `12j2r-bug files-tile-colored-line-deltas`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The Files tile correctly moved to working-tree semantics, but the line-delta presentation regressed. It now renders added and removed counts as plain text with a trailing `lines` label, which loses the old high-signal green/red visual distinction and adds unnecessary wording. The tile should show only the numbers, with added lines in green and removed lines in red.

## Requirements

1. The Files tile must show added-line counts in green.
2. The Files tile must show removed-line counts in red.
3. The Files tile must not append the word `lines` after the counts.
4. The Files tile must preserve its current working-tree file-count semantics and click-through behavior.

## Scope

**Problem statement:** visual diff semantics regressed when the Files tile absorbed the line-delta summary.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
  - Render Files tile line deltas as styled spans instead of plain joined text
- `.wavefoundry/framework/dashboard/dashboard.css`
  - Add/restore the tile-specific green/red line-delta styling

**Out of scope:**

- Header git pill changes
- Files dialog content changes
- Git stat collection changes

## Acceptance Criteria

- AC-1: Added-line counts in the Files tile render in green.
- AC-2: Removed-line counts in the Files tile render in red.
- AC-3: The Files tile no longer shows the trailing word `lines`.
- AC-4: Dashboard verification passes.

## Tasks

- Replace the Files tile plain-text delta note with styled spans
- Restore green/red line-delta styles in dashboard CSS
- Verify dashboard JS syntax and docs lint

## Affected Architecture Docs

N/A — visual presentation fix only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Restores lost positive-change affordance |
| AC-2 | required | Restores lost negative-change affordance |
| AC-3 | required | Matches the requested tighter copy |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to restore colored line deltas in the Files tile without altering the current working-tree summary behavior. | Operator request; `dashboard.js`; `dashboard.css` |
| 2026-05-11 | Restored colored `+added` / `−removed` line deltas inside the Files tile note and removed the trailing `lines` label, while preserving current file-count semantics and click-through behavior. | `dashboard.js`; `dashboard.css`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Restore color semantics inside the Files tile note instead of reverting to header diff pills | Keeps the single-source summary in the tile while preserving the stronger visual cue | Re-add header pills (rejected: reintroduces duplication) |

## Risks

| Risk | Mitigation |
|------|------------|
| Tile note styling could inherit generic metric-note color and mute the diff colors | Use nested spans with explicit colors for added/removed counts |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
