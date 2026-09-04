# A budget enforced only in helpers is not enforced; test the command path

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x4gn-mem a-budget-enforced-only-in-helpers-is-not-enforced-test-the-c`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 458752
Source event: `finding:1wpih:QA-DEL-2`
Validation: promote
Validated by: agent
Action delta: When a change claims a budget, quota, or cap, verify it on the COMMAND PATH that records the thing being capped, not on the helper functions: run the command against an already-exhausted state and confirm it refuses, writes no artifact, and leaves the ledger unchanged.
Validation rationale: Verified against both the evidence chain and the current tree. `authorize_checkpoint` and `checkpoint_budget_state` existed and were unit-tested, yet `retrieval_eval.py`'s `main()` called neither, so nothing charged a run against the cap. The consequence was measurable rather than hypothetical: the checkpoint ledger held fifteen invocations against a declared ceiling of nine, with duplicate slots, which made the ledger illegal under its own gate. `main()` now takes `--slot` and `--ledger`, authorizes BEFORE measuring, and appends the row itself; an exhausted slot returns `{"verdict": "refused", "refusal": {"code": "checkpoint_slot_already_used"}}` with exit 2, no report written, and the ledger unchanged. The second half is the accounting split that makes the cap honest: a failed attempt records its own row and consumes time, bytes and calls without occupying a slot, because a run that burned the resources spent what the cap exists to bound, and excluding failures would let unfavourable runs be quietly dropped. Fourteen retained failures in the ledger are the evidence that this matters. The generated summary quoted the reverification's disposition line instead of the reusable warning, so the record is rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

QA-DEL-2 (wave 1wpih): the nine-slot checkpoint budget shipped as `authorize_checkpoint` and `checkpoint_budget_state` with passing unit tests, but `retrieval_eval.py`'s `main()` called neither, so the ledger reached fifteen invocations against a ceiling of nine with duplicate slots -- illegal under its own gate while every test was green. The runner now takes `--slot` and `--ledger`, authorizes before measuring, and appends its own row; an exhausted slot refuses with `checkpoint_slot_already_used`, exit 2, no report, ledger unchanged. Accounting is kind-aware on purpose: a failed attempt records a row and consumes time, bytes and calls without occupying a slot, so unfavourable runs cannot be dropped. Verify any cap by invoking the command against an exhausted state, never by calling the helper it is supposed to use.

## Evidence

- `QA-DEL-2`
- `ev-qa-del-2-3`
- `1wpih`
- `test_retrieval_eval.CheckpointBudgetTests`
- `test_retrieval_eval.CheckpointLedgerKindTests`

## Targets

- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/test_retrieval_eval.py`
- `docs/evals/checkpoint-ledger.jsonl`
