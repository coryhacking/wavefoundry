# Call-compatibility checks must compare value schemas, with positive controls

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1yv64-mem call-compatibility-checks-must-compare-value-schemas-with-po`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-24
Updated: 2026-09-24
Source exploration cost: 274985
Source event: `repeated-repairs:1yv9l:tests/test_extension_tool_modules.py`
Validation: promote
Validated by: agent
Action delta: When a check claims callers of a replaced MCP tool keep working, compare each replaced parameter's normalized value schema (types, enums, items, nested defs), not only parameter names and required-ness, and pair every refusal fixture with a positive control for what must stay allowed (defaults, titles, added optional parameters).
Validation rationale: Wave 1yv9l: two repair cycles touched the extension test file, but the file itself is not fragile; the recurring defect was a compatibility check narrower than its stated promise. The first delivery pass accepted a names-and-required-only check; an independent review showed an override changing slug str to int registered and broke normal wf_create_wave calls. Repair 2 added value-schema equality with annotations ignored; QA found a title-significant mutant survived until an added-optional-parameter plus custom-title positive control was added.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

A tool-override compatibility check that compares only parameter names and required-ness lets a type change through (slug str to int registered and broke normal calls). Compare each replaced parameter's normalized value schema with annotations (title, description, default, examples) ignored, and keep positive controls proving defaults, titles and added optional parameters stay allowed, or an over-strict variant goes unnoticed.

## Evidence

- `DEL-OVERRIDE-VALUE-COMPATIBILITY`
- `DEL-CALL-PATH-TESTS`
- `1yv9l`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
