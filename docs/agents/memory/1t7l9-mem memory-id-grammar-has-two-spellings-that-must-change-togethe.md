# Memory-id grammar has two spellings that must change together

Owner: Engineering
Status: active
Last verified: 2026-08-03

Memory ID: `1t7l9-mem memory-id-grammar-has-two-spellings-that-must-change-togethe`
Kind: `review_finding`
Confidence: 0.9
Created: 2026-07-22
Updated: 2026-08-02
## Summary

The memory-id grammar is spelled in two places that must widen together: memory_records.py (MEMORY_ID_RE plus the Memory ID / Supersedes / Superseded-by line regexes) and wave_lint_lib/constants.py (MEMORY_ID_PATTERN, MEMORY_SUPERSEDED_BY_PATTERN). The 1t9w7 two-form widening initially changed only memory_records.py after a consumer census missed the lint copy, and the migrated repository failed docs-lint with 90 errors until the lint patterns were widened to the identical union. Any future memory-id grammar change must update both spellings in the same change, or better, route both through one shared constant.

## Evidence

- `1t9w7-enh lifecycle-id-memory-naming` — the widening change whose docs gate caught the miss live
- `wf_validate_docs` failure with 90 missing-Memory-ID errors immediately after the local migration, clean after the lint patterns were widened

## Targets

- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
