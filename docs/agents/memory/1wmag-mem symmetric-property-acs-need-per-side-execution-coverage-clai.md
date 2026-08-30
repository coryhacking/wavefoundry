# Symmetric-property ACs need per-side execution; coverage claims need mutation-proven regressions

Owner: Engineering
Status: active
Last verified: 2026-08-29

Memory ID: `1wmag-mem symmetric-property-acs-need-per-side-execution-coverage-clai`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-08-29
Updated: 2026-08-29
Source exploration cost: 54015
Source event: `finding:1wip2:DOCS-DEL-1`
Validation: promote
Validated by: agent
Action delta: When an AC claims a symmetric property (cross-references in both directions, a check wired into both paths), verify EACH side by execution before marking it: the delivered half passes every test while the undelivered half is invisible to the suite, and a coverage claim citing a source-ordering pin is not an executed regression — prove new gate coverage live by neutralizing the guarded branch in a scratch copy and watching the test fail.
Validation rationale: Verified against the current tree: both cross-reference directions now exist (test_shipped_reference_docs.py GuruIndexScopeParityTests and the reverse pointer in test_server_tools_lifecycle.py), and test_release_preflight_refuses_stale_version_constant_claim executes the release preflight with the mutation proof recorded in ev-docs-del-1-3. The drafted candidate's targets were bare filenames; the rewrite repoints at repo-relative paths.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1wip2 DOCS-DEL-1: AC-1's "cross-reference in both directions" shipped one-directional (the reverse docstring pointer was never written, and its home was outside the declared scope), and the record's "wired into BOTH packaging paths per the new regressions" overstated coverage (the regressions executed only the non-release home; the release side had a source-ordering pin). Repair: the reverse pointer added with the scope addition recorded, and an executed release-preflight regression whose liveness was proven by neutralizing the release-branch claims call in a scratch copy (test fails in the mutant, passes the real tree).

## Evidence

- `DOCS-DEL-1`
- `ev-docs-del-1-3`
- `test_build_pack.test_release_preflight_refuses_stale_version_constant_claim`

## Targets

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/build_pack.py`
