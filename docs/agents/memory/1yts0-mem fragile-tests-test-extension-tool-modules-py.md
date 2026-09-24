# Fragile: tests/test_extension_tool_modules.py

Owner: Engineering
Status: superseded
Last verified: 2026-09-24

Memory ID: `1yts0-mem fragile-tests-test-extension-tool-modules-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-24
Updated: 2026-09-24
Source exploration cost: 274985
Source event: `repeated-repairs:1yv9l:tests/test_extension_tool_modules.py`
Validation: rewrite
Validated by: agent
Action delta: When a check claims callers of a replaced MCP tool keep working, compare each replaced parameter's normalized value schema (types, enums, items, nested defs), not only parameter names and required-ness, and pair every refusal fixture with a positive control for what must stay allowed (defaults, titles, added optional parameters).
Validation rationale: Wave 1yv9l: two repair cycles touched the extension test file, but the file itself is not fragile; the recurring defect was a compatibility check narrower than its stated promise. The first delivery pass accepted a names-and-required-only check; an independent review showed an override changing slug str to int registered and broke normal wf_create_wave calls. Repair 2 added value-schema equality with annotations ignored; QA found a title-significant mutant survived until an added-optional-parameter plus custom-title positive control was added.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1yv64-mem call-compatibility-checks-must-compare-value-schemas-with-po`

## Summary

tests/test_extension_tool_modules.py required 2 separate repairs during wave 1yv9l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-CALL-PATH-TESTS`
- `DEL-OVERRIDE-VALUE-COMPATIBILITY`
- `1yv9l`

## Targets

- `tests/test_extension_tool_modules.py`
