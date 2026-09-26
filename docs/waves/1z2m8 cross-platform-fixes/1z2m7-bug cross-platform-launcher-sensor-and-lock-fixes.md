# Cross-Platform Fixes: Launcher Hint, Sensors, Old Python, Stamp Links and Windows Lock Waits

Change ID: `1z2m7-bug cross-platform-launcher-sensor-and-lock-fixes`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-26
Wave: 1z2m8 cross-platform-fixes

## Rationale

A cross-platform review of the framework changes since v1.25.0 (development is macOS-only, with no Windows or Linux CI) found five defects worth fixing before the 1.27.0 release:

1. **`wf.cmd` misdirects on every failure.** The rendered Windows launcher (`render_platform_surfaces.render_bin_launchers`, shipped in 1.26.0) prints "Wavefoundry command failed. If Python could not start, diagnose this workstation" after any non-zero exit. Ordinary results exit non-zero (`wf docs-lint` finds errors; `wf setup --check` reports `action_required` or `indeterminate`), so Windows agents on the documented no-MCP fallback are told to diagnose Python when Python is fine.
2. **Required phase sensors cannot start `.cmd` tools on Windows.** `lifecycle_gates.required_sensors_gate` requires a list-form command and `sensor_runner.run_sensor` runs it without a shell. Windows `CreateProcess` does not apply `PATHEXT`, so `["npm", "test"]`, `["npx", ...]` or `["pnpm", ...]` fail with WinError 2. The gate is a close hard gate, so close is blocked.
3. **The session-start hook fails on Python older than 3.11.** The rendered `.claude/hooks/wf-session-start.py` runs under whatever `python3` is on PATH and imports `setup_readiness`, which imports `tomllib` (3.11+). On Ubuntu 22.04 (3.10) or the macOS command-line-tools Python (3.9) every session reports `ModuleNotFoundError: tomllib` instead of saying Python is too old.
4. **Setup-stamp adoption needs hard links.** `setup_readiness.write_setup_stamp(exclusive=True)` publishes with `os.link`, which fails on filesystems without hard links (exFAT/FAT, many SMB/NAS shares, VM shared folders, some FUSE mounts), so the baseline is never adopted and every MCP start warns.
5. **Blocking file locks give up after about 10 seconds on Windows.** `runtime_lock.RuntimeFileLock(blocking=True)` uses `msvcrt.LK_LOCK`, which tries ten times at one-second intervals and then fails, where POSIX `fcntl` waits. `index_source_guard` (wait mode) is the new caller that exposes it: an index build raises if a guarded writer holds the guard longer than that.

## Requirements

1. The Windows launcher prints its diagnose-Python hint only when Python itself cannot start: after a non-zero exit it probes `python3 -c "import sys"` and shows the hint only if that probe fails. A command's own non-zero exit passes through with its exit code and no extra text. The renderer and this repository's rendered `.wavefoundry/bin/wf.cmd` stay identical.
2. On Windows, `sensor_runner.run_sensor` resolves a list-form command's first element through `shutil.which` (which honours `PATHEXT`) before running it, when the element names no path. An unresolvable name runs unchanged and fails as today. POSIX behaviour is unchanged. Resolution uses `PATH`, so a wrapper that lives only in the repository root (a `gradlew.bat` not on `PATH`) is still not found; name it with its full path (on Windows a relative path resolves against the MCP server's working directory).
3. The rendered session-start hook checks `sys.version_info` before importing framework modules. On Python 3.7 to 3.10 it prints the readiness header, a reason naming the running version and the 3.11 requirement, and the ask-the-operator line, without a traceback.
4. `write_setup_stamp(exclusive=True)` falls back to an exclusive create (`O_CREAT | O_EXCL`) of the stamp when `os.link` fails for a reason other than the file already existing. First-writer-wins is kept.
5. On Windows, a blocking `RuntimeFileLock` waits until the lock is free, retrying `LK_NBLCK` with a short sleep instead of `LK_LOCK`'s ten-second limit. Non-blocking behaviour is unchanged.
6. `CHANGELOG.md` `[Unreleased]` gains one Fixed bullet per user-visible fix.

## Scope

**Problem statement:** five cross-platform defects found by review, each a wrong result or a hard failure on Windows, Linux or older Python.

**In scope:**

- the five fixes above, their tests, and the changelog.

**Out of scope (backlog):**

- PowerShell-syntax commands in the hook on Windows; `diagnose_python.ps1` under PowerShell 7 (unverified); NTFS junctions in the no-links check; the stricter wrong-case `docs/` check (intended; upgrade note only).

## Acceptance Criteria

- [x] AC-1: the rendered `wf.cmd` shows the diagnose hint only when the `python3` probe fails, and passes a command's own exit code through unchanged; the repository's `.wavefoundry/bin/wf.cmd` matches the renderer.
- [x] AC-2: with Windows behaviour selected, `run_sensor` runs a list command whose first element resolves through `shutil.which` to a `.cmd` path; a name `shutil.which` cannot resolve runs unchanged; non-Windows behaviour is unchanged.
- [x] AC-3: the rendered hook, run under a Python version below 3.11 (simulated), prints the version reason and the ask line and never imports `setup_readiness`.
- [x] AC-4: when `os.link` raises a non-`FileExistsError` `OSError`, an exclusive stamp is still written; when the stamp already exists, the existing one is kept.
- [x] AC-5: with Windows behaviour selected, a blocking lock retries a held lock until it is released rather than failing after a fixed count; non-blocking acquisition still raises `RuntimeLockBusy` at once.
- [x] AC-6: The change's own tests pass and the documents this change edits validate.

## Tasks

- [x] Launcher hint gated on a Python probe (renderer and re-rendered `wf.cmd`).
- [x] Sensor command resolution on Windows.
- [x] Hook Python-version guard.
- [x] Stamp exclusive-create fallback.
- [x] Windows blocking-lock wait loop.
- [x] Tests for AC-1 to AC-5; changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Five fixes | implementer | readiness | Single write owner; independent edits |
| Review | combined reviewer | Five fixes | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/bin/wf.cmd`, `.wavefoundry/framework/scripts/sensor_runner.py`, `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/runtime_lock.py`, `.claude/hooks/wf-session-start.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: each fix is local to one module and changes no boundary or flow; the launcher and hook contracts stay the same.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Wrong guidance on the documented Windows fallback path |
| AC-2 | required | Can block wave close on Windows |
| AC-3 | required | Every session on older Python reports a traceback |
| AC-4 | required | Baseline never adopted on common shared filesystems |
| AC-5 | required | Index builds fail under ordinary contention on Windows |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-26 | Gapfill: implementation read the five target functions through shell reads by default, not as a deliberate choice; the MCP code tools (which the project requires for implementation reads) were not used. The sites had been located by the cross-platform and readiness reviews with the MCP tools, so nothing was missed, but reference checks were skipped and implement-stage retrieval telemetry is zero | Close dry-run advisory; operator question |
| 2026-09-26 | Delivery review approved (no blocking findings); its wording note fixed (a relative sensor path resolves against the MCP server's working directory on Windows). The first full run failed `test_patch_census_has_nonvacuous_runtime_obligations`: the `_IS_WINDOWS` value patch in `test_sensor_runner.py` lacked the required `inert-by-design:` note; added. Full suite then green: 9714 tests across 129 files | `run_tests.py --no-cache` |
| 2026-09-26 | Implemented all five fixes; repo `wf.cmd` and hook re-rendered with `wf render-surfaces` (only those two rendered files changed). New tests: `test_wf_cmd_hints_only_when_python_cannot_start` (includes repo-versus-renderer bytes), `test_sensor_runner.py` (4), `test_exclusive_write_falls_back_when_hard_links_are_unsupported`, `test_older_python_reports_the_version_without_importing_the_framework`, three Windows lock tests. One mutant per fix each fails a test | Focused suites green |
| 2026-09-26 | Readiness review approved (code, qa, red-team, docs-contract); implementation notes adopted: flat batch with immediate string compares and no delayed expansion; Windows-only flags patched in tests; `open(path, "xb")` for the stamp fallback; `LK_NBLCK` loop re-seeking before each attempt; a repo-versus-renderer test for `wf.cmd` | Readiness review |
| 2026-09-26 | Planned from the cross-platform review of v1.25.0..HEAD; items 1, 2 and 3 confirmed against the code before planning | Review report (session) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-26 | Gate the launcher hint on a live `python3` probe rather than on exit codes | `wf` subcommands use exit codes 1 and 2 for ordinary results, so no code range identifies a Python start failure | Hint only on 9009; drop the hint |
| 2026-09-26 | Accept cmd.exe argument parsing for resolved `.cmd` sensors | Sensor argv comes from the repository's own `docs/workflow-config.json`, the same trust level as existing `shell=True` string sensors, so no new exposure | Refuse `.cmd` targets |
| 2026-09-26 | Resolve sensor commands with `shutil.which` on Windows only | Fixes `PATHEXT` without changing POSIX behaviour or adding a shell | Document `["cmd", "/c", ...]`; run sensors through a shell |

## Risks

| Risk | Mitigation |
| --- | --- |
| No Windows machine to run the fixes on | Tests select the Windows branch by patching the platform flag; the launcher change is a line-for-line template edit pinned by renderer tests |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
