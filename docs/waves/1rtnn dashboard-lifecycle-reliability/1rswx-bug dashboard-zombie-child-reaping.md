# Dashboard Zombie Child: Reaping and Zombie-Safe Stop

Change ID: `1rswx-bug dashboard-zombie-child-reaping`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rtnn dashboard-lifecycle-reliability`

## Rationale

The long-lived MCP server spawns the local dashboard as a subprocess with `subprocess.Popen(..., start_new_session=True)` (`server_impl.py:7622`). On POSIX that only calls `setsid()` — it detaches the child from the controlling terminal/process group but does **not** reparent it, so the MCP server remains the dashboard's OS parent (observed: a `<defunct>` dashboard PID whose PPID was `server.py`).

When a dashboard child exits — a crash, an OOM, an out-of-band kill, or a prior restart cycle that never confirmed a reap — the MCP server never calls `waitpid` on it, so it lingers as a zombie in the process table for the rest of the session. The server *has* a proactive reaper, but it is scoped exclusively to background index builds (`_reap_background_build_pids` / `_BACKGROUND_BUILD_PIDS`, added in wave 1p98u, `server_impl.py:5178-5211`); the dashboard was never wired into it, and an automatic `SIGCHLD` reaper was deliberately rejected in 1p98u because it breaks the server's synchronous `subprocess.run`/`.wait()` calls with `ECHILD`. The zombie only clears when the MCP server process itself exits (launchd/init inherits and reaps it) or when a stop/restart call happens to `waitpid` the exact PID.

Worse, `wave_dashboard_stop`/`wave_dashboard_restart` **fail** on such a zombie instead of cleaning it up. The stop path decides kill targets using a bare `os.kill(pid, 0)` liveness check (`_pid_is_running`, `server_impl.py:5078`), which returns `True` for a zombie because the kernel keeps the PID slot until it is reaped. The zombie is therefore added as a stop target; `SIGTERM`/`SIGKILL` delivered to an already-dead process do nothing; the function returns failure with empty `stopped_pids` (`server_impl.py:7924-7932`). The zombie-safe helper `_dashboard_pid_is_live` (`server_impl.py:7742-7755`, combining `_pid_is_running` **and** a cmdline match, since a zombie's `ps` command renders as `<defunct>` not `dashboard_server.py`) already exists and is used on the **start** path — which is exactly why `wave_dashboard_start` succeeded in the same session — but the stop path's recorded-PID branch does not reuse it.

This is the dashboard counterpart of the two bugs 1p654 (zombie-safe liveness) and 1p98u (proactive reaping) already fixed for other subsystems; the dashboard side was never closed the same way.

## Requirements

1. Reap dashboard children proactively so they cannot accumulate: register each server-spawned dashboard PID and sweep finished ones with `os.waitpid(pid, os.WNOHANG)`, reusing the established `_BACKGROUND_BUILD_PIDS` sweep pattern from 1p98u rather than a new mechanism or a `SIGCHLD` handler (explicitly rejected in 1p98u for `ECHILD` reasons). **The sweep must fire on a frequently-hit path, not only dashboard-tool calls (readiness amendment):** register the dashboard PID into (or sweep it alongside) the same reap that `_start_background_index_refresh` already triggers on every index-build launch, so a dashboard that dies mid-session is reaped opportunistically during ordinary editing activity — not left until the next explicit `wave_dashboard_*` call or server exit. Dashboard start/stop/restart/status remain additional sweep points.
2. Make the stop path zombie-safe: the recorded-PID branch of `wave_dashboard_stop`/`restart` must classify liveness with the cmdline-verified `_dashboard_pid_is_live` (or equivalent), so a `<defunct>` recorded PID is treated as **already stopped** — reaped, its stale metadata/lock cleared — not as a live kill target that fails.
3. Preserve the existing multi-instance reconciliation: `_dashboard_cmdline_pids` scanning must still terminate genuinely-live dashboards for this root; the fix must not regress the 1p654 behavior of cleaning up real orphans.
4. `wave_dashboard_stop` on a repository whose only recorded dashboard is a zombie must return success (state = stopped, stale metadata cleared), not `stop_failed`.
5. `wave_dashboard_restart` must succeed when the prior dashboard is a zombie: reap/clear the dead PID, then start fresh (the start path already binds correctly, as observed).
6. No behavior change to the Windows spawn path (`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`) or the `--daemon` self-daemonize path beyond what reaping requires; Windows has no zombie/reap semantics and must not regress.
7. Recorded-PID liveness used for *status* reporting must not report a zombie as a live/serving dashboard (align with the start-path `_dashboard_already_serving` treatment).
8. Local-only, stdlib only; no new dependency, no `SIGCHLD` global handler.

## Scope

**Problem statement:** Dead dashboard children accumulate as zombies parented to the long-lived MCP server because the server never reaps them, and the stop/restart tools fail on those zombies because their liveness check (bare `os.kill(pid,0)`) cannot distinguish a zombie from a live process — even though the zombie-safe check already exists and is used on the start path.

**In scope:**

- Proactive reaping of server-spawned dashboard PIDs (registry + WNOHANG sweep, 1p98u pattern).
- Zombie-safe liveness in the stop/restart recorded-PID branch (reuse `_dashboard_pid_is_live`).
- Stale metadata/lock cleanup when the recorded PID is a reaped/defunct process.
- Status/liveness reporting consistency (zombie ≠ serving).
- Tests: zombie-stop returns success + clears metadata; zombie-restart reaps-and-respawns; live-dashboard stop still terminates; reaping prevents accumulation across repeated start/stop; Windows path unaffected.

**Out of scope:**

- Fully re-detaching the dashboard via double-fork so it reparents to init/launchd (considered and rejected in the Decision Log; larger spawn-model change, and reparenting removes the server's ability to `waitpid`/track the PID the start/stop reconciliation relies on).
- The dashboard's "stops updating while alive" defect — a separate live-process failure owned by `1rtju-bug dashboard-silent-staleness` in the same wave.
- Any change to what the dashboard serves or renders.
- Generalizing reaping to other server-spawned subprocesses beyond the dashboard.

## Acceptance Criteria

- [x] AC-1: `wave_dashboard_stop` against a repository whose recorded dashboard PID is a zombie (`<defunct>`) returns success with the process reaped and stale metadata/lock cleared — not `stop_failed` with empty `stopped_pids`. Reproduces the observed failure in a test via a fixture zombie/mock. Evidence: `test_stop_on_zombie_recorded_pid_returns_success` (asserts `already_stopped`, metadata cleared, WNOHANG reap on entry, no `_terminate_dashboard_pid` call).
- [x] AC-2: `wave_dashboard_restart` with a zombie prior dashboard reaps/clears the dead PID and starts a fresh serving instance. Evidence: `test_restart_reaps_zombie_then_starts_fresh`.
- [x] AC-3: The stop/restart recorded-PID branch classifies liveness with the cmdline-verified check; a `<defunct>` PID is never sent `SIGTERM`/`SIGKILL` as a live target, and a genuinely-live dashboard for the root is still terminated (1p654 reconciliation preserved). Evidence: stop-path swapped to `_dashboard_pid_is_live` (`server_impl.py`); `test_stop_still_kills_live_dashboard` + `test_stop_on_zombie_recorded_pid_returns_success`.
- [x] AC-4: Server-spawned dashboard PIDs are reaped via a WNOHANG sweep that fires on the frequently-hit index-refresh path (`_start_background_index_refresh`) as well as on dashboard start/stop/restart/status, mirroring `_reap_background_build_pids`; a test shows (a) repeated start→die→start cycles leave no accumulating zombies, and (b) a dashboard that dies is reaped by a subsequent index-refresh sweep without any `wave_dashboard_*` call. Evidence: `_DASHBOARD_CHILD_PIDS`/`_register_dashboard_child_pid`/`_reap_dashboard_child_pids`; `test_index_refresh_sweeps_dashboard_children`, `test_start_registers_spawned_dashboard_pid`, reap-registry tests.
- [x] AC-5: Status/liveness reporting does not classify a zombie as a live/serving dashboard. Evidence: `wave_dashboard_open_response` swapped to `_dashboard_pid_is_live`; `test_open_does_not_report_zombie_as_serving`.
- [x] AC-6: The Windows spawn/stop paths are behaviorally unchanged (no reaping semantics assumed on Windows); existing dashboard-lifecycle tests stay green. Evidence: register/reap are POSIX-guarded (`os.name == "nt"` early-return); `test_register_noop_on_windows`, `test_reap_noop_on_windows`; full dashboard suite green.
- [x] AC-7: Full framework tests run bytecode-free and docs validation passes. Evidence: full suite re-run at wave close; docs-lint clean.

## Tasks

- [x] Add a dashboard-PID registry + WNOHANG reap sweep (modeled on `_reap_background_build_pids`/`_BACKGROUND_BUILD_PIDS`); wire it into the existing `_start_background_index_refresh` sweep path plus the dashboard start/stop/restart/status entry points.
- [x] Replace the bare `_pid_is_running` liveness in the stop/restart recorded-PID branch with `_dashboard_pid_is_live` (cmdline-verified, zombie-safe).
- [x] On a reaped/defunct recorded PID, clear stale metadata/lock and report stopped.
- [x] Align status/liveness reporting so a zombie is not "serving".
- [x] Add tests: zombie-stop success, zombie-restart respawn, live-stop still kills, no-accumulation across cycles, Windows-path unaffected.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reaping | implementer | — | PID registry + WNOHANG sweep on entry points |
| zombie-safe-stop | implementer | — | Cmdline-verified liveness in stop/restart recorded-PID branch |
| tests | qa-reviewer | reaping, zombie-safe-stop | Zombie fixtures, no-accumulation, live-stop regression, Windows |


## Serialization Points

- Reaping and the zombie-safe stop check touch the same dashboard lifecycle functions in `server_impl.py`; land them together to avoid a half-fixed stop path.
- Companion to `1rtju-bug dashboard-silent-staleness` in the same wave: both edit dashboard code but different surfaces (process lifecycle in `server_impl.py` vs the watcher/SSE in `dashboard_server.py`/`dashboard.js`) — coordinate on any shared helper touched.

## Affected Architecture Docs

- N/A — a lifecycle bug fix confined to the dashboard process management in `server_impl.py`; no module-boundary, data-flow, or contract change. (The `wave_dashboard_*` tool contracts are unchanged; only their failure behavior on a dead PID is corrected.)

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported failure — stop fails on a zombie — must be fixed and regression-locked. |
| AC-2 | required | Restart is the operator's primary recovery verb and currently fails the same way. |
| AC-3 | required | The root cause (bare-kill liveness misclassifying a zombie) plus no-regression on real-orphan cleanup. |
| AC-4 | required | Without proactive reaping the zombies keep accumulating; this is the durable fix, not just the tool-failure symptom. |
| AC-5 | important | Status consistency prevents "it says running but it's dead" confusion. |
| AC-6 | required | Windows must not regress; it has no zombie semantics and different lifecycle code. |
| AC-7 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-05 | Diagnosed from a live incident: `wave_dashboard_restart`/`stop` returned `stop_failed` with empty `stopped_pids`; `ps` showed the recorded PID `<defunct>` (zombie) parented to `server.py`; port was free; `wave_dashboard_start` succeeded. Root cause traced to non-reparenting spawn + no dashboard reap + bare-kill liveness in the stop path. | `ps -p <pid>` → `Z`/`<defunct>`, PPID = server.py; `server_impl.py:7622` spawn, `:5178-5211` build-only reaper, `:5078` `_pid_is_running`, `:7742-7755` `_dashboard_pid_is_live`, `:7913-7932` stop-target selection; guru lifecycle trace. |
| 2026-07-05 | Readiness-council amendment: reap on the frequently-hit `_start_background_index_refresh` sweep, not only dashboard-tool entry points (Req 1, AC-4). The observed lingering zombies happened precisely because a mid-session dashboard death with no later `wave_dashboard_*` call left the zombie until server exit; folding the dashboard PID into the sweep that index builds already trigger reaps it during ordinary editing. | Prepare-council synthesis; `_start_background_index_refresh` calls `_reap_background_build_pids` on every build launch (`server_impl.py:5211`). |
| 2026-07-06 | Implemented + delivery-reviewed (code-correctness, qa, perf+security-faithfulness lanes). Reap registry/sweep, zombie-safe stop/open, spawn registration, index-refresh sweep wiring. Reviews confirmed: reap cannot mis-wait or kill a live process (scoped to self-spawned PIDs, WNOHANG, POSIX-only); thread-safety clean; zombie-stop test is revert-sensitive (mutation-verified — reverting to bare `_pid_is_running` flips the assertions). One MEDIUM accepted-tradeoff recorded (scan-miss orphan vs the AC-3 security control — security wins; see Risks). | `_DASHBOARD_CHILD_PIDS`/`_register_dashboard_child_pid`/`_reap_dashboard_child_pids`; stop-path `_dashboard_pid_is_live` swap; tests `DashboardChildReapTests` + edited open/stop tests; full suite green. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-05 | Fix via proactive reaping (1p98u registry+WNOHANG pattern) + a zombie-safe stop-path liveness check, keeping the current `start_new_session` spawn model. | Reuses two already-proven patterns in this codebase (1p98u reaping, 1p654 cmdline-verified liveness), is contained to `server_impl.py`, fixes both the accumulation and the tool-failure symptoms, and avoids reworking the spawn/detach model. | **Double-fork / full daemonize** so the dashboard reparents to init and is auto-reaped: rejected — a larger spawn-path change, and reparenting removes the server's ability to `waitpid`/track the PID that start/stop reconciliation depends on. **`SIGCHLD` auto-reap:** rejected — already ruled out in 1p98u because it breaks the server's synchronous `subprocess.run`/`.wait()` with `ECHILD`. **Stop-path liveness fix only (no reaping):** rejected — stops the tools from erroring but leaves zombies accumulating in the table until server exit. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Reaping the wrong PID (a recycled PID now owned by an unrelated process) | Reap only PIDs the server itself registered as dashboard spawns, and gate termination on the cmdline-verified check (`dashboard_server.py` match), never a bare PID — the same recycled-PID class 1p654 already guards. |
| WNOHANG sweep races with a still-starting child | Sweep only reaps already-exited PIDs (`WNOHANG` returns 0 for a live child); a starting child is untouched. |
| Windows regression from reaping assumptions | Guard reaping to POSIX; Windows keeps its existing `DETACHED_PROCESS` lifecycle and tests. |
| Over-aggressive "already stopped" classification hides a real live dashboard | Zombie classification requires BOTH not-cmdline-live AND the reap/`<defunct>` signal; a live dashboard still matches the cmdline scan and is terminated. |
| **Accepted tradeoff (delivery review):** if the cmdline scan RUNS but MISSES a genuinely-live dashboard (e.g. a symlink path component repointed mid-session so `--root` no longer resolves-equal), stop reports `already_stopped` and leaves that instance running. | We deliberately do NOT fall back to killing any os.kill-alive recorded PID, because that reintroduces the AC-3 security defect (SIGKILLing a recycled PID owned by an unrelated process — indistinguishable from a scan-missed dashboard without the cmdline check). The security control wins. This is a pre-existing blind spot of the 1p654 cmdline-scan reconciliation (start's orphan sweep uses the same scan), is rare, self-recovers once the path drift resolves, and the scan-UNAVAILABLE case still falls back to bare liveness. Documented inline at the stop path (`server_impl.py`). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
