# Decision: Fix is two layers: patch `ensure_run` in the class setUp AN…

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-decision-fix-is-two-layers-patch-ensure-run-in-the-class-set`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 19734
Source event: `decision-log:1t231-bug test-writes-memory-state-outside-fixture:3d67f46c274560dc`
Validation: rewrite
Validated by: agent
Action delta: When a test exercises a CLI main() that defaults its root to cwd, sandbox the test cwd into a tempdir AND mock every side-effecting gate the main reaches; a runner-level stray-artifact check turns any miss into a suite failure instead of a working-tree surprise.
Validation rationale: The drafted candidate buries the durable two-layer pattern in incident prose. The generalized rule applies to any future cwd-defaulting CLI test (the class recurred twice in two days: 1t1b3 CLI defaults, 1t231 test writes), and the runner guard is the enforcement half worth pointing at.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-sandbox-cwd-and-mock-all-side-effecting-gates-in-cli-main-te`
## Summary

Decision (wave 1t3ek): Fix is two layers: patch `ensure_run` in the class setUp AND sandbox the class cwd into a tempdir, so any future unmocked cwd-relative write lands in the sandbox rather than the repository. Recurrence guard added at the runner level (`run_tests.py` `stray_artifact_paths`/`_stray_artifact_failure`): a run that creates a nested `.wavefoundry` under the scripts dir fails with the offending paths listed; pre-existing artifacts are snapshotted so only run-created ones fail. Guard demonstrated against a seeded artifact by unit test.. Rationale: The mock alone fixes today's writer; the sandbox and guard close the class.

## Evidence

- `1t231-bug test-writes-memory-state-outside-fixture`
- `1t3ek`

## Targets

- `run_tests.py`
