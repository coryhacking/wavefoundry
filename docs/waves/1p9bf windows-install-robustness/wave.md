# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-01

wave-id: `1p9bf windows-install-robustness`
Title: Windows Install Robustness

## Objective

Fix two native-Windows install-robustness defects surfaced by a real 1.9.8 field install, so they ship
**in 1.10.0** (release is held for this wave). The post-edit docs-lint hook subprocess is unbounded (and
was too-short-capped in the field build) — bound + configure it and fail safe so a slow whole-tree lint
never hangs the editing agent. The install-log parser requires literal em dashes and treats an empty
parse as vacuously "complete" — so a non-UTF-8 PowerShell-written log reads as a passed install; make the
parse encoding-robust and never report "complete" from zero parsed rows.

## Changes

Change ID: `1p9bg-bug docs-lint-hook-timeout-configurable`
Change Status: `implemented`

Change ID: `1p9bh-bug install-log-encoding-robust-parse`
Change Status: `implemented`

Completed At: 2026-07-01

## Wave Summary

Wave `1p9bf` (Windows Install Robustness) delivered two changes: Post-edit docs-lint hook: bound + configure the subprocess timeout (never hang, never fail early) and Install-log parsing: encoding-robust rows + non-vacuous completeness (no false "install complete").

**Changes delivered:**

- **Post-edit docs-lint hook: bound + configure the subprocess timeout (never hang, never fail early)** (`1p9bg-bug docs-lint-hook-timeout-configurable`) — 4 ACs completed. Key decisions: On timeout, do NOT block the edit (advisory), rather than fail the edit.; Generous default (120 s) + `workflow-config` override, not a bare bump.
- **Install-log parsing: encoding-robust rows + non-vacuous completeness (no false "install complete")** (`1p9bh-bug install-log-encoding-robust-parse`) — 5 ACs completed. Key decisions: Make `_ROW_RE` separator/encoding-agnostic (anchor on structural tokens) rather than adding the `â€"` mojibake to a dash class.; `is_complete([]) → False`; a present-but-zero-rows log is a distinct audit error.
## Journal Watchpoints

- Guard: `framework_edit_allowed` for `render_platform_surfaces.py` / `install_log_lib.py` / `server_impl.py`;
  `seed_edit_allowed` for the install-seed UTF-8 mandate (`1p9bh`).
- Rendered surfaces: `1p9bg` edits hook bodies in `render_platform_surfaces.py` — edit source + re-render,
  never hand-edit a rendered hook; assert an idempotent re-render.
- Vacuous-truth (3rd occurrence): `is_complete([])` must be `False`; audit distinguishes "no log" from
  "present but unparseable". Watch for the same empty-input default at other `all(...)` call sites.
- Fail-safe: the docs-lint timeout must be advisory (non-blocking) — a timeout must never reject an edit.
- Deferred (NOT in this wave): the `#1`/`#4` install hangs are a validation item on the 1.10.0 native-Windows
  install (the zombie-reap in the 1.10.0 bundle + `1p9bg`'s timeout may already resolve them); incremental
  single-file docs-lint is a separate follow-up.

## Review Evidence

- wave-council-readiness: approved 2026-07-01 — READY. Two native-Windows install-robustness bug fixes for 1.10.0. `1p9bg` (docs-lint hook timeout): red-team — a non-blocking *timeout* lets a lint error slip the hook, but the hook is best-effort and `wave_validate`/close are the hard gate; a lint *failure* still blocks (only a timeout is advisory); `isolated_run` forwards `**kwargs` so `timeout=` reaches `subprocess.run` on both paths. `1p9bh` (install-log parse): red-team — loosening `_ROW_RE` risks over-matching, mitigated by anchoring on checkbox + dotted number + `(source)` and asserting non-rows don't match; `is_complete([])→False` is safe (only reached for an existing log); vacuous-truth guard (3rd occurrence). Architecture: both edit the canonical hook/parse sources with a shared helper each — re-render + preserved parser group indices are load-bearing. Security: no secrets/network. Qa-reviewer (required for bug fixes): ACs deterministically testable (timeout helper + timeout⇒not-blocked; four separator forms + `is_complete` arms + unparseable-audit + UTF-8 round-trip); open item — `1p9bh` confirms which install seed writes the log at implementation (seed_edit_allowed), not a readiness blocker. Reality-checker: the UTF-8 write-side fix is root-cause, not scope creep; `#1`/`#4` install hangs correctly deferred to 1.10.0 Windows validation. No blocking findings.
- wave-council-delivery: approved 2026-07-01 — PASS. Delivery review of the shipped docs-lint hook timeout (`1p9bg`) + install-log encoding robustness (`1p9bh`). Computational lanes: docs-lint ok, full suite **3,844 OK**, sensor max-severity none. Red-team: `subprocess.run(timeout=)` kills the child before raising `TimeoutExpired` (no orphan), `maybe_docs_lint` catches it → non-blocking advisory while a real lint FAILURE still blocks (`timeout=None` default keeps every other `run_command` caller unchanged); the `(?:\S+\s+)?` separator relaxation is refuted as an over-match risk by the 38 install-log tests incl. `TemplateParserParityTests` over the real template + the four-separator-form test, and `is_complete([])→False` + the `is_unparseable` guard before CHECK-2 close the vacuous-complete path. Architecture: timeout helper in `indexer.py` (tested) consumed via the hook-helpers load with a 120s fallback; `install_log_lib` keeps its 6-group `parse_row` contract; both edit canonical sources + idempotent re-render. Security: no secrets/network. Qa-reviewer (bug-fix required): deterministic coverage on every arm (timeout default/override/bad/missing; TimeoutExpired advisory; four separator encodings; `is_complete` arms; `is_unparseable`; UTF-8 round-trip). Docs-contract: new `docs_lint.hook_timeout_seconds` documented; `seed-011` UTF-8 mandate carries no wave/ADR IDs. Residual (honest): `write_install_log` is a tested sanctioned UTF-8 writer but the primary enforcement is the `seed-011` guidance (its `python -c …encoding='utf-8'` example); the robust parser + `is_unparseable` are the safety net regardless. No blocking findings.
- operator-signoff: approved 2026-07-01 — operator authorized closure ("Yes, close") after the delivery-council PASS; the two fixes ship in the 1.10.0 bundle.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: making a docs-lint *timeout* non-blocking (`1p9bg`) lets a real lint error slip the post-edit hook, and loosening `install_log_lib._ROW_RE` (`1p9bh`) risks over-matching non-row lines — MITIGATED because the hook was always best-effort (a lint *failure* still blocks; only a *timeout* is advisory) with `wave_validate`/close as the hard gate, and the relaxed row regex stays anchored on the checkbox + dotted step number + `(source)` parenthetical with tests asserting phase-headings/prose do NOT match and the parser's consumed group indices are preserved; the `is_complete([])→False` vacuous-truth guard is safe because it is only reached for a log that exists (3rd occurrence of the empty-input vacuous-truth defect); strongest-alternative: add the `â€"` mojibake to a dash alternation instead of a separator-agnostic regex (rejected — fragile, only fixes the one observed mis-encoding) / block the edit on a docs-lint timeout (rejected — false rejections, worse than skipping). Docs-contract/qa/security: both edit the canonical hook/parse sources with a shared helper each (re-render idempotent; `seed_edit_allowed` for the install-seed UTF-8 mandate — the exact seed confirmed at implementation), ACs deterministically testable, no secrets/network; `#1`/`#4` install hangs deferred to 1.10.0 Windows validation. No blocking findings.)

## Dependencies

- No external wave dependencies.
