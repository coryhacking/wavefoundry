# Repaired defect upgrade-response-cap-aggregate-bypasses

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u2jp-mem repaired-defect-upgrade-response-cap-aggregate-bypasses`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 2939264
Source event: `finding:1tz6l:upgrade-response-cap-aggregate-bypasses`
Validation: rewrite
Validated by: agent
Action delta: When changing an MCP response cap, budget the serialized size of every key, value, omission-metadata field, diagnostic, and argv; then enforce a final whole-envelope postcondition with a fixed-shape refusal fallback.
Validation rationale: The source finding is durable, but the generated candidate targets only the regression file and states no reusable mechanism. The corrected record names the implementation boundary and the exact aggregate/serialization escape class proven by the repair.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1u1xb-mem response-caps-need-aggregate-serialized-size-enforcement`
## Summary

Real defect fixed in wave 1tz6l: This was a required AC-19 integrity boundary; the bounded repair is small relative to the host-output failure it prevents.

## Evidence

- `upgrade-response-cap-aggregate-bypasses`
- `ev-upgrade-response-cap-aggregate-bypasses-4`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
