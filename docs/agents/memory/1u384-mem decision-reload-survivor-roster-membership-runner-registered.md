# Decision: Reload-survivor roster membership: runner-registered tools…

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u384-mem decision-reload-survivor-roster-membership-runner-registered`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2az-enh rendered-mcp-permission-allowlist:9566d9ec8bd807dc`
Validation: rewrite
Validated by: agent
Action delta: When adding or removing an MCP tool that server.py registers itself (rather than register_mcp_surface), add it to RUNNER_TOOLS in mcp_tool_roster.py in the same change, so the impl-side parity check excludes it while the AST parity test still censuses both registration sites.
Validation rationale: The rule is durable and non-obvious, but the draft targets the bare basename `server.py`, which is the one file that does NOT own the constraint. Verified in the current tree: RUNNER_TOOLS is defined at .wavefoundry/framework/scripts/mcp_tool_roster.py:52 (frozenset({"wf_reload_mcp"})) with the rationale at :34 and the roster entry at :150; the impl-side parity check subtracts it at server_impl.py:29666-29672; and the AST parity test that censuses both registration sites is tests/test_render_platform_surfaces.py:2169-2171 (RosterRegistrationParityTests). Rewritten with all four repo-relative targets and the two-sided rule (roster member for allowlisting, excluded from the impl-side comparison) stated as an editing constraint.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u4ms-mem runner-registered-mcp-tools-are-roster-members-but-must-be-l`
## Summary

Decision (wave 1u2b0): Reload-survivor roster membership: runner-registered tools (`wf_reload_mcp`) ARE roster members (write tier) and are listed in `RUNNER_TOOLS` so the implementation-side parity check excludes them. Rationale: They are part of the published agent-facing tool surface and need allow rules like any other tool; they are registered by `server.py` after `register_mcp_surface` returns, so the impl-side comparison must exclude them while the AST parity test censuses both registration sites.

## Evidence

- `1u2az-enh rendered-mcp-permission-allowlist`
- `1u2b0`

## Targets

- `server.py`
