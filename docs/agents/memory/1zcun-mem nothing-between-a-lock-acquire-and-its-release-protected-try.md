# Nothing between a lock acquire and its release-protected try

Owner: Engineering
Status: active
Last verified: 2026-09-30

Memory ID: `1zcun-mem nothing-between-a-lock-acquire-and-its-release-protected-try`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 335885
Source event: `finding:1zf1u:DEL-1ZF1U-ACQUIRE-METADATA`
Validation: promote
Validated by: agent
Action delta: When editing a lock context manager, keep every statement after a successful acquire (including building metadata) inside the try whose finally releases; verify with a spy on release plus an independent-process probe, not an in-process re-acquire.
Validation rationale: Verified against DEL-1ZF1U-ACQUIRE-METADATA and current lifecycle_lock.lifecycle_mutation_lock: the wave moved metadata construction between _acquire and the try, an interrupt there left the OS lock held; the draft targeted the reviewer's scratch probe.py and said nothing actionable. The in-process free probe was shown vacuous earlier in the same wave (POSIX lockf is per-process).
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

In lifecycle_lock.lifecycle_mutation_lock, wave 1zf1u moved the acquisition-metadata dict construction (os.getpid(), time.time()) to just after _acquire and before the try whose finally calls lock.release(); an interrupt there left the OS lock held, and a second process saw it busy while the traceback was retained. Fix: initialise metadata empty before the try and build it inside. Test it with a spy on RuntimeFileLock.release (an in-process re-acquire proves nothing: POSIX lockf locks are per-process) and confirm with an independent-process probe.

## Evidence

- `DEL-1ZF1U-ACQUIRE-METADATA`
- `1zf1u`

## Targets

- `lifecycle_lock.py`
- `runtime_lock.py`
- `tests/test_lifecycle_mutation_lock.py`
