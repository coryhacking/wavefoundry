# Prove MCP tool wrappers and overrides through the real call path

Owner: Engineering
Status: active
Last verified: 2026-09-26

Memory ID: `1z44o-mem prove-mcp-tool-wrappers-and-overrides-through-the-real-call-`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-26
Updated: 2026-09-26
Source exploration cost: 135009
Supersedes: `1yuj1-mem test-mcp-tool-wrappers-through-call-tool-async-handlers-esca`

## Summary

Wave 1yv9l delivery review found two ways a tool-surface guarantee looked proven but was not. (1) Calling tool.fn or checking __wf_middleware__ markers does not prove a wrapper works: FastMCP awaits whatever a sync wrapper returns, so an async handler runs after the lifecycle lock is released and a guard refusal dict becomes a ToolError. Drive lock, guard and argument checks through await mcp.call_tool with a probe inside the wrapped resource, and refuse (or skip) async handlers wherever the synchronous MIDDLEWARE chain applies. (2) An override compatibility check that compares only parameter names and required-ness lets a type change through (slug str to int registered and broke normal calls); compare each replaced parameter's normalized value schema, ignoring annotation-only keys (title, description, default, examples), and pair every refusal test with a positive control that a compatible override is accepted.

## Evidence

- `consolidated from 1yuj1-mem test-mcp-tool-wrappers-through-call-tool-async-handlers-esca`
- `consolidated from 1yv64-mem call-compatibility-checks-must-compare-value-schemas-with-po`

## Targets

- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
