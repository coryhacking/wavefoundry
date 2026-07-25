# Decision: Filter the canonical `run_tests.py` entry token plus implem…

Owner: Engineering
Status: rejected
Last verified: 2026-07-24

Memory ID: `1tidv-mem decision-filter-the-canonical-run-tests-py-entry-token-plus-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-24
Updated: 2026-07-24
Source exploration cost: 426910
Source event: `decision-log:1tgkx-bug memory-propose-harness-token-target-misattribution:033c38353f7910eb`
Validation: reject
Validated by: agent
Action delta: No new durable action: the harness-token exclusion decision is already recorded as active memory 1tdmn-mem, which correctly targets memory_supply.py; this duplicate adds nothing and mis-anchors the decision.
Validation rationale: Checked the current target and the corpus: this candidate duplicates the active decision 1tdmn-mem (both encode "exclude the test-runner entry plus workflow-config test_runner from memory-supply target extraction"). Worse, its drafted targets (run_tests.py, the literal test_&lt;module&gt;.py) are themselves the path-A misattribution: the decision governs memory_supply.py's draft_candidates, not the verification harness. The decision-log drafting path extracts backtick refs directly and was left out of 1tgkx's scope, so it still surfaces run_tests.py as a target. Reject as a duplicate; the surviving decision-log-path gap is follow-up material.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1tbt5): Filter the canonical `run_tests.py` entry token plus implementation-file tokens named by optional workflow-config `test_runner`; do not add cross-field suppression or test-module inference.. Rationale: This directly excludes known verification entry points while preserving product modules that may legitimately appear in both a fixture command and repaired-surface evidence. It is deterministic, bounded to one optional config read per draft call, and degrades to the canonical token when config is absent or invalid..

## Evidence

- `1tgkx-bug memory-propose-harness-token-target-misattribution`
- `1tbt5`

## Targets

- `run_tests.py`
- `test_<module>.py`
