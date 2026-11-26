# Fragile: test_server_tools.py

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1v1ux-mem fragile-test-server-tools-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-11
Updated: 2026-11-25
Source exploration cost: 1869289
Source event: `repeated-repairs:1v08w:test_server_tools.py`
Validation: promote
Validated by: agent
Action delta: Treat future edits to the code_ask definition-first regression owners in test_server_tools.py as fragile: run their focused suite and use explicit public-contract assertions.
Validation rationale: Four independently reviewed findings in one wave repaired collision identity, inclusive citation range, declaration authority, and fallback response-shape coverage in this shared test owner. Current tests and the final mutation controls confirm the file's contract density.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-25T16:09:21Z
Check note: Item 7 review: target gone or duplicate. The four 1v08w repairs were to code_ask, code-summary and graph-range fixtures. Those tests have left .wavefoundry/framework/scripts/tests/test_server_tools.py: grep finds 0 'code_ask' and 0 '1v08w' there, and the file was split into test_server_tools_retrieval.py and test_server_tools_lifecycle.py. The only action left, 're-verify with the full suite', is.
Check flags: target_churn, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, gone or carried by The four 1v08w repairs were to code_ask, code-summary and graph-range fixtures. Those tests have left .wavefoundry/framework/scripts/tests/test_server_tools.py: grep finds 0 'code_ask' and 0 '1v08w' there, and the file was split into test_serve.
Archive path: `docs/agents/memory/archive/1v1ux-mem fragile-test-server-tools-py.md`

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
