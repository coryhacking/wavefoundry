# Measure acquired writer intervals and freeze per-run timing evidence

Owner: Engineering
Status: active
Last verified: 2026-09-11

Memory ID: `1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-`
Kind: `failed_attempt`
Confidence: 0.97
Created: 2026-09-11
Updated: 2026-09-11
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
