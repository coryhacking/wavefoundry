# Repaired defect DEL-F2

Owner: Engineering
Status: superseded
Last verified: 2026-09-29

Memory ID: `1zbjr-mem repaired-defect-del-f2-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `finding:1za2y:DEL-F2`
Validation: rewrite
Validated by: agent
Action delta: Any in-process code that opens the index build lock file must take runtime_lock.process_hold_guard() and check the process registry first.
Validation rationale: DEL-F2: closing any descriptor of a POSIX record-locked file releases the process's lock, so a monitor-thread reader opening the file between acquire and registration dropped the lock; a stress probe lost it 150/150 without the guard.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zbqw-mem never-open-the-index-build-lock-file-while-this-process-may-`

## Summary

Real defect fixed in wave 1za2y: Resolved.

## Evidence

- `DEL-F2`
- `ev-del-f2-3`
- `1za2y`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
