# Indexer Cross-Process Lock

Change ID: `0rlec-bug indexer-cross-process-lock`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

Dashboard auto-index can start duplicate `indexer.py` jobs when more than one dashboard process is running for the same checkout. The existing `IndexBuilder` guard is process-local, and the existing Lance table `.lock` files are acquired only during the write phase after chunking and embedding have already consumed minutes of CPU and memory.

The indexer needs a repo/index-wide cross-process lock acquired before hashing, chunking, embedding, or writing. Status and dashboard surfaces also need to clean up stale table lock markers left behind when an indexer is killed, so a dead process does not leave the UI stuck in a running state.

## Requirements

1. Add a whole-index build lock acquired at `indexer.py` startup before any expensive work.
2. The lock must be cross-process and cross-platform:
   - Linux, macOS, and WSL2: `fcntl.flock`.
   - Native Windows: `msvcrt.locking`.
   - The lock file may remain as metadata, but correctness must depend on the OS-held lock, not file deletion.
3. A second concurrent indexer for the same index directory must exit quickly with a clear "already running" diagnostic.
4. Dashboard auto-index and MCP/manual index builds must all be protected by the same indexer-level lock.
5. Keep Lance table `.lock` files as write-phase markers, but do not rely on them as the whole-job concurrency authority.
6. `wave_index_build_status` must detect stale table `.lock` files whose owner PID is dead; it should remove those markers and report cleanup in structured data.
7. The dashboard index tile must surface stale lock cleanup/detection rather than leaving the layer indefinitely "running".
8. Automated tests must cover:
   - successful lock acquisition and release;
   - contention failure;
   - stale table-lock cleanup;
   - duplicate dashboard/indexer protection.

## Scope

**Problem statement:** Per-dashboard in-memory locking and late table-write locks allow duplicate indexer jobs to perform the same expensive embedding work concurrently for one checkout.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Rebuilding or compacting existing LanceDB tables.
- Changing embedding models or chunking logic.
- Disabling dashboard auto-index by default.

## Acceptance Criteria

- [x] AC-1: A second simultaneous `indexer.py` invocation for the same index directory exits quickly with an "already running" diagnostic before embedding begins.
- [x] AC-2: The whole-index lock releases automatically when the process exits or dies; status does not depend on deleting the lock file.
- [x] AC-3: `wave_index_build_status` removes stale table `.lock` files for dead owners and reports the cleanup.
- [x] AC-4: Dashboard status reflects stale lock cleanup/detection and does not leave a dead build displayed as indefinitely running.
- [x] AC-5: Existing per-table write locks remain in place for LanceDB writes.
- [x] AC-6: Targeted indexer/server/dashboard tests pass.
- [x] AC-7: `wave_validate` passes after docs/status updates.
- [x] AC-8: `wave_dashboard_start` returns an already-running/in-progress response instead of spawning a second dashboard process for the same repository.

## Tasks

- [x] Add cross-platform whole-index lock helper to `indexer.py`.
- [x] Acquire the whole-index lock before `build_index()` work begins and fail fast on contention.
- [x] Add stale table-lock inspection/cleanup helper shared by status and dashboard.
- [x] Update `wave_index_build_status` response data for stale lock cleanup.
- [x] Surface stale lock cleanup/detection in dashboard snapshot/status.
- [x] Add regression tests for lock contention and stale lock cleanup.
- [x] Add dashboard start/process lock coverage for duplicate dashboard starts.
- [x] Run targeted tests and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| indexer lock | implementer | — | Cross-platform OS lock before expensive work |
| status cleanup | implementer | indexer lock | Stale table-lock cleanup and response data |
| dashboard surfacing | implementer | status cleanup | Keep dashboard from showing dead builds indefinitely |
| tests | implementer | all implementation | Targeted indexer/server/dashboard coverage |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` may need a short update because daemon-triggered index rebuild flow changes from dashboard-local locking to indexer-owned cross-process locking.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core prevention of duplicate expensive jobs |
| AC-2 | required | Killed processes must not leave correctness dependent on cleanup |
| AC-3 | required | Repairs existing stale table-lock failure mode |
| AC-4 | important | Operator visibility and dashboard correctness |
| AC-5 | required | Preserve LanceDB write safety |
| AC-6 | required | Prevent regression |
| AC-7 | required | Docs gate |
| AC-8 | required | Prevent duplicate dashboard server processes from reintroducing duplicate index jobs |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Change created after duplicate dashboard processes started overlapping indexer jobs. | Process inspection showed two `indexer.py` jobs for one checkout; code inspection showed table locks are acquired only during write phase. |
| 2026-05-27 | Implemented whole-index OS lock, stale table-lock cleanup, dashboard surfacing, and regression coverage. | `py_compile` passed; `IndexBuildLockTests`, `BackgroundRefreshActiveTests`, and dashboard server tests passed. Full `test_indexer.py` is blocked in the base interpreter by missing optional runtime packages (`numpy`, `onnxruntime`). |
| 2026-05-27 | Validation completed. | `wave_validate` returned `docs-lint: ok`. |
| 2026-05-27 | Added dashboard start/process locks so duplicate dashboard starts return already-running/in-progress instead of spawning another server. | `py_compile`, `WaveDashboardOpenTests`, `WaveDashboardBrowserSuppressTests`, and `test_dashboard_server.py` passed. |
| 2026-05-27 | Clarified stale table-lock cleanup docs to match implementation: only dead owners are removed. | `_cleanup_stale_table_locks()` and this change doc now align on dead-PID cleanup only. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Use an OS-held whole-index lock rather than file-existence locking | OS locks release automatically when the process dies; file deletion is not required for correctness | Rely on deleting `.lock` files — rejected because killed processes skip cleanup |
| 2026-05-26 | Keep table `.lock` files as write-phase markers only | They are useful for readers/status but are too late to prevent duplicate embedding work | Remove table locks — rejected because they still protect LanceDB write visibility |
| 2026-05-26 | Use stdlib `fcntl`/`msvcrt` instead of a new dependency | Keeps framework bootstrap dependency-light and works across Linux, macOS, WSL2, and native Windows | Add `filelock` dependency — rejected unless stdlib proves insufficient |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Windows lock semantics differ from POSIX | Isolate platform-specific code behind one helper and test acquisition/contention behavior with mocked platform branches where needed |
| WSL2 on `/mnt/c` has less reliable filesystem behavior | Prefer OS locks, and surface a degraded-lock warning if WSL2 is detected on a mounted Windows filesystem |
| Status cleanup could delete a live table marker | Treat PID-alive locks as active; only remove markers whose owner PID is dead |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
