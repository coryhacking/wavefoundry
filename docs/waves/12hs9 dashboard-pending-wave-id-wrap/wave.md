# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-10

wave-id: `12hs9 dashboard-pending-wave-id-wrap`
Title: Dashboard: Fix Pending Wave ID Wrapping in Compact Row

## Objective

Fix `.open-wave-id` wrapping to a second line inside `.pending-wave-row`, which causes the wave title to appear as a misaligned second column and distorts the outer two-column content-grid layout.

## Changes

Change ID: `12hs9-bug pending-wave-id-wraps-in-compact-row`
Change Status: `complete`

Completed At: 2026-05-10

## Wave Summary

Single CSS fix: add `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex-shrink: 1` scoped to `.pending-wave-left .open-wave-id` so long pending-wave IDs truncate rather than wrap.

## Journal Watchpoints

- **Watchpoint: `.open-wave-id` used in two contexts** — `.open-wave-card` (active waves, full-card layout) and `.pending-wave-row` (compact row). The fix is scoped to `.pending-wave-left .open-wave-id` only; do not apply `nowrap` globally or it may affect the active-wave card rendering.

## Review Evidence

- wave-council-readiness: approved (2026-05-10 — single-rule CSS fix, root cause confirmed, scope limited to `.pending-wave-left .open-wave-id`)
- wave-council-delivery: approved (2026-05-10 — CSS rule added, 1087 tests passing, gate closed)
- operator-signoff: approved

## Dependencies

- No external wave dependencies.
