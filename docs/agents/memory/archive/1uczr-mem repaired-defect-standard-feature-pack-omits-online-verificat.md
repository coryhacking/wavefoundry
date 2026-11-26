# Repaired defect standard-feature-pack-omits-online-verification-manifest

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1uczr-mem repaired-defect-standard-feature-pack-omits-online-verificat`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-03
Updated: 2026-11-25
Source exploration cost: 229641
Source event: `finding:1uas8:standard-feature-pack-omits-online-verification-manifest`
Validation: promote
Validated by: agent
Action delta: When adding a metadata-only companion contract, test the default feature-package branch rather than only the optional companion branch.
Validation rationale: The recorded QA finding was reproduced from the actual build branch, repaired with a checked-in canonical manifest, and independently reverified by the default-package artifact test.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-25T16:09:20Z
Check note: Item 7 review: encoded elsewhere. The summary is a reviewer verdict, not a lesson; the repaired default branch is pinned by .wavefoundry/framework/scripts/tests/test_build_pack.py::BuildPackTests::test_standard_feature_package_contains_verification_manifest_without_model_payload (asserts model-set-verification-manifest.json is packaged without --with-models), with attestation covered by tests/tes.
Check flags: target_churn, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in The summary is a reviewer verdict, not a lesson; the repaired default branch is pinned by .wavefoundry/framework/scripts/tests/test_build_pack.py::BuildPackTests::test_standard_feature_package_contains_verification_manifest_without_model_payload (asser.
Archive path: `docs/agents/memory/archive/1uczr-mem repaired-defect-standard-feature-pack-omits-online-verificat.md`

## Summary

Real defect fixed in wave 1uas8: The repaired canonical-manifest packaging path resolves the finding and includes a direct regression guard for the previously missing default branch.

## Evidence

- `standard-feature-pack-omits-online-verification-manifest`
- `ev-standard-feature-pack-omits-online-verification--3`
- `1uas8`

## Targets

- `test_model_bundle.py`
