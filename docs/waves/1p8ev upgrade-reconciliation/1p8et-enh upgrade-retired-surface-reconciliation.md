# Upgrade-time retired-surface reconciliation routine

Change ID: `1p8et-enh upgrade-retired-surface-reconciliation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8ev upgrade-reconciliation`

## Rationale

When a minor-or-major upgrade **retires or renames** a framework surface, every reference in a consumer's repo-authored docs/configs to the old surface becomes a broken instruction. The live example: the 1.9.0 cutover retired the per-command `.wavefoundry/bin/*` wrappers for the cross-OS `wf` dispatcher, so a doc naming `.wavefoundry/bin/docs-lint` is now wrong.

Today the upgrade flow only emits **recommend-only prose** (`upgrade_wavefoundry._reconciliation_recommendation_lines` → seed-160 step 6) and stops there, so every consumer hand-rolls a fragile scan. A downstream 1.8.1→1.9.4 field upgrade had to: grep ~34 files / ~100 refs, manually derive the exclusion set (framework pack tree, generated `.wavefoundry/index/`, historical records), build a 4-pattern retired→new map by hand, nearly include generated index artifacts, and re-run a bash `mapfile` loop under `bash` because the shell was zsh. The **proven scan logic already exists** — but only as a unittest guard (`tests/test_wf_cli.py`) that `build_pack` strips from the distribution, so it is unreachable downstream.

Reconciliation is fundamentally an **upgrade-time event** (a reference only goes stale when a surface changes, which only happens crossing a version boundary — one-time per cutover, recurring across the framework's life but always at upgrade time). So the fix belongs in the **upgrade routine**, not a standalone `wf reconcile` command or `wave_reconcile` MCP tool — those add a permanent command surface and a discovery problem for an upgrade-only concern (operator decision, 2026-06-27).

## Requirements

1. Author ONE data-driven retired→new mapping table, co-located with `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`, keyed by retired surface name → replacement (`wf <subcommand>` or `None`). It must cover the non-1:1 cases: renames (`wave-dashboard`→`wf dashboard`, `wave-gate`→`wf gate`, `update-indexes`→`wf update-indexes`, `upgrade-wavefoundry`→`wf upgrade`, `setup-wavefoundry`→`wf setup`, `docs-lint`→`wf docs-lint`, `docs-gardener`→`wf docs-gardener`, `lifecycle-id`→`wf lifecycle-id`) and the no-replacement case (`mcp-server` has no `wf` form → emit "remove/rewrite; the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`").
2. Lift the retired-surface scan (the literal `.wavefoundry/bin/<wrapper>` pattern + the dynamic/variable bin-join patterns + the exclusion set) out of the unittest guard into a **shared, shipped helper module** reachable from the upgrade flow (not under `scripts/tests/`, not in `build_pack` `EXCLUDED_REL_PATHS`).
3. The helper scans a repo for stale references to retired surfaces and returns **structured** results (file, line, matched retired surface, suggested replacement), with the exclusion set baked in: framework pack tree (`.wavefoundry/framework/`), generated/runtime artifacts (`.wavefoundry/index/`), history (`docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots), and test files.
4. The upgrade flow's reconciliation phase RUNS the scan on a **major or minor** bump and surfaces the actionable `file:line → suggested wf form` list in its output, replacing the recommend-only prose. Default is **report-only** (the agent/operator applies edits); no destructive auto-fix by default.
5. The seed (`160-upgrade-wavefoundry.prompt.md`) reconciliation guidance and the recommendation text consume the SAME map, so the seed example, the renderer deletion list, and the recommendation cannot drift.
6. The Wavefoundry self-host retired-surface test guard remains green via the shared helper (single source — the test asserts through the helper, not a duplicated regex).
7. seed-160 reconciliation guidance also names host permission/allow-rule files (e.g. `.claude/settings.local.json` allow rules + per-host equivalents) as a reconciliation surface, framed **flag-for-operator** (agents cannot self-edit those under host auto-mode guards).
8. seed-160 step 11 (docs gate) names the **gate-before-reload window**: when MCP is attached but still the pre-upgrade impl, the `wf` CLI docs gate is the correct path, not only a no-MCP fallback.

## Scope

**Problem statement:** upgrade reconciliation of retired/renamed surfaces is manual, fragile, and hand-rolled per consumer; the proven scan is trapped in a unittest and stripped from the pack.

**In scope:**

- The shared, shipped scan helper (patterns + exclusions) and the structured result shape.
- The single retired→new mapping table beside `_RETIRED_BIN_WRAPPERS`.
- Wiring the scan into the upgrade reconciliation phase and its output (report-only).
- seed-160 reconciliation guidance updates (name the scan; the allow-rule surface; the gate-before-reload window) + re-render of the rendered upgrade prompt.
- Keeping the self-host test guard green via the shared helper.

**Out of scope:**

- A standalone `wf reconcile` CLI subcommand or `wave_reconcile` MCP tool (reconciliation is upgrade-time-only; rejected to avoid a permanent command surface + discovery problem).
- Destructive auto-fix by default (an opt-in apply mode is a possible later enhancement, not this change).
- The structured `wave_upgrade` summary envelope (sibling change `1p8eu-enh structured-wave-upgrade-summary`); this change only produces the reconciliation findings that change consumes.

## Acceptance Criteria

- [x] AC-1: a single retired→new mapping table exists (co-located with `_RETIRED_BIN_WRAPPERS`), covers the rename + no-replacement (`mcp-server`) cases, and is the one source consumed by the scan, the seed example, and the recommendation text; a test asserts there is no second hand-authored copy.
- [x] AC-2: a shipped (non-test) shared helper scans a repo and returns structured stale-reference results (file, line, retired surface, suggested replacement); it is importable from the upgrade flow and is not under `scripts/tests/` nor in `build_pack` `EXCLUDED_REL_PATHS`.
- [x] AC-3: the upgrade reconciliation phase runs the scan on a major/minor bump and surfaces the actionable `file:line → suggested wf form` list in the upgrade output, replacing the recommend-only prose; report-only by default.
- [x] AC-4: the exclusion set is enforced — the scan does not flag the framework pack tree, `.wavefoundry/index/`, `docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots, or test files; tests cover each exclusion.
- [x] AC-5: the self-host retired-surface guard passes via the shared helper (no duplicated regex) and catches a reintroduced retired-surface reference.
- [x] AC-6: seed-160 reconciliation guidance names host allow-rule files as a reconciliation surface (flag-for-operator) and names the gate-before-reload CLI window; the rendered upgrade prompt matches; docs-lint passes.
- [x] AC-7: full framework suite and docs-lint pass.

## Tasks

- [x] Author the retired→new map beside `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`.
- [x] Extract the scan (patterns + exclusions) from `tests/test_wf_cli.py` into a shared shipped helper module.
- [x] Wire the scan into `upgrade_wavefoundry`'s reconciliation phase; replace recommend-only prose with the actionable list (report-only).
- [x] Update seed-160 (name the scan; allow-rule surface; gate-before-reload) and re-render `docs/prompts/upgrade-wavefoundry.prompt.md`.
- [x] Repoint the self-host retired-surface test guard at the shared helper.
- [x] Run full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Map + helper | implementer | — | Single retired→new map; lift scan from the test. |
| Upgrade wiring | implementer | Map + helper | Run scan in the reconciliation phase; report-only. |
| Seed/docs | docs-contract-reviewer | Upgrade wiring | seed-160 guidance + re-render; keep map-consuming text in lockstep. |
| QA | qa-reviewer | all | Exclusion coverage, self-host guard, full suite. |

## Serialization Points

- The retired→new map + the shared helper must land before the upgrade-wiring and the seed edits (so all consume the one map).
- Coordinate with sibling `1p8eu` on `upgrade_wavefoundry.py` and `server_impl.py` `wave_upgrade` (the reconciliation findings become a field in that change's structured summary).

## Affected Architecture Docs

`docs/references/native-windows-support.md` (the reconciliation story is documented there). Architecture hub / ADR `N/A` — no new boundary; this turns an existing recommend-only phase into a scan, reusing the established renderer map.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | One map is the anti-drift contract. |
| AC-2 | required | The helper must ship to be reachable downstream. |
| AC-3 | required | The core behavior: scan at upgrade, not prose. |
| AC-4 | required | Wrong exclusions corrupt history/generated files. |
| AC-5 | required | Self-host guard must not regress. |
| AC-6 | important | Closes the allow-rule + gate-before-reload guidance gaps. |
| AC-7 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from the 1.8.1→1.9.4 downstream upgrade field trace + trace-mining synthesis. | Consumer hand-rolled a ~34-file/~100-ref sed swap; proven scan trapped in `tests/test_wf_cli.py`; reconciliation is upgrade-time-only. |
| 2026-06-27 | Implemented. One map `_RETIRED_SURFACE_REPLACEMENTS` + `retired_surface_suggestion()` in `render_platform_surfaces.py`; shipped helper `reconcile_scan.py` (`scan_repo` → `StaleReference`); wired into `upgrade_wavefoundry._print_operator_summary` via `_run_reconciliation_scan` + rewritten `_reconciliation_recommendation_lines` (actionable list, report-only); seed-160 + rendered prompt + mcp-tool-surface updated; self-host guard repointed at the helper. | `test_reconcile_scan` 12 pass; `test_wf_cli` 16 pass (incl. reintroduced-ref catch); `test_upgrade_wavefoundry` 237 pass; `test_server_tools`/`test_build_pack`/`test_render_platform_surfaces` pass; docs-lint ok; full suite 3542 tests pass after the prompt-parity assertion update. |
| 2026-06-27 | Adversarial-review fixes (pre-1.9.4): SCAN-1 `_LITERAL_PATTERN` separator char class `[\\/]` (catches Windows-backslash + mixed refs); SCAN-2 `is_excluded` now component/prefix-matches EXCLUDED_DIRS (mirrors `build_pack.should_exclude`), root-only `CHANGELOG.md`, `journals`/`snapshots` as path components, `tests` component + `test_` filename; INV-recline added `StaleReference.matched` and the actionable list prints it; live self-host scan still 0 offenders. | New tests: backslash/mixed flagged, near-miss in-scope (`docs/reports-overview.md`, `src/snapshotter.py`, nested `CHANGELOG.md`), non-framework `src/tests/test_*` excluded + `src/tests/helper.py` in-scope, negative controls (`bin_dir/"wf"`, `docs-lint-extra`) zero, seed/prompt arrow↔map parity (TA-4), `should_exclude` real ship gate (TA-5), `matched` for .py-join. `test_reconcile_scan` 20 pass; full suite 3555 pass; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Reconciliation is an upgrade helper routine, not a standalone command. | Reconciliation is upgrade-time-only; a `wf reconcile`/`wave_reconcile` adds a permanent command surface + a discovery problem. | Standalone `wf reconcile` + `wave_reconcile` (rejected: kitchen-sink + discovery); leave recommend-only prose (rejected: each consumer hand-rolls a fragile sed). |
| 2026-06-27 | Default report-only; auto-fix opt-in deferred. | The scan mutating repo-authored docs is the risky part; reliable reporting removes the friction without that risk. | Default `--fix` (rejected for now: mutation risk). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The retired→new map mis-maps a non-1:1 case (`mcp-server` has no wf form). | Hand-author the map; `mcp-server`→"remove/rewrite, python3 server.py"; test the no-replacement case. |
| Wrong exclusions corrupt history/generated files. | Bake in the exclusion set the field agent re-derived; cover each exclusion with a test. |
| Map/scan/seed drift over time. | One shared map consumed by scan + seed + recommendation; a test asserts no second copy. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
