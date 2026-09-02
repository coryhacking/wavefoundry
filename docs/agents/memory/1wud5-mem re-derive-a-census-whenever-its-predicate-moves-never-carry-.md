# Re-derive a census whenever its predicate moves; never carry the figure forward

Owner: Engineering
Status: active
Last verified: 2026-09-01

Memory ID: `1wud5-mem re-derive-a-census-whenever-its-predicate-moves-never-carry-`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-01
Updated: 2026-09-01

## Summary

A corpus census is a function of its predicate, so quote it only with the predicate that produced it and re-derive it every time that predicate changes. Wave 1wur7 published four wrong counts for the same population: 297 (counted files containing a phrase anywhere, not acceptance criteria), then 317 (a different phrasing family, also withdrawn), then "seven non-closed carriers" carried forward across a matcher repair that itself surfaced an eighth, then a closed-archive figure that two independent scans measured differently. The eighth carrier is the instructive one: `1vt2s` AC-4 is a WRAPPED bullet, invisible to the pre-repair matcher, so the post-repair replay that reported "exactly the same seven as before" could not have covered it — the replay was run but not re-derived. Practical rules. State the predicate inline with any figure. When a figure is scan-dependent, say so and do not let a claim rest on it; 1wur7's load-bearing numbers (eight non-closed carriers, five parked plans, zero in the wave itself) reproduced identically across two independent scans while the archive total did not. Mark a withdrawn figure WITHDRAWN in place rather than editing it away, so the correction is auditable. And check the durable handoff artifact before close: 1wur7 re-published its own withdrawn 297 there after retracting it in the wave record.

## Evidence

- `1wur7 evaluator-identity-and-ac-locality`
- `1wuui-enh acceptance-criteria-locality-and-gate-scope`
- `DOCS-DEL-2`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `docs/waves`
