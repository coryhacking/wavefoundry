# Repaired defect memory-close-one-shot-silent

Owner: Engineering
Status: superseded
Last verified: 2026-07-19

Memory ID: `mem-repaired-defect-memory-close-one-shot-silent`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-19
Updated: 2026-07-19
Source exploration cost: 1764640
Source event: `finding:1sxj7:memory-close-one-shot-silent`
Validation: rewrite
Validated by: agent
Action delta: Before closing a wave, require every evidence-derived memory source to have a candidate and an explicit validation disposition; zero-memory is valid only after drafting finds no material source.
Validation rationale: The independent public close probe reproduced the missing-candidate and pending-candidate gates, then showed an explicit rejection clears the diagnostic. This is a durable lifecycle invariant, while the original generated summary was too generic.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-close-requires-explicit-disposition-for-evidence-derived-mem`
## Summary

Real defect fixed in wave 1sxj7: Independent QA verified the repair and its executable regression.

## Evidence

- `memory-close-one-shot-silent`
- `ev-memory-close-one-shot-silent-4`
- `1sxj7`

## Targets

- `test_memory_records.py`
