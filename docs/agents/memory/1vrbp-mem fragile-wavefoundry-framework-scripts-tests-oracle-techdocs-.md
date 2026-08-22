# Fragile: .wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py

Owner: Engineering
Status: active
Last verified: 2026-08-20

Memory ID: `1vrbp-mem fragile-wavefoundry-framework-scripts-tests-oracle-techdocs-`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-20
Updated: 2026-08-20
Source exploration cost: 3060087
Source event: `repeated-repairs:1vry5:.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`
Validation: promote
Validated by: agent
Action delta: When editing the TechDocs boundary oracle, rerun the full pinned MkDocs/pathspec harness and its stale-label and directed-padding known-bad controls before trusting its publication or collapse claims.
Validation rationale: QA-DEL-1 and QA-DEL-2 were two independent repairs to this new harness: one made expected escaped-slash labels live-oracle-derived and falsifiable, and the other prevented directed cases from vacuously satisfying the random changed-emission floor. The current target contains both mechanisms and the final oracle run passed.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py required 2 separate repairs during wave 1vry5; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `QA-DEL-1`
- `QA-DEL-2`
- `1vry5`

## Targets

- `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`
