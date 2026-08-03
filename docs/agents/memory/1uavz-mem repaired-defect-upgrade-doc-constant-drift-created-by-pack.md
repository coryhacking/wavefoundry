# Repaired defect upgrade-doc-constant-drift-created-by-pack

Owner: Engineering
Status: rejected
Last verified: 2026-08-03

Memory ID: `1uavz-mem repaired-defect-upgrade-doc-constant-drift-created-by-pack`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-03
Updated: 2026-08-03
Source exploration cost: 1882438
Source event: `finding:1u8r2:upgrade-doc-constant-drift-created-by-pack`
Validation: reject
Validated by: agent
Action delta: No new memory is needed: apply the existing upgrade-runner phase-transition playbook whenever a lint-bound transition must ship on the installing upgrade, and extend its seam tests instead of creating a finding-specific record.
Validation rationale: The field failure and current pgi7 repair were verified in the review ledger and current upgrade extension/lock code. The reusable lesson is already captured by active memory 1u8q3: treat the old-code/new-code phase boundary as one unit, run behavior that must affect the installing upgrade from the incoming extension, and exercise docs/resume/cleanup seams. A separate graph-builder-specific failed-attempt record would duplicate that action without changing future work.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1u8r2: The known field failure is removed at the installing extension boundary, controls protect operator-authored content, and release/package evidence is clean.

## Evidence

- `upgrade-doc-constant-drift-created-by-pack`
- `ev-upgrade-doc-constant-drift-created-by-pack-4`
- `1u8r2`

## Targets

- `upgrade_extensions.py`
