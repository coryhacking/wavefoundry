# Editing an @mcp.tool handler needs the handler digest fixture

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24amf-mem editing-an-mcp-tool-handler-needs-the-handler-digest-fixture`
Kind: `failed_attempt`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 190020
Supersedes: `1zxfj-mem repaired-defect-del-2`
Checked at: 2026-11-26T06:32:43Z
Check note: Handler source changes can rotate the registry fixture. Check the registered digest even when the tool name is unchanged. Reviewed .wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py:44.
Check flags: none

## Summary

When a change edits any @mcp.tool handler in register_mcp_surface (parameter, docstring or body), update that handler's hash in .wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json, add a sentence to its description naming the wave, and list the fixture in the change doc's Serialization Points. Why: wave 1zyc3 added an optional parameter to wf_review_event; focused runs were green but the full suite failed on tests/test_mcp_tool_registry.py HandlerDigestTests.test_every_handler_matches_its_pre_change_digest because the fixture was not in the plan (DEL-2).

## Evidence

- `DEL-2`
- `ev-del-2-3`
- `1zyc3`
- `test_mcp_tool_registry.HandlerDigestTests.test_every_handler_matches_its_pre_change_digest`

## Targets

- `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
