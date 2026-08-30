# Repaired defect QA-DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-08-29

Memory ID: `1wjcc-mem repaired-defect-qa-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-29
Updated: 2026-08-29
Source exploration cost: 176572
Source event: `finding:1wl7w:QA-DEL-1`
Validation: reject
Validated by: agent
Action delta: No durable action from this draft as written: its sole target is the reverifier's ephemeral scratchpad mutant copy, which is not in the tree; the reusable lesson is re-recorded via memory_add with repo-relative targets.
Validation rationale: The generated candidate targets scratchpad/reverify-qd1/chunker_mutant.py (deliberately outside the repo) and summarizes the reverification verdict rather than the reusable lesson. The QA-DEL-1 evidence chain is real and verified (ev-qa-del-1 through ev-qa-del-1-3, strong-form mutant proof); the corrected record with durable targets (chunker.py, test_chunker.py) is added separately.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1wl7w: Repair verified: the original do_now judgment is kept; the oracle gap is closed by a delivered test proven to kill the exact surviving mutant, and every co-landed repair is executed-verified with its scope pinned.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1-3`
- `1wl7w`

## Targets

- `scratchpad/reverify-qd1/chunker_mutant.py`
