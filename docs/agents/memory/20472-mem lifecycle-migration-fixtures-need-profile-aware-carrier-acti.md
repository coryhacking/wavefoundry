# Lifecycle migration fixtures need profile-aware carrier activation and history paths

Owner: Engineering
Status: active
Last verified: 2026-10-08

Memory ID: `20472-mem lifecycle-migration-fixtures-need-profile-aware-carrier-acti`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 696912
Source event: `repeated-repairs:204hi:test_lifecycle_document_names.py`
Validation: promote
Validated by: agent
Action delta: Before trusting lifecycle migration fixtures under renamed distributions, seed the readable prompt manifest, assert the profiled Prepare policy marker, and derive historical fixture location from record_paths.WAVES_ROOT with a computed relative link; run both renamed profiles.
Validation rationale: QA-204HI-001 and QA-204HI-002 were independent fixture defects, not production migration defects. The repaired test activates actual profiled policy carriers and uses configured history discovery; default, second and prompt-names owners pass and removed-manifest/hardcoded-root mutants fail. Rewrite the generic fragility draft to the exact recurring boundary and full file path.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

In test_lifecycle_document_names.py, real-render validator tests must supply a readable prompt-surface manifest and assert the active profile's Prepare policy marker before claiming direct-document validation. History-link fixtures must live under record_paths.WAVES_ROOT and compute their link relative to that directory. Missing manifest silently leaves direct_docs checks inactive under prompt-names; hardcoded docs/waves leaves history undiscovered under second. Preserve exact-byte assertions and qualify both profiles.

## Evidence

- `QA-204HI-001`
- `QA-204HI-002`
- `204hi lifecycle-document-names`
- `LifecycleDocumentMoveTests.test_real_render_reconciles_policy_and_validation_follows_new_path`
- `LifecycleDocumentMoveTests.test_links_reported_without_rewriting_history`

## Targets

- `.wavefoundry/framework/scripts/tests/test_lifecycle_document_names.py`
