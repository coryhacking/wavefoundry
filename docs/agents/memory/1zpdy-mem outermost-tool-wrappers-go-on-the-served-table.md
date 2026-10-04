# Outermost tool wrappers go on the served table

Owner: Engineering
Status: active
Last verified: 2026-10-03

Memory ID: `1zpdy-mem outermost-tool-wrappers-go-on-the-served-table`
Kind: `decision`
Confidence: 0.8
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 303228
Source event: `decision-log:1zodw-bug unhandled-tool-exception-text-is-path-free:f71cc5c4cddbee30`
Validation: promote
Validated by: agent
Action delta: When adding a wrapper that must cover every served tool, add it as one final pass over the served table after _install_served_names, not as a slot in the middleware tuples.
Validation rationale: 1zoju readiness found that a slot in MIDDLEWARE left install-time rewrite and omitted passes and the mapped-alias translator outside the wrapper; the final pass over the served table is outermost by construction.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

register_mcp_surface applies MIDDLEWARE, then appends install-time passes (rewrite, omitted), then _install_served_names builds aliases and mapped-alias translators that wrap the canonical callable from outside. A wrapper that must be outermost for every served entry (like the 1zodw render pass) is applied once over the whole served table at the end, with an idempotence marker; a slot in MIDDLEWARE or _CORE_BEHAVIOUR_MIDDLEWARE is not outermost. Plain aliases share the canonical's wrapped callable.

## Evidence

- `1zodw-bug unhandled-tool-exception-text-is-path-free`
- `1zoju`

## Targets

- `wf_server/server_impl.py`
- `mcp_tool_registry.py`
