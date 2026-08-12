# Fragile: test_server_tools.py

Owner: Engineering
Status: active
Last verified: 2026-08-11

Memory ID: `1v1ux-mem fragile-test-server-tools-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-11
Updated: 2026-08-11
Source exploration cost: 1869289
Source event: `repeated-repairs:1v08w:test_server_tools.py`
Validation: promote
Validated by: agent
Action delta: Treat future edits to the code_ask definition-first regression owners in test_server_tools.py as fragile: run their focused suite and use explicit public-contract assertions.
Validation rationale: Four independently reviewed findings in one wave repaired collision identity, inclusive citation range, declaration authority, and fallback response-shape coverage in this shared test owner. Current tests and the final mutation controls confirm the file's contract density.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

test_server_tools.py required 4 separate repairs during wave 1v08w; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `1v08w-code-summary-collision`
- `1v08w-graph-range-off-by-one`
- `1v08w-graph-declaration-authority-unproven`
- `1v08w-fallback-response-shape-self-reference`
- `1v08w`

## Targets

- `test_server_tools.py`
