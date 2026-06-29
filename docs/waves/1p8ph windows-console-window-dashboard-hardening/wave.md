# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-28

wave-id: `1p8ph windows-console-window-dashboard-hardening`
Title: Windows Console Window Dashboard Hardening

## Objective

When this wave closes the native-Windows experience is window-free and the dashboard starts cleanly: every framework python spawn that doesn't need a console launches via `pythonw.exe` (no flashing windows during upgrade / index / graph / dashboard), the dashboard start no longer false-reports `url_not_ready` or double-spawns and climbs ports, and the dashboard markdown renderer shows `---` as a horizontal rule. Now, because the 1.9.5 post-release native-Windows test surfaced these three residuals.

## Changes

Change ID: `1p8pe-bug windows-pythonw-framework-spawns`
Change Status: `implemented`

Change ID: `1p8pf-bug dashboard-lock-pid-race-lifecycle`
Change Status: `implemented`

Change ID: `1p8pg-bug dashboard-markdown-thematic-break-render`
Change Status: `implemented`

Completed At: 2026-06-29

## Wave Summary

Wave `1p8ph` (Windows Console Window Dashboard Hardening) delivered 3 changes: Convert framework python spawns to pythonw on Windows, Dashboard lock / PID-race lifecycle on start, and Dashboard markdown renderer: thematic break (`---`) → `<hr>`. Notable adjustments during implementation: Convert framework python spawns to pythonw on Windows: Implemented. Resolver edits in `server_impl._preferred_python` + `upgrade_wavefoundry._preferred_python` (prefer `windowless_pythonw()` on Windows, ~19 redirected consumers each). Per-site converts: `setup_index` background-build / foreground-indexer / import-probe (`windowless_pythonw() or <venv python>`); `dashboard_server._daemonize` (`windowless_pythonw() or sys.executable`). Renderer: new `hook_python()` in `hook_helpers()` threaded into docs-lint + reindex-Popen + cursor gate launches; inline guarded windowless resolution in `claude_simulate_hooks_source` (no shared helpers). Hard-exclusions verified untouched (every MCP command stays `python3`; `setup_index:134` + `venv_bootstrap.tool_venv_python` + console pip/venv installs + `wf` re-exec preserved). New source-scan guard + non-vacuous tests added; AC-6 stays `[~]` (Windows-repro-gated).; Dashboard lock / PID-race lifecycle on start: Implemented in `server_impl.py`. Added `_dashboard_url_reachable` (any HTTP response incl. 4xx/5xx = serving; connect-fail/timeout = not) + `_dashboard_already_serving` (reconcile: live recorded PID+URL, OR reachable URL backed by a live dashboard process). Wired the reconcile both pre-lock and post-lock (before the orphan-kill/spawn). Relaxed the readiness poll: the just-spawned-PID still accepts on metadata (backward compatible); a non-matching PID now accepts on live-PID+URL or URL-reachability, with the bounded `DASHBOARD_START_WAIT_SECONDS` deadline preserved so a real failure still reports `url_not_ready`. Orphan reconcile + start/server lock gating + stop/restart unchanged.; Dashboard lock / PID-race lifecycle on start: Windows lock-vs-metadata-write fix. Root cause: `dashboard-server.lock` is BOTH the lifetime lock and the metadata store (1p64x); the `msvcrt` branch locked byte 0, which (mandatory byte-range on Windows) blocked the daemon's own separate-handle metadata rewrite at byte 0+ → `url` never published → false `url_not_ready`. Fix: added `_LOCK_BYTE_OFFSET = 1 << 30` and locked/unlocked the SENTINEL byte at that offset in `dashboard_lib.dashboard_lock` (Windows branch only); metadata JSON at byte 0+ is now disjoint from the lock region. POSIX whole-file advisory `flock` unchanged.

**Changes delivered:**

- **Convert framework python spawns to pythonw on Windows** (`1p8pe-bug windows-pythonw-framework-spawns`) — 6 ACs completed. Key decisions: --------; pythonw (windows subsystem) over more `CREATE_NO_WINDOW`.
- **Dashboard lock / PID-race lifecycle on start** (`1p8pf-bug dashboard-lock-pid-race-lifecycle`) — 5 ACs completed. Key decisions: --------; Reconcile already-serving + relax the readiness poll (don't require own PID).
- **Dashboard markdown renderer: thematic break (`---`) → `<hr>`** (`1p8pg-bug dashboard-markdown-thematic-break-render`) — 3 ACs completed. Key decisions: --------; Treat `---`/`***`/`___` as a thematic break (`<hr>`), not a setext heading underline.
## Journal Watchpoints

- **Serialization (1p8pe ↔ 1p8pf):** both edit the `server_impl.py` dashboard-start block (~`6777`/`6796`). `1p8pe` only swaps the interpreter token to pythonw; `1p8pf` reworks the readiness/reconcile logic. Keep the interpreter swap minimal and coordinate so the two edits don't clobber.
- **1p8pe — adversarial-verify-confirmed UNSAFE site:** do NOT resolver-convert `setup_index._tool_venv_python` (`:134`) or mutate `venv_bootstrap.tool_venv_python` (`:71`) — they feed venv path-math (`venv_python.parent.parent`, `.exists()`) and the console-streaming `pip install` keep. setup_index converts are PER-SITE (`959`/`1004`/`214`) only.
- **1p8pe — pythonw safety:** convert only redirected-output spawns; `pythonw` + an unredirected stdout → `sys.stdout` is `None` → child `print()` crash. The hard-exclusions (every MCP server command across hosts, the `wf` shims + `wf_cli` re-exec, console-streaming installs, the version probes, `wave_run_sensors`) MUST stay `python3`/`python.exe` — assert the rendered MCP command stays `python3`.
- **1p8pe — AC-6 is Windows-repro-gated `[~]`:** the no-flash confirmation is post-release on native Windows (macOS can't exercise pythonw/`CREATE_NO_WINDOW`); every non-Windows-repro AC must still be fully met + tested, and POSIX behavior proven unchanged (`windowless_pythonw()` → `None`).
- **1p8pf — don't mask a failed start:** when relaxing the PID-exact readiness poll, verify URL reachability and/or a live PID and keep a bounded deadline so a genuinely-failed start still reports failure.
- **1p8pg — code-block guard:** a `---` inside a fenced code block must stay literal (the renderer's code-block collector `continue`s first); test that explicitly.
- **Non-vacuous tests:** the spawn-convert tests must reproduce the real behavior (pythonw-on-Windows, graceful POSIX fallback, keep-list intact) — green-but-vacuous guards are the failure mode to avoid.

## Review Evidence

- wave-council-readiness: passed 2026-06-28 — moderator: wave-council; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer. All three changes grounded in the 1.9.5 post-release native-Windows test; `1p8pe` additionally backed by a 117-site spawn audit + adversarial verify that PRE-CAUGHT the two risky items (setup_index `:134` is not spawn-only → demoted to per-site; three rendered-hook child spawns were missed converts → added). Strongest challenge: `1p8pe` is broad and could convert a spawn that needs console stdio (None `sys.stdout` crash) or break venv bootstrap — mitigated by the verified convert/keep list (resolver-only for the two spawn-only `_preferred_python`; per-site for setup_index; never touch `venv_bootstrap.tool_venv_python`/`:134`), the hard-exclusion list (MCP server commands, `wf` shims, console-streaming installs, version probes, `wave_run_sensors` stay `python3`), a POSIX-unchanged proof, and a source-scan guard. `1p8pf` risk (relaxing the PID-exact readiness poll masks a genuinely-failed start) mitigated by URL-reachability / live-PID checks + a bounded deadline. `1p8pg` is small and contained (a `---` inside a code block stays literal). Strongest alternative: more `CREATE_NO_WINDOW` — rejected (already present and insufficient on console `python.exe`, the root cause). Load-bearing constraints: keep the MCP transport on `python3`, don't mutate venv path-math, don't mask failed dashboard starts. ACs testable; AC-6 (no-flash) is Windows-repro-gated `[~]` (post-release confirmation). Ready to implement.
- operator-signoff: approved when operator confirms closure
- wave-council-delivery: passed 2026-06-29 — moderator: wave-council; seats: code-reviewer, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team. All 3 changes + the sentinel-byte lock fix implemented and verified — full suite 3683 green, docs-lint clean. **security-reviewer:** the MCP server command stays `python3` on every host (`test_every_rendered_mcp_command_stays_python3`), `setup_index._tool_venv_python` / `venv_bootstrap.tool_venv_python` are untouched (AST-asserted; console `pip install` + venv path-math preserved), POSIX behavior provably unchanged (`windowless_pythonw()` → `None`, confirmed at runtime). **code/architecture:** resolver-level for the two spawn-only `_preferred_python`, per-site for setup_index/dashboard_server, the `hook_python()` renderer helper for the hook bodies — localized, extends the 1p8gu single-source helper. **qa:** ACs tested non-vacuously (resolver behavior, the 18-site spawn-token guard with 0 offenders, the PID-race regression 4920-vs-4924 → no false `url_not_ready` / no double-spawn, the sentinel-lock offset / disjoint-metadata / concurrency-gate / POSIX-flock tests, and the real-renderer `---`→horizontal-rule conversion via a node+vm harness). **red-team strongest-challenge:** the sentinel-byte lock's native-Windows runtime behavior (truncating/writing the small metadata while the daemon holds a beyond-EOF mandatory byte-lock) cannot be exercised on macOS — the Windows re-test must confirm the dashboard URL is actually published while the lock is held. **RESIDUAL `[~]` (Windows-repro-gated):** 1p8pe AC-6 (no console flash) and 1p8pf AC-6 (live lock / url publication) — mechanism + POSIX-no-regression met and tested; the live native-Windows confirmation is the gating check. PASS to close (the `[~]` Windows items validate on the native-Windows re-test).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-28: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: `1p8pe` is broad — converting a spawn that needs console stdio (None `sys.stdout` crash) or resolver-converting setup_index would break venv path-math and hide `pip` progress; mitigated by the adversarially-verified convert/keep list (which already pre-caught setup_index `:134` as not-spawn-only and three missed renderer converts), per-site setup_index handling, the hard-exclusion list keeping every MCP/CLI/install/probe on `python3`, a POSIX-unchanged proof, and a source-scan guard; security-reviewer confirms no auth/trust/transport change — the MCP server command stays `python3` and the secrets pool is unchanged; `1p8pf` relaxes the PID-exact readiness poll with URL-reachability/live-PID checks + a bounded deadline so a genuinely-failed start still reports failure; `1p8pg` is line-level and fenced-code-guarded; strongest-alternative: more `CREATE_NO_WINDOW` — rejected, already present and insufficient on console `python.exe`.)

## Dependencies

- No external wave dependencies.
