# Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill

Change ID: `1zimk-bug setup-and-server-robustness-gaps`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zime downstream-gap-fixes

## Rationale

A downstream fork reported four robustness gaps as still open at commit `5004296a`, each as a one-line description; the original detailed request is not available. Each was located and confirmed against the current tree before planning:

- **(a) A denied `.env` stat stops the walk.** `indexer.walk_repo` calls `path.is_file()` on every listed name before any filter. On the Python versions this framework supports up to 3.13, `pathlib.Path.is_file` re-raises `PermissionError` (only `ENOENT`, `ENOTDIR`, `EBADF` and `ELOOP` are ignored), so one entry whose stat is denied aborts the whole walk. Reproduced on Python 3.13.5: a repository whose root `.env` is a symlink into a directory with mode `000` raises `PermissionError` out of `walk_repo` at the `is_file` line. `.env` is the realistic case because the walker deliberately includes `.env` and `.env.*` (values are redacted at chunk time) and secret managers commonly provide it as a symlink into a protected location. Every consumer of the walk fails with it: the index build (`wf setup`, upgrade Phase 4, the MCP refresh), `index_health` (`McpRepoCache._layer_current_hashes`), the live docs fallback (`_live_docs_chunks`) and every code navigation tool (`_walk_repo_for_navigation`). The walk already tolerates an unreadable DIRECTORY (wave 1x54z, `unreadable_dirs`), but not an unreadable file entry.
- **(b) An inherited `PROJECT_ROOT` redirects the upgrade's docs gate.** `upgrade_wavefoundry.phase_docs_gate` runs `docs_gardener.py` and `docs_lint.py` with `cwd=root` but the caller's environment. Both scripts resolve their root from `PROJECT_ROOT` first and fall back to the working directory (`docs_gardener.project_root`, `wave_lint_lib.context.build_context`), and neither takes a root argument. So an upgrade run from a shell or host that exports `PROJECT_ROOT` for another repository gardens and lints THAT repository: the gate can pass for the wrong tree, and the gardener writes `Last verified` stamps into it. The MCP paths already pin the variable (`server_impl._run_full_docs_lint` and the post-write lint, `docs_handlers`, `index_handlers` pass `env={**os.environ, "PROJECT_ROOT": str(root)}`); the upgrade gate does not. The rendered post-edit hook's `maybe_docs_lint` (`render_platform_surfaces`, `run_command` with `cwd=REPO_ROOT`) has the same shape.
- **(c) A native crash in the provider probe ends `wf setup` with no explanation.** `setup_index.report_embedding_provider_decision` runs `_probe_embedding_provider` IN-PROCESS: it builds two fastembed `TextEmbedding` sessions (CPU and the candidate, for example CoreML or DirectML) inside the `wf setup` process itself (`wf_cli` dispatches `setup_wavefoundry.main` in-process, which calls `setup_index.main`). A native fault in ONNX Runtime or a provider library (a segmentation fault, an abort, a Windows access violation) kills the whole setup process; Python's `except Exception` cannot catch it, nothing is printed, and `wf setup` simply ends with a signal or NTSTATUS exit code. The same function runs in-process inside the MCP server for `wf_gpu_doctor` (`server_impl` diagnostic report) and in `gpu_doctor.py`, so the same crash would end the server.
- **(d) The dashboard's Windows `taskkill` has no timeout.** `dashboard_handlers._terminate_dashboard_pid` calls `server_impl._mcp_subprocess_run(["taskkill", "/PID", pid, "/T", "/F"], ...)` with no `timeout`, so a `taskkill` that hangs (a stuck process tree, an unresponsive service host) blocks `wf_stop_dashboard` and `wf_restart_dashboard` indefinitely. Waves 1z8tr and 1z822 bounded timed helpers with `run_with_tree_kill`, which `_mcp_subprocess_run` uses only when a timeout is passed; 1zc7n added the start-time pid-reuse guard on this path but left the call untimed. The POSIX branch is already bounded (SIGTERM, 5 s, SIGKILL, 2 s).

All four are local, offline fixes with no new dependency.

## Requirements

1. **A denied file stat is skipped with a diagnostic, never fatal.** In `walk_repo`, an `OSError` raised while classifying a listed file (the `is_file` check) skips that entry instead of propagating. Classification stats the entry directly (`os.stat`, following symlinks) so the result is the same on every supported Python. An `OSError` whose errno or Windows error code is one `pathlib` itself ignores (`ENOENT`, `ENOTDIR`, `EBADF`, `ELOOP`; `winerror` 21, 123, 1921) keeps today's meaning: the entry is not a file and is skipped silently, so a dangling symlink or a file deleted after listing still reads as removed. Any other `OSError` (for example `EACCES` or `EPERM`) marks the entry unreadable. A successful stat of something that is not a regular file is skipped silently, as today. Skipped entries are collected like unreadable directories: the root-relative path is added to a new optional `unreadable_files` set parameter when the caller passes one, and one stderr line per walk names the count and the paths (bounded the same way as `_describe_unreadable_dirs`), never stdout, since the walk runs in-process in the MCP server. The behaviour is the same on every supported Python, including versions whose `is_file` swallows the error and returns False: an entry the walk cannot stat is reported, not silently dropped. The filter logic is otherwise unchanged (no `WALKER_VERSION` bump).
2. **A skipped file is "not walked", not "deleted".** Every consumer that honours `unreadable_dirs` treats an unreadable file the same way, matched by exact path:
   - the incremental change-detection carry-forward in `_build_index_locked` (`_walk_shadowed`);
   - the `storage_rebuild` refusal and `preflight_rebuild_sources`, which raise `storage_rebuild_source_unreadable` naming the file;
   - `_validate_prepared_removals`;
   - the canonical eligibility reap;
   - `_plan_orphan_store_reconcile`;
   - the graph merge's `unreadable_dirs` input.

   `_shadowed_by_unreadable` already matches an exact path. The build may pass the union of unreadable directories and files to these existing parameters, while `walk_repo` reports the two kinds separately to stderr. Stored rows, layer hashes and bookkeeping for the file are kept only while its stat is denied.
3. **The upgrade's docs gate is pinned to the target root.** `phase_docs_gate` runs both children with `env={**os.environ, "PROJECT_ROOT": str(root)}` (the pattern the MCP lint paths already use), so an inherited `PROJECT_ROOT` (or `REPO_ROOT`, which neither child reads) cannot redirect either one. The rendered post-edit hook's docs-lint spawn sets `PROJECT_ROOT` to its `REPO_ROOT` the same way. No other root resolver changes.
4. **The provider probe runs in a child process.** `_probe_embedding_provider` keeps its signature and result type, but runs the measurement (both sessions, the CoreML temp-directory retry, the shape, finiteness and speedup checks) in a child Python process started through `subprocess_util.run_with_tree_kill` with a bounded timeout (constant `PROVIDER_PROBE_TIMEOUT_SECONDS`, 600 s), stdin closed and output captured, returning the result as one JSON line. The child is spawned through `setup_index`'s existing call-time resolver (`_run_install_step`, which falls back to `isolated_run`), consistent with the 1z8tr routing census. The parent maps the outcome to a `ProviderProbeResult`:
   - a clean exit with a parseable result: that result;
   - death by a signal (negative return code on POSIX): not accepted, reason `provider probe crashed (signal N, NAME)`;
   - a Windows crash code (a return code at or above `0xC0000000`): not accepted, reason `provider probe crashed (exception code 0xXXXXXXXX)`;
   - any other non-zero exit, an unparseable result, or the timeout: not accepted, reason naming the exit code or the timeout and the last lines of the child's stderr.
   A rejected candidate leaves CPU selected exactly as an ordinary probe failure does today, so setup continues, and the existing decision line and remediation are printed. The child enables `faulthandler` so a native fault leaves a Python-level trace in the captured stderr. `wf_gpu_doctor` and `gpu_doctor.py` use the same function and so gain the same isolation; in the MCP server the child never inherits the JSON-RPC stdout. The child writes its result as the last stdout line, prefixed `WF_PROBE_RESULT `. The parent parses only that line and echoes the child's other stdout lines with `print`; inside `wf_gpu_doctor` the existing `redirect_stdout(sys.stderr)` sends them to stderr. The measurement stays in one in-process function that the child calls. That function keeps `venv_bootstrap.disable_onnxruntime_telemetry()` before the `fastembed` import and stays serial (no `parallel=`).
5. **The dashboard `taskkill` is bounded.** `_terminate_dashboard_pid` passes a timeout (10 s, matching `subprocess_util._kill_process_tree`) to `_mcp_subprocess_run`; a `subprocess.TimeoutExpired` is caught and the function returns whether the pid is still running (`not _pid_is_running(pid)`), so the stop reports "not stopped" instead of hanging, and the existing not-stopped diagnostics apply.
6. **Platforms.** Windows, macOS, Linux and WSL2:
   - (a) the stat-denial handling is platform-neutral. On POSIX the trigger is a symlink into, or an entry inside, a directory without search permission; on Windows a denied ACL (a broken reparse point is absence, not denial). Paths are reported with `/` separators on every platform.
   - (b) an environment variable set for a child process, identical on every platform.
   - (c) on POSIX a crash is a negative return code and a signal name from `signal.Signals`; on Windows a crash is an NTSTATUS code; WSL2 behaves as Linux. The child uses `run_with_tree_kill`, which ends the child's whole tree on timeout on every platform.
   - (d) changes only the Windows branch; the POSIX branch is unchanged.

## Scope

**Problem statement:** four reported robustness gaps let one denied stat, one inherited environment variable, one native crash or one hung helper abort or misdirect setup, upgrade, indexing or dashboard control without a usable diagnostic.

**In scope:**

- `indexer.walk_repo` and the reconcile callers named in Requirement 2.
- `upgrade_wavefoundry.phase_docs_gate`; the rendered post-edit hook's docs-lint spawn in `render_platform_surfaces` (and its re-rendered surfaces).
- `setup_index._probe_embedding_provider` and its child entry point.
- `dashboard_handlers._terminate_dashboard_pid`.
- Tests for each; the `test_tree_kill_routing` timed-call census entries for the two new timed calls; CHANGELOG `## [Unreleased]` bullets.

**Out of scope:**

- Consolidating the several root resolvers (`repo_root`, `docs_gardener.project_root`, `wave_lint_lib.context`, `render_platform_surfaces.discover_repo_root`) into one; only the spawn sites are pinned.
- Adding a `--root` argument to `docs_lint.py` or `docs_gardener.py`.
- Changing which files the walker includes (`.env` stays included and redacted).
- The MCP server process's own exit behaviour on a tool exception (FastMCP already converts it into an error result).

## Acceptance Criteria

- [x] AC-1: a repository whose `.env` is a symlink into a directory without search permission (POSIX test; skipped on Windows with a reason) walks without raising: `walk_repo` returns the other files, the caller's `unreadable_files` set contains `.env`, one stderr line names it, and stdout is empty. The test fails on the unfixed walker with `PermissionError`.
- [x] AC-2: with the stat of a previously indexed file denied, an incremental build keeps that file's stored rows (the file is not reported as removed); a test drives the build's reconcile path and fails if the rows are removed. A second test replaces a previously indexed file with a dangling symlink and shows its rows ARE removed.
- [x] AC-3: an upgrade docs gate run with `PROJECT_ROOT` set to a second scratch repository gardens and lints only the target root: the second repository (a git repository with an uncommitted doc carrying an old `Last verified` date, so the unfixed gate would restamp it) is unchanged (no `Last verified` restamp) and a lint failure planted only in the target fails the gate. The test fails when `phase_docs_gate` passes the inherited environment. The rendered hook's spawn is checked to pass `PROJECT_ROOT` equal to its `REPO_ROOT`.
- [x] AC-4: a probe child that dies by a signal (POSIX test with a fake child that kills itself with `SIGSEGV`), one that exits with a Windows crash code (simulated return code), one that exits non-zero, one that prints no parseable result and one that exceeds the timeout each yield a not-accepted `ProviderProbeResult` whose reason names the signal, code, exit status or timeout. `report_embedding_provider_decision` then selects CPU and returns normally. With the child seam reverted to in-process execution, the signal case kills the test's own child process instead of returning.
- [x] AC-5: the probe child's real path still accepts or rejects a provider exactly as before for CPU-only hosts (no candidate probed) and, where an accelerated provider is available, returns the same result shape (accepted flag, reason, timings); the JSON round trip is pinned by a unit test of the parent's parser.
- [x] AC-6: on the Windows branch (`os.name` patched to `nt` on the module under test, as `test_tree_kill_routing` does), `_terminate_dashboard_pid` passes a timeout to `_mcp_subprocess_run`, and a `TimeoutExpired` returns False while the pid still runs and True once it is gone, never raising. The timed-call census lists the new call.
- [x] AC-7: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Retarget the tests that depend on the in-process probe to the measurement function: `GpuDoctorProbeSerialTests` and the fake-`TextEmbedding` probe tests in `test_setup_index.py`, and in `test_onnxruntime_telemetry.py` the `EXPECTED_SCOPES` `setup_index.py` entry and `test_setup_index_probe_embedding_provider`.
- [x] Walker: catch `OSError` around the per-entry stat classification, collect `unreadable_files`, print one stderr line; thread the set through the reconcile callers that honour `unreadable_dirs`.
- [x] Upgrade docs gate: pass `PROJECT_ROOT` to both children; set it in the rendered hook's docs-lint spawn and re-render the platform surfaces.
- [x] Provider probe: move the measurement into a child entry point in `setup_index.py` (JSON result on stdout, `faulthandler` enabled), run it through `run_with_tree_kill` with `PROVIDER_PROBE_TIMEOUT_SECONDS`, map signal, crash-code, exit, parse and timeout outcomes to a not-accepted result.
- [x] Dashboard: bound `taskkill` with a 10 s timeout and handle `TimeoutExpired`.
- [x] Census: add the two timed calls to `test_tree_kill_routing`'s expected map (the probe spawn keyed on `_run_install_step` as the callee, the dashboard `taskkill` on `_mcp_subprocess_run`).
- [x] Tests for AC-1 through AC-6.
- [x] CHANGELOG `## [Unreleased]` `### Fixed` bullets for the four gaps.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Walker stat denial | implementer | readiness | indexer only |
| Upgrade docs gate root | implementer | readiness | upgrade and hook render |
| Provider probe child | implementer | readiness | setup_index; coordinate with wave 1zimd on the same file |
| Dashboard taskkill bound | implementer | readiness | dashboard handler |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/wf_server/dashboard_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`, `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`
- `.wavefoundry/framework/scripts/tests/test_onnxruntime_telemetry.py`
- `docs/architecture/data-and-control-flow.md`, `docs/architecture/graph-index-system.md`, `docs/architecture/chunking-and-indexing-pipeline.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` item 15: the walk's unreadable report and change detection now cover a file whose stat is denied, matched by exact path, as well as unreadable directories. `docs/architecture/graph-index-system.md`, where it names `GraphIndexSession(unreadable_dirs=...)`. `docs/architecture/chunking-and-indexing-pipeline.md` provider-selection item 2: the initial bounded provider probe also runs in a crash-isolated child, and a native crash or timeout rejects the candidate and leaves CPU selected.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported crash; one denied stat must not abort every walk consumer |
| AC-2 | required | Skipping must not turn into deleting stored rows |
| AC-3 | required | The gate must validate the tree being upgraded and never write into another |
| AC-4 | required | A native crash must be reported and setup must continue on CPU |
| AC-5 | important | The child must not change probe outcomes on healthy hosts |
| AC-6 | required | A stop must never hang the MCP tool call |
| AC-7 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery-review repair (implementer B, `server_impl`): `index_health` no longer reports a file the build kept while its stat is denied as removed or stale. `McpRepoCache._layer_current_state` passes both unreadable sets to `walk_repo` and `_layer_health` leaves those paths (and paths under unreadable directories) out of the comparison; a genuinely removed file is still reported. Test `LayerHealthFileMetaTests.test_unreadable_paths_are_neither_removed_nor_stale`; mutants K1 and K2 killed | `scratchpad/1zime-B-repair-mutations.txt` |
| 2026-10-01 | Delivery-review repair round. (1) `walk_repo` now runs every path- and name-based filter (hard-coded excludes, dot directories, name layer, extension layers, ignore files) before the entry stat, through the new `_walk_entry_is_regular_file`; only the content sniff and the size cap follow it, so a gitignored denied entry (a `server.pem` symlink into a protected directory) is never stat'ed, reported or allowed to block `preflight_rebuild_sources` or a storage rebuild. The ignore check moved above the content sniff, which changes no result because both only exclude. The optional "denied entry with no stored rows is absent for a storage rebuild" alternative was NOT taken: filter order alone removes the reported false block, and the strict census stays fail-closed for any non-ignored denied entry. (2) Added the probe-child venv-activation assertion and the `0xC0000000` crash-code boundary test. Scratch mutations: stat-before-filters, removed child activation and `>=` to `>` each fail a named test | `WalkEntryClassificationTests.test_ignored_denied_entry_is_never_stated_or_reported`, `WalkStatDenialReconcileTests.test_ignored_denied_entry_neither_reports_nor_blocks_the_rebuild` (`test_indexer.py`); `ProviderProbeChildIsolationTests.test_child_entry_activates_the_tool_venv_and_writes_the_last_line`, `ProviderProbeChildIsolationTests.test_crash_code_boundary` (`test_setup_index.py`) |
| 2026-10-01 | Implemented all four fixes test-first. (a) `walk_repo` classifies each entry with `os.stat`; absence errnos and winerrors 21/123/1921 stay silent, any other `OSError` goes to the new `unreadable_files` set and one stderr line; the build, `preflight_rebuild_sources` and `_validate_prepared_removals` pass the union to the existing `unreadable_dirs` consumers. (b) `phase_docs_gate` and the rendered hooks' `run_command` pin `PROJECT_ROOT` to the checked root; surfaces re-rendered. (c) `_probe_embedding_provider` spawns `_measure_embedding_provider` in a child through `_run_install_step` (600 s, stdin closed, `faulthandler`, `WF_PROBE_RESULT ` last line) and maps signal, crash code, exit, parse and timeout outcomes to a rejected candidate. (d) dashboard `taskkill` bounded at 10 s; two census entries added. Each new test failed on the unfixed code (AC-1 `PermissionError`, AC-2 rows lost to `PermissionError` in the build, AC-3 other repository restamped and gate passed, AC-4 the caller died with -11, AC-6 no timeout and `TimeoutExpired` raised) | `WalkStatDenialTests`, `WalkEntryClassificationTests`, `WalkStatDenialReconcileTests` (`test_indexer.py`); `DocsGateProjectRootPinTests` (`test_upgrade_wavefoundry.py`); `ProviderProbeChildIsolationTests` (`test_setup_index.py`); `DashboardTaskkillBoundTests` (`test_dashboard_server.py`); `test_tree_kill_routing.py` census |
| 2026-10-01 | Planned from the downstream report (one-line descriptions only). Verified: (a) reproduced, `walk_repo` raises `PermissionError` at `path.is_file()` for a `.env` symlink into a mode-000 directory on Python 3.13.5; (b) `phase_docs_gate` spawns without an env override while `docs_gardener.project_root` and `wave_lint_lib.context.build_context` read `PROJECT_ROOT` first; (c) `report_embedding_provider_decision` runs `_probe_embedding_provider` in the `wf setup` process, which `wf_cli._dispatch` runs in-process; (d) `_terminate_dashboard_pid` calls `_mcp_subprocess_run` for `taskkill` without `timeout` | `indexer.py`, `upgrade_wavefoundry.py`, `setup_index.py`, `wf_server/dashboard_handlers.py`; scratch reproduction |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Treat (a) as a walker defect for any denied file stat, with `.env` as the reported instance | The fault is at the per-entry `is_file` that runs before any filter, so every file shape is affected; fixing only `.env` would leave the same crash for any other entry | Special-case `.env` (narrower, leaves the defect) |
| 2026-10-01 | Interpret "stops the server" as "stops the server's walk consumers" (assumption) | FastMCP converts a tool exception into an error result, so the process keeps running in the code as read; but indexing, `index_health`, navigation and the docs fallback all fail on every call, which is what an operator observes as the server not working. The process exit could not be reproduced because the server refuses to start in an un-set-up scratch repository | Reproduce against a fully set-up scratch copy during implementation; if the process does exit, extend AC-1 to the server |
| 2026-10-01 | Pin `PROJECT_ROOT` at the spawn sites rather than scrub it or add `--root` | Matches the pattern the MCP lint paths already use; the children keep their single resolver; scrubbing would fall back to the working directory, which is already the root but is a weaker contract | Add `--root` to both scripts (larger surface, every caller changes) |
| 2026-10-01 | Run the provider probe in a child rather than install a signal handler | A native fault cannot be recovered in-process; a child is the only way to report it and continue. It also protects the MCP server, which runs the same probe for `wf_gpu_doctor` | `faulthandler` alone (prints a trace but still kills setup) |
| 2026-10-01 | A fixed 600 s probe timeout constant, not a new config key | First-time CoreML compilation can take minutes; a constant keeps the change free of new configuration until a host needs it | A `setup.provider_probe_timeout_seconds` key in workflow-config |

## Risks

| Risk | Mitigation |
| --- | --- |
| The probe child cannot see the same model cache, provider libraries or environment as the parent, changing the selected provider | The child inherits the parent environment and interpreter (`sys.executable`); AC-5 pins the result shape and the CPU-only path; manual check on an Apple Silicon host that CoreML is still selected |
| Two sessions are built twice (once per child) and setup gets slower | One child per probed provider, as today; CUDA still bypasses the probe |
| A file skipped for a denied stat leaves stale index rows indefinitely | The stderr line names it on every walk; rows are only kept while the stat is denied and reconcile normally once it succeeds |
| Wave 1zimd edits `setup_index.py` and its tests concurrently | Serialization point declared; rebase on whichever lands first |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
