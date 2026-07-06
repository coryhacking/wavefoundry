# Dashboard stop: honest report for an alive-but-unverified recorded PID

Change ID: `1rvfw-bug dashboard-stop-unverified-pid-safe-report`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rvfy release-1p11-preship-hardening`

## Rationale

Wave `1rswx` (shipped in 1.11.0's 1rtnn wave) correctly stopped `wave_dashboard_stop` from SIGKILLing a recycled/zombie PID by classifying the recorded PID with the cmdline-verified `_dashboard_pid_is_live` instead of a bare `os.kill` liveness. Its delivery review flagged a MEDIUM residual, accepted-and-documented at the time: when the cmdline scan RUNS but MISSES a genuinely-live dashboard for this root (e.g. a symlink path component repointed mid-session so the process's `--root` no longer `resolve()`-equals `root`), the recorded PID fails `_dashboard_pid_is_live`, `targets` is empty, and stop takes the "nothing to stop" branch (`server_impl.py:7993-7995`): it reports `already_stopped: True` **and removes the metadata file** — a *false success* plus *state loss*, while the dashboard keeps serving. Because the start path's orphan reconciliation uses the same scan, that instance is then hard to manage from the tool.

The security tradeoff (never kill an unverified PID — a scan-missed live dashboard is indistinguishable from a recycled PID without the cmdline check) is correct and stays. But two behaviours around it are gratuitously bad and fixable **without** touching the kill decision:

1. Stop reports `already_stopped` (success) when the recorded PID is demonstrably still **alive** (`os.kill(pid,0)` succeeds) — it should not claim the dashboard is stopped when it cannot confirm that.
2. Stop **deletes** the metadata for an alive-but-unverified instance, making it unmanageable and destroying the only record of it.

This change makes stop *honest and non-destructive* in that ambiguous case: don't claim stopped, don't delete metadata, and surface a distinct diagnostic so the operator can investigate. The kill path and the zombie/reap behaviour are unchanged.

## Requirements

1. **Detect the ambiguous case.** In `wave_dashboard_stop_response`, after reaping and computing `targets`, when `targets` is empty AND the recorded `pid` is a positive int that is still `os.kill`-alive (`_pid_is_running(pid)` is True) but was NOT added to `targets` (i.e. not cmdline-verified as a dashboard for this root), treat it as **unverified-alive**, distinct from genuinely-stopped.
2. **Do not falsely report stopped, do not delete metadata.** For the unverified-alive case, return `status: "ok"` with `already_stopped: False`, `stopped: False`, the metadata **retained** (not removed), and a distinct diagnostic (e.g. `dashboard_pid_unverified`) explaining: PID N is alive but could not be verified as a dashboard for this repository (it may be a recycled PID owned by another process, or a live dashboard the process scan could not match); it was NOT terminated; investigate and, if it is a stray dashboard, stop it manually.
3. **Preserve the genuinely-stopped path.** When `targets` is empty and the recorded PID is absent or NOT `os.kill`-alive (dead / reaped / no metadata), keep today's clean behaviour: `already_stopped: True` + metadata removed. In particular the `1rswx` zombie path (reaped on entry → PID no longer `os.kill`-alive → genuinely stopped) must still report the clean `already_stopped` + cleared metadata.
4. **Never terminate an unverified PID.** The kill decision is unchanged: only cmdline-verified dashboards for this root (the `targets` set) are passed to `_terminate_dashboard_pid`; the unverified-alive PID is never sent a signal. The security control from `1rswx` AC-3 is preserved.
5. **Restart is unchanged in contract.** `wave_dashboard_restart_response` still proceeds to start when stop returns `status: "ok"` (the unverified-alive case is `ok`), so restart behaviour is not regressed by this change (a scan-miss duplicate remains the pre-existing, port-guarded 1p8pf behaviour — out of scope here).
6. Local-only, stdlib only; no new dependency; POSIX/Windows liveness parity unchanged (`_pid_is_running` already guards Windows).

## Scope

**Problem statement:** `wave_dashboard_stop` reports `already_stopped` and deletes the metadata for a recorded dashboard PID that is still alive but not cmdline-verifiable — a false success plus state loss — instead of surfacing that it could not confirm the stop.

**In scope:**

- The empty-`targets` branch of `wave_dashboard_stop_response` (`server_impl.py`): split "genuinely stopped" from "unverified-alive".
- The new `dashboard_pid_unverified` diagnostic + response shape (`already_stopped: False`, `stopped: False`, metadata retained).
- Tests: unverified-alive returns the honest response and keeps metadata; genuinely-stopped and zombie-reaped paths still report clean `already_stopped` + cleared metadata; the kill path still terminates a cmdline-verified live dashboard; no unverified PID is ever passed to terminate.

**Out of scope:**

- Changing the kill decision or reintroducing bare-liveness termination (that is the `1rswx` AC-3 security control).
- The scan-miss duplicate-on-restart case (pre-existing 1p8pf behaviour; port-guarded).
- Improving the cmdline scan's path-resolution matching so it stops missing live dashboards (a separate, larger change to `dashboard_lib.dashboard_cmdline_pids`).

## Acceptance Criteria

- [x] AC-1: `wave_dashboard_stop` against a repo whose recorded PID is `os.kill`-alive but NOT in the cmdline scan for this root returns `status: "ok"` with `already_stopped: False`, `stopped: False`, a `dashboard_pid_unverified` diagnostic, and the metadata file **still present**. Deterministic test (mock `_dashboard_cmdline_pids=[]`, `_pid_is_running=True`, reap a no-op) asserting `_terminate_dashboard_pid` is never called. Evidence: `test_stop_unverified_alive_pid_reports_honestly`.
- [x] AC-2: The genuinely-stopped path is unchanged — recorded PID absent, or present but NOT `os.kill`-alive, with no scanned pids → `already_stopped: True` + metadata removed. Evidence: `test_stop_genuinely_stopped_dead_pid_clears_metadata`.
- [x] AC-3: The `1rswx` zombie path still yields a clean stop — a registered `<defunct>` recorded PID reaped on entry (no longer `os.kill`-alive) reports `already_stopped: True` + metadata cleared, no `dashboard_pid_unverified` diagnostic. Evidence: `test_stop_on_zombie_recorded_pid_returns_success` (updated to model the reaped zombie as `_pid_is_running=False`, its real post-reap state).
- [x] AC-4: The security control is intact — a genuinely-live, cmdline-verified dashboard for the root is still terminated; the unverified-alive PID is never passed to `_terminate_dashboard_pid`. Evidence: `test_stop_still_kills_live_dashboard`; `term.assert_not_called()` in `test_stop_unverified_alive_pid_reports_honestly`; the kill decision (`targets` → `_terminate_dashboard_pid`) is unchanged.
- [x] AC-5: Full framework tests run bytecode-free and docs validation passes. Evidence: full suite re-run at wave close; docs-lint clean.

## Tasks

- [x] Split the empty-`targets` branch in `wave_dashboard_stop_response` into genuinely-stopped vs unverified-alive (`_pid_is_running(pid)` and not-in-`targets`); add the `dashboard_pid_unverified` diagnostic + retain-metadata response.
- [x] Update the inline stop-path comment (was the accepted-tradeoff note) to describe the honest-report behaviour + the retained security-control note.
- [x] Add/adjust tests: unverified-alive honest response + metadata retained + no terminate; genuinely-stopped unchanged; zombie-reap unchanged; live-verified still terminated.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| stop-honest-report | implementer | — | Split empty-targets branch in `server_impl.py`; new diagnostic |
| tests | qa-reviewer | stop-honest-report | Unverified-alive, genuinely-stopped, zombie-reap, live-verified |


## Serialization Points

- Single-file change in `server_impl.py` (`wave_dashboard_stop_response`); no shared surface with `1rvfx` (upgrade module).

## Affected Architecture Docs

- N/A — a response-shape/behaviour refinement confined to the dashboard stop tool in `server_impl.py`; no module boundary, data-flow, or transport change. The `wave_dashboard_stop` contract gains one additive diagnostic and a corrected `already_stopped` value in a previously-mishandled case.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — stop must not lie or delete state for an alive-but-unverified instance. |
| AC-2 | required | The common genuinely-stopped path must not regress. |
| AC-3 | required | The `1rswx` zombie fix must stay intact. |
| AC-4 | required | The `1rswx` AC-3 security control (never kill an unverified PID) must stay intact. |
| AC-5 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Split from the `1rtnn`/`1rswx` delivery-review MEDIUM accepted-tradeoff, to land before the official 1.11.0 ship (operator direction). Fix targets the false-`already_stopped` + metadata-deletion behaviour, NOT the kill decision. | `1rswx` delivery review; `server_impl.py:7993-7995` empty-targets branch. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Make stop honest (don't claim stopped, don't delete metadata, emit a diagnostic) in the unverified-alive case; leave the kill decision untouched. | The tension "never kill an unverified PID" vs "always terminate a scan-missed live dashboard" is unresolvable without the cmdline scan; the security control wins. But the *false success* + *metadata deletion* are separable and gratuitously harmful — fixing only those keeps the control and removes the bad UX. | Kill any `os.kill`-alive recorded PID (rejected — reintroduces the `1rswx` recycled-PID SIGKILL defect). Abort `restart` on the ambiguous case (rejected for this scope — changes restart's recovery contract and the recycled-PID sub-case still wants a fresh start; the standalone-stop honesty is the win). Improve the cmdline scan to stop missing live dashboards (rejected here — a larger, separate change to `dashboard_lib`). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The unverified-alive branch mis-fires for a genuinely-dead PID and leaves stale metadata behind | The branch is gated on `_pid_is_running(pid)` being True (the PID is demonstrably alive); a dead PID takes the genuinely-stopped path and metadata is cleared as before. |
| A zombie recorded PID reaches the unverified-alive branch and is left as "alive" | `1rswx` reaps registered dashboard children on stop entry, so a `<defunct>` recorded PID is no longer `os.kill`-alive by the time targets are classified → genuinely-stopped path. Covered by AC-3. |
| Callers relying on `already_stopped: True` in the ambiguous case | The prior value was a false positive (the dashboard was still serving); the new `already_stopped: False` + diagnostic is the correct signal. Additive diagnostic; `status` stays `ok` so restart is unaffected. |
| A cross-process, not-yet-reaped zombie (spawned by a now-dead prior server, so NOT in this server's `_DASHBOARD_CHILD_PIDS`) still passes `os.kill(pid,0)` and lands in the new unverified-alive branch (report + keep metadata) rather than the clean already-stopped path (delivery-review note) | Inherent `1rswx` OS-semantics window, unchanged by `1rvfw`: a re-parented zombie is reaped near-instantly by init, closing the window. The behaviour is safe (no kill, honest report); the diagnostic tells the operator to investigate. Not exercised by unit tests without real subprocesses. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
