# Fragile: tests/test_render_platform_surfaces.py

Owner: Engineering
Status: rejected
Last verified: 2026-07-31

Memory ID: `1u5g4-mem fragile-tests-test-render-platform-surfaces-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:tests/test_render_platform_surfaces.py`
Validation: reject
Validated by: agent
Action delta: No durable action: nothing changes for the next editor of this test file beyond what the production record already says, which names the exact classes to rerun (ClaudePermissionsRenderTests, SyncSurfacesNeverRendersPermissionsTests) and is already targeted at this file.
Validation rationale: Both "repairs" credited to this file are the same two findings credited to render_platform_surfaces.py (seed-050-documents-nonworking-drop-procedure and ac3-overclaims-agent-reachable-render-paths). Following them in the 1u2b0 ledger shows neither is a defect IN the test module: they are a seed-prose defect and a required-AC overclaim whose repairs added pinning tests here (the knob-off invariant test the AC-3 finding explicitly noted did not yet exist, plus the permissions-switch census). A test file being edited alongside its subject is co-change, not fragility, and the file carries no mechanism of its own. Verified in the current tree: the file exists at .wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py with ClaudePermissionsRenderTests (:1726), SyncSurfacesNeverRendersPermissionsTests (:2008) and RosterRegistrationParityTests (:2091) present. The reusable content is already carried by the rewritten production record (1u51u-mem, which lists this test file as a target and names the classes to rerun) and by the RUNNER_TOOLS decision record (1u4ms-mem, which cites the AST parity test here). A second generic "treat as fragile" record for the test module would add retrieval noise with no action delta.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

tests/test_render_platform_surfaces.py required 2 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `seed-050-documents-nonworking-drop-procedure`
- `ac3-overclaims-agent-reachable-render-paths`
- `1u2b0`

## Targets

- `tests/test_render_platform_surfaces.py`
