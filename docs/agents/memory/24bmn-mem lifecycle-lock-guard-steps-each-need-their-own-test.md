# Lifecycle lock guard steps each need their own test

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bmn-mem lifecycle-lock-guard-steps-each-need-their-own-test`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 244563
Supersedes: `1zkyn-mem lifecycle-lock-guard-steps-each-need-their-own-test`

## Summary

When changing the hold, re-entry or probe logic in .wavefoundry/framework/scripts/lifecycle_lock.py, keep one failing-on-removal test per guard step in tests/test_lifecycle_mutation_lock.py LifecycleHoldGuardOrderingTests and mutate each step to confirm its test fails. Why: wave 1zimc found the in-guard re-entry re-check, the same-thread check in the publication refusal, registration atomic with acquire under the guard, and the probe's open under the guard each had no test that failed when removed (DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS); reviewer mutations M8-M11 confirmed the new pins.

## Evidence

- `DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS`
- `1zimc`
- `test_lifecycle_mutation_lock.LifecycleHoldGuardOrderingTests`

## Targets

- `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`
