# Repaired defect public-release-emits-special-upgrade-package

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u2fl-mem repaired-defect-public-release-emits-special-upgrade-package`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `finding:1tz6l:public-release-emits-special-upgrade-package`
Validation: rewrite
Validated by: agent
Action delta: Any change to release packaging must keep the single-package guards (_reject_stale_public_build_artifacts, _enforce_single_public_package) and their real-build test green; never introduce a second public artifact name
Validation rationale: The generated draft restates only that a reverification confirmed a repair, which carries no reusable mechanism. The durable lesson is the one-package contract and its guard structure, including that the original defect was co-signed by its own test. Evidence chain followed in events.jsonl; guards verified in build_pack.py today via executed ReleaseOrchestrationOrderingTests.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1u1af-mem release-builds-must-enforce-the-single-public-package-postco`
## Summary

Real defect fixed in wave 1tz6l: Independent fresh-context docs-contract-reviewer reverification confirms the repair

## Evidence

- `public-release-emits-special-upgrade-package`
- `ev-public-release-emits-special-upgrade-package-6`
- `1tz6l`

## Targets

- `build_pack.py`
