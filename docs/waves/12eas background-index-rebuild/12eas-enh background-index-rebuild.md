# Background Index Rebuild

Change ID: `12eas-enh background-index-rebuild`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-06
Wave: `12eas background-index-rebuild`

## Rationale

`wave_index_build` previously ran the indexer synchronously inside the MCP server process, blocking the entire MCP connection for several minutes during a full rebuild. The operator received no feedback until the build completed, and script stdout was swallowed entirely — making it impossible to show the operator what was being indexed or how long it would take. This change makes `wave_index_build` return immediately with pre-build statistics, spawns the indexer as a detached background process writing to a log file, and adds an up-to-date fast-path that skips spawning entirely when no files have changed.

## Requirements

1. `wave_index_build` must return to the caller immediately — it must not block waiting for the indexer to finish.
2. The response must include a human-readable `notice` field stating which index is being built, how many source files are involved, and where to watch progress.
3. Pre-build statistics (files_total, doc_chunks, code_chunks) must be captured before the background process starts and included in the response.
4. The indexer process must write stdout and stderr to a persistent log file (`index-build.log` in the index directory) so operators and agents can tail progress.
5. If a build is already running for the requested layer, `wave_index_build` must return an `already_running` response without spawning a second process.
6. For incremental updates (`mode='update'`), if the index is already current (no file changes detected), the tool must return an `up_to_date` response without spawning any process.
7. The `indexer.py` CLI must gain a `--dry-run` flag that performs the full staleness check (hash comparison) but exits before embedding or writing — used to implement requirement 6 efficiently.
8. The indexer's start-of-rebuild banner must always print to stdout (not gated on `--verbose`) and must include: index name, file count, and a "may take several minutes" advisory.
9. Cache invalidation must only occur when a process is actually spawned — not for up-to-date or already-running short-circuits.
10. All existing tests must pass; new tests must cover the background spawn path, up-to-date fast path, already-running guard, and cache invalidation behaviour.

## Scope

**Problem statement:** `wave_index_build` was synchronous and silent — it blocked the MCP connection for minutes and gave the operator no information about what was happening.

**In scope:**

- `server.py`: `run_index_rebuild` rewritten to spawn via `Popen`; new helpers `_index_build_state_path`, `_index_build_log_path`, `_index_build_active`, `_index_is_up_to_date`; `wave_index_build_response` updated for async result shape and conditional cache invalidation
- `indexer.py`: `--dry-run` CLI flag and `dry_run` parameter on `build_index` / `_build_index_locked`; start-of-rebuild banner unconditionally printed
- Dead code removal: `_extract_rebuild_runtime_stats` removed (parsed stdout that is no longer read)
- `test_server_tools.py`: `RunIndexRebuildTests` and `WaveIndexBuildResponseTests` updated throughout

**Out of scope:**

- A poll/status MCP tool for checking whether the background build has completed
- Streaming log output to the MCP client
- Background rebuild for `content=all` / `setup_index.py` (spawns the same way, log file captures output)

## Acceptance Criteria

- AC-1: `wave_index_build` returns a response dict immediately after spawning the background process; it does not block on process completion.
- AC-2: Response includes `notice` string naming the index, file count (for full rebuilds), and log path.
- AC-3: Response includes `stats` with pre-build `files_total`, `doc_chunks`, `code_chunks` from the index directory.
- AC-4: Indexer stdout/stderr is written to `.wavefoundry/index/index-build.log` (project layer) or `.wavefoundry/framework/index/index-build.log` (framework layer).
- AC-5: A state file (`index-build.json`) is written with `pid`, `started_at`, `content`, `layer`, `full`.
- AC-6: Calling `wave_index_build` while a build is already active returns `already_running: true` without spawning a second process.
- AC-7: Calling `wave_index_build(mode='update')` when the index is current returns `up_to_date: true` without spawning any process.
- AC-8: `--dry-run` flag on `indexer.py` performs hash staleness check and exits before embedding; prints `"build_index: index is up to date"` when current or `"build_index: dry-run — rebuild needed"` when stale.
- AC-9: The start-of-rebuild banner prints unconditionally (not gated on `--verbose`) and includes file count and timing advisory.
- AC-10: Cache is invalidated only when a process is spawned (`already_running=False`, `up_to_date=False`).
- AC-11: `full=True` bypasses the up-to-date check and always spawns.
- AC-12: All 944 tests pass.

## Tasks

- [x] Add `--dry-run` to `indexer.py` CLI and `build_index` / `_build_index_locked`
- [x] Make start-of-rebuild banner unconditional in `indexer.py`
- [x] Add `_index_build_state_path`, `_index_build_log_path`, `_index_build_active` helpers to `server.py`
- [x] Add `_index_is_up_to_date` helper (spawns `--dry-run` subprocess with 30s timeout)
- [x] Rewrite `run_index_rebuild` to use `Popen` (detached, log file, state file)
- [x] Add up-to-date fast-path before Popen in `run_index_rebuild`
- [x] Update `wave_index_build_response` for new result shape and conditional cache invalidation
- [x] Remove dead `_extract_rebuild_runtime_stats`
- [x] Update all affected tests; add tests for background spawn, up-to-date, already-running, cache invalidation

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| indexer dry-run flag | code | — | prerequisite for up-to-date check |
| server rebuild rewrite | code | indexer dry-run | Popen + state file + log |
| tests | code | server rebuild rewrite | all in one pass |

## Serialization Points

- `server.py` and `indexer.py` must be updated atomically — `_index_is_up_to_date` calls `--dry-run` which must exist before server changes land.

## Affected Architecture Docs

N/A — confined to the indexer and MCP server layer; no module boundaries, data flow, or domain ownership changed.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core goal — non-blocking MCP |
| AC-2 | required | Operator visibility |
| AC-3 | required | Pre-build stats in response |
| AC-4 | required | Log file for progress monitoring |
| AC-5 | required | State file for already-running guard |
| AC-6 | required | Prevent duplicate builds |
| AC-7 | required | Fast path — avoid unnecessary spawns |
| AC-8 | required | Foundation for AC-7 |
| AC-9 | required | Operator visibility in CLI use |
| AC-10 | important | Correctness — stale cache signals |
| AC-11 | required | Full rebuild must always proceed |
| AC-12 | required | No regressions |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-06 | Implemented all tasks; 944 tests pass | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-06 | Use `Popen` + log file rather than streaming stdout to MCP | MCP protocol has no push/streaming primitive; log file is observable by operator and agent via file tail | Synchronous subprocess.run (blocks MCP); streaming via repeated poll tool calls (adds complexity) |
| 2026-05-06 | `--dry-run` in indexer rather than reimplementing hash check in server | Single source of truth for staleness logic; avoids duplicating walk + hash comparison | Duplicate logic in server.py (maintenance burden) |
| 2026-05-06 | Cache invalidation only on actual spawn | Invalidating on up-to-date is harmless but noisy; already-running means cache state is unchanged | Invalidate always (previous behaviour) |

## Risks

| Risk | Mitigation |
|---|---|
| `--dry-run` subprocess has 30s timeout; very large repos may exceed it | Returns `False` (assumes stale) on timeout — safe fallback, spawns a real build |
| Log file truncated on each new build | Intentional — each `wave_index_build` call gets a fresh log; old builds are not retained |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
