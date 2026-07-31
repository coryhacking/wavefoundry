# Release packaging tests must pin main orchestration, not helpers alone

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1tzj7-mem release-packaging-tests-must-pin-main-orchestration-not-help`
Superseded by: `1tzsp-mem`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:release-main-bundle-wiring-unpinned`
Validation: promote
Validated by: agent
Action delta: When release artifact wiring changes, pin build_pack.main output count and names in addition to helper behavior.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Helper-level packaging tests can pass while the release entry point emits the wrong artifact set. Execute build_pack.main and assert the exact distribution shape: the feature zip plus one combined bundle, with no internal bridge artifact leaking into the release.

## Evidence

- `release-main-bundle-wiring-unpinned`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
