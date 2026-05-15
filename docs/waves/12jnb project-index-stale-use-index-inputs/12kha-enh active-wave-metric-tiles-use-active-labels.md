# Active Wave Metric Tiles Use Active Labels

Change ID: `12kha-enh active-wave-metric-tiles-use-active-labels`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

When a wave is active, the detail dialogs already use `Active Changes`, `Active ACs`, and `Active Tasks`. The metric tiles should use the same active wording instead of staying on the pending labels.

## Requirements

1. The Changes, ACs, and Tasks metric tiles should read `Active` when there is at least one active wave.
2. The same tiles should continue to read `Pending` when no wave is active.
3. The metric values and counts should remain unchanged.
4. Regression coverage should lock the active/pending label behavior in place.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing the metric counts
- Changing dialog titles
- Changing wave list behavior

## Acceptance Criteria

- When an active wave exists, the metric tiles read `Active Changes`, `Active ACs`, and `Active Tasks`.
- When no active wave exists, the metric tiles read `Pending Changes`, `Pending ACs`, and `Pending Tasks`.
- The visible numbers and subnotes remain unchanged.
- Regression coverage locks the label mode in place.

## Tasks

- Update the metric tile labels to follow active-wave mode
- Keep the pending-mode labels intact when no active wave exists
- Add regression coverage for both active and pending label states

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The dashboard should present a consistent mode across tiles and dialogs |
| AC-2 | required | Pending-mode behavior must not regress |
| AC-3 | required | Counts must remain unchanged |
| AC-4 | required | Tests should prevent label drift |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Label changes could accidentally alter the counts or scope filtering | Keep the patch limited to label selection only |
| Pending-mode wording could be lost | Preserve the existing pending labels when no active wave exists |
