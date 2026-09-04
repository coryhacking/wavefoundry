# Repaired defect QA-DEL-2

Owner: Engineering
Status: superseded
Last verified: 2026-09-04

Memory ID: `1x4my-mem repaired-defect-qa-del-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 458752
Source event: `finding:1wpih:QA-DEL-2`
Validation: rewrite
Validated by: agent
Action delta: When a change claims a budget, quota, or cap, verify it on the COMMAND PATH that records the thing being capped, not on the helper functions: run the command against an already-exhausted state and confirm it refuses, writes no artifact, and leaves the ledger unchanged.
Validation rationale: Verified against both the evidence chain and the current tree. `authorize_checkpoint` and `checkpoint_budget_state` existed and were unit-tested, yet `retrieval_eval.py`'s `main()` called neither, so nothing charged a run against the cap. The consequence was measurable rather than hypothetical: the checkpoint ledger held fifteen invocations against a declared ceiling of nine, with duplicate slots, which made the ledger illegal under its own gate. `main()` now takes `--slot` and `--ledger`, authorizes BEFORE measuring, and appends the row itself; an exhausted slot returns `{"verdict": "refused", "refusal": {"code": "checkpoint_slot_already_used"}}` with exit 2, no report written, and the ledger unchanged. The second half is the accounting split that makes the cap honest: a failed attempt records its own row and consumes time, bytes and calls without occupying a slot, because a run that burned the resources spent what the cap exists to bound, and excluding failures would let unfavourable runs be quietly dropped. Fourteen retained failures in the ledger are the evidence that this matters. The generated summary quoted the reverification's disposition line instead of the reusable warning, so the record is rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x4gn-mem a-budget-enforced-only-in-helpers-is-not-enforced-test-the-c`
## Summary

Real defect fixed in wave 1wpih: Reverified through the command line rather than the functions beneath it, because the defect was precisely that the command line did not call them.

## Evidence

- `QA-DEL-2`
- `ev-qa-del-2-3`
- `1wpih`

## Targets

- `retrieval_eval.py`
