# Dashboard lifecycle: reconcile against real processes (orphans, port climb, dead-PID)

Change ID: `1p654-bug dashboard-lifecycle-reconciliation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

> Operator-directed addition (2026-06-17), acknowledged off-theme for the codebase-map wave; same dashboard surface as `1p64x`. Field-reported by javaagent and reproduced live on the self-host (3 orphaned `dashboard_server.py --root <wavefoundry>` processes accumulated across this session's restarts).

## Rationale

The dashboard lifecycle tools (`wave_dashboard_start`/`_stop`/`_restart`) derive state SOLELY from the recorded-PID metadata (now `dashboard-server.lock`, post-`1p64x`) with a bare `os.kill(pid,0)` liveness check (`_pid_is_running`, `server_impl.py:4511`) and NO reconciliation against actual processes. Two failure modes, one root:

- **A — false positive:** `running_meta` (`:6484`) and `wave_dashboard_stop_response` (`:6760`) trust `_pid_is_running`, which succeeds for a zombie (until reaped) or a recycled PID → a just-killed PID reports `already_running`. The index-status path already guards exactly this (`:6365-6378` log-done cross-check + "os.kill succeeds on zombies until reaped"); the dashboard path never got the parallel fix.
- **B — false negative:** stop/restart read the recorded PID; when metadata drifted (a prior restart removed it but the detached child — `start_new_session=True`, `:6580` — survived), `pid` is absent → returns `already_stopped` and never kills the real orphan. Restart then can't reuse the port (held by the orphan) → the port climbs.

## Requirements

1. **Process-cmdline reconciliation.** A helper finds live `dashboard_server.py --root <this root>` processes by scanning process cmdlines (POSIX `ps`; resolved-path token match). Used to (a) verify a recorded PID is actually a dashboard for this root, and (b) find orphans regardless of metadata state.
2. **Zombie/recycled-safe liveness for this surface.** `already_running` / `running_meta` must require the recorded PID both be alive AND cmdline-match a dashboard for this root — a recycled/zombie PID (empty/mismatched cmdline) is NOT "running". Where the scan is unavailable (e.g. Windows), fall back to the existing bare check (no regression).
3. **Stop kills all orphans.** `wave_dashboard_stop` terminates every live dashboard process for this root (cmdline scan ∪ recorded PID), not just the recorded one — so a drifted metadata file can't leave an orphan alive. Reports the count.
4. **Start reconciles to one instance.** When there is no valid recorded instance but orphans exist, `start` terminates them before spawning (replace) rather than spawning alongside — and emits a `dashboard_orphan_detected` diagnostic. (A valid live instance is still adopted via `already_running`, no duplicate.) This + stop-kills-orphans frees the held port so the existing `restart_port` capture reuses it — closing the port climb.
5. Generic, cross-platform-safe (POSIX primary; Windows best-effort = current behavior); no version bumps.

## Scope

**In scope (`server_impl.py` dashboard lifecycle):**

- `_dashboard_cmdline_pids(root) -> list[int] | None` (None = scan unsupported/failed → callers fall back).
- `_dashboard_pid_is_live(pid, root)` = `_pid_is_running` AND cmdline-match (or fallback when scan is None).
- `running_meta` gates on `_dashboard_pid_is_live`.
- `wave_dashboard_stop_response`: terminate the union of scanned orphans + recorded PID; report `stopped_pids` / `orphans_terminated`.
- `wave_dashboard_start_response`: pre-spawn orphan reconciliation + `dashboard_orphan_detected` diagnostic.
- Tests (mock the scan + liveness + terminate).

**Out of scope:**

- A dependency on `psutil` (use `ps`; keep it dependency-free).
- Windows cmdline scanning (best-effort no-op; documented).
- Changing the lock file / metadata shape (that was `1p64x`).

## Acceptance Criteria

- [x] AC-1: `wave_dashboard_start` does NOT report `already_running` for a recorded PID whose cmdline no longer matches a dashboard for this root (recycled/dead/zombie PID) — gated on `_dashboard_pid_is_live`. A genuinely-live matching instance is still adopted.
- [x] AC-2: `wave_dashboard_stop` terminates ALL live dashboard processes for this root (orphans included) even when the recorded metadata PID is absent or stale; reports how many.
- [x] AC-3: `wave_dashboard_start` reconciles to one instance — when no valid recorded instance exists but orphans do, it terminates them before spawning and emits `dashboard_orphan_detected`; no spawn-alongside. The scan is dependency-free (`ps`) and Windows falls back to current behavior.
- [x] AC-4: Tests cover A (recycled-PID not adopted), B (orphan killed with absent metadata), and the start reconciliation; full suite + docs-lint clean; no version bumps.

## Tasks

- [x] Add `_dashboard_cmdline_pids` (POSIX `ps`, resolved-root token match, excludes self) + `_dashboard_pid_is_live`.
- [x] Gate `running_meta` on `_dashboard_pid_is_live`.
- [x] Stop: terminate the orphan ∪ recorded-PID set; report counts.
- [x] Start: pre-spawn orphan reconciliation + diagnostic.
- [x] Tests (mock scan/liveness/terminate); full suite + docs-lint.

## Affected Architecture Docs

`N/A` — dashboard process-lifecycle internals; no boundary/flow/verification change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Stops `already_running` on a dead/recycled PID (fix A). |
| AC-2 | required | Eliminates orphan accumulation — the highest-impact symptom (fix B). |
| AC-3 | required | Converges to one instance + frees the port (closes the climb). |
| AC-4 | required | Locks the reconciliation behavior against regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | javaagent field report + reproduced live (3 orphan dashboards for the self-host repo; port climbed 43129→43132 across restarts; killed PID reported `already_running`). Index-status path already has the guard to mirror. | `server_impl.py:4511,6365-6378,6484,6760`; field-feedback memory `project-dashboard-lifecycle-bug` |
| 2026-06-17 | Delivery-review follow-up RESOLVED: relocated the cmdline scan to the shared `dashboard_lib.dashboard_cmdline_pids` (server_impl now delegates) and hardened `upgrade_wavefoundry._detect_dashboard` to cmdline-verify the recorded PID (was a bare `os.kill`, same recycled/zombie-PID class). Also added a direct parse/match test for the kill-decision logic (this-root-only, self/other-root/non-dashboard exclusion, `--root=`, None-on-failure). +5 tests; full suite 3274 green. | `dashboard_lib.py` (shared helper); `server_impl.py` (delegate); `upgrade_wavefoundry.py:148`; `test_dashboard_server.py`, `test_upgrade_wavefoundry.py::DetectDashboardLivenessTests` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Reconcile via a dependency-free `ps` cmdline scan, not `psutil`. | Keeps the tool venv lean; `ps` is universal on the POSIX self-host/consumer boxes. | `psutil` (rejected — new dependency for a local-only convenience surface). |
| 2026-06-17 | Start does adopt-or-REPLACE (kill orphans + spawn), not adopt. | Adopting an orphan with drifted metadata can't recover its URL/port reliably; replacing converges deterministically to one fresh instance. | Adopt the orphan (rejected — unreliable without its metadata). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `ps` cmdline match is too broad/narrow (wrong process killed or orphan missed). | Match requires BOTH `dashboard_server.py` in the cmdline AND a `--root` token resolving to this exact root; excludes the current PID. Other repos' dashboards (different `--root`) are never matched. |
| Windows has no cmdline scan → orphans not reconciled there. | Documented; Windows falls back to current single-PID behavior (no regression). The bug is observed on POSIX. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
