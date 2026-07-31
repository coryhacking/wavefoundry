# Lifecycle assertions in test_server_tools.py need polarity checks

Owner: Engineering
Status: active
Last verified: 2026-07-28

Memory ID: `1tubb-mem lifecycle-assertions-in-test-server-tools-py-need-polarity-c`
Kind: `fragile_file`
Confidence: 0.94
Created: 2026-07-28
Updated: 2026-07-28
Source exploration cost: 3365185
Source event: `repeated-repairs:1tsyx:test_server_tools.py`
Validation: promote
Validated by: agent
Action delta: When editing lifecycle tests in test_server_tools.py, run the focused lifecycle classes plus the canonical suite and mutation-check the claimed branch polarity.
Validation rationale: Three separate 1tsyx repair chains changed or restored lifecycle assertions in this large shared test module; the durable lesson is the verification posture, but the generated basename target was ambiguous.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Repeated 1tsyx repairs showed that lifecycle assertions in the shared server-tools suite can silently transfer or invert coverage. For changes in this area, execute the focused lifecycle fixtures, mutate the claimed branch to prove the assertion bites, and then run the canonical suite.

## Evidence

- `populated-roster-enforcement-mislabeled-red-first`
- `ac7-stale-readiness-fix-is-mock-shadowed`
- `legacy-prose-activation-branches-unpinned`
- `1tsyx`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
