# Decision: memory-supply targets exclude the verification command field

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-decision-memory-supply-targets-exclude-the-verification-comm`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-20
Updated: 2026-07-20
Source event: `decision-log:1t728-bug memory-propose-target-misattribution:81659afd823c32ea`
Validation: promote
Validated by: agent
Action delta: When drafting memory candidates from repaired findings in memory_supply.py, never treat command_or_fixture file tokens as targets; targets come from public_path and artifact_or_test_id only.
Validation rationale: The drafted candidate's target came from a backtick mention of run_tests.py inside the decision's rationale prose (the example of the bug), not from the surface the decision governs. The decision itself is durable and correct; the anchor belongs on the drafter module the decision changed.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t72b (1t728): memory_supply.py's repaired-finding target extraction uses public_path and artifact_or_test_id only; command_or_fixture was dropped because its file tokens name the verification harness (run_tests.py was extracted from the suite command on 1t3ek and misattributed a fragile_file record), not the repaired surface. When no repaired-surface anchor exists, draft nothing — an honest gap beats a wrong advisory.

## Evidence

- `1t728-bug memory-propose-target-misattribution`
- `test_verification_command_never_becomes_a_target`
- `test_command_only_file_token_drafts_nothing`
- `1t72b`

## Targets

- `.wavefoundry/framework/scripts/memory_supply.py`
