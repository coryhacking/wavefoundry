# Memory-supply targets exclude harness entries on both drafting paths

Owner: Engineering
Status: active
Last verified: 2026-07-25

Memory ID: `1tj3j-mem memory-supply-targets-exclude-harness-entries-on-both-drafti`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-25
Updated: 2026-07-25
Supersedes: `1tdmn-mem decision-memory-supply-targets-exclude-verification-harness-`

## Summary

When drafting memory candidates in memory_supply.py, exclude verification-runner entries (canonical run_tests.py plus any runner named by docs/workflow-config.json test_runner) from BOTH drafting paths: repaired-finding evidence and Decision Log prose refs. Angle-bracket placeholders like test_&lt;module&gt;.py are rejected for every caller in _code_targets. Do NOT screen prose targets by on-disk existence: decision docs legitimately name paths absent at drafting time, so an existence check drops genuine targets. If no qualifying target survives, draft nothing.

## Evidence

- `1tis7-bug memory-propose-decision-log-harness-target`
- `1tgkx-bug memory-propose-harness-token-target-misattribution`
- `MemoryProposeTests.test_decision_prose_harness_and_placeholder_never_become_targets`
- `MemoryProposeTests.test_decision_prose_keeps_the_governed_module`
- `1tis8`

## Targets

- `.wavefoundry/framework/scripts/memory_supply.py`
