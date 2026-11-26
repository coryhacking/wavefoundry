# Server-tools test playbook

Owner: Engineering
Status: archived
Last verified: 2026-08-02

Memory ID: `1u8q2-mem server-tools-test-playbook`
Superseded by: `249w5-mem server-tools-test-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-02
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 249w5-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1u8q2-mem server-tools-test-playbook.md`

## Summary

For changes covered by test_server_tools.py, prove lifecycle and reload regressions can fail: assert exact state, spy each mutating seam, mutate the claimed branch to test polarity, and exercise the server close-to-restore window when reload behavior changes. Counters, unset fixture flags, and happy-path-only assertions are not evidence of no mutation.

## Evidence

- `1tlbt-mem`
- `1tubb-mem`
- `1u498-mem`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/server.py`
