# Index Build Lock Hygiene and Auto-Rebuild Coordination

Change ID: `1p2w5-bug index-build-lock-and-autorebuild-coordination`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Teton field session on the v22 → v23 upgrade hit a recurring "Phase 4b code-index lock conflict" pattern. Investigation surfaced three related framework defects in the index-build / auto-rebuild path:

1. **`wave_index_build` returns misleading success when the spawned subprocess fails to acquire the lock.** The MCP tool fires `subprocess.Popen` and returns `{"passed": True, "already_running": False, "graph_rebuilt": True, "pid": <new_pid>}` immediately. The subprocess can die in its first few hundred milliseconds with "lock file busy" written to the log, and the caller has already received a success response. Downstream `wave_graph_report` calls still surface `graph_auto_rebuild_failed` because the rebuild never actually ran. Teton's exact words: *"the new diagnostic correctly identifies the problem AND points at the recovery tool, but the recovery tool silently lies about completing the work."*

2. **`_index_build_lock` does not auto-unlink lock-file metadata that records a dead PID.** `classify_index_build_lock_owner` already detects the stale state and returns `"stale"`, but the diagnostic in `format_index_build_lock_conflict` tells the user to manually `rm` the lock file. On most paths this is harmless (the OS releases `flock()` on process death so a fresh acquire succeeds), but the persistent stale metadata causes downstream tools that read the lock file to surface the dead PID in user-facing messages, adding confusion.

3. **`_ensure_graph_builder_current` (graph_query.py) lacks coordination across concurrent auto-rebuild attempts.** Every `load_graph` call independently checks the on-disk `builder_version` against the runtime constant and, on mismatch, calls `indexer_mod.build_index(...)` synchronously in-process. When several MCP tools fire concurrently after a `GRAPH_BUILDER_VERSION` bump, each tool's auto-rebuild triggers its own `build_index` call. The first wins the flock; the others raise `IndexBuildAlreadyRunning`, get caught by the broad `except Exception`, and emit a `graph_auto_rebuild_failed` diagnostic — even though a rebuild is already running successfully in a concurrent thread/call.

The user-visible failure mode is a noisy stream of `graph_auto_rebuild_failed` diagnostics during the auto-rebuild window after a builder-version bump. The MCP server is technically working correctly (one rebuild succeeds; subsequent tool calls eventually see the new graph), but the diagnostics noise and the misleading `wave_index_build` success make recovery harder than it should be.

## Requirements

1. `wave_index_build_response` must verify that the spawned indexer subprocess actually acquired the lock before returning `passed: true`. When the subprocess exits within a brief verification window with a lock-busy error, the response must return `passed: false`, set `graph_rebuilt: false`, and emit a `build_skipped_lock_busy` diagnostic carrying the lock-holder PID.
2. `_index_build_lock` must proactively unlink a lock file whose metadata records a dead PID before attempting to acquire `flock()`. This keeps the lock-file metadata consistent with the actual lock state and makes the diagnostic surface self-healing.
3. `_ensure_graph_builder_current` must coordinate concurrent auto-rebuild attempts within a single MCP server process. When a rebuild is already in-flight for the same `(root, layer)` cache key, the duplicate attempt must defer and return a `graph_auto_rebuild_in_progress` diagnostic instead of racing for the flock.
4. The coordination must include a stale-inflight safety net (≥120s) so a crashed rebuild does not permanently block future auto-rebuild attempts.
5. No existing successful behavior may regress: clean builds, idempotent acquire, completed-classification semantics, and the existing on-disk lock format must all be preserved.

## Scope

**Problem statement:** Index build lock hygiene and auto-rebuild coordination defects cause misleading success responses and noisy duplicate-rebuild diagnostics in the auto-rebuild window after a `GRAPH_BUILDER_VERSION` bump.

**In scope:**

- `wave_index_build` post-Popen synchronous lock-acquisition verification (Bug 2)
- `_index_build_lock` stale-metadata auto-unlink (Bug 1)
- `_ensure_graph_builder_current` in-process coordination of concurrent auto-rebuild attempts (Bug 3)
- New `build_skipped_lock_busy` and `graph_auto_rebuild_in_progress` diagnostic codes
- Regression tests covering each of the three behaviors

**Out of scope:**

- Cross-process auto-rebuild coordination (multiple MCP server processes on the same repo). The lock file is already the authoritative cross-process gate; deferring to it from a single process is sufficient for the observed Teton scenario.
- Changes to `setup_index.py`'s subprocess output parsing (the current `"Another index build is already running"` regex check is correct).
- Changes to the on-disk lock-file format or the existing `classify_index_build_lock_owner` return values (consumers depend on them).
- Generic process-supervision improvements to the background indexer (separate scope).

## Acceptance Criteria

- [x] AC-1: After `wave_index_build(content='graph', mode='rebuild')` is invoked while another live process holds the index-build flock, the response returns `passed: false`, `graph_rebuilt: false`, and a `build_skipped_lock_busy` diagnostic with the lock-holder PID. Test: `test_subprocess_early_exit_with_lock_busy_surfaces_failure` in `test_server_tools.py`.
- [x] AC-2: After `wave_index_build` is invoked when no other process holds the flock, the response returns `passed: true` and the spawned subprocess proceeds normally (no regression on the happy path). Verified by the unchanged passing `RunIndexRebuildTests` suite.
- [x] AC-3: When `_index_build_lock` is entered with a pre-existing lock file whose recorded PID is dead, the lock file is unlinked before the `flock()` attempt, the acquire succeeds, and a new metadata payload (current PID + `started_at`) is written. Test: `test_stale_lock_file_is_unlinked_before_acquire` in `test_indexer.py`.
- [x] AC-4: When two `load_graph` calls fire concurrently in the same Python process after a builder-version mismatch, only one triggers `build_index`. The second observes the in-flight marker and returns a `graph_auto_rebuild_in_progress` diagnostic instead of raising `IndexBuildAlreadyRunning`. Test: `test_concurrent_auto_rebuild_defers_via_inflight_marker` in `test_graph_query.py`.
- [x] AC-5: When the in-flight marker has been present for ≥120 seconds (stale inflight), the next caller is permitted to attempt a fresh rebuild. Test: `test_stale_inflight_marker_allows_fresh_rebuild_attempt` in `test_graph_query.py`. The in-flight marker is also verified to release on every exit path (success and failure) by `test_inflight_marker_released_on_success_and_failure`.

## Tasks

- [x] Add synchronous lock-acquisition verification to `run_index_rebuild` (`server_impl.py`): poll `proc.poll()` for up to `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` (default 1.5s) in `_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS` increments (default 0.1s). On non-zero early exit, read the log tail, look up the lock-holder PID from `index-build.lock`, and return `passed: false`, `build_failed_early: true`, `diagnostic_code: build_skipped_lock_busy` (or `index_build_subprocess_failed`).
- [x] Update `wave_index_build_response` to surface the `build_skipped_lock_busy` / `index_build_subprocess_failed` diagnostic, set `graph_rebuilt: false` when the build failed early, return envelope status `"error"` instead of `"ok"`, and skip cache invalidation + post-rebuild dispatch when the rebuild didn't actually run.
- [x] Add stale-metadata unlink to `_index_build_lock` (`indexer.py`): when `classify_index_build_lock_owner` returns `"stale"` for the pre-existing metadata and the file exists, `lock_path.unlink()` (catching `FileNotFoundError` / `OSError`) before opening the file for the `flock()` attempt. Preserves all existing behavior on live and completed-but-recent classifications.
- [x] Add in-process coordination to `_ensure_graph_builder_current` (`graph_query.py`): module-level `_VERSION_REBUILD_INFLIGHT` dict keyed on `(root, layer)`, guarded by `_VERSION_REBUILD_INFLIGHT_LOCK`. When a mismatch is detected and another rebuild is in-flight (`now - started_at < _INFLIGHT_REBUILD_STALE_SECONDS`), return a `graph_auto_rebuild_in_progress` diagnostic with `rebuild_started_at_age_seconds`. Otherwise claim the marker, run `build_index`, and release the marker in `finally`.
- [x] Add regression tests: AC-1 (`test_subprocess_early_exit_with_lock_busy_surfaces_failure`), AC-3 (`test_stale_lock_file_is_unlinked_before_acquire`), AC-4 (`test_concurrent_auto_rebuild_defers_via_inflight_marker`), AC-5 (`test_stale_inflight_marker_allows_fresh_rebuild_attempt` and `test_inflight_marker_released_on_success_and_failure`).
- [x] Module-level override in `tests/test_server_tools.load_server` to set `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` to `0.0` for all tests (preserves the historical race window the existing graph-refresh-and-resolve tests rely on; tests that exercise the verification behavior locally re-set the constant).

## Agent Execution Graph


| Workstream                     | Owner       | Depends On   | Notes |
| ------------------------------ | ----------- | ------------ | ----- |
| lock-hygiene-and-verification  | Engineering | —            | Bugs 1+2 are independent edits in `indexer.py` and `server_impl.py` |
| autorebuild-coordination       | Engineering | —            | Bug 3 edits are confined to `graph_query.py` |
| regression-tests               | Engineering | lock-hygiene-and-verification, autorebuild-coordination | One test file each in `tests/` |


## Serialization Points

- `wave_index_build_response` and `_ensure_graph_builder_current` both call `indexer.build_index` (transitively). No code-path serialization beyond the file lock itself is needed.

## Affected Architecture Docs

`N/A` — the change is confined to the indexer / graph-query subsystem and does not alter cross-module boundaries, data flow, or testing architecture. The lock file format, `classify_index_build_lock_owner` semantics, and `auto_rebuild_diagnostic` attachment point are all preserved.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Without it `wave_index_build` keeps lying about success — operator-recovery path is broken |
| AC-2 | required | Happy path must not regress |
| AC-3 | important | Stale-metadata noise; not user-blocking but visible in diagnostics |
| AC-4 | required | The diagnostic-spam pattern Teton hit is directly caused by absence of coordination |
| AC-5 | important | Safety net against a crashed rebuild permanently blocking future ones |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-02 | Change admitted to 1p2q3 in response to Teton field session. Investigation completed; three defects confirmed in code. | This doc |
| 2026-06-02 | All three bugs fixed and tests landed. 2251 framework tests pass (was 2246 before — net +5 regression tests for AC-1, AC-3, AC-4, AC-5). | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| 2026-06-02 | Teton's 1.3.17 install reproduced Bug 4 (parallel-extraction fork-after-state deadlock). 1.3.18 ships parallel mode default-off (`WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` default 1 instead of `min(cpu_count, 4)`) as the conservative bridge until spawn-mode worker initializer lands. Bug 4 itself is out of scope for this change doc and will be tracked separately in a follow-up change. | `.wavefoundry/CHANGELOG.md` 1.3.18 entry |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-02 | In-process auto-rebuild coordination (module-level dict guarded by `threading.Lock`) rather than file-based coordination across processes. | The observed Teton scenario is concurrent MCP tool calls in a single server process. File-based cross-process coordination is the lock file itself, which is already in place. Adding a second cross-process coordination layer would duplicate the lock-file mechanism for no observed benefit. | (a) File-based inflight marker; (b) Defer to lock file unconditionally without an in-memory marker (would still hit the contention). |
| 2026-06-02 | Bug 1 fix is unlink-on-stale-classification, not a redesign of `classify_index_build_lock_owner`. | The classification logic is correct; the gap is between classification and action. | Rewrite the classifier to coalesce `stale`/`completed`/`unknown` (over-broadens existing semantics, breaks consumers). |
| 2026-06-02 | Bug 2 verification window is short (≤1.5s) and process-presence-based, not log-parsing-based. | A subprocess that survives 1.5s past Popen has acquired its locks and is into the body of `build_index`. Log parsing would couple `wave_index_build` to indexer log format. | Log-based verification (brittle), longer poll window (delays MCP response to operators). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| In-memory coordination marker leaks if `build_index` raises with a never-released finally. | The `try/finally` in `_ensure_graph_builder_current` releases the marker on every exit path. The 120s stale-inflight safety net is a defense-in-depth backstop. |
| Short verification window in `wave_index_build` returns success for a subprocess that exits with lock-busy at ~2s. | Acceptable: the upstream caller can re-invoke; the worst case is one stale "success" response, vs. the current scenario where every response is "success" regardless of outcome. The 1.5s window covers ~99% of observed startup latencies. |
| Auto-unlink of stale lock files races with another process that just opened the file. | Wrap unlink in `try/except FileNotFoundError`. POSIX `unlink` does not affect file descriptors already open in other processes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
