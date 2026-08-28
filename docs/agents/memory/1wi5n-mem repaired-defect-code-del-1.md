# Repaired defect CODE-DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-08-27

Memory ID: `1wi5n-mem repaired-defect-code-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-27
Updated: 2026-08-27
Source exploration cost: 368764
Source event: `finding:1wik9:CODE-DEL-1`
Validation: reject
Validated by: agent
Action delta: The candidate's only target is an ephemeral scratchpad repro script absent from the tree, so the record as drafted cannot anchor future work; the durable lesson is re-recorded via memory_add against chunker.py and its pinned regressions.
Validation rationale: Evidence chain (CODE-DEL-1, ev-code-del-1-3) followed and real, but the drafted target repro_code_del_1.py lives in the session scratchpad and is not part of the repository; a memory pointing at a nonexistent file misleads recall. A corrected record with durable targets (chunker.py chunk_graphql_sdl/chunk_proto, test_chunker SpecFamilyTests repair regressions) is being added separately.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1wik9: repair verified complete by an independent fresh context distinct from the repairer; the pinned regressions keep each class from returning

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-3`
- `1wik9`

## Targets

- `repro_code_del_1.py`
