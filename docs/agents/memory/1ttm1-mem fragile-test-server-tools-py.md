# Fragile: test_server_tools.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-28

Memory ID: `1ttm1-mem fragile-test-server-tools-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-28
Updated: 2026-07-28
Source exploration cost: 3365185
Source event: `repeated-repairs:1tsyx:test_server_tools.py`
Validation: rewrite
Validated by: agent
Action delta: When editing lifecycle tests in test_server_tools.py, run the focused lifecycle classes plus the canonical suite and mutation-check the claimed branch polarity.
Validation rationale: Three separate 1tsyx repair chains changed or restored lifecycle assertions in this large shared test module; the durable lesson is the verification posture, but the generated basename target was ambiguous.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tubb-mem lifecycle-assertions-in-test-server-tools-py-need-polarity-c`
## Summary

test_server_tools.py required 3 separate repairs during wave 1tsyx; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `populated-roster-enforcement-mislabeled-red-first`
- `ac7-stale-readiness-fix-is-mock-shadowed`
- `legacy-prose-activation-branches-unpinned`
- `1tsyx`

## Targets

- `test_server_tools.py`
