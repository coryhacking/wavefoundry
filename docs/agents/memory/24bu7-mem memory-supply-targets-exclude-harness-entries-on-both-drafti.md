# Memory-supply targets exclude harness entries on both drafting paths

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bu7-mem memory-supply-targets-exclude-harness-entries-on-both-drafti`
Kind: `decision`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1tj3j-mem memory-supply-targets-exclude-harness-entries-on-both-drafti`

## Summary

When changing how .wavefoundry/framework/scripts/memory_supply.py drafts candidate targets, keep verification-runner entries (run_tests.py plus any runner named by the docs/workflow-config.json test_runner key, via _test_runner_entry_names) out of BOTH drafting paths, repaired-finding evidence and Decision Log prose refs, and keep rejecting angle-bracket placeholders such as test_<module>.py for every caller in _code_targets. A decision governs the module it changes, never the harness that verified it. Automatic drafts now also anchor only to current, contained regular files (eligible_repository_targets), so a prose ref to a not-yet-existing path yields no target; if no target survives, draft nothing.

## Evidence

- `1tis7-bug memory-propose-decision-log-harness-target`
- `1tgkx-bug memory-propose-harness-token-target-misattribution`
- `MemoryProposeTests.test_decision_prose_harness_and_placeholder_never_become_targets`
- `MemoryProposeTests.test_decision_prose_keeps_the_governed_module`
- `1tis8`

## Targets

- `.wavefoundry/framework/scripts/memory_supply.py`
