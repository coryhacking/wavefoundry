# Outermost tool wrappers go on the served table

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249qe-mem outermost-tool-wrappers-go-on-the-served-table`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 303228
Supersedes: `1zpdy-mem outermost-tool-wrappers-go-on-the-served-table`
Checked at: 2026-11-26T06:32:43Z
Check note: Server wrapper passes operate on the served-name table. Cover aliases and extension tools when adding outer middleware. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:24487.
Check flags: none

## Summary

When adding a wrapper that must cover every served tool, apply it as a final pass over the served table after _install_served_names, as _RENDER_PASS / _apply_render_pass in .wavefoundry/framework/scripts/wf_server/server_impl.py does with its _wf_rendered idempotence marker, not as a slot in MIDDLEWARE or _CORE_BEHAVIOUR_MIDDLEWARE. Why: 1zoju readiness found a MIDDLEWARE slot left the install-time rewrite and omitted passes and the mapped-alias translators built by _install_served_names outside the wrapper; plain aliases share the canonical's wrapped callable.

## Evidence

- `1zodw-bug unhandled-tool-exception-text-is-path-free`
- `1zoju`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/mcp_tool_registry.py`
