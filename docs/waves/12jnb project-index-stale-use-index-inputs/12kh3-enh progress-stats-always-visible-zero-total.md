# Progress Stats Always Visible at Zero Total

Change ID: `12kh3-enh progress-stats-always-visible-zero-total`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard progress card should always show the progress rows for Waves, Changes, ACs, and Tasks even when a row's total is zero. Hiding ACs or Tasks when they are `0/0` makes the progress section feel incomplete and obscures the fact that there simply is no work of that type in the current snapshot.

## Requirements

1. The progress card should continue to render the Waves and Changes rows as it does today.
2. The ACs and Tasks rows should still render when their totals are zero.
3. A zero-total row should display as `0/0` rather than disappearing.
4. Regression coverage should verify the zero-total progress rows are present in the rendered dashboard component output.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing active-wave metric semantics
- Changing progress-bar semantics for non-zero totals
- Changing dialog or table layouts

## Acceptance Criteria

- The progress card still renders Waves and Changes rows.
- The progress card renders ACs and Tasks rows even when their totals are zero.
- Zero-total rows display `0/0` in the fraction text.
- Regression coverage exercises the zero-total render path.

## Tasks

- Remove the zero-total guard from the progress rows in the dashboard UI
- Keep the zero-total fraction visible as `0/0`
- Add a regression that renders the progress card with zero AC and task totals

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The progress card should remain complete even when some totals are zero |
| AC-2 | required | Zero-total AC and task rows should not disappear |
| AC-3 | required | The UI should show `0/0` instead of suppressing the row |
| AC-4 | required | Regression coverage should prove the render behavior |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Zero-total rows may look visually different from populated rows | Keep the same row structure and let the existing styling handle the empty state |
| The zero-total bar could imply completion | Render the fraction explicitly as `0/0` and keep the bar neutral |
