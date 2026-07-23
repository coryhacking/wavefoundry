# retirement-census-must-cover-every-envelope-surface

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1t8nj-mem retirement-census-must-cover-every-envelope-surface`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-07-22
Updated: 2026-07-22
Source event: `finding:1t9wa:stale-journal-watchpoints-envelope-key`
Validation: promote
Validated by: agent
Action delta: When retiring an artifact class, census every MCP response envelope and docstring for the retired vocabulary, not just the creation path that scaffolds it.
Validation rationale: The generated candidate extracted its targets from the verification commands (run_tests.py, test_server_tools.py) instead of the repaired surface (server_impl.py wf_implement_wave), repeating the known drafter target-extraction weakness. The underlying lesson is real: the 1t9w9 retirement swept wf_create_wave's envelope but missed wf_implement_wave's journal_watchpoints key and docstrings, caught only by operator review.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t9wa retired journals and claimed envelope fields removed, but the census stopped at wf_create_wave's response: wf_implement_wave still returned journal_watchpoints with Journal Watchpoints docstrings until operator review caught it. When retiring an artifact class, census every tool response envelope and registered docstring for the retired vocabulary (code_keyword over the token and its prose form), not just the surface that created the artifact.

## Evidence

- `stale-journal-watchpoints-envelope-key`
- `ev-stale-journal-watchpoints-envelope-key-3`
- `1t9wa`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
