# Fragile: tests/test_extension_tool_modules.py

Owner: Engineering
Status: superseded
Last verified: 2026-10-01

Memory ID: `1zfwg-mem fragile-tests-test-extension-tool-modules-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 108574
Source event: `repeated-repairs:1zim3:tests/test_extension_tool_modules.py`
Validation: rewrite
Validated by: agent
Action delta: When a declaration validates a value, forward the validated value (strict) rather than the declared one, and test the hint rewrite with the canonical name hidden.
Validation rationale: The two repairs were in production code (lax pin forwarded raw; hints naming a hidden canonical), not test fragility; the durable lesson is about the validate-then-forward pattern and the hidden-name case.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zfjy-mem forward-the-validated-value-and-test-hints-with-the-canonica`

## Summary

tests/test_extension_tool_modules.py required 2 separate repairs during wave 1zim3; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-1ZIM3-FIXED-VALUE-UNVALIDATED`
- `DEL-1ZIM3-UNPINNED-GUARDS`
- `1zim3`

## Targets

- `tests/test_extension_tool_modules.py`
