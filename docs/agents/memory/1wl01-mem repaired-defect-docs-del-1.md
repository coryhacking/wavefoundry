# Repaired defect DOCS-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-08-29

Memory ID: `1wl01-mem repaired-defect-docs-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-29
Updated: 2026-08-29
Source exploration cost: 54015
Source event: `finding:1wip2:DOCS-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: When an AC claims a symmetric property (cross-references in both directions, a check wired into both paths), verify EACH side by execution before marking it: the delivered half passes every test while the undelivered half is invisible to the suite, and a coverage claim citing a source-ordering pin is not an executed regression — prove new gate coverage live by neutralizing the guarded branch in a scratch copy and watching the test fail.
Validation rationale: Verified against the current tree: both cross-reference directions now exist (test_shipped_reference_docs.py GuruIndexScopeParityTests and the reverse pointer in test_server_tools_lifecycle.py), and test_release_preflight_refuses_stale_version_constant_claim executes the release preflight with the mutation proof recorded in ev-docs-del-1-3. The drafted candidate's targets were bare filenames; the rewrite repoints at repo-relative paths.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1wmag-mem symmetric-property-acs-need-per-side-execution-coverage-clai`
## Summary

Real defect fixed in wave 1wip2: repair verified complete by an independent fresh context distinct from the repairer; the release-home regression is proven live by mutation, closing the coverage gap the record claimed

## Evidence

- `DOCS-DEL-1`
- `ev-docs-del-1-3`
- `1wip2`

## Targets

- `test_build_pack.py`
- `test_server_tools_lifecycle.py`
- `build_pack.py`
