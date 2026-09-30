# Repaired defect DEL-1ZF1U-ACQUIRE-METADATA

Owner: Engineering
Status: superseded
Last verified: 2026-09-30

Memory ID: `1zeg1-mem repaired-defect-del-1zf1u-acquire-metadata`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 335885
Source event: `finding:1zf1u:DEL-1ZF1U-ACQUIRE-METADATA`
Validation: rewrite
Validated by: agent
Action delta: When editing a lock context manager, keep every statement after a successful acquire (including building metadata) inside the try whose finally releases; verify with a spy on release plus an independent-process probe, not an in-process re-acquire.
Validation rationale: Verified against DEL-1ZF1U-ACQUIRE-METADATA and current lifecycle_lock.lifecycle_mutation_lock: the wave moved metadata construction between _acquire and the try, an interrupt there left the OS lock held; the draft targeted the reviewer's scratch probe.py and said nothing actionable. The in-process free probe was shown vacuous earlier in the same wave (POSIX lockf is per-process).
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zcun-mem nothing-between-a-lock-acquire-and-its-release-protected-try`

## Summary

Real defect fixed in wave 1zf1u: Repair verified by test, mutant and cross-process probe.

## Evidence

- `DEL-1ZF1U-ACQUIRE-METADATA`
- `ev-del-1zf1u-acquire-metadata-3`
- `1zf1u`

## Targets

- `probe.py`
