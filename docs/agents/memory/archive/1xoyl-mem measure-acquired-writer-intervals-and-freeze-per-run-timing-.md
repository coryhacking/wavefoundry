# Measure acquired writer intervals and freeze per-run timing evidence

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-`
Superseded by: `24aqd-mem time-a-sqlite-publication-from-begin-immediate-return-to-com`
Kind: `failed_attempt`
Confidence: 0.97
Created: 2026-09-11
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 24aqd-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-.md`

## Summary

For SQLite publication timing, start after BEGIN IMMEDIATE returns successfully and stop after COMMIT returns; report acquisition wait separately. A pre-execution trace callback includes wait and misses commit duration. Copy each run's timing records before clearing shared buffers. Validate with blocked acquisition and a delayed-commit control, not only no-contention runs.

## Evidence

- `1xny6`
- `PERF-CURRENT-1`
- `ev-perf-current-1-3`
- `test_publication_timer_excludes_acquisition_and_includes_commit`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
