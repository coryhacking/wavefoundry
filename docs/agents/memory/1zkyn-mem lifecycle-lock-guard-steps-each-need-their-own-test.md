# Lifecycle lock guard steps each need their own test

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zkyn-mem lifecycle-lock-guard-steps-each-need-their-own-test`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 244563
Source event: `finding:1zimc:DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS`
Validation: promote
Validated by: agent
Action delta: When changing lifecycle_lock hold or re-entry logic, keep each guard step pinned by its own LifecycleHoldGuardOrderingTests case and mutate it to confirm the test fails.
Validation rationale: The finding (four lock guard mechanisms with no test that fails when removed) was repaired with LifecycleHoldGuardOrderingTests, verified by reviewer mutations M8-M11. The generated summary carries no actionable content, so it is rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1zimc: the lifecycle lock's in-guard re-entry re-check, the same-thread check in the publication refusal, registration atomic with acquire under the guard, and the probe's open under the guard each had no test that failed when removed. LifecycleHoldGuardOrderingTests now pins each one; reviewer mutations M8-M11 confirm it. Any change to these steps must keep a failing-on-removal test per step.

## Evidence

- `DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS`
- `1zimc`

## Targets

- `lifecycle_lock.py`
- `review_evidence.py`
- `tests/test_lifecycle_mutation_lock.py`
