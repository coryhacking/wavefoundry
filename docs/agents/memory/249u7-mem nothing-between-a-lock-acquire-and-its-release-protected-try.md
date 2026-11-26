# Nothing between a lock acquire and its release-protected try

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249u7-mem nothing-between-a-lock-acquire-and-its-release-protected-try`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 335885
Supersedes: `1zcun-mem nothing-between-a-lock-acquire-and-its-release-protected-try`
Checked at: 2026-11-26T06:32:43Z
Check note: The interrupt-on-acquire test shows why even metadata construction belongs inside cleanup coverage after lock acquisition. Reviewed .wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py:422.
Check flags: none

## Summary

When editing a lock context manager such as lifecycle_mutation_lock in .wavefoundry/framework/scripts/lifecycle_lock.py, keep every statement after a successful acquire, including building metadata, inside the try whose finally releases. Verify with a spy on RuntimeFileLock.release plus an independent-process probe, not an in-process re-acquire. Why: wave 1zf1u moved the metadata dict construction between _acquire and the try, so an interrupt left the OS lock held (DEL-1ZF1U-ACQUIRE-METADATA); POSIX lockf locks are per-process, so an in-process re-acquire proves nothing. tests/test_lifecycle_mutation_lock.py test_an_interrupt_while_building_the_acquire_metadata_still_releases pins that instance.

## Evidence

- `DEL-1ZF1U-ACQUIRE-METADATA`
- `1zf1u`
- `test_lifecycle_mutation_lock.test_an_interrupt_while_building_the_acquire_metadata_still_releases`

## Targets

- `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/runtime_lock.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`
