# Dashboard Auto-Index

Change ID: `12gtx-enh dashboard-auto-index`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-10
Wave: `12g47 dashboard-framework`

## Rationale

The dashboard daemon already detects file changes via mtime polling every 3 seconds and maintains an in-memory snapshot. When files change, the search index silently falls behind the working tree — the only way to update it is to run the indexer manually. Operators who keep the dashboard open during active development get stale search results without any indication the index is out of date.

The daemon is the right place to close this gap: it already has the file-change signal, owns the `.wavefoundry/` runtime state boundary, and is scoped to local developer workflows. Adding an opt-in incremental index rebuild here eliminates the manual step without changing the project-visible write contract.

## Requirements

1. The dashboard daemon must support an opt-in `dashboard.auto_index` config flag in `docs/workflow-config.json`; the feature is **disabled by default**.
2. When enabled, the daemon must trigger an **incremental** index rebuild whenever mtime polling detects file changes in watched paths, after a configurable settling delay (default: 30 seconds).
3. Only one index build may run at a time; a new file-change signal during a build must reschedule the rebuild for after the current build completes rather than spawning a second subprocess.
4. Index build status (`idle` | `running` | `done` | `failed`) and timestamps (`build_started_at`, `build_finished_at`) must be tracked in memory by `IndexBuilder` and overlaid onto `health.index.project` in `SnapshotStore._rebuild()` — they must **not** be added to `dashboard_lib._index_stats()` or `collect_health`, since `dashboard_lib` is a pure disk reader with no access to server-layer in-memory state.
5. `SnapshotStore._watched_paths` must include `.wavefoundry/index/index-build-stats.json` so that index updates triggered by **any** process — the daemon's own `IndexBuilder` or an external reindex (manual CLI, MCP tool) — are detected within `_WATCH_INTERVAL` seconds and cause a snapshot rebuild and SSE push.
6. After an index build completes, `IndexBuilder` must call `SnapshotStore._rebuild()` **before** `SnapshotStore._notify_sse()` so that the fresh `index-build-stats.json` data is in the snapshot before the browser is told to fetch.
7. The `IndexCard` in the dashboard UI must reflect live build status: a running indicator while the build is active, and a done/failed badge when complete.
8. The auto-index subprocess must use the same Python interpreter that started the dashboard server and must not inherit the server's open file handles.
9. If the indexer executable cannot be found or returns a non-zero exit code, the daemon must log the failure and set `build_status: failed` without crashing the server or disrupting snapshot delivery.
10. The settling delay must be configurable via `dashboard.auto_index_delay_seconds` in `docs/workflow-config.json` (default: 30, minimum: 10).
11. Tests must cover: the debounce / re-arm logic, single-build-at-a-time gate, status field transitions (idle → running → done/failed), subprocess failure handling, and external-build detection via mtime watch.

## Scope

**Problem statement:** The search index falls behind the working tree silently during active development. Operators running the dashboard must manually trigger reindexing to keep search results accurate.

**In scope:**

- `IndexBuilder` background class in `dashboard_server.py` — debounce timer, subprocess management, in-memory status tracking
- `read_dashboard_config` additions for `auto_index` and `auto_index_delay_seconds`
- `SnapshotStore._watched_paths` — add `.wavefoundry/index/index-build-stats.json` to detect external builds
- `SnapshotStore._rebuild()` — overlay `IndexBuilder.get_status()` onto `health.index.project` after `collect_dashboard_snapshot()` returns; call `_rebuild()` before `_notify_sse()` on build completion
- `IndexCard` UI — running spinner, done/failed state, last-build timestamp
- Test coverage for debounce, single-build gate, status transitions, failure handling, external-build mtime detection

**Out of scope:**

- Full (non-incremental) rebuilds triggered by the daemon
- Remote or multi-user index coordination
- Index rebuild triggered by UI button (a separate enhancement)
- Framework index auto-rebuild (project index only)
- Configuring which files trigger a rebuild beyond the existing watched-path set

## Acceptance Criteria

- [x] AC-1: `dashboard.auto_index: false` by default; no subprocess spawned unless explicitly enabled.
- [x] AC-2: When enabled, incremental rebuilds are triggered by any of three conditions: (a) watched dashboard-file mtime change, (b) startup staleness check — git detects uncommitted changes or commits since `built_at` in `meta.json`, (c) periodic staleness check every `_STALENESS_CHECK_INTERVAL` seconds (default 60s) using the same git-based test. All three arm the debounce timer and wait `auto_index_delay_seconds` (default 30s) before building.
- [x] AC-3: A second file-change signal during a running build does not spawn a second process; it re-arms the trigger for after completion.
- [x] AC-4: `health.index.project.build_status` transitions correctly through `idle → running → done` (or `failed`) and is visible in `/api/dashboard`; the field is injected at the `SnapshotStore` layer, not in `dashboard_lib`.
- [x] AC-5: After a daemon-triggered build completes, `_rebuild()` is called before `_notify_sse()` so the browser fetches a snapshot that already contains the fresh `index-build-stats.json` data.
- [x] AC-6: When an external process (manual reindex, MCP tool) updates `.wavefoundry/index/index-build-stats.json`, the dashboard detects the mtime change within `_WATCH_INTERVAL` seconds, rebuilds the snapshot, and pushes an SSE update.
- [x] AC-7: The `IndexCard` shows a live "Indexing…" indicator while a build is running and a done/failed badge afterward.
- [x] AC-8: Subprocess failure (non-zero exit or missing executable) sets `build_status: failed`, logs to stderr, and does not crash the server.
- [x] AC-9: Tests cover debounce logic, single-build gate, all status transitions, subprocess failure, external-build detection via mtime, startup staleness detection (`_index_is_stale` git logic), and periodic staleness check triggering `signal_change` (and skipping when a build is running).

## Tasks

- [x] Extend `read_dashboard_config` with `auto_index` (bool, default false) and `auto_index_delay_seconds` (int, min 10, default 30)
- [x] Implement `IndexBuilder` class in `dashboard_server.py` — debounce timer, subprocess gate (`Popen` with `start_new_session=True`, `close_fds=True`), in-memory status (`idle`/`running`/`done`/`failed`), timestamps, `get_status() -> dict` accessor
- [x] Add `.wavefoundry/index/index-build-stats.json` to `SnapshotStore._watched_paths` (covers both daemon and external builds)
- [x] In `SnapshotStore._rebuild()`, call `IndexBuilder.get_status()` and merge into `snap["health"]["index"]["project"]` after `collect_dashboard_snapshot()` returns
- [x] In `SnapshotStore`, after daemon build completes: call `_rebuild()` then `_notify_sse()` (not the reverse)
- [x] Wire `IndexBuilder` signal into `SnapshotStore._watch_loop` — trigger on file change when `auto_index` is enabled
- [x] Update `IndexCard` JS component to render build status (spinner for running, pill for done/failed, exit-code snippet for failed)
- [x] Add CSS for running/done/failed index build states
- [x] Write tests: debounce re-arm, single-build gate, idle→running→done, idle→running→failed, external mtime detection triggers snapshot refresh

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Config + schema | implementer | — | Extend `read_dashboard_config` and `_index_stats` |
| `IndexBuilder` class | implementer | Config + schema | Core debounce + subprocess logic |
| `SnapshotStore` integration | implementer | `IndexBuilder` class | Wire trigger and post-build SSE notify |
| UI + CSS | implementer | Config + schema | `IndexCard` status display |
| Tests | implementer | `IndexBuilder` class | Debounce, gate, transitions, failure |

## Serialization Points

- `IndexBuilder` API must be stable before `SnapshotStore` integration and UI work can proceed in parallel.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — new Path 8 for daemon-triggered incremental index rebuild
- `docs/architecture/cross-cutting-concerns.md` — daemon write boundary now includes `.wavefoundry/index/` in addition to `dashboard-server.json`

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Opt-in gate is the safety baseline — must be off by default |
| AC-2 | required | Core feature: file-change → incremental rebuild |
| AC-3 | required | Single-build gate prevents thrashing and race conditions |
| AC-4 | required | Status injection layer correctness — wrong layer causes coupling bug |
| AC-5 | required | Rebuild-before-notify ordering — wrong order causes browser to fetch stale data |
| AC-6 | required | External build detection — the "monitor updates" contract |
| AC-7 | important | UI feedback makes the feature discoverable |
| AC-8 | required | Failure must not crash the server |
| AC-9 | important | Test coverage for the non-trivial async logic |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-09 | Created change doc and admitted to wave 12g47 dashboard-framework. | `docs/waves/12g47 dashboard-framework/wave.md` |
| 2026-05-09 | Reviewed change doc; identified and resolved three gaps: (1) external builds not monitored — added `index-build-stats.json` to `_watched_paths`; (2) SSE notify before rebuild ordering bug — made rebuild-before-notify explicit; (3) wrong injection layer for in-memory build status — moved from `dashboard_lib` to `SnapshotStore._rebuild()`. Added R5, R6, AC-5, AC-6, updated AC-4, corrected tasks and decisions. | This review session |
| 2026-05-09 | Implemented all tasks: `read_dashboard_config` extended with `auto_index`/`auto_index_delay_seconds`; `IndexBuilder` class added to `dashboard_server.py` (debounce timer, single-build gate, `Popen(start_new_session=True, close_fds=True)`, idle/running/done/failed status, `get_status()`, `_pending_after_build` re-arm, `_on_done` callback); `SnapshotStore._watched_paths` includes `index-build-stats.json`; `_rebuild()` overlays `IndexBuilder.get_status()` into `health.index.project`; `_on_index_build_done` calls `_rebuild()` then `_notify_sse()`; `_watch_loop` signals `IndexBuilder` only on non-stats-file changes; `IndexCard` JS updated with running spinner and done/failed badge; CSS added for all three build states (light + dark). Tests: 13 new tests across `IndexBuilderTests` and `IndexBuilderSnapshotIntegrationTests` (debounce, single-build gate, idle→running→done, idle→running→failed, re-arm, missing executable, thread safety, snapshot overlay, external mtime, rebuild-before-notify ordering). Suite: 1075 tests, all passing. | `dashboard_server.py`, `dashboard_lib.py`, `dashboard.js`, `dashboard.css`, `test_dashboard_server.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-09 | Incremental-only rebuilds from the daemon | Full rebuilds can take 7+ minutes on large repos; the daemon should never block or thrash the machine | Allow full rebuilds as a fallback (deferred — adds complexity and risk for v1) |
| 2026-05-09 | Default `auto_index: false` | Unexpected CPU usage from a passive dashboard tool would surprise operators; opt-in keeps first-run safe | Default true (rejected: too aggressive for a local dev tool) |
| 2026-05-09 | 30-second settling delay default | Rapid edits during a coding session should not thrash the indexer; 30s balances freshness with stability | 10s (too aggressive for large file saves), 60s (too long for a responsive dev loop) |
| 2026-05-09 | Build status injected at `SnapshotStore._rebuild()`, not in `dashboard_lib` | `dashboard_lib` is a pure disk reader; injecting in-memory `IndexBuilder` state there would couple the server layer into the library | Pass status via `collect_health` parameter (rejected: leaks server concerns into the library contract) |
| 2026-05-09 | Watch `.wavefoundry/index/index-build-stats.json` to detect external builds | Any process can update the index (manual CLI, MCP tool); watching the stats file means the dashboard stays current regardless of who triggered the build | Watch the whole `.wavefoundry/index/` directory (more permissive but noisier — single file is sufficient and precise) |
| 2026-05-09 | `_rebuild()` called before `_notify_sse()` after build completion | SSE notifies the browser to fetch a new snapshot; if the snapshot hasn't been rebuilt yet the browser gets stale index data | Notify first, then rebuild (rejected: browser fetch races the rebuild and sees the old chunk counts) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Daemon-spawned indexer consumes excessive CPU during active coding | Incremental-only, opt-in, with a 30s debounce settles most rapid-edit storms |
| Subprocess leaks if server is killed mid-build | Use `subprocess.Popen` with `start_new_session=True`; the index write is idempotent so a partial build is safe to abandon |
| Auto-index write conflicts with a manually triggered reindex | Index build is file-level atomic (writes to temp then renames); concurrent builds are safe but wasteful — single-build gate prevents both from running simultaneously |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
