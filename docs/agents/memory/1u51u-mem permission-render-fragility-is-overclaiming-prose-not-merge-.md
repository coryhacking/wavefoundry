# Permission-render fragility is overclaiming prose, not merge logic

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u51u-mem permission-render-fragility-is-overclaiming-prose-not-merge-`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:render_platform_surfaces.py`
Validation: promote
Validated by: agent
Action delta: When editing render_claude_permissions or any surface describing it, re-verify the PROSE rather than the merge logic: say operator-approved and host-enforced (never "structurally unable to widen permissions"), check any "how to drop a rule" text against the unconditional declarative append, disclose rules the merge leaves unmanaged, and rerun ClaudePermissionsRenderTests + SyncSurfacesNeverRendersPermissionsTests.
Validation rationale: The draft records a repair count with no mechanism, and the mechanism here is unusually specific: in all five 1u2b0 repairs the merge CODE was found correct and every defect was a claim about it that outran it. Verified in the current tree: the render_claude_permissions docstring at render_platform_surfaces.py:1335-1347 now reads "OPERATOR-APPROVED, not structurally unreachable by an agent", names wf_upgrade as an agent-callable MCP tool that renders, bounds the blast radius to the read tier via PERMISSIONS_WRITE_TIER_KEY, and attributes knob protection to the HOST rather than the framework, replacing the disproved "structurally unable to widen permissions" sentence; seed 050-agent-entry-surface-bootstrap.prompt.md:361 now documents the three real levers (host deny, clearing wavefoundryAllowWriteTools, and the explicit warning that removing a rule from provenance while leaving it in allow suppresses nothing and does the opposite of the intent); and the unmanaged-rules disclosure landed in upgrade_wavefoundry.py:1508/1639-1645/2868, not in the renderer, confirming the renderer's non-claiming behavior was correct as written. Test carriers exist at tests/test_render_platform_surfaces.py:1726 and :2008. Evidence chain followed in the 1u2b0 ledger; the architecture lane's knob finding also traced the framework_edit_allowed to wf_open_gate chain that makes the guarantee a host property.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

All five render_platform_surfaces.py repairs in wave 1u2b0 landed on CLAIMS about the permission surface, never on the merge itself; each review that examined the code found it correct and each defect was a surface describing it as stronger or different than it is. (1) The function docstring and required AC-3 asserted agent-reachable renders are "structurally unable to widen permissions", which wf_upgrade disproves: it is an ordinary agent-callable MCP tool whose orchestration passes --include-permissions. The boundary is OPERATOR-APPROVED and HOST-ENFORCED, bounded to the READ tier because the write tier needs an operator-authored knob and wf_upgrade is itself write tier, so an agent-triggered upgrade can never allowlist the tool that triggered it. (2) The write-tier knob's protection was attributed to the framework, but the framework's own guard on .claude/settings.json is framework_edit_allowed, which the agent-callable wf_open_gate unlocks; the real guarantee is the host prompting, plus prompt policy. (3) Seed 050 documented a drop procedure the declarative merge undoes: every roster-desired rule absent from permissions.allow is appended and claimed on the next render, so provenance governs only PRUNING; the three real levers are a host deny entry, clearing wavefoundryAllowWriteTools for a write-tier rule, and (never as a drop) removing from provenance while leaving in allow, which converts the rule to operator-owned so it SURVIVES a later retirement. (4) The merge's deliberate refusal to claim an already-present unclaimed rule is correct and load-bearing for operator-rule survival, but it meant the motivating repositories got no rename self-heal while seeing only "Permissions: unchanged"; the fix was a disclosure of the unmanaged count on the upgrade side, not a code change here.

## Evidence

- `ac3-overclaims-agent-reachable-render-paths`
- `renderer-docstring-retains-structural-overclaim`
- `knob-operator-space-is-host-guarantee-not-framework`
- `seed-050-documents-nonworking-drop-procedure`
- `preexisting-rules-never-adopted-defeats-motivating-case`
- `1u2b0`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py:1324-1360 (corrected docstring)`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md:361 (three real levers)`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py:1726 ClaudePermissionsRenderTests, :2008 SyncSurfacesNeverRendersPermissionsTests`

## Targets

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
