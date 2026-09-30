# A Setup Run Counts Only For The Repository It Was Stamped For

Change ID: `1zc7k-bug rootless-setup-pid-attributed-to-any-repository`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1zc7l rootless-setup-status-attribution

## Rationale

Wave `1za2y` made `index_build_status` report the background build as `running` only while the pid in `.wavefoundry/index/background-build.pid` is an index build for this repository. `setup_index.main` stamps that file with its own pid, and under `wf setup` or `wf update-indexes` that pid is the `wf_cli.py` process, which usually names no `--root`. `_pid_is_live_index_build(..., unbound_ok=True)` therefore accepted any live setup-shaped process without a `--root`: if the recorded pid was reused by a `wf setup` running in another repository, this repository's status read `running` until that process exited (finding CR-L1 from the 1za2y delivery review). The lock was never affected; only the status report was wrong.

Wave `1zc7n` (change `1zc7m`) added a start-time guard to the same predicate: `index_handlers._pid_started_after` rejects a process whose start time (`process_info.create_time`) is more than 2 s after the pid file's modification time. The pid file is written while the stamped process owns that pid, so any process that later reuses the pid, including a rootless `wf setup` in another repository, started after the write and reads as completed. That resolves CR-L1.

The residual gap is a reuse within about 2 s of the write, which needs the stamped process to exit and its pid to be handed to another setup-shaped process inside that window: effectively impossible on Linux and macOS (sequential pid allocation), rare on Windows (fast pid recycling), and limited to a wrong status line, never a second build. The originally planned identity stamp (a sibling `background-build.json` with pid, root and exact start time, plus a working-directory fallback) is deferred; see the Decision Log. This change pins the resolution with a regression test so the guard cannot be lost without a failing test.

## Requirements

0. The test runs on Windows, macOS, Linux and WSL2: it uses a real idle process, sets the pid file's modification time with `os.utime`, and depends only on `process_info.create_time`, which `psutil` provides on every supported platform.
1. **Regression test.** With `background-build.pid` naming a live, rootless setup-shaped process (`wf_cli.py setup`, no `--root`) running in another directory, `_background_build_status` returns `running` while the pid file's modification time is current, and `completed` for the same process after the modification time is set an hour back with `os.utime` (simulated pid reuse), so one test isolates the start-time guard.
2. **No production code change.** `setup_index`, `index_handlers` and the stamp format are unchanged.

## Scope

**Problem statement:** CR-L1 is resolved by wave `1zc7n`'s start-time guard but no test names the scenario, so a later edit could drop the guard's effect on the rootless setup case unnoticed.

**In scope:**

- One regression test in `tests/test_server_tools_retrieval.py` `BackgroundBuildStatusTests`.

**Out of scope:**

- The identity stamp `background-build.json`, root comparison and working-directory fallback (deferred; Decision Log).
- `sqlite_storage_migration._process_cwds` (pre-dependency code, stays standard-library per ADR `1z9df-adr psutil-process-info`).

## Acceptance Criteria

- [x] AC-1: a live rootless `wf_cli.py setup` process whose start is later than the pid file's modification time reads `completed` from `_background_build_status`; removing the start-time guard (`_pid_started_after` returning False) makes the test fail.
- [x] AC-2: the change's own test module passes, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the regression test to `BackgroundBuildStatusTests`.
- [x] Mutant check: patch `wf_server.index_handlers._pid_started_after` (not the `server_impl` re-export) to return False and confirm the test fails.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Regression test | implementer | wave `1zc7n` closed | Uses `server_tools_support.spawn_idle_process` |
| Review | code, QA reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

## Affected Architecture Docs

N/A: test-only change; no ownership, data flow or contract changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Pins the CR-L1 resolution |
| AC-2 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | Full framework suite green on a quiet tree (10070 tests, receipt recorded); `BackgroundBuildStatusTests` 11 OK. An earlier run passed every test but tripped the repository-change guard because this doc and the wave record were edited during it. | `run_tests.py --no-cache` |
| 2026-09-29 | Implemented `BackgroundBuildStatusTests.test_a_rootless_setup_that_started_after_the_stamp_is_a_reused_pid`: a live `wf_cli.py setup --background-code` with no `--root` reads `running` with a current pid-file modification time and `completed` after `os.utime` sets it an hour back. Mutant: `_pid_started_after` replaced with a constant False in the loaded `wf_server.index_handlers` globals after `setUpClass` makes the test fail (`running` != `completed`); control passes. A first harness patched the module before `setUpClass`, whose `load_server` re-imports it, so that mutant falsely survived; a probe confirmed the guard decides the case. Gapfill: the change is one test; the guard order was verified by the readiness reviewer through MCP code tools, and the mutant and probe are executed shell work. | `tests/test_server_tools_retrieval.py`; scratch `mutant_1zc7l.py`, `probe_1zc7l.py` |
| 2026-09-29 | Rescoped: operator agreed that wave `1zc7n`'s start-time guard resolves CR-L1; the identity stamp is deferred and this change adds a regression test only. | `wf_server/index_handlers.py` `_pid_started_after`, `_pid_is_live_index_build`, `_background_build_status` |
| 2026-09-29 | Replanned after the `psutil` evaluation (ADR `1z9df-adr psutil-process-info`): operator approved recording identity in the stamp instead of scraping it, and running the `process_info` wave first. The feasibility check found existing readers parse `background-build.pid` strictly as an integer, so identity goes in a sibling file. | ADR `1z9df`; feasibility check of `index_handlers._background_build_status` and `index_build_status` |
| 2026-09-29 | Planned from CR-L1 in the 1za2y delivery review; operator confirmed a separate follow-up. | 1za2y review record |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | Defer the identity stamp; pin the `1zc7n` start-time guard with a regression test | The guard already rejects any reuser that started after the stamp; the remaining window (reuse within about 2 s by another setup-shaped process) is rare and affects only a status line, never the lock | Identity stamp with pid and exact start time only (closes the 2 s window; revisit if Windows reports a stuck `running` after a crashed background build); the full plan with root and working-directory matching (redundant with the guard) |
| 2026-09-29 | Record pid, root and start time when stamping; scrape working directories only for older stamps | The writer knows the root; start time detects pid reuse; works the same on every platform once `process_info` exists | Working-directory lookup only (the first plan; no reuse detection, and Windows needed a dependency anyway) |
| 2026-09-29 | Identity in a sibling `background-build.json`, bare-pid file unchanged | Current readers parse the pid file with `int(text.strip())`; an older loaded server must keep working | Change the pid file to JSON (older servers would read every run as completed) |
| 2026-09-29 | Depend on `process_info` (wave `1zc7n`) rather than adding a helper here | ADR `1z9df-adr psutil-process-info`; one process-information seam | A private `indexer._process_cwd` helper (the first plan) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Coarse file-system timestamps (FAT, 2 s) make the modification time earlier than the write | An earlier time only makes the guard stricter for reusers; the stamped process itself started before the write |
| A pid reused within 2 s of the stamp still reads `running` | Accepted; affects a status line only; the deferred identity stamp closes it if it is ever observed |
| The guard compares the file's modification time with the process start time; on WSL2 with the repository on `/mnt/c` the host sets the modification time while `psutil` reads the guest clock, so drift weakens the guard or marks a live build `completed` | Status-only (the OS lock stays authoritative); inherited from wave `1zc7n`; the deferred identity stamp records the start time itself and removes the clock mismatch |
| Without `psutil` every background pid reads `completed` (liveness is unavailable, so `server_impl._pid_is_running` returns False before the guard) | Status-only; the OS lock decides; the `process_info_unavailable` diagnostic recommends `wf setup` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
