# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-27

wave-id: `1p8gx windows-upgrade-hardening`
Title: Windows Upgrade Hardening

## Objective

Make the native-Windows upgrade/setup path robust. A real 1.9.4 upgrade on Windows flashed a stack of console windows, hung on inherited stdin, crashed on a `/tmp` fallback and on a cp1252-unencodable `⚠`, emitted garbled output, and mis-audited the install log. When this wave closes, the Windows upgrade runs window-free, non-hanging, and crash-free, with correct output and install-audit. Expedited toward 1.9.5 because three of these defects genuinely break the upgrade on Windows.

## Changes

Change ID: `1p8gu-bug windows-subprocess-isolation-complete`
Change Status: `implemented`

Change ID: `1p8gv-bug windows-cli-encoding-and-path-robustness`
Change Status: `implemented`

Change ID: `1p8gw-bug install-audit-log-format-mismatch`
Change Status: `implemented`

Change ID: `1p8gz-enh wf-gpu-doctor-subcommand`
Change Status: `implemented`

Change ID: `1p8kz-bug upgrade-summary-surfacing-and-mcp-handler-readiness`
Change Status: `implemented`

Completed At: 2026-06-28

## Wave Summary

Wave `1p8gx` (Windows Upgrade Hardening) delivered 5 changes: Complete subprocess isolation across the framework, Windows CLI encoding + path robustness, wave_install_audit / install-log format mismatch, Add a `wf gpu-doctor` subcommand, and Surface the wave_upgrade summary on the primary phase + fix MCP handler_not_ready. Notable adjustments during implementation: Complete subprocess isolation across the framework: Implemented. Created `subprocess_util.py` (shared isolation: `no_window_creationflags`, `detached_background_creationflags`, `isolated_run`, `isolated_popen` — stdin=DEVNULL default, Windows no-window/detached creationflags, UTF-8 capture folded in for 1p8gv). Consolidated the 4 dup helpers (dashboard_lib/provider_policy/secrets_validators removed; server_impl alias delegates). Routed all pipeline spawns: `upgrade_wavefoundry` (9), `setup_index` (venv-create/probe/uv/install + 2 Popen), `indexer` (tasklist+pip), `graph_indexer` (git+sysctl), `scan_secrets`/`run_secrets_scan` (sysctl), `dashboard_lib` (6 git/ps/powershell), `dashboard_server` (daemon Popen), `provider_policy` (2), `secrets_validators` (8), `venv_bootstrap` (inline — stdlib-only contract), `wf_cli` re-exec, and the `render_platform_surfaces` hook-body templates incl. the session-capture hook. Remaining inline-isolated raw spawns documented. `build_pack.py`/`run_tests.py` are dev-host-only (pack-excluded) documented exceptions.; Complete subprocess isolation across the framework: Adversarial-review fixes (BLOCKER MP-1/MP-2 + GUARD generalization). The per-spawn helpers did NOT cover the multiprocessing POOLS — the operator's actual flashing-window stack. Added `subprocess_util.windowless_mp_context`/`configure_windowless_mp_context`/`windowless_pythonw` (point the spawn pool's executable at console-free `pythonw.exe` on Windows; None → caller serial/thread fallback). Wired at graph_indexer ProcessPoolExecutor + secrets_validators ProcessPoolExecutor. Reconciled `_PARALLEL_EXTRACTION_BACKEND` default `processes`→`threads` (MP-2). Corrected the false "no ProcessPoolExecutor" comment in indexer.py (MP-4). Rebuilt the guard: AST-scoped per-Call kwargs, alias/from-import/os.system/asyncio detection, NEW pool guard, planted-defect regressions (GUARD-1/2/5), and a render-time scan over all 5+ rendered hook bodies (GUARD-4).; Windows CLI encoding + path robustness: Adversarial-review fixes (BLOCKER F1 + F2/F3/GUARD-3). ROOT CAUSE of the AC-4 garble found: the spawned index CHILD owned a cp1252 stdout (only the parent had been reconfigured) → `→` crash, silent index fail. Added `subprocess_util.utf8_child_env` (PYTHONUTF8=1 + PYTHONIOENCODING=utf-8, override-on); applied at the setup_index foreground+background launchers and the upgrade Phase-4 launchers; indexer/check_version/prune_framework mains now call `configure_utf8_stdio()` (F3). Added `encoding=`/`errors=` to the inline-isolated captures (server_impl `_mcp_subprocess_run` + tasklist, venv_bootstrap — F2/GUARD-3). Broadened the AC-3 encoding scan framework-wide (was upgrade-only). AC-4 → met (root-caused + landed; rc==0 child proof).

**Changes delivered:**

- **Complete subprocess isolation across the framework** (`1p8gu-bug windows-subprocess-isolation-complete`) — 5 ACs completed. Key decisions: --------; One shared helper for all spawns.
- **Windows CLI encoding + path robustness** (`1p8gv-bug windows-cli-encoding-and-path-robustness`) — 5 ACs completed. Key decisions: --------; Shared UTF-8 stdio reconfigure at all CLI entry points.
- **wave_install_audit / install-log format mismatch** (`1p8gw-bug install-audit-log-format-mismatch`) — 4 ACs completed. Key decisions: --------; Add a template↔parser parity test.
- **Add a `wf gpu-doctor` subcommand** (`1p8gz-enh wf-gpu-doctor-subcommand`) — 4 ACs completed. Key decisions: --------; Reuse the `wave_gpu_doctor` backing logic for the CLI.
- **Surface the wave_upgrade summary on the primary phase + fix MCP handler_not_ready** (`1p8kz-bug upgrade-summary-surfacing-and-mcp-handler-readiness`) — 6 ACs completed. Key decisions: --------; Emit the summary on the primary phase (not just clarify docs).
## Journal Watchpoints

- **Serialization — shared spawn calls:** `1p8gu` and `1p8gv` edit the SAME `subprocess.run` calls in `upgrade_wavefoundry.py` / `setup_index` (`1p8gu` adds stdin+creationflags; `1p8gv` adds `encoding=`). Land `1p8gu`'s shared isolation helper first; fold the encoding kwarg into it or layer `1p8gv` on top — do not let two passes clobber the same call sites.
- **Anti-drift — one helper each:** the subprocess-isolation logic (currently duplicated 4×) and the UTF-8 stdio-reconfigure logic (currently only in `server.py:65`) must each become ONE shared source consumed everywhere; cover with anti-duplication / source-scan guards.
- **Watchpoint — non-vacuous guards:** the spawn-isolation source guard must scan ALL framework scripts (not just `server_impl`+`secrets`), and the encoding/parity tests must reproduce the real field defects (cp1252 `⚠` crash, `/tmp`, description-as-path) — green-but-vacuous is the failure mode to avoid.
- **Blocking risk — `\u0000` garble needs a Windows repro:** `1p8gv` AC-4 is repro-gated; if the capture/stdio fixes don't resolve it, root-cause on a real Windows console before claiming the AC.
- **Bring local patches home:** the Windows consumer agent hand-patched the `/tmp` + `_log` fixes locally; ensure the canonical versions here supersede those (don't assume the consumer's patch is the final shape).
- **Independence + new overlap:** `1p8gw` (install-log parser) shares no files with the others. `1p8gz` (`wf gpu-doctor`) adds a `_SUBCOMMANDS` entry in `wf_cli.py`, which `1p8gu` also touches for `wf`-dispatch spawn coverage — coordinate the `wf_cli.py` edits (small, additive overlap). `1p8gz` reuses the existing `wave_gpu_doctor`/`provider_policy` detection (no duplicate logic).

## Review Evidence

- wave-council-readiness: passed 2026-06-27 — all four changes grounded in a real native-Windows 1.9.4 upgrade trace (3 upgrade-breaking) plus an operator-requested CLI gap, confirmed against the canonical code (75-spawn isolation gap, now scoped call-path-independent per operator — any spawn, any entry point incl. agent-invoked `wf`, no window ever; `/tmp` at `:58`; `⚠`/cp1252 at `_log`; capture encoding; install-log parser↔template drift; no `wf gpu-doctor` though `wave_gpu_doctor` exists at `server_impl:15908`); ACs testable and tied to the defects; `1p8gu`/`1p8gv`/`1p8gz` shared `wf_cli`/spawn serialization defined; severity correct (expedite 1.9.5). Ready to implement.
- operator-signoff: approved 2026-06-28 — operator authorized close + a local 1.9.5 build (official release deferred until the Windows re-test confirms the isolation/encoding fixes).
- wave-council-delivery: passed 2026-06-28 — moderator: wave-council; seats: code-reviewer, architecture-reviewer, qa-reviewer, release-reviewer, docs-contract-reviewer, red-team. Two adversarial-review workflows ran over the implementation. The first found 4 CONFIRMED blockers — multiprocessing/ProcessPoolExecutor spawn windows bypassing the subprocess-only isolation (the operator's graph/secrets/index windows); graph backend defaulting to processes; spawned-child cp1252 crash (only parent stdout was reconfigured); install-log backtick-marker disabling CHECK 2 on the shipped template — ALL fixed and re-verified: windowless_mp_context (pythonw on Windows, serial/threads fallback) at every pool site + the isolation guard generalized to AST-detect process pools and aliased/os.system/asyncio spawns; utf8_child_env + child-main UTF-8 stdio; the install-log structural classifier (11 stat-able rows on the shipped template, was 0) with a positive parity assertion; wf gpu-doctor reuses provider_policy detection (no duplication); and 1p8kz (primary-phase data.summary, handler lazy-init, reconciliation on EVERY upgrade) directly verified by smoke + non-vacuous tests. Full suite 3625 green; docs-lint clean. Residual [~]: 1p8gu AC-6 (the wf shim's own native-Windows console launch) is host process-creation, Windows-repro-gated; the operator's symptom fixes are Windows-only mechanisms confirmed by the post-release Windows re-test. PASS to close.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-27: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: consolidating 4 isolation helpers + auditing 75 spawns is broad and could miss a spawn or break a must-inherit case — mitigated by a source-scan guard over ALL framework scripts plus documented inline exceptions, and by landing the shared helper before the routing audit; strongest-alternative: per-site fixes again as in 1p88t — rejected because that is exactly what left the pipeline gap and duplicated the no-window logic 4×.)

## Prepare Review Evidence

- code-reviewer: passed 2026-06-27 — plan is implementable with clear targets; one shared isolation helper, one shared UTF-8 stdio reconfigure, `tempfile.gettempdir()`, and a seed↔parser parity test are all sound and contained.
- architecture-reviewer: passed 2026-06-27 — generalizes existing patterns (the 1p88t isolation helper, the `server.py:65` stdio reconfigure) into single shared sources; no new boundary; the install-log parser realignment is module-local.
- qa-reviewer: passed 2026-06-27 — ACs testable and reproduce the real defects (cp1252 `⚠` non-crash, temp-path resolution, source-scan over all scripts, template↔parser parity, description-as-path regression); non-vacuity is an explicit watchpoint.
- release-reviewer: passed 2026-06-27 — fixes a SHIPPED release (1.9.4) on native Windows; expedite as 1.9.5; all changes are reachable/shippable (no stripped-from-pack risk).
- docs-contract-reviewer: passed 2026-06-27 — seed/doc touch-points coordinated (`install-log-format` seed for `1p8gw` under `seed_edit_allowed`; `native-windows-support.md` for `1p8gu`/`1p8gv`); the parity test is the anti-drift contract.

## Dependencies

- No external wave dependencies. Internal: `1p8gv` coordinates with `1p8gu` on shared spawn call sites (see Journal Watchpoints).
