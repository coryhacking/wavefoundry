# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-27

wave-id: `1p8ev upgrade-reconciliation`
Title: Upgrade Reconciliation

## Objective

Turn upgrade-time reconciliation of retired/renamed framework surfaces from manual, hand-rolled per-consumer work into a built-in upgrade routine: a minor+ upgrade scans for stale references to retired surfaces (the proven scan, lifted out of a unittest and driven by one shared retired→new map) and surfaces an actionable `file:line → suggested wf form` list, and the `wave_upgrade` response gains a structured summary so agents act on fields instead of parsing a blob. Motivated by the 1.8.1→1.9.4 downstream upgrade where the consumer hand-rolled a ~34-file sed swap.

## Changes

Change ID: `1p8et-enh upgrade-retired-surface-reconciliation`
Change Status: `implemented`

Change ID: `1p8eu-enh structured-wave-upgrade-summary`
Change Status: `implemented`

Completed At: 2026-06-27

## Wave Summary

Wave `1p8ev` (Upgrade Reconciliation) delivered two changes: Upgrade-time retired-surface reconciliation routine and Structured wave_upgrade summary. Notable adjustments during implementation: Upgrade-time retired-surface reconciliation routine: Adversarial-review fixes (pre-1.9.4): SCAN-1 `_LITERAL_PATTERN` separator char class `[\\/]` (catches Windows-backslash + mixed refs); SCAN-2 `is_excluded` now component/prefix-matches EXCLUDED_DIRS (mirrors `build_pack.should_exclude`), root-only `CHANGELOG.md`, `journals`/`snapshots` as path components, `tests` component + `test_` filename; INV-recline added `StaleReference.matched` and the actionable list prints it; live self-host scan still 0 offenders.; Structured wave_upgrade summary: Implemented. `_build_upgrade_summary` assembles the dict once; `_print_operator_summary` renders prose + the `WAVE_UPGRADE_SUMMARY_JSON:` sentinel from it (carrying the 1p8et `reconciliation` findings). `server_impl._parse_upgrade_summary` parses the sentinel into `data['summary']`, fail-safe; `_upgrade_next_step` adds `next_step` + `next_tools`; `output`/`exit_code` unchanged. seed-160 + mcp-tool-surface note added.

**Changes delivered:**

- **Upgrade-time retired-surface reconciliation routine** (`1p8et-enh upgrade-retired-surface-reconciliation`) — 7 ACs completed. Key decisions: --------; Reconciliation is an upgrade helper routine, not a standalone command.
- **Structured wave_upgrade summary** (`1p8eu-enh structured-wave-upgrade-summary`) — 5 ACs completed. Key decisions: --------; Additive `summary` field; keep `output`/`exit_code`.
## Journal Watchpoints

- **Follow-up — one shared retired→new map:** the scan, the seed example, and the recommendation text must all consume a single hand-authored map co-located with `_RETIRED_BIN_WRAPPERS`; a second copy is a drift hazard (cover with an anti-duplication test).
- **Watchpoint — reconciliation is upgrade-time-only:** do NOT add a standalone `wf reconcile` / `wave_reconcile` surface (operator decision); the scan runs inside the upgrade reconciliation phase.
- **Blocking risk — non-1:1 mapping:** `mcp-server` has no `wf` replacement (the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`); the map must emit "remove/rewrite", never a wrong `wf` form.
- **Serialization — shared upgrade files:** `1p8et` and `1p8eu` both edit `upgrade_wavefoundry.py` and `server_impl.py` `wave_upgrade`; land the map + scan helper (`1p8et`) first, then the structured summary (`1p8eu`) consumes the reconciliation findings.
- **Safety — report-only default:** the scan must not auto-mutate repo-authored docs by default; bake in the exclusion set (framework pack, `.wavefoundry/index/`, `docs/waves/`, `CHANGELOG.md`, journals/snapshots).

## Participants

| Lane | Phase | Scope |
| --- | --- | --- |
| implementer | implementation | both admitted changes |
| code-reviewer | review | scan helper, retired→new map, upgrade wiring, wave_upgrade summary |
| architecture-reviewer | review | upgrade reconciliation phase + wave_upgrade response contract |
| qa-reviewer | review | exclusion coverage, self-host guard, fallback tests, full suite |
| release-reviewer | review/council rotating seat | distribution reachability (helper ships, not stripped by build_pack) |
| docs-contract-reviewer | review | seed-160 + mcp-tool-surface guidance |

## Review Evidence

- wave-council-readiness: passed 2026-06-27 — plan grounded in the adversarially-verified trace-mining synthesis + the 1.8.1→1.9.4 field trace; design confirmed as an upgrade-time routine (no standalone command); ACs testable; distribution-reachability and the non-1:1 `mcp-server` mapping captured; serialization across the two changes defined. Ready to implement.
- operator-signoff: approved 2026-06-27 — operator authorized close + the official 1.9.4 release.
- code-reviewer: passed 2026-06-27 — adversarial implementation review found 0 blockers; all confirmed findings fixed and re-verified (the 2 HIGH: Windows-backslash scan blind spot + double-defined summary sentinel); reconcile_scan single-sources the retired→new map; full suite 3555 green.
- architecture-reviewer: passed 2026-06-27 — upgrade-time-only design intact (reconcile_scan is a pure importable helper — no `wf` subcommand, no `wave_reconcile` MCP tool); the wave_upgrade `summary` is additive and back-compatible; sentinel single-sourced via import after the fix.
- qa-reviewer: passed 2026-06-27 — full suite 3555 (+13), docs-lint clean; exclusion coverage + the self-host guard are non-vacuous; fail-safe missing/corrupt-summary fallback tested; the HIGH faithfulness fixes runtime-verified on adversarial inputs (backslash refs flagged, in-scope near-misses caught, true exclusions hold).
- release-reviewer: passed 2026-06-27 — reconcile_scan ships (build_pack.should_exclude=False, asserted); the downstream p8fn upgrade adopted the new content cleanly (scanner ships + runs, seed-160 guidance landed).
- docs-contract-reviewer: passed 2026-06-27 — seed-160 is source-of-truth with the rendered prompt mirrored and a seed↔map parity test added; mcp-tool-surface documents the `summary` block; the allow-rule flag-for-operator guidance was validated in the field.
- wave-council-delivery: passed 2026-06-27 — moderator: wave-council; seats: code-reviewer, architecture-reviewer, qa-reviewer, release-reviewer, docs-contract-reviewer, red-team; synthesis: 0 blockers; all 10 actionable findings fixed and re-verified, 1 deprioritized-as-covered; all five hard invariants hold; suite 3555 + downstream p8fn validation; ready to close.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-27: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: report-only default could look like it only half-removes the friction — resolved because the costly part was BUILDING the exclusion-aware scan/map, not applying a precise file:line list, so report-only removes the real cost and auto-fix stays a deferred opt-in; strongest-alternative: a standalone wf reconcile / wave_reconcile command — rejected because reconciliation is upgrade-time-only and a permanent command surface adds a discovery problem.)

## Prepare Review Evidence

- code-reviewer: passed 2026-06-27 — plan is implementable with clear targets; lifting the proven scan into a shared shipped helper, one retired→new map, and a fail-safe wave_upgrade summary parse are sound; no architectural red flags.
- architecture-reviewer: passed 2026-06-27 — upgrade-routine design is correct (reconciliation is upgrade-time-only; no standalone command); the wave_upgrade summary is additive; reuses `_RETIRED_BIN_WRAPPERS`, `_docs_gate_summary_line`, `_is_major_or_minor_upgrade`; no new boundary.
- qa-reviewer: passed 2026-06-27 — ACs are testable: exclusion coverage, self-host guard via the shared helper, fail-safe missing/corrupt-summary fallback, and an anti-duplication test for the single map.
- release-reviewer: passed 2026-06-27 — distribution reachability is an explicit AC (the helper must ship, not be stripped by build_pack `EXCLUDED_REL_PATHS`) — the exact trap that hid the scan in a unittest.
- docs-contract-reviewer: passed 2026-06-27 — seed-160 stays source-of-truth with the rendered prompt mirrored; mcp-tool-surface note planned; the two changes' shared-file edits (`upgrade_wavefoundry.py`, `server_impl.py`) are serialization-coordinated.

## Dependencies

- `1p8eu-enh structured-wave-upgrade-summary` depends on `1p8et-enh upgrade-retired-surface-reconciliation` for the reconciliation-findings field shape.
- No external wave dependencies.
