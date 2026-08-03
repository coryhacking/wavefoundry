# No-mutation regressions: assert exact state and spy the seam, not counters

Owner: Engineering
Status: archived
Last verified: 2026-07-25

Memory ID: `1tlbt-mem no-mutation-regressions-assert-exact-state-and-spy-the-seam-`
Superseded by: `1u8q2-mem server-tools-test-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-25
Updated: 2026-08-02
Source exploration cost: 1048595
Source event: `repeated-repairs:1ti11:.wavefoundry/framework/scripts/tests/test_server_tools.py`
Validation: promote
Validated by: agent
Action delta: When writing a "nothing was mutated" regression, assert the EXACT state value and spy the mutating seam; per-stage counters and stored-flag comparisons both pass against real mutations and prove nothing.
Validation rationale: The generated draft says only that test_server_tools.py "required 2 separate repairs", which does not change any future action for a 23k-line test file that nearly every wave touches. The durable lesson is in HOW the regressions were weak, and it generalizes well past this file. The `invalid-purpose-test-misses-focus-and-seal` finding proved the shipped test passed against an injected mutation because it compared only `review`/`implement` per-stage call counters, which cannot observe a focus move to a third stage such as `plan`. While repairing it I found a second-order vacuity of the same shape: comparing the stored `sealed` flag is null-versus-null whenever the fixture has no `wave_state` row, so an injected `unseal_wave` call would also have passed; that is why the repair spies the seam rather than only reading state. I verified both against the current tree, where the test now asserts the exact frozen `Focus` value and wraps `unseal_wave` in a call spy. This supplements the existing "prove a regression can fail before trusting it" guidance by naming the two specific shapes that silently pass.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tlbt-mem no-mutation-regressions-assert-exact-state-and-spy-the-seam-.md`
## Summary

Two "nothing was mutated" assertion shapes in test_server_tools.py silently passed against real mutations in wave 1ti11. Comparing per-stage call counters (`review`/`implement`) cannot see a mutation into any other stage, so an injected move to `plan` passed. Comparing a stored flag is vacuous whenever the fixture never created the row, so a `sealed` read returned None both before and after and an injected `unseal_wave` call also passed. The repair asserts the exact frozen `Focus` value and wraps the mutating function in a call spy. Rule: assert the exact state, and observe the CALL at the seam when the stored state may be absent. Then prove it by injecting the mutation and requiring the test to fail.

## Evidence

- `invalid-purpose-test-misses-focus-and-seal`
- `reopen-failure-envelope-undocumented-and-unpinned`
- `1ti11`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
