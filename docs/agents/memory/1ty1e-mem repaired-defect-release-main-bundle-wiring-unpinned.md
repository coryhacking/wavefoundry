# Repaired defect release-main-bundle-wiring-unpinned

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1ty1e-mem repaired-defect-release-main-bundle-wiring-unpinned`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:release-main-bundle-wiring-unpinned`
Validation: rewrite
Validated by: agent
Action delta: When release artifact wiring changes, pin build_pack.main output count and names in addition to helper behavior.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tzj7-mem release-packaging-tests-must-pin-main-orchestration-not-help`
## Summary

Real defect fixed in wave 1tz6l: The required-AC defect was valid and the bounded repair was independently verified.

## Evidence

- `release-main-bundle-wiring-unpinned`
- `ev-release-main-bundle-wiring-unpinned-4`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
