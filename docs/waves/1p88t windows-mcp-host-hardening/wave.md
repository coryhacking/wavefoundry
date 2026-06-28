# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-27

wave-id: `1p88t windows-mcp-host-hardening`
Title: Windows MCP Host Hardening

## Objective

Make Wavefoundry's native-Windows MCP path boring and repeatable after the 1.9.x field reports: a single committed MCP config surface, no inherited JSON-RPC streams in helper subprocesses, no unnecessary visible console windows from Wavefoundry-spawned children, and a first-class `wf` command surface for agent-run framework scripts so agents stop guessing raw Python invocations.

This wave preserves the project-local, committed MCP config model. The intended direction is to standardize the committed MCP command on `python3`, then make setup heal common Windows/POSIX environments where only `python` exists by creating an appropriate user-local shim. Direct raw script invocations are moved behind `wf` subcommands except for development-only internals.

## Changes

Change ID: `1p88t-enh python3-mcp-command-standard`
Change Status: `implemented`

Change ID: `1p88t-enh mcp-subprocess-isolation`
Change Status: `implemented`

Change ID: `1p88t-enh wf-command-coverage`
Change Status: `implemented`

Change ID: `1p88t-enh windows-console-window-suppression`
Change Status: `implemented`

Completed At: 2026-06-27

## Wave Summary

Wave `1p88t` (Windows MCP Host Hardening) delivered 4 changes: Python3 MCP command standard, MCP subprocess isolation, WF command coverage, and Windows console-window suppression. Notable adjustments during implementation: Python3 MCP command standard: **Superseded: pivot to detect + guide (no environment mutation).**; MCP subprocess isolation: Post-review: AC-2 scope made honest.; Windows console-window suppression: Post-review: AC-4 docs added; AC-1 scope made honest..

**Changes delivered:**

- **Python3 MCP command standard** (`1p88t-enh python3-mcp-command-standard`) — 6 ACs completed. Key decisions: --------; Plan around committed `python3` MCP command plus setup healing.
- **MCP subprocess isolation** (`1p88t-enh mcp-subprocess-isolation`) — 5 ACs completed. Key decisions: --------; Isolate helper subprocess stdio instead of raising timeout.
- **WF command coverage** (`1p88t-enh wf-command-coverage`) — 7 ACs completed. Key decisions: --------; Make `wf` the operator/agent CLI surface for covered scripts.
- **Windows console-window suppression** (`1p88t-enh windows-console-window-suppression`) — 5 ACs completed. Key decisions: --------; First suppress Wavefoundry child-process windows; treat main MCP window as separate evidence-gated follow-up.
## Journal Watchpoints

- **Follow-up - single committed MCP surface:** do not solve Windows by generating per-machine `.mcp.json` files. Generated repo-local MCP configs should remain commit-safe and byte-identical across hosts.
- **Follow-up - interpreter command decision:** the proposed standard is `python3`, not `python3.exe`. Setup should make that command resolvable when a valid Python is already installed under another common token; otherwise fail with concrete install guidance.
- **Blocking risk - MCP stdio isolation:** any helper subprocess launched inside the MCP server must never inherit the JSON-RPC stdin stream. Use `stdin=DEVNULL` and intentional stdout/stderr capture or redirection.
- **Watchpoint - console-window evidence:** first eliminate visible windows from Wavefoundry-spawned child processes with Windows no-window creation flags. If the blank window remains, the visible process is likely the host-launched main MCP server and requires a separate launcher/client strategy.
- **Blocking order - `wf` coverage before docs cleanup:** add subcommands before rewriting docs/prompts away from raw `python3 .wavefoundry/framework/scripts/*.py` references, so every replacement command actually exists.

## Review Evidence

- wave-council-readiness: passed 2026-06-27
- code-reviewer: passed 2026-06-27 — multi-agent implementation review + final pre-build review. 3 blockers found and fixed (wf prune-framework int(None) crash; Windows python-only heal fail-closed on the verify probe; heal durability fail-open), then superseded by the detect+guide pivot that removed the shim/symlink/PATH-mutation machinery entirely. All confirmed fixed by adversarial re-verification; no outstanding code findings.
- architecture-reviewer: passed 2026-06-27 — MCP launch contract unchanged (python3 server.py, raw spawn); subprocess-isolation boundary centralized on _mcp_subprocess_run with a non-vacuous breadth guard over server_impl + secrets_validators; detect+guide amendment recorded in ADR 1p7pb; git hooks dropped (the in-session staleness monitor + global incremental indexer cover VCS-driven refresh). Boundaries consistent.
- qa-reviewer: passed 2026-06-27 — AC verification + test-vacuity audit; added non-vacuous source guards and behavioral tests (prune removal, detect+guide fail-closed, subprocess isolation, gitattributes); full framework suite 3516 OK; docs-lint OK.
- release-reviewer: passed 2026-06-27 — package exclusions verified (build_pack.py / run_tests.py / build_scan_allowlist.py / git-hooks excluded; prune_framework.py still shipped as the manual upgrade-cleanup script); local 1.9.4 prerelease pack built and validated downstream on a multi-minor 1.8.1 to 1.9.4 upgrade.
- docs-contract-reviewer: passed 2026-06-27 — docs/AC/change-doc accuracy swept; stale heal/shim/git-hook prose removed across CHANGELOG, ADR 1p7pb, and native-windows-support; AC-5 raw-script scan enforces wf usage in operator docs; change-doc ACs reconciled to the implemented end state.
- wave-council-delivery: passed 2026-06-27 — final pre-build review verdict GO with zero blockers; all surfaced findings (3 implementation blockers + 8 final-review items) fixed and verified; suite green, docs-lint clean, prerelease validated downstream. Cleared for close.
- operator-signoff: approved 2026-06-27 — operator confirmed closure ("close the existing wave now").

## Participants

| Lane | Phase | Scope |
| --- | --- | --- |
| implementer | implementation | all admitted changes |
| code-reviewer | review | framework scripts, tests, rendered config behavior |
| architecture-reviewer | review | MCP launch contract, subprocess isolation boundary |
| qa-reviewer | review | AC verification and Windows/POSIX simulated tests |
| security-reviewer | council | PATH/shim behavior, process/stdio trust boundary |
| reality-checker | council | field-report assumptions and Windows host constraints |
| release-reviewer | review/council rotating seat | package exclusions and distribution surface |
| docs-contract-reviewer | review | docs/prompts/seeds command guidance |

## Review Checkpoints

- Prepare wave - readiness verdict: passed (2026-06-27) - all four admitted changes are wave-owned, AC priority tables are present, required lanes selected, and source-host-only `run_tests.py` / `build_pack.py` exclusions are explicitly in scope for the command coverage change.
- prepare-council: moderator=wave-council; primer-depth=standard; seats=architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat=release-reviewer; strongest-challenge=the wave spans interpreter resolution, MCP stdio, docs guidance, and package contents, so partial implementation could create a new mismatched surface; strongest-alternative=avoid new `wf` commands and only rewrite docs, rejected because field feedback shows agents need a concrete cross-OS command surface.
- pre-implementation-review: passed (2026-06-27) - highest risk is inconsistent command/package surfaces; addressed by sequencing interpreter policy and subprocess helper first, adding `wf` commands before docs cleanup, and verifying package exclusions before release.
- code-review follow-up: fixed (2026-06-27) - addressed incomplete Windows no-window flags in background index/hook spawns, pinned the Windows `python3.cmd` shim to the validated interpreter, made strict setup fail early on unusable `python3`, converted remaining active raw-script guidance to `wf`, and updated hook launch configs to `python3` repo-relative paths with no `$CLAUDE_PROJECT_DIR` dependency.

## Progress Log

- Thought: implementation starts after readiness with MCP unavailable in this session; use local file reads/search as the fallback evidence path and keep change-doc checkboxes current.
- Gapfill: MCP code navigation tools are not attached in this Codex session, so repository reads and `rg` are the fallback for code discovery.
- Observe: full framework test suite passed after review fixes — 3512 tests across 35 files.
- Observe: docs-lint passed after implementation.
- Observe: docs-lint passed after review fixes.
- Observe: final `python` command-surface scan passed - generated MCP configs, hook configs, bin launchers, and git hooks use `python3`; setup verifies `python3` resolves and never creates a `python3`/`python` launcher (detect + guide — see pivot below).
- Reflect: the only intentionally deferred item is downstream confirmation of whether the blank Windows console persists after child-process suppression; if it does, the next decision is a main-process no-console launcher strategy.
- Observe: full implementation review (multi-agent, adversarially verified) found 3 blocking issues, all fixed this session — (1) `wf prune-framework` crashed every call (`int(None)`) → removed from the `wf` surface (manual-only) + dispatcher hardened; (2) the Windows `python`-only heal created a non-raw-spawnable `.cmd` → now prefers a raw-spawnable `python3.exe` sibling and fails closed otherwise; (3) the heal's "fresh subprocess" verification was a fail-open (in-process-mutated PATH + swallowed rc-write error) → now durability-checked and fails closed. Full suite 3521 tests OK; docs-lint OK.
- Observe: AC-honesty fixes — built the real AC-5 raw-script scan (`NoRawCoveredScriptInvocationInOperatorDocsTests`) + converted operator-facing breaches; added the console-suppression boundary doc (`native-windows-support.md`) and CHANGELOG `[Unreleased]` entries (AC-4); recorded the bounded residual MCP-reachable subprocess probes honestly in AC-1/AC-2.
- Decide (pivot, supersedes the blocker-2/3 heal above): operator chose **detect + guide only** — setup must not mutate the environment to make `python3` resolve. Removed all shim/symlink/sibling-`exe`/`.cmd`/PATH-mutation code and its helpers (`_create_python3_shim*`, `_ensure_dir_on_path`, `_shell_rc`, `_user_local_bin`, `_probe_shim`); `ensure_python_resolves` now just verifies `python3` resolves to ≥3.11 and fails closed (setup) / warns (render, upgrade) with platform-aware guidance + the per-machine fallback. Tests rewritten to assert nothing is created. Amended ADR `1p7pb`, the change doc, README, install prompt, CHANGELOG, and gui-fallback prose. Full suite 3513 tests OK; docs-lint OK.
- Observe: resolved the MCP-reachable subprocess-probe residual — routed the git audits through `_mcp_subprocess_run` and isolated the inline probes (`tasklist`, `nvidia-smi`, `ldconfig`, dashboard PowerShell/`ps`) with `stdin=DEVNULL` (+ `CREATE_NO_WINDOW` where a console can appear). Added a non-vacuous breadth source-scan guard over `server_impl` (catches the aliased `_sp.run`/`__import__` forms that evaded the first review) plus behavioral tests; console AC-1 / isolation AC-2 are now genuinely "all".
- Reflect (residual): with detect + guide there is no Windows auto-heal left to field-verify (the previous sibling-`exe`/durability residual is moot), and the subprocess-probe residual is now closed. The only Windows-specific items remaining are field-smoke confirmations (console-window persistence after suppression; native attach), tracked by console-suppression AC-5.
- Observe: shell-compat pass — confirmed native PowerShell + cmd.exe work (MCP server, hooks, `wf.cmd`, setup are shell-agnostic given `python3` on PATH). Fixed two operator-facing doc bugs: the `upgrade-wave` skill renderer now emits both `wf`/`wf.cmd` forms (with a test), and `native-windows-support.md` C-3/M-1/M-2 marked resolved.
- Decide: **dropped the git hooks** (operator decision). They only spawned a background incremental reindex, were opt-in/inactive-by-default, and duplicated the in-session staleness monitor (which hash-detects VCS-driven changes and refreshes within ~20s; `indexer.py`'s incremental diff is global so any trigger catches up `git pull`/`merge`/`checkout`). Removed `git_hook_source`/`render_git_hooks`/`GIT_HOOK_NAMES` + the four rendered `.wavefoundry/git-hooks/*`; added `remove_git_hooks` so a re-render cleans up prior renders. This also retires the M-3 git-bash/`python3` Windows concern entirely. Suite green; docs-lint OK.

## Dependencies

- `python3-mcp-command-standard` should land before broad docs cleanup, because it changes the canonical command token.
- `wf-command-coverage` should land before prompt/docs rewrites that replace direct script calls with `wf` subcommands.
- `windows-console-window-suppression` depends on the subprocess isolation audit to identify every Wavefoundry-spawned helper path.
