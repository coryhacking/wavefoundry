# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-06

wave-id: `12eas background-index-rebuild`
Title: Background Index Rebuild

## Objective

Add background incremental index rebuild, wave-reopen capability, an operator review gate for wave-close, and wave-index-build-status polling.

## Changes

Change ID: `12eas-enh background-index-rebuild`
Change Status: `done`

Change ID: `12eb0-enh wave-reopen`
Change Status: `done`

Change ID: `12eb2-enh wave-close-operator-review`
Change Status: `done`

Change ID: `12ebh-enh wave-index-build-status`
Change Status: `done`

Completed At: 2026-05-06

## Wave Summary

Makes `wave_index_build` non-blocking: the indexer spawns as a background subprocess, the MCP call returns immediately with pre-build stats and a log path, and a dry-run fast path skips spawning when the index is already up to date. Also converts `kind` in `search_docs`/`search_code` from a post-filter to a pre-filter via a kind index built at load time.

## Journal Watchpoints

- **Watch:** Background log files under `.wavefoundry/` grow unbounded on repos with frequent rebuilds — may need rotation if operators trigger many sequential builds.
- **Watch:** `_index_is_up_to_date` dry-run times out after 30 s; on very large repos this may add latency to every `wave_index_build` incremental call. Monitor if operators report slow responses.
- **Watch:** State file staleness — if the indexer process crashes without cleaning up, the state file PID may refer to a dead process. The 15 s throttle window mitigates duplicate spawns but does not detect crashed builds; a follow-up could check `psutil.pid_exists`.
- **Follow-up:** Consider surfacing log tail in `wave_index_build` response once polling support is available in the MCP layer.

## Review Evidence

- All 12 ACs verified complete in `12eas-enh background-index-rebuild.md`.
- All tasks complete in `12eb0-enh wave-reopen.md` and `12eb2-enh wave-close-operator-review.md`.
- Framework tests pass: 954 tests OK (`python3 .wavefoundry/framework/scripts/run_tests.py`).
- `wave_review` lint passed (2026-05-06).
- code-review: approved — no branch gaps, correct re-entrancy handling, operator signoff check unconditional on both wave_review and wave_close paths, kind pre-filter uses set intersection before cosine, cache invalidation only on spawn.
- architecture-review: approved — no new module boundaries; wave_reopen and operator lane check are surface additions consistent with existing patterns; kind index follows existing tag index pattern; no on-disk format changes.
- performance-review: approved — kind pre-filter strictly faster than post-filter; background rebuild adds at most 30s dry-run latency on incremental; no hot-path regressions.
- code-review (12ebh): approved — `wave_index_build_status_response` is read-only; PID liveness check reuses `_pid_is_running`; log parser is defensive with fallback to last line; all branches (running/finished/idle/invalid) handled.
- architecture-review (12ebh): approved — read-only query tool, no new state or storage; reuses existing `_index_build_state_path`/`_index_build_log_path` helpers; consistent with existing tool surface pattern.
- performance-review (12ebh): approved — reads two small files (state JSON + log tail); no embedding, no subprocess, no writes; negligible overhead.
- operator-signoff: approved — tested in external project (2026-05-06), confirmed working.

## Dependencies

- No external wave dependencies.
