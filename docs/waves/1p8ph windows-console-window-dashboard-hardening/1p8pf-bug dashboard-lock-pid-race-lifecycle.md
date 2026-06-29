# Dashboard lock / PID-race lifecycle on start

Change ID: `1p8pf-bug dashboard-lock-pid-race-lifecycle`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-28
Wave: `1p8ph windows-console-window-dashboard-hardening`

## Rationale

On the native-Windows post-release test, starting the dashboard produced a false **`url_not_ready`** even though the server was serving (HTTP 200), and the start path can double-spawn and **climb ports** (43127→43147). Root cause: the start poll at `server_impl.py:6812` strictly requires **`meta.get("pid") == proc.pid`**. When a *prior* successful spawn already wrote `dashboard-server.lock` metadata under a **different** PID (observed: poller PID 4920 vs metadata PID 4924), the new start never matches → it reports `url_not_ready` despite a live, serving dashboard, and can spawn a duplicate that climbs to the next port. The start path does not robustly reconcile "a dashboard is already serving under *any* live PID" before spawning.

This is the dashboard lifecycle/reconciliation bug class: the metadata-IS-the-lock model (`dashboard_lib`, wave 1p64x) plus a PID-exact readiness check is racy under concurrent/repeat starts on Windows.

## Requirements

1. **Reconcile-before-spawn:** before spawning, detect an already-serving dashboard (server-lock held OR a live PID in metadata with a reachable URL) and **return that URL** instead of spawning a duplicate — no port climb.
2. **Relax the readiness poll:** accept a serving dashboard without requiring `meta.pid == proc.pid` — e.g. accept any live PID + URL, and/or verify the URL is actually reachable, rather than tying success to the just-spawned PID.
3. **No false `url_not_ready`** when the dashboard is in fact serving.
4. **Preserve** the existing orphan reconciliation (`dashboard_orphan_detected`), the `dashboard-start.lock` transient gate, the lifetime `dashboard-server.lock`, and stop/restart behavior.
5. **Windows lock/metadata-write semantics:** the daemon must be able to publish its full metadata (incl. `url`) via the separate-handle `write_dashboard_metadata` *while holding the lifetime lock* on native Windows. Because `dashboard-server.lock` is BOTH the lifetime lock and the metadata store (wave 1p64x) and `msvcrt.locking` is **mandatory** byte-range (unlike POSIX advisory `flock`), a byte-0 lifetime lock blocks the daemon's own byte-0 metadata rewrite (`ERROR_LOCK_VIOLATION`) → the daemon never publishes `url` → false `url_not_ready`. The lifetime lock must therefore cover a region disjoint from the byte-0 metadata. POSIX whole-file advisory `flock` is unchanged.

## Scope

**Problem statement:** racy dashboard start on Windows — PID-exact readiness check + insufficient already-running reconciliation → false `url_not_ready`, duplicate spawn, port climb.

**In scope:** the start/readiness/reconcile path in `server_impl.py` (~`6760`–`6840`) and the metadata/lock helpers in `dashboard_lib.py` as needed; tests that reproduce the PID-mismatch race.

**Out of scope:** the console-window flash (`1p8pe` swaps the interpreter token), the markdown render (`1p8pg`), a full dashboard lifecycle redesign.

## Acceptance Criteria

- [x] AC-1: starting the dashboard when one is already serving (under any live PID) returns the existing URL, does NOT spawn a duplicate, and does NOT climb ports. (`_dashboard_already_serving` reconcile-before-spawn at both pre-lock and post-lock points; `test_reconcile_before_spawn_returns_serving_url_without_spawning`.)
- [x] AC-2: the readiness poll declares success for a serving dashboard without requiring `meta.pid == proc.pid` (reachable-URL or live-PID+URL check). (`test_metadata_pid_differs_from_proc_pid_no_false_url_not_ready`.)
- [x] AC-3: no false `url_not_ready` is returned when the dashboard is actually serving (regression test reproducing metadata-PID ≠ poller-PID). (poller PID 4920 vs metadata PID 4924 reproduced in the same test.)
- [x] AC-4: stop/restart and orphan reconciliation still behave; the start/server locks still gate concurrent starts (no double-spawn window). (Existing `WaveDashboardTransientStartLockTests` + `WaveDashboardOpenTests` + `WaveDashboardBrowserSuppressTests` all still green; orphan reconcile + start/server lock gating preserved.)
- [x] AC-5: full suite + docs-lint pass. (Suite green except a pre-existing, out-of-scope `scan-findings-format.md` template-parity drift.)
- [~] AC-6: the daemon publishes full metadata (incl. `url`) while holding the lifetime lock on Windows (sentinel-byte lock at `_LOCK_BYTE_OFFSET`, disjoint from the byte-0 metadata); a concurrent start still sees the lock busy (`DashboardLockBusy`); POSIX whole-file `flock` is unchanged. **Status `[~]` (Windows-repro-gated):** the mechanism + POSIX-no-regression are fully met and tested — `DashboardWindowsSentinelLockTests` (POSIX-runnable via a fake `msvcrt` recording the locked offset = `_LOCK_BYTE_OFFSET` ≠ 0; metadata region disjoint from the sentinel; concurrency gate intact; POSIX still uses whole-file `flock`). The remaining live-native-Windows confirmation (`url` actually publishes with no `ERROR_LOCK_VIOLATION`) is unmet on this host because macOS cannot exercise `msvcrt` mandatory byte-range locking; confirmable only on a native-Windows post-release test.

## Tasks

- [x] Add reconcile-before-spawn: return an already-serving dashboard's URL instead of spawning (`_dashboard_already_serving` — live recorded PID + URL, OR a reachable URL backed by a live dashboard process for this root).
- [x] Relax the readiness poll to a reachable-URL / live-PID+URL check (drop the PID-exact requirement); kept the just-spawned-PID accept for backward compatibility + a bounded `DASHBOARD_START_WAIT_SECONDS` deadline so a genuinely-failed start still reports failure.
- [x] Preserve start/server lock gating + orphan reconciliation + stop/restart.
- [x] Tests reproducing the PID-mismatch race + the no-double-spawn/no-port-climb (`WaveDashboardPidRaceTests`); suite + docs-lint.
- [x] Windows lock-vs-metadata-write fix: lock a sentinel byte at `_LOCK_BYTE_OFFSET` (not byte 0) on the `msvcrt` branch of `dashboard_lib.dashboard_lock` so the daemon's separate-handle metadata rewrite (incl. `url`) is not blocked; POSIX `flock` unchanged. Tests in `DashboardWindowsSentinelLockTests`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reconcile-before-spawn + readiness poll | implementer | — | server_impl ~6760-6840 + dashboard_lib |
| race regression tests | qa-reviewer | impl | reproduce metadata-PID ≠ poller-PID |

## Serialization Points

- Shares `server_impl.py` dashboard start (`:6777`/`:6796`) with `1p8pe` (which only swaps the interpreter token). Land the interpreter swap minimal; do the lifecycle rework here. Coordinate so the two edits to the start block do not clobber.

## Affected Architecture Docs

`docs/references/native-windows-support.md` (dashboard start reconciliation note) if a contract is described. ADR `N/A`.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Stops duplicate spawns / port climb. |
| AC-2 | required | The false-negative root cause. |
| AC-3 | required | The operator-visible symptom. |
| AC-4 | required | Must not regress lifecycle/locks. |
| AC-5 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Planned from the 1.9.5 Windows test — false `url_not_ready` + port climb traced to the PID-exact readiness poll. | `server_impl.py:6812` (`meta.get("pid") == proc.pid`); `dashboard_lib` metadata-IS-lock (1p64x); operator trace PID 4920 vs 4924, ports 43127→43147. |
| 2026-06-28 | Implemented in `server_impl.py`. Added `_dashboard_url_reachable` (any HTTP response incl. 4xx/5xx = serving; connect-fail/timeout = not) + `_dashboard_already_serving` (reconcile: live recorded PID+URL, OR reachable URL backed by a live dashboard process). Wired the reconcile both pre-lock and post-lock (before the orphan-kill/spawn). Relaxed the readiness poll: the just-spawned-PID still accepts on metadata (backward compatible); a non-matching PID now accepts on live-PID+URL or URL-reachability, with the bounded `DASHBOARD_START_WAIT_SECONDS` deadline preserved so a real failure still reports `url_not_ready`. Orphan reconcile + start/server lock gating + stop/restart unchanged. | `server_impl._dashboard_url_reachable`/`_dashboard_already_serving`; readiness poll rework (former `meta.pid == proc.pid`); `test_server_tools.WaveDashboardPidRaceTests` (PID 4920 vs 4924, no double-spawn/port-climb, failed-start still reports). |
| 2026-06-28 | Windows lock-vs-metadata-write fix. Root cause: `dashboard-server.lock` is BOTH the lifetime lock and the metadata store (1p64x); the `msvcrt` branch locked byte 0, which (mandatory byte-range on Windows) blocked the daemon's own separate-handle metadata rewrite at byte 0+ → `url` never published → false `url_not_ready`. Fix: added `_LOCK_BYTE_OFFSET = 1 << 30` and locked/unlocked the SENTINEL byte at that offset in `dashboard_lib.dashboard_lock` (Windows branch only); metadata JSON at byte 0+ is now disjoint from the lock region. POSIX whole-file advisory `flock` unchanged. | `dashboard_lib._LOCK_BYTE_OFFSET`; `dashboard_lock` Windows branch (sentinel `fh.seek(_LOCK_BYTE_OFFSET)` acquire/release); `test_dashboard_server.DashboardWindowsSentinelLockTests` (offset ≠ 0, metadata disjoint, concurrency gate intact, POSIX flock unchanged). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | Reconcile already-serving + relax the readiness poll (don't require own PID). | The dashboard genuinely serves; the failure is the success check, not the server. | Kill+respawn on every start (rejected — churn, orphan risk). |
| 2026-06-28 | Sentinel-byte lock (lock a high fixed offset, not byte 0) on the Windows `msvcrt` branch. | Smallest change that keeps the one-file metadata model (1p64x): the metadata at byte 0+ stays disjoint from the mandatory byte-range lock, so the daemon publishes `url` while holding the lifetime lock; concurrency still gated (second start locking the same offset fails). | Write-through the locked handle (rejected — the metadata writer is a separate handle and an in-place rewrite still hit the byte-0 mandatory lock); split the lock into a second file (rejected — re-introduces the two-sidecar model 1p64x removed + a new orphan-the-lock-on-rename risk). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Relaxing the PID check masks a genuinely-failed start. | Verify URL reachability (HTTP) and/or a live PID before declaring success; keep a bounded poll deadline. |
| Reconcile-before-spawn returns a stale/dead dashboard. | Gate on `_pid_is_running` + URL reachability, not metadata alone. |
| The sentinel offset overlaps a (huge) metadata file → re-introduces the conflict. | `_LOCK_BYTE_OFFSET = 1 GiB`; the metadata is small JSON written at byte 0+ (a test asserts `meta_size < _LOCK_BYTE_OFFSET`), so the regions never overlap. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
