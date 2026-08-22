# Repaired defect ARCH-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-08-20

Memory ID: `1vsu1-mem repaired-defect-arch-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-20
Updated: 2026-08-20
Source exploration cost: 3060087
Source event: `finding:1vry5:ARCH-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: After any TechDocs matcher edit, refresh the load-bearing cost comment and retained module hash last, and verify the pinned MkDocs/pathspec oracle remains test-only, excluded from packages, and absent from runtime imports.
Validation rationale: ARCH-DEL-1 showed that correct matcher code can still ship with a stale source carrier and stale retained-artifact provenance. Current targets confirm the corrected historical/delivered wording, exact module hash binding, source-only oracle placement, and scripts/tests package exclusion. The generated candidate was truncated and omitted the oracle/testing-architecture target, so a rewrite is more durable and actionable.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vtfy-mem techdocs-matcher-provenance-and-oracle-isolation-move-togeth`
## Summary

Real defect fixed in wave 1vry5: Cycle 5 resolves the architecture finding: the load-bearing source carrier now matches the delivered mechanism and surviving availability risk, artifact provenance is exact, and the external oracle remains isolated to the source-repository…

## Evidence

- `ARCH-DEL-1`
- `ev-arch-del-1-3`
- `1vry5`

## Targets

- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `build_pack.py`
