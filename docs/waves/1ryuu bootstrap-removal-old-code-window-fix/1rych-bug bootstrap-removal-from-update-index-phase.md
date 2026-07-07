# Upgrade: wire the bootstrap-file removal into the new-code `--update-index` phase so a from-old upgrade cleans it up

Change ID: `1rych-bug bootstrap-removal-from-update-index-phase`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1ryuu bootstrap-removal-old-code-window-fix`

## Rationale

Field-reported (external operator, 2026-07-06): upgrading a repo from 1.11.0 to 1.11.1 left the single-use bootstrap `install-wavefoundry.md` in the project root — the exact file the just-shipped 1rxyi fix (wave `1rycd`, in 1.11.1) was supposed to auto-remove. The agent deleted it manually and flagged that the seed's "automatic removal" claim did not hold.

**Root cause — the "upgrade runs old code" window ([[project_upgrade_old_code_window]]), the same class of bug as `1ryce`.** `_remove_root_bootstrap_file` is wired into **only** the extract phase (`upgrade_wavefoundry.py:2668`, Phase 0b, right after `zf.extractall`). On an MCP `wave_upgrade` the extract is performed by the **old** in-process orchestrator — a running Python process keeps its already-loaded bytecode even after it overwrites its own `.py` on disk — so a from-`<1.11.1>` upgrade runs the old extract code, which has no removal helper, and the file is left behind. Only the `--update-index` phase runs as a fresh subprocess against the freshly-extracted **new** code. `1rxyi` (wave `1rycd`) closed before the old-code window was understood, so it never got the `--update-index` treatment that `1ryce` was given (`:2479`). Because 1.11.1 is the current latest release, **every** upgrade into 1.11.1 from any prior version leaves the stray file; from-≥1.11.1 upgrades self-correct (1.11.1's extract code has the helper).

**Fix:** also call `_remove_root_bootstrap_file(root)` from the `--update-index` phase, next to the existing `_ensure_lifecycle_policy_backstop(root)` call — the only new-code phase a from-old MCP upgrade reliably invokes post-extract. Belt-and-suspenders with the existing extract-phase call: from-≥fixed upgrades clean at extract, from-old upgrades clean at `--update-index`. The helper is already idempotent (missing file = no-op) and fail-safe (best-effort unlink, catches `OSError`, never aborts the phase), so no new safety work is required.

## Requirements

1. **Provision removal from the new-code phase.** Add a `_remove_root_bootstrap_file(root)` call to the `--update-index` phase of `upgrade_wavefoundry.py` (the `args.update_index` branch, next to `_ensure_lifecycle_policy_backstop(root)` at `:2479`). Rationale: the `--update-index` subprocess runs the freshly-extracted NEW `upgrade_wavefoundry.py`, and every MCP upgrade flow invokes it after `preflight`.
2. **Keep the existing extract-phase call.** The extract-phase removal (`:2668`) stays as-is — this ADDS one more new-code execution point, it does not move or remove the existing one. Running the removal twice is a no-op (a missing file is a no-op).
3. **No new safety work.** The removal is already idempotent + fail-safe; the added call inherits both. It must never abort or gate the `--update-index` phase.
4. Local-only, stdlib only; no new dependency; no seed or contract change (the seed 012/160 "automatic removal" claim becomes accurate for from-old upgrades once this lands).

## Scope

**Problem statement:** The bootstrap-file removal runs only in the extract phase, which executes old code on a from-old MCP upgrade, so the removal never fires on the upgrade *into* the version that introduces it — the stray `install-wavefoundry.md` is left in the project root on every upgrade into 1.11.1.

**In scope:**

- `upgrade_wavefoundry.py`: add the idempotent, fail-safe `_remove_root_bootstrap_file(root)` call to the `--update-index` phase.
- Tests: a wiring-lock (removal called in `--update-index` after `phase_index_update`) plus present→removed / absent→no-op behavior coverage on the `--update-index` path.

**Out of scope:**

- The extract-phase call (`:2668`) — unchanged.
- Any change to `_remove_root_bootstrap_file` itself (already idempotent + fail-safe).
- Seed/doc edits — the "automatic removal" claim becomes accurate once this lands; no wording change needed.
- Retroactively cleaning repos already upgraded to 1.11.1 (they self-correct on their next upgrade, or a one-time manual `rm`).

## Acceptance Criteria

- [x] AC-1: The `--update-index` phase of `upgrade_wavefoundry.py` calls `_remove_root_bootstrap_file(root)`; a source-assertion wiring-lock test asserts the call exists in the `--update-index` handler after `phase_index_update(root)`. — call added next to `_ensure_lifecycle_policy_backstop(root)` right after `phase_index_update`; `test_update_index_phase_wires_the_bootstrap_removal` locks it (removal call after `phase_index_update`).
- [x] AC-2: Running the `--update-index` removal against a root that has an `install-wavefoundry.md` deletes it, and against a root without one is a no-op (fail-safe); a deterministic test covers both. — the reused `_remove_root_bootstrap_file` helper is covered by `test_removes_present_bootstrap_file` / `test_absent_is_noop` / `test_unlink_error_is_swallowed` (present→removed, absent→no-op, unlink error swallowed).
- [x] AC-3: The existing extract-phase removal (`:2668`) is unchanged; a test/inspection confirms both call sites are present. — extract-phase call untouched; `test_removal_wired_at_both_extract_and_update_index_sites` asserts ≥2 call sites; `test_extract_phase_wires_the_cleanup_after_extractall` updated to anchor on the call at/after `zf.extractall` (still locks the extract-phase call).
- [x] AC-4: Full framework tests run bytecode-free and docs validation passes. — `run_tests.py`: 4727 tests OK (bytecode-free); `wave_validate` at wave verification.

## Tasks

- [x] Add the idempotent, fail-safe `_remove_root_bootstrap_file(root)` call to the `args.update_index` branch of `upgrade_wavefoundry.py`, next to `_ensure_lifecycle_policy_backstop(root)`. — added after `phase_index_update(root)`.
- [x] Tests: `--update-index` wiring-lock; present→removed / absent→no-op on the removal helper; both call sites present. — `test_update_index_phase_wires_the_bootstrap_removal` + `test_removal_wired_at_both_extract_and_update_index_sites`; existing present/absent/error helper tests reused; `test_extract_phase_wires_the_cleanup_after_extractall` updated for the second call site. `RemoveRootBootstrapFileTests` (7) green.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — suite 4727 OK; `wave_validate` at wave verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| update-index-removal | implementer | — | Idempotent/fail-safe removal call in `--update-index` |
| tests | qa-reviewer | update-index-removal | wiring-lock + present/absent + both-sites |


## Serialization Points

- Single-file production change in `upgrade_wavefoundry.py` (the `--update-index` phase). Same file + phase region as the closed `1ryce` (which added the lifecycle backstop at the same point); no other surface touched.

## Affected Architecture Docs

N/A — a provisioning-timing fix in the upgrade script; no contract change. The removal helper and its behavior are unchanged; only an additional new-code execution point is added (directly mirroring `1ryce`).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — a from-old upgrade must remove the stray file via the new-code phase. |
| AC-2 | required | The removal must delete a present file and no-op on an absent one (fail-safe). |
| AC-3 | required | Must not disturb the existing extract-phase removal (belt-and-suspenders preserved). |
| AC-4 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Field-reported from a 1.11.0→1.11.1 MCP upgrade that left the root `install-wavefoundry.md`; root cause confirmed = the old-code window (removal wired only into the extract phase, which runs old code on a from-old upgrade), identical class to `1ryce`. Fix: provision the removal from the new-code `--update-index` phase. | `upgrade_wavefoundry.py:2668` (extract-phase call), `:2479` (the `1ryce` backstop location to mirror), `:675` (`_remove_root_bootstrap_file`). |
| 2026-07-06 | Implemented: added `_remove_root_bootstrap_file(root)` to the `--update-index` phase after `phase_index_update`, next to the `1ryce` lifecycle backstop; extract-phase call unchanged. Added `--update-index` wiring-lock + both-sites tests; updated the extract-phase wiring test to anchor at/after `zf.extractall` (the new call precedes it in source order). Full suite 4727 OK. | `upgrade_wavefoundry.py` (`--update-index` removal call); `test_upgrade_wavefoundry.py::RemoveRootBootstrapFileTests` (7 tests). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Add the removal to the new-code `--update-index` phase (keep the extract-phase call). | It is the only new-code phase a from-old MCP upgrade reliably invokes post-extract; mirrors the proven `1ryce` fix exactly. | Move the removal out of the extract phase (rejected — extract-phase removal is correct for from-≥fixed upgrades; keep both). Republish 1.11.1 (rejected — a published version is a frozen artifact; a fix gets a new version). Do nothing (rejected — every upgrade into 1.11.1 leaves the stray file, undermining the headline 1rxyi fix). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Double removal (extract phase + update-index) | The helper is idempotent — a missing file is a no-op; the second call does nothing. |
| The added call aborts the index update | Fail-safe: `_remove_root_bootstrap_file` catches `OSError` and logs a non-fatal warning; it never raises. |
| Terminal old-code window (the very first upgrade from a version predating this fix) | Inherent and unavoidable for any new-code phase; harm is a single inert, self-correcting stray file, and a from-`≥this-version` upgrade cleans it at extract thereafter. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
