# Repaired defect qa-build-pack-direct-run

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-repaired-defect-qa-build-pack-direct-run`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `finding:1slep:qa-build-pack-direct-run`
Validation: rewrite
Validated by: agent
Action delta: Before trusting direct execution of a unittest file, keep unittest.main() at EOF and compare its test count with the canonical per-file runner.
Validation rationale: The executed 1slep repair proved that a mid-file unittest.main() terminated discovery before later classes while still exiting green; the current file keeps the entrypoint at EOF.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-mid-file-unittest-main-hides-later-tests`
## Summary

Real defect fixed in wave 1slep: Original attack closed; controls pass.

## Evidence

- `qa-build-pack-direct-run`
- `ev-qa-build-pack-direct-run-3`
- `1slep`

## Targets

- `test_build_pack.py`
