# Response caps need aggregate serialized-size enforcement

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u1xb-mem response-caps-need-aggregate-serialized-size-enforcement`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 2939264
Source event: `finding:1tz6l:upgrade-response-cap-aggregate-bypasses`
Validation: promote
Validated by: agent
Action delta: When changing an MCP response cap, budget the serialized size of every key, value, omission-metadata field, diagnostic, and argv; then enforce a final whole-envelope postcondition with a fixed-shape refusal fallback.
Validation rationale: The source finding is durable, but the generated candidate targets only the regression file and states no reusable mechanism. The corrected record names the implementation boundary and the exact aggregate/serialization escape class proven by the repair.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Per-field truncation does not bound an MCP envelope: many small fields, oversized keys, omission metadata, diagnostics, and escaped argv can exceed the host cap in aggregate. Budget their serialized wire size and retain a final whole-envelope size check that returns a fixed-shape terminal refusal if compaction still cannot fit.

## Evidence

- `upgrade-response-cap-aggregate-bypasses`
- `ev-upgrade-response-cap-aggregate-bypasses-4`
- `wave 1tz6l`
- `.wavefoundry/framework/scripts/server_impl.py`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
