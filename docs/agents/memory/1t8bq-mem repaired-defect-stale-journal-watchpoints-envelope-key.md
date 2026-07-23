# Repaired defect stale-journal-watchpoints-envelope-key

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1t8bq-mem repaired-defect-stale-journal-watchpoints-envelope-key`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 104004
Source event: `finding:1t9wa:stale-journal-watchpoints-envelope-key`
Validation: rewrite
Validated by: agent
Action delta: When retiring an artifact class, census every MCP response envelope and docstring for the retired vocabulary, not just the creation path that scaffolds it.
Validation rationale: The generated candidate extracted its targets from the verification commands (run_tests.py, test_server_tools.py) instead of the repaired surface (server_impl.py wf_implement_wave), repeating the known drafter target-extraction weakness. The underlying lesson is real: the 1t9w9 retirement swept wf_create_wave's envelope but missed wf_implement_wave's journal_watchpoints key and docstrings, caught only by operator review.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1t8nj-mem retirement-census-must-cover-every-envelope-surface`
## Summary

Real defect fixed in wave 1t9wa: Repair verified terminal: executed suite evidence plus a by-construction failing regression against the pre-repair behavior.

## Evidence

- `stale-journal-watchpoints-envelope-key`
- `ev-stale-journal-watchpoints-envelope-key-3`
- `1t9wa`

## Targets

- `run_tests.py`
- `test_server_tools.py`
