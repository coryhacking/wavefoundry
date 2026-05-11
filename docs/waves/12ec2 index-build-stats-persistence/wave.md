# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-06

wave-id: `12ec2 index-build-stats-persistence`
Title: Index Build Stats Persistence

## Objective

Persist index build stats (elapsed time, file and chunk counts) to `index-build-stats.json` after each completed build, and surface timing estimates in `wave_index_build` notices and `wave_index_build_status` responses.

## Changes

Change ID: `12ec1-enh index-build-stats-persistence`
Change Status: `done`

Completed At: 2026-05-06

## Wave Summary

Persists index build stats (elapsed time, file/chunk counts) to `index-build-stats.json` after each completed build, and surfaces timing estimates in `wave_index_build` notices and `wave_index_build_status` responses.

## Journal Watchpoints

- **Watchpoint:** Stats are only written when the log contains the `"done —"` completion marker — a crashed build will not corrupt the stats file.
- **Watchpoint:** Stats reflect the most recent completed build only; if build scope changes significantly (e.g., repo doubles in size), the estimate will be stale until the next build completes.

## Review Evidence

- operator-signoff: approved

## Dependencies

- No external wave dependencies.
