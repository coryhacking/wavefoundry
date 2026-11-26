# memory_backfill.py fragile seams

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24b9i-mem memory-backfill-py-fragile-seams`
Kind: `fragile_file`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 3641306
Supersedes: `1u25a-mem fragile-memory-backfill-py`
Checked at: 2026-11-26T06:32:44Z
Check note: Memory backfill uses persistent source IDs and records prior dispositions. Renames need tests for identity and replay. Reviewed .wavefoundry/framework/scripts/memory_backfill.py:116.
Check flags: none

## Summary

When editing .wavefoundry/framework/scripts/memory_backfill.py, check the two seams that broke in wave 1tz6l: renamed backfill source ids must resolve to their on-disk lifecycle ids, and a resumed docs gate must leave a checkpoint the memory phases accept (finding memory-id-rename-and-gate-resume-deadlock); and graph maintenance must not change the build attempt that the upgrade staging receipt validates (finding graph-maintenance-invalidates-upgrade-staging-receipt). Run tests/test_memory_backfill.py and tests/test_archive_memory_backfill.py plus an interrupted-rename resume, not only the happy path.

## Evidence

- `1tz6l`
- `memory-id-rename-and-gate-resume-deadlock`
- `graph-maintenance-invalidates-upgrade-staging-receipt`
- `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`

## Targets

- `.wavefoundry/framework/scripts/memory_backfill.py`
