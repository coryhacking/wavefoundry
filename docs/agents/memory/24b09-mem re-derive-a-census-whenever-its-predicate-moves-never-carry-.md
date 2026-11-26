# Re-derive a census whenever its predicate moves; never carry the figure forward

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24b09-mem re-derive-a-census-whenever-its-predicate-moves-never-carry-`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1wud5-mem re-derive-a-census-whenever-its-predicate-moves-never-carry-`
Checked at: 2026-11-26T06:32:44Z
Check note: Counts in retained documentation depend on the exact selection predicate. Recount whenever that definition changes. Reviewed .wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py:1572.
Check flags: none

## Summary

When you quote a count of corpus sites (ACs, carriers, matched files) in a wave record, review finding or handoff and the matcher or predicate behind it changes, re-run the census under the new predicate. Do not carry the old figure forward. Wave 1wur7 published four wrong counts for the same population. One of them, 'seven non-closed carriers', was carried across a repair of the wave_validators.py matcher that surfaced an eighth carrier (1vt2s AC-4, a wrapped bullet the old matcher could not see). The replay was run but the count was not re-derived. State the predicate inline with every figure, say when a figure depends on the scan, and never rest a claim on such a figure. Mark a withdrawn figure WITHDRAWN where it appears, so the correction stays auditable. Check docs/agents/session-handoff.md before close: 1wur7 re-published a figure there after withdrawing it in the wave record (DOCS-DEL-2).

## Evidence

- `1wur7 evaluator-identity-and-ac-locality`
- `1wuui-enh acceptance-criteria-locality-and-gate-scope`
- `DOCS-DEL-2`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `docs/agents/session-handoff.md`
