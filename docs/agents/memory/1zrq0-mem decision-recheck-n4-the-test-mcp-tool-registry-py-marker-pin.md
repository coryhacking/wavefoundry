# Decision: Recheck N4: the `test_mcp_tool_registry.py` marker pins gai…

Owner: Engineering
Status: superseded
Last verified: 2026-10-03

Memory ID: `1zrq0-mem decision-recheck-n4-the-test-mcp-tool-registry-py-marker-pin`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 303228
Source event: `decision-log:1zodw-bug unhandled-tool-exception-text-is-path-free:f71cc5c4cddbee30`
Validation: rewrite
Validated by: agent
Action delta: When adding a wrapper that must cover every served tool, add it as one final pass over the served table after _install_served_names, not as a slot in the middleware tuples.
Validation rationale: 1zoju readiness found that a slot in MIDDLEWARE left install-time rewrite and omitted passes and the mapped-alias translator outside the wrapper; the final pass over the served table is outermost by construction.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zpdy-mem outermost-tool-wrappers-go-on-the-served-table`

## Summary

Decision (wave 1zoju): Recheck N4: the `test_mcp_tool_registry.py` marker pins gain `render` unconditionally, and the pass wraps each served entry exactly once. Rationale: Those pins come from a full `register_mcp_surface` build.

## Evidence

- `1zodw-bug unhandled-tool-exception-text-is-path-free`
- `1zoju`

## Targets

- `test_mcp_tool_registry.py`
