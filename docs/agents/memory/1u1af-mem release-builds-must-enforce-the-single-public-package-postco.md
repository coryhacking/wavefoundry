# Release builds must enforce the single-public-package postcondition

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u1af-mem release-builds-must-enforce-the-single-public-package-postco`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `finding:1tz6l:public-release-emits-special-upgrade-package`
Validation: promote
Validated by: agent
Action delta: Any change to release packaging must keep the single-package guards (_reject_stale_public_build_artifacts, _enforce_single_public_package) and their real-build test green; never introduce a second public artifact name
Validation rationale: The generated draft restates only that a reverification confirmed a repair, which carries no reusable mechanism. The durable lesson is the one-package contract and its guard structure, including that the original defect was co-signed by its own test. Evidence chain followed in events.jsonl; guards verified in build_pack.py today via executed ReleaseOrchestrationOrderingTests.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1tz6l shipped a build that emitted TWO public distributables (the normal zip plus a wavefoundry-upgrade pyz), and its own release test required both, so nothing caught it. The durable rule: the builder nests bridge and payload inside the one wavefoundry-<version>.zip, deletes every composition artifact from dist in a finally block, refuses to build when a stale special artifact pre-exists, and asserts exactly one new public package after the real build. Do not add a second public artifact name; extend the embedded payload instead.

## Evidence

- `public-release-emits-special-upgrade-package`
- `ev-public-release-emits-special-upgrade-package-6`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
