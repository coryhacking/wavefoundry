# Mid-file unittest.main hides later tests

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-mid-file-unittest-main-hides-later-tests`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `finding:1slep:qa-build-pack-direct-run`
Validation: promote
Validated by: agent
Action delta: Before trusting direct execution of a unittest file, keep unittest.main() at EOF and compare its test count with the canonical per-file runner.
Validation rationale: The executed 1slep repair proved that a mid-file unittest.main() terminated discovery before later classes while still exiting green; the current file keeps the entrypoint at EOF.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A mid-file unittest.main() can exit before later test classes are defined while reporting green; keep the entrypoint at EOF and compare direct-execution counts with the canonical runner.

## Evidence

- `1slep`
- `qa-build-pack-direct-run`
- `ev-qa-build-pack-direct-run-3`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

## Targets

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
