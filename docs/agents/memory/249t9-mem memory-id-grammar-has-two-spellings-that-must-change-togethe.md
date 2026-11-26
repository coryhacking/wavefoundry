# Memory-id grammar has two spellings that must change together

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249t9-mem memory-id-grammar-has-two-spellings-that-must-change-togethe`
Kind: `review_finding`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1t7l9-mem memory-id-grammar-has-two-spellings-that-must-change-togethe`

## Summary

When changing the memory-id grammar, update both spellings in the same change: .wavefoundry/framework/scripts/memory_records.py (_MEMORY_ID_PATTERN, MEMORY_ID_RE and the Memory ID / Pointer to / Supersedes / Superseded by line regexes) and .wavefoundry/framework/scripts/wave_lint_lib/constants.py (_MEMORY_ID_BODY, MEMORY_ID_PATTERN, MEMORY_SUPERSEDED_BY_PATTERN, MEMORY_POINTER_TO_PATTERN), or route both through one shared constant. No parity test exists; the 1t9w7 widening changed only memory_records.py and wf_validate_docs then failed with 90 missing-Memory-ID errors until the lint copy matched.

## Evidence

- `1t9w7-enh lifecycle-id-memory-naming`
- `wf_validate_docs`

## Targets

- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
