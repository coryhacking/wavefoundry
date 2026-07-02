# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-02

wave-id: `1p9hn windows-portability-round-2`
Title: Windows Portability Round 2

## Objective

Close the remaining Windows-portability gaps identified in the 2026-07-02 10-dimension audit (workflow wf_51bd40fe-082): two HIGH findings (in-process stdout protocol corruption; os.kill liveness regression), three MEDIUM findings (install-log encoding crash; venv rmtree silent no-op; dashboard cmdline parse failure on spaced paths), and a LOW batch (CRLF hash normalization, .gitattributes propagation, cosmetic path output, seed-050 doc drift, hook OS-awareness, dashboard SO_REUSEADDR). All load-bearing invariants from prior Windows waves were confirmed intact; this wave closes the gaps they did not reach.

## Changes

Change ID: `1p9io-bug windows-stdout-purity`
Change Status: `implemented`

Change ID: `1p9hi-bug windows-oskill-liveness-regression`
Change Status: `implemented`

Change ID: `1p9hj-bug windows-install-log-encoding`
Change Status: `implemented`

Change ID: `1p9hk-bug windows-venv-rmtree-hardening`
Change Status: `implemented`

Change ID: `1p9hl-bug windows-dashboard-cmdline-parse`
Change Status: `implemented`

Change ID: `1p9hm-enh windows-line-endings-and-paths`
Change Status: `implemented`

Change ID: `1p9i7-enh server-startup-missing-venv-detection`
Change Status: `implemented`

Completed At: 2026-07-02

## Wave Summary

Wave `1p9hn` (Windows Portability Round 2) delivered 7 changes: Windows stdout purity: in-process print() corrupts MCP JSON-RPC channel, Windows os.kill regression: unguarded liveness probe in upgrade dashboard detection, Windows install-log encoding: strict UTF-8 read crashes wave_install_audit on non-UTF-8 logs, Windows venv rmtree hardening: setup_index venv recreation silently no-ops on Windows, Windows dashboard cmdline parse: spaced --root paths defeat reconciliation, Windows line-endings and path normalization: latent CRLF and cosmetic path issues, and Server Startup: Missing Venv Detection. Notable adjustments during implementation: Windows stdout purity: in-process print() corrupts MCP JSON-RPC channel: Implemented: 4 print sites routed to stderr, graph_query.py:223 wrapped in isolated_stdout_fd+redirect_stdout, AST guard + regression test added; Windows line-endings and path normalization: latent CRLF and cosmetic path issues: Delivery review fixes: (a) `_run_hook` `.cmd`/`.bat` branch now launches via `cmd /c` (bare-path `subprocess.run` would raise WinError 193 on Windows); (b) `allow_reuse_address` OS-scoped to avoid a POSIX TIME_WAIT regression.

**Changes delivered:**

- **Windows stdout purity: in-process print() corrupts MCP JSON-RPC channel** (`1p9io-bug windows-stdout-purity`) — 7 ACs completed. Key decisions: Route prints to `file=sys.stderr` rather than fully removing them; Add defense-in-depth wrapper at `graph_query.py:220` even after fixing print sites
- **Windows os.kill regression: unguarded liveness probe in upgrade dashboard detection** (`1p9hi-bug windows-oskill-liveness-regression`) — 4 ACs completed. Key decisions: Reuse existing `upgrade_lib._pid_is_running` rather than inlining a Windows branch
- **Windows install-log encoding: strict UTF-8 read crashes wave_install_audit on non-UTF-8 logs** (`1p9hj-bug windows-install-log-encoding`) — 5 ACs completed. Key decisions: Use `errors="replace"` (not `errors="ignore"`)
- **Windows venv rmtree hardening: setup_index venv recreation silently no-ops on Windows** (`1p9hk-bug windows-venv-rmtree-hardening`) — 5 ACs completed. Key decisions: Reuse the existing `_clear_readonly_and_retry` pattern from upgrade_wavefoundry rather than hoisting into subprocess_util
- **Windows dashboard cmdline parse: spaced --root paths defeat reconciliation** (`1p9hl-bug windows-dashboard-cmdline-parse`) — 4 ACs completed. Key decisions: Planned `shlex.split(posix=False)`; **Changed to a quote-aware regex** (`_ROOT_ARG_RE`) during implementation
- **Windows line-endings and path normalization: latent CRLF and cosmetic path issues** (`1p9hm-enh windows-line-endings-and-paths`) — 6 ACs completed. Key decisions: Batch all L-4 items into this change; Merge .gitattributes rather than overwrite
- **Server Startup: Missing Venv Detection** (`1p9i7-enh server-startup-missing-venv-detection`) — 4 ACs completed. Key decisions: Fail-fast in server.py, not in venv_bootstrap.py; No MCP surface changes (exit before handshake)
## Journal Watchpoints

- **1p9io (stdout-purity):** The AST print-purity guard (AC-6) must be written after print-site fixes are applied so it passes from day one. The `redirect_stdout` wrapper at `graph_query.py:220` is defense-in-depth and should land in the same commit as the print-site fixes.
- **1p9hm (line-endings):** seed-050 edit requires `wave_gate_open(gate="seed_edit_allowed")` before touching `050-agent-entry-surface-bootstrap.prompt.md` and `wave_gate_close` immediately after. Do not leave the gate open across other work.
- **1p9hm (line-endings):** `.gitattributes` merge must never overwrite operator-custom entries — show diff and abort on conflict.
- **Sequencing:** 1p9io (HIGH) and 1p9hi (HIGH) should be implemented first; they block the most Windows users. Remaining changes (1p9hj, 1p9hk, 1p9hl, 1p9hm) are independent and can proceed in parallel after the HIGH changes are in.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1p9io — `indexer.py` has ~52 `print()` calls beyond the four named sites reachable from in-process server code; AST guard (AC-6) must use conservative reachability or it produces a false green on day one; also `shlex.split(posix=False)` in 1p9hl preserves surrounding quotes so the extracted `--root` token must be stripped before Path resolution; and 1p9hj `is_unparseable` extension must add a replacement-char primary clause independent of the phase-heading pattern or AC-2 fails for UTF-16-BOM logs; strongest-alternative: 1p9hm `.gitattributes` merge should use idempotent block-markers to avoid requiring interactive confirmation in non-interactive render contexts; AC-1 tightened to encode abort-on-conflict behavior)
- pre-implementation-review: passed (2026-07-02) — Highest risk is 1p9io's AST print-purity guard reachability model (must conservatively cover the full in-process call set reachable from tool handlers, not just the 4 named print sites). Addressed by building the guard from the actual `register_mcp_surface`/tool-handler entry points and erring toward over-inclusion. Secondary risks (1p9hj is_unparseable replacement-char clause, 1p9hl quote-strip, 1p9hm non-interactive gitattributes merge) are encoded into the change docs' ACs and Risks tables. Packet complete: all 6 change docs have Requirements + ACs, AC priorities recorded, no required builder lanes beyond `implementer`. Builder lane: `implementer` (surgical, cross-cutting Windows-portability fixes).
- **Delivery-phase Wave Council [delivery-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team/reality-checker, code-reviewer, qa-reviewer (test-adequacy), architecture-reviewer (POSIX-regression + CRLF/path-consistency), rotating-seat: reality-checker; full suite **4096 tests OK**, max-severity **low**, docs-lint clean. **Two blocking bugs found in the wave's OWN fixes and fixed before sign-off:** (1) `dashboard_server.allow_reuse_address` was a blanket `False` → POSIX TIME_WAIT regression (choose_port prefers the last-recorded port, so a quick restart would fail to rebind); fixed to `os.name != "nt"`. (2) `_run_hook` launched a `.cmd`/`.bat` convention hook by bare path → Windows `subprocess.run(shell=False)` raises WinError 193 (the very crash class the wave targets); fixed to `cmd /c`, with a regression test. **Two test weaknesses hardened:** the 1p9io AST wrapper test was comment-satisfiable (now checks the `with`-block AST via `ast.dump`, comment-immune); the `_run_hook` Windows branch was untested (added 3 tests). strongest-challenge: 1p9io's "exactly two in-process boundaries" reachability claim — independently verified accurate (only `graph_query.py:231` build_index is in-process-reachable-and-wrapped; `walk_repo` is stderr-clean; `read_graph_payload`/`chunker._ts_parse` don't print). strongest-alternative: enforce stdout purity at the server dispatch boundary globally rather than per-site (noted as a more-robust future option; per-site is lower blast-radius and adequate). No POSIX functional regressions (two benign behavior changes — Permission=>running, RuntimeError-instead-of-silent-broken-venv — both strict improvements on rare paths). CRLF/path handling confirmed consistent (`_sha256_file` copies md5-identical; gitattributes ordering/scope correct; all path sites covered). Non-blocking note: the unconditional `render_gitattributes_block` will cosmetically reshuffle the self-host repo's own `.gitattributes` on the next render (functionally identical per `git check-attr`, idempotent) — recorded in 1p9hm Progress Log.)

## Review Evidence

- wave-council-readiness: approved 2026-07-02 — READY. Six Windows-portability bug fixes and one hardening enhancement, all sourced from a verified 10-dimension audit (wf_51bd40fe-082) with adversarial verification. No required council lanes triggered (no MCP endpoint additions, no architecture boundary changes, no security-sensitive data paths). Red-team pass: `1p9io` (stdout purity) — `contextlib.redirect_stdout` is not reentrant-safe but `_VERSION_REBUILD_INFLIGHT_LOCK` ensures only one thread performs the rebuild; the AST guard is gated after print-site fixes so it passes from day one. `1p9hi` (os.kill) — `upgrade_lib._pid_is_running` is already used at three sibling sites; POSIX path is preserved transparently. `1p9hj` (install-log encoding) — `errors="replace"` is safe for valid UTF-8 (no replacement chars fired); `is_unparseable` extension requires BOTH replacement chars AND zero parseable rows to avoid false positives. `1p9hk` (venv rmtree) — `_clear_readonly_and_retry` pattern is proven from 1p6d6; post-rmtree existence check is new but low-risk (only fires on partial rmtree). `1p9hl` (dashboard cmdline) — `shlex.split(posix=False)` wrapped in try/except degrades gracefully to empty list on malformed cmdline (same behavior as today). `1p9hm` (line-endings/paths) — seed-050 edit requires `seed_edit_allowed` gate per CLAUDE.md, noted in watchpoints; `.gitattributes` merge never overwrites operator entries. No blocking findings. All ACs are deterministically testable.
- wave-council-delivery: approved 2026-07-02 — PASS. Full suite 4096 tests OK, max-severity low, docs-lint clean. Delivery review found and fixed two blocking bugs in the wave's own fixes (POSIX `allow_reuse_address` regression → OS-scoped; `_run_hook` `.cmd` bare-path WinError 193 → `cmd /c`) and hardened two test weaknesses (comment-immune AST wrapper guard; `_run_hook` Windows-branch coverage). No POSIX functional regressions; CRLF/path handling consistent. See `## Review Checkpoints` for the full seat roster and reasoning.
- operator-signoff: approved 2026-07-02 — operator instructed close ("close 1p9hn") after implementation of all seven changes including the late-added 1p9i7 venv-detection guard.

## Dependencies

- No external wave dependencies.
