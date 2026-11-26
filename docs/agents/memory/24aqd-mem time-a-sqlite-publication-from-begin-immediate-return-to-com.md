# Time a SQLite publication from BEGIN IMMEDIATE return to COMMIT return

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aqd-mem time-a-sqlite-publication-from-begin-immediate-return-to-com`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-`

## Summary

When you add or change timing for a SQLite write publication (for example publication_held_ms in indexer._build_index_locked), start the clock after BEGIN IMMEDIATE returns and stop it after COMMIT returns, and report the lock-acquisition wait as a separate figure. A pre-execution trace callback includes the wait and misses the commit duration. Copy each run's timing records before shared buffers are cleared, and validate with a blocked-acquisition control and a delayed-commit control, not only with runs that have no contention. Wave 1xny6 (PERF-CURRENT-1) pins the indexer instance in test_publication_timer_excludes_acquisition_and_includes_commit, which adds 0.3 s after BEGIN and 0.1 s before COMMIT and expects 100 ms.

## Evidence

- `1xny6`
- `PERF-CURRENT-1`
- `ev-perf-current-1-3`
- `test_indexer.test_publication_timer_excludes_acquisition_and_includes_commit`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
