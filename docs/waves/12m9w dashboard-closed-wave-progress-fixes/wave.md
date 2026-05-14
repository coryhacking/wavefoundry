# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-14

wave-id: `12m9w dashboard-closed-wave-progress-fixes`
Title: Dashboard Closed Wave Progress Fixes

## Objective

Fix five bugs across `dashboard.js`, `dashboard_lib.py`, and `server.py` that caused the progress bars and tile metrics to show incorrect counts when closed or completed waves were present, and that made change docs using `Item Status:` or bare `Status:` fields invisible to the dashboard.

## Changes

Change ID: `12m9w-bug dashboard-js-closed-wave-progress-accuracy`
Change Status: `complete`

Change ID: `12m9w-bug dashboard-parser-closed-wave-and-status-fallback`
Change Status: `complete`

Change ID: `12ma1-enh ac-numbered-id-scaffold-standard`
Change Status: `complete`

Completed At: 2026-05-14

## Wave Summary

Five targeted fixes restoring accuracy of the Waves, Changes, and ACs progress bars for projects with closed/completed waves and non-canonical status field naming. All fixes verified with 1161 passing tests; packaged in `wavefoundry-2026-05-14d.zip`.

## Journal Watchpoints

- **Watchpoint:** `12ma1-enh ac-numbered-id-scaffold-standard` seed edit requires `seed_edit_allowed` gate — open before editing seed-170, close immediately after.

## Review Evidence

- wave-council-readiness: approved (2026-05-14 — root causes confirmed, fixes targeted and verified)
- wave-council-delivery: approved (2026-05-14 — 1161 tests pass, operator-tested in 14b–14d packages)
- operator-signoff: approved

## Dependencies

- No external wave dependencies.
