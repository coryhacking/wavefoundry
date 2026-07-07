# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-06

wave-id: `1ryuu bootstrap-removal-old-code-window-fix`
Title: Bootstrap Removal Old Code Window Fix

## Objective

**Fast follow-up to 1.11.1: make the `install-wavefoundry.md` root cleanup actually fire on a from-old MCP upgrade (operator-directed, field-reported 2026-07-06).** The 1rxyi removal (shipped in 1.11.1) is wired only into the extract phase, which runs OLD code during a from-old MCP upgrade, so the stray bootstrap file is left in the project root on every upgrade into 1.11.1. `1rych` adds the removal to the new-code `--update-index` phase — the same old-code-window fix `1ryce` already applied for lifecycle provisioning — so a from-old upgrade self-cleans. When this wave closes: an upgrade into the fixed version removes the root `install-wavefoundry.md` even from an older source version, and the seed's "automatic removal" claim holds. Ships as 1.11.2.

## Changes

Change ID: `1rych-bug bootstrap-removal-from-update-index-phase`
Change Status: `implemented`

Completed At: 2026-07-06

## Wave Summary

Wave `1ryuu` (Bootstrap Removal Old Code Window Fix) delivered one change: Upgrade: wire the bootstrap-file removal into the new-code `--update-index` phase so a from-old upgrade cleans it up. Notable adjustments during implementation: Upgrade: wire the bootstrap-file removal into the new-code `--update-index` phase so a from-old upgrade cleans it up: Implemented: added `_remove_root_bootstrap_file(root)` to the `--update-index` phase after `phase_index_update`, next to the `1ryce` lifecycle backstop; extract-phase call unchanged. Added `--update-index` wiring-lock + both-sites tests; updated the extract-phase wiring test to anchor at/after `zf.extractall` (the new call precedes it in source order). Full suite 4727 OK.

**Changes delivered:**

- **Upgrade: wire the bootstrap-file removal into the new-code `--update-index` phase so a from-old upgrade cleans it up** (`1rych-bug bootstrap-removal-from-update-index-phase`) — 4 ACs completed. Key decisions: Add the removal to the new-code `--update-index` phase (keep the extract-phase call).
## Journal Watchpoints

- Watchpoint (`1rych` — new-code execution point): the fix MUST run in the extracted-pack (new) code — the only new code during a from-old-version MCP upgrade is the `upgrade_wavefoundry.py` subprocess post-extract. The `--update-index` phase is the reliably-invoked new-code phase (this is exactly where `1ryce` put the lifecycle backstop, `:2479`); the extract-phase call (`:2668`) runs OLD code on a from-old upgrade and cannot be relied on for that transition. Do NOT move or remove the extract-phase call — ADD the `--update-index` call alongside it (belt-and-suspenders).
- Watchpoint (`1rych` — no new safety work): `_remove_root_bootstrap_file` is already idempotent (missing file = no-op) and fail-safe (catches `OSError`, logs, never raises). The added call inherits both; it must never abort or gate the `--update-index` phase. Running the removal twice (extract + update-index) is a harmless no-op.
- Watchpoint (`1rych` — no seed/contract change): scope is confined to `upgrade_wavefoundry.py` + tests. The seed 012/160 "automatic removal" claim becomes accurate for from-old upgrades once this lands — do NOT edit the seeds.
- Watchpoint (release): ships as 1.11.2; VERSION bump + CHANGELOG + package happen at the release step (not inside the change). Do NOT republish 1.11.1 — a published version is a frozen artifact.

## Participants

- code-reviewer — the single-surface `upgrade_wavefoundry.py` `--update-index` removal call
- qa-reviewer — required for bug fixes (`review_policies.require_qa_reviewer_for_bug_fixes`); AC priority table present on the change

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, qa-reviewer, reality-checker; rotating-seat: reality-checker; strongest-challenge: whether adding the removal to `--update-index` could double-delete or interfere with the extract-phase call — resolved by the helper's idempotence (a missing file is a no-op) so the second call is harmless; strongest-alternative: move the removal out of the extract phase into `--update-index` only — rejected because the extract-phase call is correct and sufficient for from-≥fixed upgrades, so keeping both is strictly safer belt-and-suspenders)
- Council seat notes: reality-checker — verified against source: the removal is wired ONLY at `upgrade_wavefoundry.py:2668` (extract phase, Phase 0b after `zf.extractall`); the `1ryce` lifecycle backstop sits at `:2479` in the `--update-index` branch (the proven new-code execution point); `_remove_root_bootstrap_file` (`:675`) is idempotent (`path.exists()` guard) and fail-safe (catches `OSError`, logs, swallows); the old-code window is the same one `1ryce` addressed (a running orchestrator keeps loaded bytecode after overwriting its own `.py`, so extract runs old code while the `--update-index` subprocess runs the extracted new code). qa-reviewer — deterministic coverage required: a source-assertion wiring-lock (`--update-index` calls the removal after `phase_index_update`), present→removed / absent→no-op on the helper, and both call sites present; qa-reviewer required per `review_policies.require_qa_reviewer_for_bug_fixes` and rostered. red-team — the only real risks are double-delete (closed by idempotence) and aborting the index phase (closed by the inherited fail-safe catch); no seed/contract surface is touched, so no drift risk. seat_agreement: unanimous; one small single-surface change mirroring a proven fix; no challenge round.
- AC priority: confirmed at prepare as proposed (AC-1..4 required). qa-reviewer assigned per `review_policies.require_qa_reviewer_for_bug_fixes`. Product-owner acknowledgment: operator-reported field finding, operator-directed for a 1.11.2 fast follow-up.

## Review Evidence

- wave-council-readiness: approved 2026-07-06 — prepare council synthesis verdict READY. Load-bearing claims verified against source: the removal is wired only in the extract phase (`:2668`), the `1ryce` new-code backstop point is `:2479`, and `_remove_root_bootstrap_file` (`:675`) is idempotent + fail-safe. The fix mirrors the proven `1ryce` old-code-window pattern exactly, adds one idempotent/fail-safe call to the new-code `--update-index` phase, keeps the extract-phase call (belt-and-suspenders), and touches no seed/contract surface. Seats unanimous; no amendment. Full synthesis in Review Checkpoints.
- wave-council-delivery: approved (2026-07-06 — moderator: wave-council; adversarial delivery review against the actual code and tests; no blocking findings. **code-reviewer** — `_remove_root_bootstrap_file(root)` is added in the `args.update_index` branch immediately after `phase_index_update(root)` and next to `_ensure_lifecycle_policy_backstop(root)` (the proven `1ryce` new-code point), inside the phase's `try/finally`; the extract-phase call (Phase 0b, after `zf.extractall`) is untouched, so the two sites are genuine belt-and-suspenders — from-≥fixed upgrades clean at extract, from-old upgrades clean at `--update-index`. Reusing the existing helper means the added call inherits its idempotence (`path.exists()` guard) and fail-safe `OSError` catch verbatim — a from-old upgrade whose extract left the file now removes it, a repo without the file no-ops, and an unlink error is logged and swallowed so the index phase never aborts. No seed/contract/behavior surface beyond the one call. **qa-reviewer** — deterministic coverage: `test_update_index_phase_wires_the_bootstrap_removal` locks the new wiring (removal call after `phase_index_update`), `test_removal_wired_at_both_extract_and_update_index_sites` asserts both sites survive (≥2 call sites; the `(root: Path)` def line does not match `(root)` so the count is exactly the two calls), and the pre-existing `test_extract_phase_wires_the_cleanup_after_extractall` was correctly updated to anchor on the first call AT OR AFTER `zf.extractall` — necessary because the new `--update-index` call precedes the extract block in source order and would otherwise have been matched as the "first" occurrence, silently breaking the extract-phase lock. Present→removed / absent→no-op / unlink-error-swallowed / reserved-name-only remain green. `RemoveRootBootstrapFileTests` 7/7; full framework suite 4727 OK bytecode-free; `wave_validate` clean. Synthesis verdict: SHIP — one small single-surface change cloning an already-reviewed fix; the only subtlety (the source-order shift breaking the old wiring test) was caught and corrected in the same change.)
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies.
