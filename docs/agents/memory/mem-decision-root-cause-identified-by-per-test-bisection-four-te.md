# Decision: Root cause identified by per-test bisection: four `test_set…

Owner: Engineering
Status: rejected
Last verified: 2026-07-20

Memory ID: `mem-decision-root-cause-identified-by-per-test-bisection-four-te`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 19734
Source event: `decision-log:1t231-bug test-writes-memory-state-outside-fixture:4dd14218c442e009`
Validation: reject
Validated by: agent
Action delta: No durable action: the incident narrative is captured in the 1t231 Decision Log, and recurrence of the artifact class is now mechanically enforced by the run_tests.py stray-artifact guard, so a memory advisory adds no behavior change.
Validation rationale: The candidate restates a one-time root-cause narrative. The durable half (the fix pattern) is being promoted via the sibling candidate's rewrite; the detection half is now a runner-level guard that fails the suite on recurrence, which is stronger than an advisory.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

Decision (wave 1t3ek): Root cause identified by per-test bisection: four `test_setup_wavefoundry` tests call `setup_wavefoundry.main([])` (cwd-default root) with render/index/dry-run mocked but `memory_backfill.ensure_run` UNMOCKED — the real gate call created `.wavefoundry/index/memory-state.sqlite` under whatever cwd the suite ran from (the scripts dir under `run_tests.py`), matching the observed stray row (`entry_path='setup'`, `inventory_pending`).. Rationale: Reproduced deterministically: the artifact appears after `tests.test_setup_wavefoundry` and after exactly those four test ids; the class setUp already mocked `sync_inventory`/`mark_indexed` but missed `ensure_run`..

## Evidence

- `1t231-bug test-writes-memory-state-outside-fixture`
- `1t3ek`

## Targets

- `run_tests.py`
