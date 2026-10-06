# Repaired defect DEL-2

Owner: Engineering
Status: active
Last verified: 2026-10-06

Memory ID: `1zxfj-mem repaired-defect-del-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-06
Updated: 2026-10-06
Source exploration cost: 190020
Source event: `finding:1zyc3:DEL-2`
Validation: promote
Validated by: agent
Action delta: When a change edits any @mcp.tool handler in register_mcp_surface (parameter, docstring or body), update that handler's hash in tests/fixtures/register-surface-handler-digests.json and add a sentence to its description naming the wave; add the fixture to the change doc's Serialization Points.
Validation rationale: Wave 1zyc3 added an optional parameter to wf_review_event; the implementer's focused runs were green but the full suite failed on HandlerDigestTests because the fixture was not in the plan.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Real defect fixed in wave 1zyc3: resolved

## Evidence

- `DEL-2`
- `ev-del-2-3`
- `1zyc3`

## Targets

- `test_mcp_tool_registry.py`
