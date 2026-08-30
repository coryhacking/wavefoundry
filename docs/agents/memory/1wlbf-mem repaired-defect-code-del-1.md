# Repaired defect CODE-DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-08-29

Memory ID: `1wlbf-mem repaired-defect-code-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-29
Updated: 2026-08-29
Source exploration cost: 214119
Source event: `finding:1wl7u:CODE-DEL-1`
Validation: reject
Validated by: agent
Action delta: No durable action from this draft as written: its target list includes an ephemeral scratchpad mutant copy that is not in the tree, so the record cannot bind to current targets; the reusable lesson is re-recorded via memory_add with repo-relative targets.
Validation rationale: The generated candidate targets scratchpad/reverify-cd1/chunker_mutant.py (the reverifier's temporary mutant, deliberately outside the repo) and summarizes the reverification verdict rather than the reusable lesson. The underlying CODE-DEL-1 evidence chain is real and verified (events ev-code-del-1 through ev-code-del-1-3); the corrected record with durable targets (chunker.py, test_chunker.py) is added separately.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1wl7u: Repair verified: the original do_now judgment is kept; the finding's failure condition is closed by executed evidence and the pin is proven non-vacuous by the scratch-copy revert.

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-3`
- `1wl7u`

## Targets

- `scratchpad/reverify-cd1/chunker_mutant.py`
- `chunker.py`
