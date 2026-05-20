# Upgrade Log File

Change ID: `12r21-enh upgrade-log-file`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

The upgrade script runs as a subprocess captured by `wave_upgrade_response`. All output is returned in `data.output` when the phase completes — but the agent and operator have no visibility into what's happening while it runs. For long phases (surface rendering, docs gate on large repos) this is a black box.

Writing all `_log()` / `_err()` output to `.wavefoundry/upgrade.log` in parallel gives real-time progress visibility: `tail -f .wavefoundry/upgrade.log` shows each phase as it completes. The pid for the running upgrade process is already recorded in the lock file (`upgrade-in-progress.json`), so the log + lock together give a complete picture of who is running what and what it's doing.

## Requirements

1. A module-level `_log_file` handle and `_open_log(root, mode)` / `_close_log()` functions manage the log file. `mode="w"` truncates for a fresh upgrade run; `mode="a"` appends for continuation phases (`--rebuild-index`, `--cleanup`).
2. `_log(msg)` and `_err(msg)` both tee to the log file with a `[HH:MM:SS]` timestamp prefix. Stdout output is unchanged (no timestamp, for clean MCP capture).
3. The log file lives at `.wavefoundry/upgrade.log` alongside the lock file. `upgrade_log_path(root)` is a module-level helper returning the canonical path.
4. The log is opened immediately after the lock is written in the full upgrade path. The first two log lines inform the operator where to find it:
   ```
     Upgrade log: /abs/path/.wavefoundry/upgrade.log
     Watch:       tail -f /abs/path/.wavefoundry/upgrade.log
   ```
5. `wave_upgrade_response` pre-creates the log file (empty touch via `Path.touch(exist_ok=True)`) before spawning the subprocess for apply-mode phases. This ensures `log_path` in the response always refers to a real file, even when the upgrade fails before the script opens it itself. The script still manages truncation (`mode="w"`) and appending (`mode="a"`).
6. `wave_upgrade_response` adds `"log_path"` to `data` for `mode="apply"` phases (`null` for `mode="dry_run"`, which writes no log). The path is computed from `root` — not parsed from subprocess stdout.
7. `--rebuild-index` records `index_rebuilt_at` (ISO-8601 UTC) in the lock file via `update_upgrade_lock` after `phase_index_rebuild` completes. `--cleanup` reads `index_rebuilt_at` from the lock to set `ran_index_rebuild=True` accurately in the operator summary.
8. Dry-run writes no log file (it is read-only and synchronous; the output is the point).
9. `_close_log()` is called in the `except SystemExit` cleanup handler and at successful exit, ensuring the handle is always released.
10. `UpgradeLogTests.setUp` calls `_close_log()` defensively on entry (not only in tearDown) to ensure clean global state even if a prior test left a stale handle. `DryRunTests` saves and restores the `_log_file` global around each test so dry-run's `_log()` calls cannot bleed into a log file opened by another test class.

## Scope

**In scope:**

- `scripts/upgrade_wavefoundry.py` — `_log_file`, `_open_log`, `_close_log`, `upgrade_log_path`, updated `_log` / `_err`, wiring in `main()`
- `scripts/server.py` — `log_path` field in `wave_upgrade_response` data
- `tests/test_upgrade_wavefoundry.py` — `UpgradeLogTests` (8 tests)

**Out of scope:**

- Routing child-process stdout (render, docs-gate) through the log — those subprocesses write to their own stdout which is inherited from the upgrade script; they are captured by `wave_upgrade_response` but not individually logged. The log contains framework-level progress messages (phase start/end, hook results, errors, summaries), which is sufficient for watching progress.
- Rotating or size-limiting the log file — upgrade runs are infrequent; the log is truncated at the start of each new full upgrade
- Async upgrade execution — the log is the groundwork for that if needed later

## Acceptance Criteria

- AC-1: `.wavefoundry/upgrade.log` is created when a full upgrade run starts (phases 0–3).
- AC-2: Every `_log()` call writes a timestamped line to the log file.
- AC-3: Every `_err()` call writes a timestamped `ERROR:` line to the log file.
- AC-4: `--rebuild-index` and `--cleanup` append to the existing log.
- AC-5: A fresh full upgrade run truncates the previous log.
- AC-6: `wave_upgrade_response` pre-creates the log file before spawning; `log_path` always refers to a real file for apply-mode phases.
- AC-7: `wave_upgrade_response` returns `log_path` in `data` for apply-mode phases.
- AC-8: After `--rebuild-index` completes, `--cleanup` operator summary shows "Index rebuild: docs layer complete, code layer running in background" rather than "not run".
- AC-9: Dry-run writes no log file.
- AC-10: All existing tests pass; `_log_file` global does not bleed between test classes.

## Tasks

- Add `_log_file`, `upgrade_log_path`, `_open_log`, `_close_log` to `upgrade_wavefoundry.py`
- Update `_log` and `_err` to tee to log file with timestamp
- Wire `_open_log` after lock write in full upgrade path; print watch instruction
- Wire `_open_log(mode="a")` + `_close_log` in `--rebuild-index` and `--cleanup` paths
- Wire `_close_log` in `except SystemExit` handler and success exit
- Add `log_path` to `wave_upgrade_response` data in `server.py`
- Write `UpgradeLogTests`

## Affected Architecture Docs

N/A — new file artifact at a well-known path; no MCP surface or schema change beyond an additive `log_path` field.

## AC Priority

| AC   | Priority  | Rationale                                        |
| ---- | --------- | ------------------------------------------------ |
| AC-1 | required  | Core deliverable                                 |
| AC-2 | required  | Progress visibility                              |
| AC-3 | required  | Error visibility                                 |
| AC-4 | required  | Continuity across upgrade phases                 |
| AC-5 | required  | No stale log from previous run                   |
| AC-6 | required  | `log_path` must always be a real file            |
| AC-7 | required  | Agent needs log path without parsing stdout      |
| AC-8 | required  | `--cleanup` summary must reflect actual rebuild  |
| AC-9 | required  | Dry-run must remain read-only                    |
| AC-10 | required | No regression; no cross-test state bleed        |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented. `_open_log`, `_close_log`, `upgrade_log_path` added; `_log`/`_err` tee with `[HH:MM:SS]` timestamps; lock→log wiring in all three execution paths; `log_path` in server response. Server pre-creates log file. `index_rebuilt_at` added to lock after rebuild; `--cleanup` reads it for accurate summary. Test global isolation fixed. 9 unit tests. 1428 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1428 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Timestamp in log file only (not stdout) | Stdout is captured by `wave_upgrade_response`; timestamps in stdout would clutter `data.output` and change existing test assertions | Timestamp on both (noisier MCP output) |
| 2026-05-19 | `mode="w"` truncates at start of full run | Operator wants to see the current upgrade, not accumulation from previous runs | Append always (makes log hard to read across runs) |
| 2026-05-19 | Log path computed from root in server, not parsed from stdout | Deterministic; avoids fragile stdout parsing; `log_path` is always correct even if the upgrade script's output changes | Parse from stdout (brittle) |
| 2026-05-19 | Log file not written during dry-run | Dry-run is read-only; the output IS the point and it's returned synchronously | Write a dry-run log (adds confusion about what the log file represents) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
