# Test Suite Dashboard Isolation

Change ID: `12r12-maint test-suite-dashboard-isolation`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

Running the full framework test suite was spawning a real dashboard process and opening the browser mid-run. `test_restart_allowed_when_no_lock` (added in 12r08/12r0b) called `wave_dashboard_restart_response` without mocking `wave_dashboard_start_response`, so the function fell through to `subprocess.Popen(dashboard_server.py --open)` — the spawned process called `webbrowser.open()` and persisted after the test finished.

Separately, `SnapshotStoreTests` and `IndexBuilderSnapshotIntegrationTests` created real `SnapshotStore` instances that started daemon watcher threads and scheduled `IndexBuilder` timers. In a slow test run the timers fired before tearDown, spawning real indexer subprocesses that wrote into the test temp directory. When tearDown then called `tmp.cleanup()`, the subprocess was still writing → `OSError: Directory not empty`. The threads themselves leaked between test methods because `SnapshotStore` had no stop mechanism.

## Requirements

1. `SnapshotStore` must expose a `stop()` method that: (a) sets a stop event so the `_watch_loop` daemon thread exits cleanly on its next iteration; (b) cancels any pending `IndexBuilder` timer; (c) waits (up to 10 s) for any in-progress build subprocess to finish before returning, so callers can safely delete the working directory immediately after.
2. `_watch_loop` must use `_stop_event.wait(timeout=_WATCH_INTERVAL)` instead of `time.sleep(_WATCH_INTERVAL)` so the stop signal interrupts the sleep immediately.
3. `SnapshotStoreTests` must call `store.stop()` in tearDown for every store created during the test, via a tracked-store pattern.
4. `IndexBuilderSnapshotIntegrationTests` must call `store.stop()` in tearDown for every store created during the test, via the same tracked-store pattern.
5. `WaveDashboardRestartUpgradeGuardTests.test_restart_allowed_when_no_lock` must mock `wave_dashboard_start_response` so no real subprocess is spawned or browser opened.

## Scope

**Problem statement:** The test suite was opening the browser and leaving a real dashboard process running after `test_restart_allowed_when_no_lock`. SnapshotStore daemon threads and IndexBuilder timers were leaking between tests, causing `OSError: Directory not empty` in tearDown under a slow full-suite run.

**In scope:**

- `dashboard_server.py` — `SnapshotStore.stop()`, `_stop_event`, `_watch_loop` change
- `tests/test_dashboard_server.py` — `SnapshotStoreTests` and `IndexBuilderSnapshotIntegrationTests` teardown tracking
- `tests/test_server_tools.py` — `test_restart_allowed_when_no_lock` mock fix

**Out of scope:**

- Terminating already-running indexer subprocesses from a prior crashed test (the 10 s wait in `stop()` covers the normal case)
- Changing IndexBuilder's internal subprocess handling

## Acceptance Criteria

- AC-1: Running the full test suite does not open a browser window or leave a dashboard process running after completion.
- AC-2: Running the full test suite produces no `OSError: Directory not empty` cleanup errors.
- AC-3: `SnapshotStore.stop()` exists, sets `_stop_event`, cancels any pending IndexBuilder timer, and waits for any in-progress build to finish.
- AC-4: `SnapshotStoreTests` and `IndexBuilderSnapshotIntegrationTests` call `stop()` on all created stores in tearDown.
- AC-5: `test_restart_allowed_when_no_lock` passes without spawning a real subprocess.
- AC-6: All 1374 framework tests pass.

## Tasks

- Add `self._stop_event = threading.Event()` to `SnapshotStore.__init__`
- Add `stop()` method to `SnapshotStore`
- Change `_watch_loop` from `while True: time.sleep(...)` to `while not self._stop_event.wait(timeout=...)`
- Update `SnapshotStoreTests`: add `_stores_to_stop`, `_track()` helper, stop in tearDown
- Update `IndexBuilderSnapshotIntegrationTests`: add `_stores_to_stop`, `_track()` helper, stop in tearDown
- Fix `test_restart_allowed_when_no_lock`: add `patch.object(srv, "wave_dashboard_start_response", ...)`

## Agent Execution Graph

| Workstream    | Owner              | Depends On   | Notes                             |
| ------------- | ------------------ | ------------ | --------------------------------- |
| server-stop   | framework-engineer | —            | SnapshotStore.stop() + _watch_loop |
| test-teardown | framework-engineer | server-stop  | Both test classes + restart guard  |

## Serialization Points

- `dashboard_server.py` — must precede test_dashboard_server.py changes (tests call `store.stop()`)

## Affected Architecture Docs

N/A — internal testability fix; no boundary or data-flow change. `SnapshotStore.stop()` is not part of the MCP or HTTP surface.

## AC Priority

| AC   | Priority  | Rationale                                     |
| ---- | --------- | --------------------------------------------- |
| AC-1 | required  | Directly addresses user-reported symptom      |
| AC-2 | required  | Directly addresses user-reported symptom      |
| AC-3 | required  | Foundation for AC-4 and AC-2                  |
| AC-4 | required  | Ensures cleanup in all test classes            |
| AC-5 | required  | Root cause of AC-1                             |
| AC-6 | required  | No regression                                 |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented. `SnapshotStore.stop()` added; `_stop_event` wired into `_watch_loop`; `SnapshotStoreTests` and `IndexBuilderSnapshotIntegrationTests` updated with `_track()` / tearDown stop calls; `test_restart_allowed_when_no_lock` mocks `wave_dashboard_start_response`. 1374 tests pass, no cleanup errors, no browser opens. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1374 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | `stop()` waits for in-progress build (spin-wait up to 10 s) | Ensures tearDown can delete temp dir without racing the indexer subprocess | `ignore_cleanup_errors=True` on TemporaryDirectory (hides rather than fixes); terminate subprocess directly (complex, OS-specific) |
| 2026-05-19 | `_stop_event.wait(timeout=N)` replaces `time.sleep(N)` | Makes `stop()` interrupt the sleep immediately rather than waiting up to 3 s for the next iteration | Separate wakeup queue; pipe-based interrupt (both more complex for no benefit) |
| 2026-05-19 | Mock `wave_dashboard_start_response` directly (not `subprocess.Popen`) | The test is checking the upgrade guard, not start behavior; mocking at the higher level is semantically correct and avoids the 5 s polling loop | Patching subprocess.Popen (works but adds noise from the 5 s deadline timeout) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| In-progress build takes >10 s in a slow CI environment | 10 s covers the indexer for all known repo sizes; if exceeded, tmp.cleanup() may still get OSError (tolerable vs. indefinite hang) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
