# Runner-registered MCP tools are roster members but must be listed in RUNNER_TOOLS

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u4ms-mem runner-registered-mcp-tools-are-roster-members-but-must-be-l`
Kind: `decision`
Confidence: 0.85
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2az-enh rendered-mcp-permission-allowlist:9566d9ec8bd807dc`
Validation: promote
Validated by: agent
Action delta: When adding or removing an MCP tool that server.py registers itself (rather than register_mcp_surface), add it to RUNNER_TOOLS in mcp_tool_roster.py in the same change, so the impl-side parity check excludes it while the AST parity test still censuses both registration sites.
Validation rationale: The rule is durable and non-obvious, but the draft targets the bare basename `server.py`, which is the one file that does NOT own the constraint. Verified in the current tree: RUNNER_TOOLS is defined at .wavefoundry/framework/scripts/mcp_tool_roster.py:52 (frozenset({"wf_reload_mcp"})) with the rationale at :34 and the roster entry at :150; the impl-side parity check subtracts it at server_impl.py:29666-29672; and the AST parity test that censuses both registration sites is tests/test_render_platform_surfaces.py:2169-2171 (RosterRegistrationParityTests). Rewritten with all four repo-relative targets and the two-sided rule (roster member for allowlisting, excluded from the impl-side comparison) stated as an editing constraint.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Reload survivors that server.py registers itself after register_mcp_surface returns (today: wf_reload_mcp) ARE part of the published agent-facing tool surface, so they belong in the permission roster at write tier and get allow rules like any other tool. But the impl-side parity check cannot see them, because they are not registered by register_mcp_surface. The reconciliation is RUNNER_TOOLS in mcp_tool_roster.py: the roster lists the tool, server_impl subtracts RUNNER_TOOLS before comparing registered tools against the roster, and the AST parity test censuses BOTH registration sites so the exclusion cannot be used to hide a genuinely missing tool. Adding a runner-registered tool without updating RUNNER_TOOLS makes the impl-side parity check fail; removing one without updating it makes the exclusion silently over-broad.

## Evidence

- `1u2az-enh rendered-mcp-permission-allowlist`
- `1u2b0`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py:34,52,150`
- `.wavefoundry/framework/scripts/server_impl.py:29666-29672`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py:2091 RosterRegistrationParityTests`

## Targets

- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
