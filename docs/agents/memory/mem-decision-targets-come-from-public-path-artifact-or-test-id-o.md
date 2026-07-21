# Decision: Targets come from `public_path` + `artifact_or_test_id` onl…

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-decision-targets-come-from-public-path-artifact-or-test-id-o`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 24594
Source event: `decision-log:1t728-bug memory-propose-target-misattribution:81659afd823c32ea`
Validation: rewrite
Validated by: agent
Action delta: When drafting memory candidates from repaired findings in memory_supply.py, never treat command_or_fixture file tokens as targets; targets come from public_path and artifact_or_test_id only.
Validation rationale: The drafted candidate's target came from a backtick mention of run_tests.py inside the decision's rationale prose (the example of the bug), not from the surface the decision governs. The decision itself is durable and correct; the anchor belongs on the drafter module the decision changed.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-decision-memory-supply-targets-exclude-the-verification-comm`
## Summary

Decision (wave 1t72b): Targets come from `public_path` + `artifact_or_test_id` only; `command_or_fixture` dropped from target extraction. Rationale: Its file tokens name the verification harness (`_PATH_TOKEN_RE` extracted `run_tests.py` from the suite command on 1t3ek), not the repaired surface.

## Evidence

- `1t728-bug memory-propose-target-misattribution`
- `1t72b`

## Targets

- `run_tests.py`
