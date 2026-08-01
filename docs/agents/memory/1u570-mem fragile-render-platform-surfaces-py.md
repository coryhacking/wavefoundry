# Fragile: render_platform_surfaces.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u570-mem fragile-render-platform-surfaces-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:render_platform_surfaces.py`
Validation: rewrite
Validated by: agent
Action delta: When editing render_claude_permissions or any surface describing it, re-verify the PROSE rather than the merge logic: say operator-approved and host-enforced (never "structurally unable to widen permissions"), check any "how to drop a rule" text against the unconditional declarative append, disclose rules the merge leaves unmanaged, and rerun ClaudePermissionsRenderTests + SyncSurfacesNeverRendersPermissionsTests.
Validation rationale: The draft records a repair count with no mechanism, and the mechanism here is unusually specific: in all five 1u2b0 repairs the merge CODE was found correct and every defect was a claim about it that outran it. Verified in the current tree: the render_claude_permissions docstring at render_platform_surfaces.py:1335-1347 now reads "OPERATOR-APPROVED, not structurally unreachable by an agent", names wf_upgrade as an agent-callable MCP tool that renders, bounds the blast radius to the read tier via PERMISSIONS_WRITE_TIER_KEY, and attributes knob protection to the HOST rather than the framework, replacing the disproved "structurally unable to widen permissions" sentence; seed 050-agent-entry-surface-bootstrap.prompt.md:361 now documents the three real levers (host deny, clearing wavefoundryAllowWriteTools, and the explicit warning that removing a rule from provenance while leaving it in allow suppresses nothing and does the opposite of the intent); and the unmanaged-rules disclosure landed in upgrade_wavefoundry.py:1508/1639-1645/2868, not in the renderer, confirming the renderer's non-claiming behavior was correct as written. Test carriers exist at tests/test_render_platform_surfaces.py:1726 and :2008. Evidence chain followed in the 1u2b0 ledger; the architecture lane's knob finding also traced the framework_edit_allowed to wf_open_gate chain that makes the guarantee a host property.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u51u-mem permission-render-fragility-is-overclaiming-prose-not-merge-`
## Summary

render_platform_surfaces.py required 5 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `seed-050-documents-nonworking-drop-procedure`
- `ac3-overclaims-agent-reachable-render-paths`
- `knob-operator-space-is-host-guarantee-not-framework`
- `preexisting-rules-never-adopted-defeats-motivating-case`
- `renderer-docstring-retains-structural-overclaim`
- `1u2b0`

## Targets

- `render_platform_surfaces.py`
