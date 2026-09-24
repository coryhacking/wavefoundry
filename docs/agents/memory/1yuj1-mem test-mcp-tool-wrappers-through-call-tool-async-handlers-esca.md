# Test MCP tool wrappers through call_tool; async handlers escape sync wrappers

Owner: Engineering
Status: active
Last verified: 2026-09-24

Memory ID: `1yuj1-mem test-mcp-tool-wrappers-through-call-tool-async-handlers-esca`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-24
Updated: 2026-09-24
Source exploration cost: 135009
Source event: `finding:1yv9l:DEL-CALL-PATH-TESTS`
Validation: promote
Validated by: agent
Action delta: Prove MCP tool wrapper behavior (lifecycle lock, upgrade guard, argument validation) through FastMCP call_tool with a probe inside the wrapped resource, never only by calling tool.fn or checking __wf_middleware__ markers; refuse async handlers wherever sync MIDDLEWARE wrappers apply.
Validation rationale: Wave 1yv9l delivery: tests called table[name].fn and asserted wrapper markers, so an async extension override passed while running outside the lifecycle lock (FastMCP awaits the sync wrapper's return value, so the with-block exits before the coroutine runs). Red-team, code and security lanes reproduced it through build_server plus call_tool; the repair refused async staged tools and moved assertions onto call_tool with a lock probe; QA mutant Q7 confirmed the new assertion discriminates. The drafted target path was incomplete and the summary generic.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Calling tool.fn or checking __wf_middleware__ markers does not prove a wrapper's guarantee. FastMCP awaits whatever a sync wrapper returns, so an async handler runs after the lifecycle lock is released and a guard refusal dict becomes a ToolError. Drive lock, guard and argument checks through await mcp.call_tool with a probe inside the wrapped resource, and refuse async handlers where the synchronous MIDDLEWARE chain applies.

## Evidence

- `DEL-ASYNC-HANDLERS`
- `DEL-CALL-PATH-TESTS`
- `ev-del-call-path-tests-3`
- `1yv9l`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
