# Server-tools test playbook

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249w5-mem server-tools-test-playbook`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1u8q2-mem server-tools-test-playbook`
Checked at: 2026-11-26T06:32:43Z
Check note: Lifecycle and reload suites span multiple modules. A green unit test alone does not establish the claimed public failure behavior. Reviewed .wavefoundry/framework/scripts/tests/test_server_tools.py:7.
Check flags: none

## Summary

When writing or changing tests in .wavefoundry/framework/scripts/tests/test_server_tools.py for lifecycle or reload behavior, prove the regression can fail: assert exact state, spy each mutating seam, mutate the claimed branch to check polarity, and exercise the server close-to-restore window when reload behavior changes. Counters, unset fixture flags and happy-path-only assertions passed while the defect was present in the consolidated source records, so they are not evidence that nothing mutated.

## Evidence

- `1tlbt-mem no-mutation-regressions-assert-exact-state-and-spy-the-seam-`
- `1tubb-mem`
- `1u498-mem`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/server.py`
