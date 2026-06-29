# Complete subprocess isolation across the framework

Change ID: `1p8gu-bug windows-subprocess-isolation-complete`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8gx windows-upgrade-hardening`

## Rationale

Wave 1p88t isolated **MCP-reachable** subprocesses (`stdin=DEVNULL` + `CREATE_NO_WINDOW`), but left the **setup/upgrade/index/graph/secrets pipeline** spawns uncovered. A real native-Windows 1.9.4 upgrade surfaced the gap as two field defects: (a) a **stack of flashing console windows** (each unisolated child `python.exe` opens its own console) and (b) the **upgrade hanging** (a child that inherits the host console's stdin blocks). Of **75** framework subprocess spawns, only `server_impl` (MCP), `secrets_validators`, `dashboard_lib`, and `provider_policy` are isolated; the pipeline spawns in `upgrade_wavefoundry.py` (`:1192/:1247/:1277/:1300/:1314/:1349/:1368/:1379/:1413`), plus `setup_index`, `indexer`, `graph_indexer`, `scan_secrets`/`run_secrets_scan`, and `gen_codebase_map`, are bare. The no-window logic is also **duplicated across 4 modules** (`_no_window_creationflags`/`_windows_no_window_flag` in dashboard_lib/provider_policy/secrets_validators/server_impl) — a drift hazard.

**Universality (operator clarification):** the fix must guarantee that **no console window ever appears for a framework-initiated subprocess on Windows, regardless of how the framework code was reached** — the MCP server, the `wf` CLI dispatcher, a direct `python <script>.py` run, or an agent invoking `wf <subcommand>` directly. The field stack came from the upgrade pipeline, but the same per-spawn gap exists on every wf-dispatched and directly-invoked path; this change closes all of them, not just the pipeline.

## Requirements

1. ONE shared subprocess-isolation helper (consolidating the 4 duplicated copies) providing: `stdin` detached (`DEVNULL`) by default, `CREATE_NO_WINDOW` on Windows, and intentional stdout/stderr — usable for both `subprocess.run` and `subprocess.Popen`.
2. **Every** framework subprocess spawn — reachable from **any** entry point (the MCP server, the `wf` CLI dispatcher, a direct `python <script>.py` run, or an agent invoking `wf <subcommand>`) — routes through the shared helper, or documents a must-inherit exception inline. The guarantee is **call-path-independent: no framework-initiated subprocess ever creates or shows a console window on Windows, and none inherits a blocking stdin** — not just the upgrade pipeline.
3. The duplicated isolation helpers collapse to the single shared source (anti-drift; a test asserts no second copy).
4. Background `Popen` launchers (the code-index launchers at `:1349`/`:1413`) get the no-window + detached-stdin treatment while keeping their existing log-file stdout/stderr redirection.
5. The `wf`-invoked path is explicitly covered: scripts run via `wf <subcommand>` spawn their children window-free through the helper, AND the `wf` shim (`.wavefoundry/bin/wf` / `wf.cmd`) / dispatcher launch is validated on Windows not to flash a console when an agent invokes `wf` directly (adopt a no-console launch strategy if the shim itself pops a window).

## Scope

**Problem statement:** subprocess isolation is incomplete and **call-path-dependent** — 1p88t hardened only MCP-reachable spawns, so the setup/upgrade/index/graph/secrets pipeline AND every `wf`-dispatched / directly-invoked path can flood Windows with console windows and hang on inherited stdin. The fix must guarantee **no window ever, from any entry point**.

**In scope:**

- The shared isolation helper + consolidation of the 4 duplicates.
- Auditing and routing **all** framework spawns through it: `upgrade_wavefoundry`, `setup_index`, `indexer`, `graph_indexer`, `scan_secrets`/`run_secrets_scan`, `gen_codebase_map`, the docs-gardener/docs-lint launchers, `server_impl`, `dashboard_lib`, `provider_policy`.
- The `wf`-invoked path: the `wf` dispatcher's dispatched code spawns through the helper, and the `wf` shim (`.wavefoundry/bin/wf` / `wf.cmd`) launch is validated window-free on Windows when invoked by an agent.
- A non-vacuous source-scan guard over **all** framework scripts.

**Out of scope:**

- The encoding/path fixes (sibling `1p8gv-bug windows-cli-encoding-and-path-robustness`) — though both touch the same `subprocess.run` calls (see Serialization).
- Changing what the subprocesses do; non-spawn console behavior.

## Acceptance Criteria

- [x] AC-1: a single shared isolation helper exists; the 4 duplicated `_no_window_creationflags`/`_windows_no_window_flag` copies are removed in favor of it (anti-duplication test). — `subprocess_util.py` (`no_window_creationflags`/`detached_background_creationflags`/`isolated_run`/`isolated_popen`); dups removed from `dashboard_lib`, `provider_policy`, `secrets_validators`; `server_impl._windows_no_window_flag` is now a thin delegating alias. Guard: `FrameworkWideSubprocessIsolationGuard.test_single_shared_isolation_helper_no_duplicates`.
- [x] AC-2: every framework subprocess spawn (excluding documented must-inherit exceptions) passes detached stdin (`stdin=DEVNULL` or `input=`) AND the Windows no-window creationflags **regardless of entry point (MCP / `wf` dispatch / direct / agent)**; a source-scan guard test enforces this over **all** framework scripts and fails when a new bare spawn is added. — AST-SCOPED guard rebuilt after adversarial review: `test_every_framework_spawn_isolates_stdin_and_suppresses_window` checks each spawn Call's OWN kwargs (not a text window), resolves aliased/`from subprocess import`/`os.system`/`asyncio` spawn forms, and `test_guard_detects_planted_bare_and_aliased_spawns` proves it FAILS on planted bare/aliased/from-import/os.system spawns. **NEW — process POOLS** (the operator's actual flashing-window defect): `test_every_process_pool_uses_windowfree_helper` requires every `ProcessPoolExecutor`/`Pool`/`Process` to route its mp context through `subprocess_util.windowless_mp_context` (pythonw.exe → console-free workers on Windows; falls back to serial/threads when pythonw is absent). Wired at graph_indexer + secrets_validators (server_impl has no real PPE — its docstring mention is the run_secrets_scan subprocess; indexer uses only ThreadPoolExecutor). `_PARALLEL_EXTRACTION_BACKEND` default reconciled `processes`→`threads` (MP-2: it took the spawn-window path by default). `test_guard_detects_planted_process_pool` proves the pool guard is non-vacuous.
- [x] AC-3: the upgrade/setup/index/graph/secrets pipeline spawns specifically are covered (named-file assertions for `upgrade_wavefoundry`, `setup_index`, `indexer`, `graph_indexer`, `scan_secrets`, `gen_codebase_map`). — `test_pipeline_files_route_through_shared_helper`.
- [x] AC-4: background `Popen` launchers keep their log-file redirection while adding no-window + detached stdin. — both upgrade launchers + setup_index/dashboard_server launchers route through `isolated_popen`; `test_background_popen_launchers_keep_logfile_and_add_isolation`.
- [x] AC-5: full framework suite + docs-lint pass. — `run_tests.py`: 3611 tests across 38 files OK; `docs_lint.py`: ok.
- [~] AC-6: the `wf`-invoked path is window-free — a test asserts `wf`-dispatched code routes child spawns through the shared helper; the `wf` shim launch is confirmed not to flash a console when an agent invokes `wf` (Windows-validation note). — Code side DONE: the `wf_cli` re-exec fallback routes through `isolated_run`, and all `wf`-dispatched targets (run in-process) spawn children through the shared helper (covered by the framework-wide guard). The `wf` SHIM launch itself (`.wavefoundry/bin/wf` POSIX / `wf.cmd` Windows, rendered by `render_platform_surfaces`) is a host process-creation concern not expressible/observable in POSIX tests — **Windows-repro-gated**: confirm on a native Windows host that invoking `wf <subcommand>` does not flash a console (the shim launches `python3`, which when launched from an existing console inherits it; a GUI-agent-spawned `wf` may need `CREATE_NO_WINDOW` at the host's spawn boundary, outside framework code).

## Tasks

- [x] Extract/consolidate the shared isolation helper into one module; remove the 4 duplicates.
- [x] Audit all 75 spawns; route each through the helper or add stdin + creationflags; document any must-inherit exception inline.
- [x] Extend the source-guard test from `server_impl`+`secrets` to all framework scripts.
- [x] Full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| shared isolation helper + consolidation | implementer | — | one module; remove the 4 dup copies |
| audit + route all 75 spawns | implementer | shared helper | document must-inherit exceptions |
| source guard over all scripts | qa-reviewer | audit | non-vacuous; named-file pipeline assertions |

## Serialization Points

- The shared helper must land before the spawn-routing audit.
- Coordinate with `1p8gv`: both edit the SAME `subprocess.run` calls in `upgrade_wavefoundry.py` / `setup_index` (this change adds stdin+creationflags; `1p8gv` adds `encoding=`). Land this helper first; fold the encoding kwarg into the shared helper or add it in `1p8gv` on top.

## Affected Architecture Docs

`docs/references/native-windows-support.md` (the subprocess-isolation story extends from MCP-reachable to the full pipeline). Architecture hub / ADR `N/A` — generalizes an existing pattern, no new boundary.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | One helper is the anti-drift contract. |
| AC-2 | required | The guard is what prevents regression of the field defect. |
| AC-3 | required | The pipeline spawns are the ones that broke. |
| AC-4 | important | Background launchers also flash/hang. |
| AC-5 | required | Regression safety. |
| AC-6 | required | The wf-invoked path is the operator's explicit "no window regardless of how it's called" requirement. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from a real native-Windows 1.9.4 upgrade (flashing console-window stack + upgrade hang). | 75 spawns; only server_impl/secrets/dashboard/provider isolated; pipeline spawns bare. |
| 2026-06-27 | Implemented. Created `subprocess_util.py` (shared isolation: `no_window_creationflags`, `detached_background_creationflags`, `isolated_run`, `isolated_popen` — stdin=DEVNULL default, Windows no-window/detached creationflags, UTF-8 capture folded in for 1p8gv). Consolidated the 4 dup helpers (dashboard_lib/provider_policy/secrets_validators removed; server_impl alias delegates). Routed all pipeline spawns: `upgrade_wavefoundry` (9), `setup_index` (venv-create/probe/uv/install + 2 Popen), `indexer` (tasklist+pip), `graph_indexer` (git+sysctl), `scan_secrets`/`run_secrets_scan` (sysctl), `dashboard_lib` (6 git/ps/powershell), `dashboard_server` (daemon Popen), `provider_policy` (2), `secrets_validators` (8), `venv_bootstrap` (inline — stdlib-only contract), `wf_cli` re-exec, and the `render_platform_surfaces` hook-body templates incl. the session-capture hook. Remaining inline-isolated raw spawns documented. `build_pack.py`/`run_tests.py` are dev-host-only (pack-excluded) documented exceptions. | AST audit: 0 unisolated non-exempt spawns. Guard tests in `FrameworkWideSubprocessIsolationGuard`. Full suite OK. |
| 2026-06-27 | Adversarial-review fixes (BLOCKER MP-1/MP-2 + GUARD generalization). The per-spawn helpers did NOT cover the multiprocessing POOLS — the operator's actual flashing-window stack. Added `subprocess_util.windowless_mp_context`/`configure_windowless_mp_context`/`windowless_pythonw` (point the spawn pool's executable at console-free `pythonw.exe` on Windows; None → caller serial/thread fallback). Wired at graph_indexer ProcessPoolExecutor + secrets_validators ProcessPoolExecutor. Reconciled `_PARALLEL_EXTRACTION_BACKEND` default `processes`→`threads` (MP-2). Corrected the false "no ProcessPoolExecutor" comment in indexer.py (MP-4). Rebuilt the guard: AST-scoped per-Call kwargs, alias/from-import/os.system/asyncio detection, NEW pool guard, planted-defect regressions (GUARD-1/2/5), and a render-time scan over all 5+ rendered hook bodies (GUARD-4). | New guard methods + `test_every_process_pool_uses_windowfree_helper`; pool helper proven None-on-nt-without-pythonw. Full suite 3611 OK. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | One shared helper for all spawns. | 1p88t's per-site approach left gaps + duplicated the no-window logic 4×. | Per-site fixes again (rejected: same gap recurs). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A spawn genuinely needs to inherit stdin (interactive). | Audit each; document + exempt explicitly; the guard allows `input=`/documented exceptions. |
| Source guard is vacuous if it only scans server_impl. | Scan ALL framework scripts; named-file pipeline assertions. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
