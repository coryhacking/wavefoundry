# Prove MCP tool wrappers and overrides through the real call_tool path

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24alk-mem prove-mcp-tool-wrappers-and-overrides-through-the-real-call-`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 135009
Supersedes: `1z44o-mem prove-mcp-tool-wrappers-and-overrides-through-the-real-call-`
Checked at: 2026-11-26T06:32:43Z
Check note: The registered call path includes middleware and overrides that direct handler invocations bypass. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:23954.
Check flags: none

## Summary

When you test an MCP tool wrapper, middleware guard or extension override, prove it through await mcp.call_tool with a probe inside the wrapped resource. Calling tool.fn or checking __wf_middleware__ markers proves nothing: FastMCP awaits whatever a sync wrapper returns, so an async handler runs after the lifecycle lock is released, and a guard's refusal dict becomes a ToolError. Refuse or skip async handlers wherever the synchronous middleware chain applies. When you check that an override is compatible, compare each replaced parameter's normalized value schema, ignoring annotation-only keys (title, description, default, examples). Comparing only names and required-ness let a slug str-to-int change register and break normal calls. Pair every refusal test with a positive control that a compatible override is accepted (wave 1yv9l delivery review).

## Evidence

- `1yv9l`
- `test_extension_tool_modules.test_real_client_path_holds_the_lock_and_validates_arguments`

## Targets

- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
