# Python3 MCP command standard

Change ID: `1p88t-enh python3-mcp-command-standard`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p88t windows-mcp-host-hardening`

## Rationale

Native-Windows field testing exposed an interpreter-command mismatch: a clean machine had no Python, Claude Code installed Python through Scoop, and the resulting command was `python3` rather than `python`. Wavefoundry's 1.9.x committed MCP config and setup smoke test standardized on `python`, which made setup fail even though a valid Python was present.

The project still needs a single committed `.mcp.json` surface. Per-machine generated MCP configs are too brittle and make target repositories harder to commit/review. The better standard is a stable command token (`python3`) plus a setup **verification** step. **Post-review operator decision (detect + guide; amends ADR 1p7pb):** setup does **not** mutate the environment to make `python3` resolve — auto-creating a shim/symlink/copy was invasive and fragile across OSes (a Windows `.cmd` is not raw-spawnable; a sibling `python3.exe` copy mutates the user's Python install; a POSIX symlink still needs PATH cooperation). Setup verifies `python3` resolves to ≥3.11 and, when it does not, fails closed with platform-aware guidance. Making `python3` resolvable is the operator's step.

## Requirements

1. Generated MCP configs for Claude, Cursor, Junie, Antigravity, Codex, and instruction docs standardize on `command: "python3"` with the existing repo-relative `server.py` args.
2. `wf setup`, `render_platform_surfaces`, and `upgrade_wavefoundry` verify `python3` resolves to Python 3.11+ before relying on generated MCP configs.
3. **Detect + guide, no mutation (amended post-review):** setup does NOT create or repair a `python3` shim/symlink, copy into a Python install, or edit PATH on any OS. When `python3` does not resolve to ≥3.11, setup **fails closed** (strict) with concrete, platform-aware guidance (Windows: install via Scoop/Microsoft Store, which provide `python3`, or add a `python3` to PATH; POSIX: install via your package manager or symlink `python3` on PATH).
4. render/upgrade call the same verification non-strict: warn (do not abort) when `python3` does not resolve.
5. The guidance always also names the no-PATH escape hatch: the per-machine absolute-venv-path MCP config fallback (printed by setup).
6. Setup smoke-tests the exact generated MCP launch shape: `python3 .wavefoundry/framework/scripts/server.py --dry-run` (reached only after `python3` is confirmed to resolve).

## Scope

**Problem statement:** committed MCP configs need one interpreter command, but Windows installations differ between `python` and `python3`.

**In scope:**

- Interpreter command selection policy.
- `venv_bootstrap.ensure_python_resolves` replacement or extension for `python3` resolution.
- Generated MCP config updates.
- Setup/render smoke tests and docs/prompts/seeds that describe MCP attachment.
- Tests for Windows and POSIX command-heal behavior.

**Out of scope:**

- Per-machine `.mcp.json` generation.
- Switching MCP to `wf`.
- Requiring one specific Windows Python installer.
- No-console launchers for the main MCP process; tracked separately in `windows-console-window-suppression`.

## Acceptance Criteria

- [x] AC-1: every generated MCP config uses `command: "python3"` and the repo-relative `.wavefoundry/framework/scripts/server.py` arg shape; tests cover Claude, Cursor, Junie, Antigravity, and Codex surfaces.
- [x] AC-2 (revised post-review — detect + guide, no mutation): `wf setup` verifies `python3` resolves to Python 3.11+ (a fresh-subprocess version probe of the bare token) and, when it does not, **fails closed (strict)** with platform-aware guidance; render/upgrade warn non-fatally. Setup creates **no** shim/symlink/copy and edits **no** PATH. Tests (`EnsurePythonResolvesTests`) cover: env opt-out → skipped; `python3` already ≥3.11 → ok; `python3` <3.11 → warn/strict-raise; `python3` absent with `python` present (POSIX and Windows) → warn/strict-raise **and asserts nothing is created**; no-Python → warn/strict-raise; platform-aware guidance text + "does not modify your Python" assertion.
- [x] AC-3: setup dry-run invokes `python3 server.py --dry-run`, not `python` or `sys.executable` (reached only after `python3` is confirmed to resolve).
- [x] AC-4: docs/prompts/seeds describe `python3` as the committed MCP command and tell operators how to make `python3` resolve when it is missing; they state setup does not modify the Python install or PATH.
- [x] AC-5: no generated MCP config points at `.wavefoundry/venv/Scripts/python.exe`, `.wavefoundry/venv/bin/python`, `wf`, or a machine-absolute interpreter path.
- [x] AC-6: full framework suite and docs-lint pass.

## Tasks

- [x] Update interpreter-resolution helpers and tests.
- [x] Update MCP renderers and config-surface drift tests.
- [x] Update setup dry-run command and tests.
- [x] Update install/native-Windows docs, AGENTS, seeds, and changelog.
- [x] Run full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Resolver | implementer | — | `venv_bootstrap` command-heal behavior. |
| Renderers | implementer | Resolver | MCP config surfaces and tests. |
| Docs | docs-contract-reviewer | Renderers | Keep guidance consistent with generated behavior. |
| QA | qa-reviewer | all | Windows/POSIX simulated tests plus full suite. |

## Serialization Points

- `venv_bootstrap.py`, `render_platform_surfaces.py`, `setup_wavefoundry.py`, and their tests should be edited as one coordinated unit.

## Affected Architecture Docs

`docs/references/native-windows-support.md` and MCP setup guidance. Architecture hub likely `N/A` unless the implementation introduces a new launcher abstraction.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Single committed MCP surface is the central contract. |
| AC-2 | required | Windows install reliability depends on healing common command shapes. |
| AC-3 | required | Setup must test the exact host launch shape. |
| AC-4 | important | Prevents agent/operator misconfiguration. |
| AC-5 | required | Avoids the already-observed hardcoded-venv failure. |
| AC-6 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from native-Windows field feedback after 1.9.3. | Operator report: Scoop installed `python3`; existing `python` standard failed detection. |
| 2026-06-27 | Implemented `python3` MCP command standard. | Generated MCP configs and docs now use `python3`; `wf setup` creates/verifies `python3` shim behavior; full suite 3510 tests OK; docs-lint OK. |
| 2026-06-27 | Post-review: fixed the heal fail-open + Windows `.cmd` non-resolvability. | (1) The "fresh subprocess" verification used the in-process-mutated PATH and swallowed rc-write failures, so a non-durable heal reported success — now `_ensure_dir_on_path` returns a durability status (`already`/`persisted`/`ephemeral`), the probe runs in a clean env, and a non-durable heal **fails closed** (strict `SystemExit`). Genuine non-mocked POSIX tests in `EnsureDirOnPathDurabilityTests`. (2) On Windows-`python`-only, the heal now prefers a raw-spawnable `python3.exe` SIBLING of `python.exe` (a `.cmd` is not exec'able by a raw `CreateProcess` spawn) and **fails closed** when only a non-raw-spawnable `.cmd` can be created. Full suite 3521 tests OK. |
| 2026-06-27 | AC-2/AC-3 honest status. | The durability fail-closed behavior and the Windows sibling-`exe` heal are unit-tested via simulated Windows (`os.name` patch) on POSIX; **real-Windows field verification is still pending** (same residual class as console-suppression AC-5). POSIX heal is fully exercised end-to-end. |
| 2026-06-27 | **Superseded: pivot to detect + guide (no environment mutation).** | Operator decision after reviewing the heal feasibility: auto-creating `python3` is invasive (a sibling `python3.exe` copy mutates the user's Python install) and fragile (Windows `.cmd` not raw-spawnable; POSIX symlink needs PATH cooperation), and on macOS it cannot be verified for real Windows. `ensure_python_resolves` is now detect + guide only: verify `python3` resolves to ≥3.11, else fail closed (setup) / warn (render, upgrade) with platform-aware guidance + the per-machine fallback. Removed all shim/symlink/copy/PATH-mutation code and its helpers; setup prints the GUI/no-PATH fallback stanza before the strict check. Tests rewritten (`EnsurePythonResolvesTests`) to assert nothing is created. Full suite OK; docs-lint OK. | Auto-create a `python3.exe`/symlink (rejected: invasive + unverifiable + only per-user installs); keep the `.cmd` shim (rejected: not raw-spawnable). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Plan around committed `python3` MCP command plus setup healing. | Keeps one commit-safe MCP config while handling Windows `python`-only installs. | Per-machine MCP config (rejected); route MCP through `wf` (rejected); require one installer (too brittle). |
| 2026-06-27 | **Amend (post-review): setup detects + guides, never heals.** Setup verifies `python3` resolves and fails closed with guidance; it does not create a shim/symlink/copy or edit PATH. | Auto-heal was invasive (mutates the user's Python install / shell rc) and fragile/unverifiable across OSes; making `python3` resolve is a one-time operator step, and the per-machine absolute-venv-path fallback covers the no-PATH case. Amends ADR `1p7pb`. | Sibling `python3.exe` copy (rejected: invasive, per-user-only, unverified); `.cmd` shim (rejected: not raw-spawnable); POSIX symlink (rejected: still needs PATH + new shell, and inconsistent to heal one OS only). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| python.org Windows users have only `python`, so the committed `python3` config does not launch. | Setup detects this and **fails closed with platform-aware guidance** (install via Scoop/Microsoft Store which provide `python3`, or add a `python3` to PATH) plus the no-PATH per-machine fallback stanza. Setup does not mutate their Python install (detect + guide, amended post-review). |
| Existing targets already have committed `python` configs. | Upgrade/render migration rewrites the Wavefoundry stanza only, preserving unrelated MCP servers. |
| Operator must make `python3` resolve before MCP works. | Setup fails loudly with concrete steps and the per-machine absolute-venv-path fallback that needs nothing on PATH; render/upgrade warn non-fatally so they never abort on this. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
