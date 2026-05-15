# Active Change Dialog Header Overflow Wrap

Change ID: `12kh2-bug active-change-dialog-header-overflow-wrap`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

Long change IDs in the active changes dialog can push the status badge into the edge of the status pill or outside the card boundary. The shared dashboard should keep the header content contained so long identifiers remain readable without breaking the card layout, while leaving single-item AC/task headers left-aligned.

## Requirements

1. The active changes dialog header should keep the change identifier and status badge inside the card boundary.
2. Long change identifiers should wrap or otherwise constrain themselves before they can run into the status badge or overflow the dialog card.
3. Single-item headers in the AC and task dialogs should remain left-aligned and readable.
3. The fix should preserve the existing card styling and status badge behavior.
4. Regression coverage should prevent the overflow layout from returning.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing dialog copy or data ordering
- Changing active-wave filtering behavior
- Changing repository-specific surfaces

## Acceptance Criteria

- The active changes dialog header no longer lets the status badge run outside the dialog card.
- Long change identifiers remain readable and contained within the dialog layout.
- Single-item AC/task headers stay left-aligned instead of drifting to the right edge.
- Regression coverage exercises the long-header case.

## Tasks

- Constrain the metric dialog header layout so the left side can wrap or shrink
- Keep the metric dialog header left-aligned for single-item cards
- Add a regression that covers the long change ID / status badge case
- Sync the wave record after implementation

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The badge must remain inside the card boundary |
| AC-2 | required | Long identifiers should remain readable |
| AC-3 | required | Single-item AC/task headers should remain left-aligned |
| AC-4 | required | Regression coverage should guard the layout |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Wrapping the header may increase card height | Keep the wrap limited to the header row only |
| Truncating the identifier could reduce readability | Prefer wrap/shrink behavior over clipping |
