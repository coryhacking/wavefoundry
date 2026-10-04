# Decision: Leave `wfds.js` `badgeClass` alone

Owner: Engineering
Status: rejected
Last verified: 2026-10-03

Memory ID: `1zrtu-mem decision-leave-wfds-js-badgeclass-alone`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 303228
Source event: `decision-log:1zody-bug dashboard-done-statuses-from-lint-constants:12712e66bf014168`
Validation: reject
Validated by: agent
Action delta: No durable action: badgeClass is a colour map recorded in the 1zody Decision Log; nothing future depends on it.
Validation rationale: A scoping note for one change, not a reusable lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1zoju): Leave `wfds.js` `badgeClass` alone. Rationale: It is a tone map spanning in-progress, wave and review statuses, not a done test.

## Evidence

- `1zody-bug dashboard-done-statuses-from-lint-constants`
- `1zoju`

## Targets

- `wfds.js`
