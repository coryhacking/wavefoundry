# Sandbox cwd and mock all side-effecting gates in CLI-main tests

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-sandbox-cwd-and-mock-all-side-effecting-gates-in-cli-main-te`
Kind: `successful_pattern`
Confidence: 0.9
Created: 2026-07-20
Updated: 2026-07-20
Source event: `decision-log:1t231-bug test-writes-memory-state-outside-fixture:3d67f46c274560dc`
Validation: promote
Validated by: agent
Action delta: When a test exercises a CLI main() that defaults its root to cwd, sandbox the test cwd into a tempdir AND mock every side-effecting gate the main reaches; a runner-level stray-artifact check turns any miss into a suite failure instead of a working-tree surprise.
Validation rationale: The drafted candidate buries the durable two-layer pattern in incident prose. The generalized rule applies to any future cwd-defaulting CLI test (the class recurred twice in two days: 1t1b3 CLI defaults, 1t231 test writes), and the runner guard is the enforcement half worth pointing at.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Tests that call a CLI main() with a cwd-default root must chdir into a tempdir sandbox for the whole test class AND mock every side-effecting gate that main reaches (the 1t231 miss was one unmocked gate, memory_backfill.ensure_run, writing real sqlite state into the working tree). The run_tests.py stray-artifact guard (stray_artifact_paths/_stray_artifact_failure) fails any run that creates a nested .wavefoundry under the scripts directory, so a future miss surfaces as a suite failure with the offending paths listed rather than an untracked working-tree artifact.

## Evidence

- `1t231-bug test-writes-memory-state-outside-fixture`
- `1t3ek`
- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`

## Targets

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`
