# Fragile: test_upgrade_wavefoundry.py

Owner: Engineering
Status: rejected
Last verified: 2026-07-31

Memory ID: `1u5dd-mem fragile-test-upgrade-wavefoundry-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:test_upgrade_wavefoundry.py`
Validation: reject
Validated by: agent
Action delta: No durable action: the upgrade-side records already target this test file and name the exact classes to rerun together (PermissionsRenderBackstopTests, PermissionsConsentCrossesTheProcessBoundaryTests, PermissionsRenderConsentTests), so a separate repair-count record for the test module changes nothing.
Validation rationale: Both "repairs" credited to this file are the same two findings credited to upgrade_wavefoundry.py (preexisting-rules-never-adopted-defeats-motivating-case and permissions-backstop-unreachable-on-default-upgrade-path). Following them in the 1u2b0 ledger shows the defects are in the production module, not the test module: an undisclosed unmanaged-rules consequence, and a backstop whose only call site sat under an --update-index guard the default path never satisfies. The second finding's own artifact reference is a test in this file (PermissionsRenderBackstopTests::test_update_index_phase_calls_the_backstop) that PASSED while the behavior was still broken, which is a point about control design already captured in the production record rather than a fragility of the file. Verified in the current tree: .wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py exists and carries PermissionsRenderConsentTests (:6512), PermissionsConsentCrossesTheProcessBoundaryTests (:6765) and PermissionsRenderBackstopTests (:6829), with backstop assertions at :6908-6923 and :7001-7061. This test file is already a target of both the rewritten 1u2b0 upgrade record (1u551-mem) and the active 1u0dl-mem from wave 1tz6l, so a third generic record for it is retrieval noise.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

test_upgrade_wavefoundry.py required 2 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `preexisting-rules-never-adopted-defeats-motivating-case`
- `permissions-backstop-unreachable-on-default-upgrade-path`
- `1u2b0`

## Targets

- `test_upgrade_wavefoundry.py`
