# Fragile: test_lifecycle_document_names.py

Owner: Engineering
Status: superseded
Last verified: 2026-10-08

Memory ID: `202kr-mem fragile-test-lifecycle-document-names-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 696912
Source event: `repeated-repairs:204hi:test_lifecycle_document_names.py`
Validation: rewrite
Validated by: agent
Action delta: Before trusting lifecycle migration fixtures under renamed distributions, seed the readable prompt manifest, assert the profiled Prepare policy marker, and derive historical fixture location from record_paths.WAVES_ROOT with a computed relative link; run both renamed profiles.
Validation rationale: QA-204HI-001 and QA-204HI-002 were independent fixture defects, not production migration defects. The repaired test activates actual profiled policy carriers and uses configured history discovery; default, second and prompt-names owners pass and removed-manifest/hardcoded-root mutants fail. Rewrite the generic fragility draft to the exact recurring boundary and full file path.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `20472-mem lifecycle-migration-fixtures-need-profile-aware-carrier-acti`

## Summary

test_lifecycle_document_names.py required 2 separate repairs during wave 204hi; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `QA-204HI-001`
- `QA-204HI-002`
- `204hi`

## Targets

- `test_lifecycle_document_names.py`
