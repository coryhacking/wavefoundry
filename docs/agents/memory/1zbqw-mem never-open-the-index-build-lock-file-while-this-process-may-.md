# Never open the index build lock file while this process may hold it

Owner: Engineering
Status: active
Last verified: 2026-09-29

Memory ID: `1zbqw-mem never-open-the-index-build-lock-file-while-this-process-may-`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `finding:1za2y:DEL-F2`
Validation: promote
Validated by: agent
Action delta: Any in-process code that opens the index build lock file must take runtime_lock.process_hold_guard() and check the process registry first.
Validation rationale: DEL-F2: closing any descriptor of a POSIX record-locked file releases the process's lock, so a monitor-thread reader opening the file between acquire and registration dropped the lock; a stress probe lost it 150/150 without the guard.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

POSIX lockf locks are released when the holder closes any fd of the file, and F_GETLK never reports the caller's own lock. _index_build_lock registers its hold in runtime_lock (survives reload) under process_hold_guard() as part of acquiring; read_index_build_lock_metadata and _index_build_lock_held take the same RLock around check-and-open. A new reader that skips the guard reopens the release race; test with a reader thread racing the acquire and a second-process lockf probe.

Never unlink or replace the carrier either (DEL-F3): a contender that deleted a stale-looking file raced a build that had just locked that inode, and a third process then locked a fresh file alongside it. Stale metadata is rewritten in place by write_metadata after acquire. Tests that inspect the file during a hold must read it from another process.

## Evidence

- `DEL-F2`
- `ev-del-f2-3`
- `DEL-F3`
- `1za2y`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/runtime_lock.py`
