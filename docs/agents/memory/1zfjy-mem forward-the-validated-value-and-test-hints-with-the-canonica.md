# Forward the validated value, and test hints with the canonical hidden

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zfjy-mem forward-the-validated-value-and-test-hints-with-the-canonica`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 108574
Source event: `repeated-repairs:1zim3:tests/test_extension_tool_modules.py`
Validation: promote
Validated by: agent
Action delta: When a declaration validates a value, forward the validated value (strict) rather than the declared one, and test the hint rewrite with the canonical name hidden.
Validation rationale: The two repairs were in production code (lax pin forwarded raw; hints naming a hidden canonical), not test fragility; the durable lesson is about the validate-then-forward pattern and the hidden-name case.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1zim3 delivery: an extension pin was checked with a lax TypeAdapter and the raw declared value forwarded, so with_line_numbers='false' ran as true; fixed by strict validation and forwarding the validated value. Separately, excluding mapped canonical names from the whole-name hint rewrite left hints naming a hidden canonical tool; any served-name feature needs a test with the canonical name hidden.

## Evidence

- `DEL-1ZIM3-FIXED-VALUE-UNVALIDATED`
- `DEL-1ZIM3-HIDDEN-NAME-HINTS`
- `1zim3`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
