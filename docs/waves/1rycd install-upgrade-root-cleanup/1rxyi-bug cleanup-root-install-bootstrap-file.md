# Install/upgrade leave the bootstrap install-wavefoundry.md in the project root

Change ID: `1rxyi-bug cleanup-root-install-bootstrap-file`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rycd install-upgrade-root-cleanup`

## Rationale

The distribution zip ships `install-wavefoundry.md` at the **zip root** (`build_pack.py:828` — `zf.writestr("install-wavefoundry.md", …)`), by design: the install agent must discover the bootstrap instructions before `.wavefoundry/` is known (`test_build_pack.py` AC-7 asserts it ships at the zip root, NOT under `.wavefoundry/`). When the operator drops the zip and it is unpacked, `install-wavefoundry.md` lands at the **project root**.

The problem: nothing ever removes it. It is a single-use bootstrap file, but:
- After a fresh **install** it is left in the project root (consumed, but never cleaned up).
- On every **upgrade** the flow re-extracts the whole zip (`unzip -o <zip> -d .` in seed-160 step 0 / `zf.extractall(str(root))` in `upgrade_wavefoundry.py:2627`), re-dropping `install-wavefoundry.md` at the root. The prune step (`prune_framework.py`) only diffs the MANIFEST, which covers `.wavefoundry/framework/` paths — it never touches a root-level file — so the bootstrap file is re-created and left behind on every upgrade.

The canonical install instructions live in the rendered `docs/prompts/install-wavefoundry.prompt.md` (and the seeds), so the root bootstrap copy has no post-install value. It should be removed after install/upgrade so it does not clutter the operator's project root.

## Requirements

1. **Upgrade removes the re-dropped bootstrap file (mechanical/automatic).** `upgrade_wavefoundry.py` must delete `install-wavefoundry.md` from the repository root after extraction, so both the MCP `wave_upgrade` path and the `wf upgrade` CLI path clean it up without relying on the agent. Best-effort / fail-safe: a missing file or an unlink error must NOT fail the upgrade.
2. **Upgrade CLI-fallback docs.** The seed-160 no-MCP CLI fallback (step 0, after the prune step) must document removing the root `install-wavefoundry.md` (`rm -f install-wavefoundry.md`) so the fully-manual path also cleans it up.
3. **Install removes the consumed bootstrap file.** The install procedure (seed-012) must, after the final `wave_install_audit()` returns `complete` (step 2.13), delete `install-wavefoundry.md` from the project root — it was only needed to bootstrap; the canonical instructions live in `docs/prompts/install-wavefoundry.prompt.md`.
4. **Do NOT change where the zip ships it.** `install-wavefoundry.md` must still ship at the zip root (the bootstrap-discovery contract; `test_build_pack.py` AC-7). This change is a post-install/upgrade cleanup of the extracted copy, not a packaging-layout change.
5. **Delete, not move.** Remove the file rather than relocating it into `.wavefoundry/` — it is transient and single-use, and a `.wavefoundry/` copy would go stale and be re-created on the next upgrade. (Operator gave the delete-or-move choice; delete is the simplest that satisfies "not left in the project root".)
6. Local-only, stdlib only; no new dependency. Cross-platform (the upgrade removal must work on the WSL2 upgrade path and native paths).

## Scope

**Problem statement:** The single-use bootstrap `install-wavefoundry.md`, shipped at the zip root, is left in the project root after every install and re-created + left there on every upgrade, because nothing cleans up root-level extracted files.

**In scope:**

- `upgrade_wavefoundry.py`: remove the root `install-wavefoundry.md` after extraction (fail-safe), logged.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`: CLI-fallback step documents the manual removal.
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md` (and a pointer in `010`): final cleanup step after install completes.
- Rendered `docs/prompts/{install,upgrade}-wavefoundry.prompt.md`: sync the cleanup guidance.
- Tests: `upgrade_wavefoundry.py` removes the root bootstrap file after extract (and is a no-op when absent); the zip still ships it at the root (existing `test_build_pack.py` AC-7 unaffected).

**Out of scope:**

- Changing the zip packaging layout (`install-wavefoundry.md` still ships at the zip root — Req 4).
- The install log (`.wavefoundry/install-log.md`) or the template under `.wavefoundry/framework/install/` — those live under `.wavefoundry/` already and are not root clutter.
- Automating the install-side cleanup in code (install is agent-driven with no single finalizing script; a seed step is the right home).

## Acceptance Criteria

- [x] AC-1: After `upgrade_wavefoundry.py` extracts a pack containing a root `install-wavefoundry.md`, the file is removed from the repository root; a deterministic test asserts it is gone post-extract and that the upgrade did not fail. Evidence: `_remove_root_bootstrap_file` called right after `extractall` in the extract phase; `test_removes_present_bootstrap_file`.
- [x] AC-2: The removal is fail-safe — a missing root `install-wavefoundry.md` (e.g. idempotent re-extract skip, or already cleaned) is a no-op and never raises; a test covers the absent case. Evidence: `test_absent_is_noop`, `test_unlink_error_is_swallowed` (OSError caught + logged), plus `test_only_touches_the_reserved_bootstrap_name`.
- [x] AC-3: The zip still ships `install-wavefoundry.md` at the zip root (packaging unchanged) — existing `test_build_pack.py` AC-7 stays green. Evidence: no `build_pack.py` change; the released zip still has the root file (verified); full suite green.
- [x] AC-4: Seed-160 (upgrade CLI fallback) documents removing the root bootstrap file; seed-012 documents the post-install cleanup step (2.14); the rendered `docs/prompts/{install,upgrade}-wavefoundry.prompt.md` reflect the same guidance (install step 7; upgrade Step 0 note — hand-synced, these prompt docs are curated summaries). `wave_validate` clean. (seed-010 not edited — it is an overview; the authoritative install cleanup lives in seed-012 + the rendered install prompt.)
- [x] AC-5: Full framework tests run bytecode-free and docs validation passes. Evidence: full suite re-run at wave close; docs-lint clean.

## Tasks

- [x] Add a fail-safe `install-wavefoundry.md` root removal in `upgrade_wavefoundry.py` after extraction; log it.
- [x] Seed-160 CLI-fallback: document `rm -f install-wavefoundry.md` after prune.
- [x] Seed-012: add a final cleanup step (2.14, after 2.13) deleting the root bootstrap file. (seed-010 pointer folded into the rendered install prompt step 7 instead — 010 is an overview.)
- [x] Re-render `docs/prompts/{install,upgrade}-wavefoundry.prompt.md`; verify parity. (Hand-synced — curated summaries; `wf render-surfaces` does not regenerate these.)
- [x] Tests: upgrade removes the root file (present → gone; absent → no-op; unlink-error swallowed; unrelated files untouched); `test_build_pack.py` AC-7 unaffected.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| upgrade-cleanup | implementer | — | Fail-safe root-file removal in `upgrade_wavefoundry.py` + test |
| install/upgrade-docs | implementer | — | Seed-012 + seed-160 steps; re-render; parity |
| tests | qa-reviewer | upgrade-cleanup | present→gone, absent→no-op, packaging-unchanged |


## Serialization Points

- `upgrade_wavefoundry.py` (code) and the two seeds (docs) are disjoint; the rendered-doc re-render depends on the seed edits landing first (seed-first).

## Affected Architecture Docs

- N/A — a cleanup/hygiene fix in the install/upgrade procedures; no module boundary, data-flow, or contract change. The packaging contract (bootstrap file at the zip root) is explicitly preserved.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — upgrade must not re-leave the bootstrap file. |
| AC-2 | required | The removal must never break the upgrade (fail-safe). |
| AC-3 | required | Must not regress the deliberate zip-root packaging contract. |
| AC-4 | required | Install-side cleanup + docs parity (seed-first). |
| AC-5 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Operator-reported: install/upgrade leave `install-wavefoundry.md` in the project root; requested delete or move to `.wavefoundry/`. Scoped to a post-install/upgrade cleanup (the zip-root ship location is a deliberate bootstrap contract). Chose delete. | `build_pack.py:828` (zip-root ship); `upgrade_wavefoundry.py:2627` (`extractall`) + `prune_framework.py` MANIFEST-only prune; seed-160 step 0; seed-012 step 2.13; `test_build_pack.py` AC-7. |
| 2026-07-06 | Implemented + delivery-reviewed (clean, no blocking findings). Confirmed scope: only `install-wavefoundry.md` actually lands at the project root (the released zip has exactly one root file; `wavefoundry-install-log.md` is a permitted-name allowance, not written; the live log lives at `.wavefoundry/install-log.md`). Review F1 (low, wiring untested) CLOSED in-session with a source-assertion wiring-lock test; F2 (info, wording) accepted. | `_remove_root_bootstrap_file` + call after `extractall`; seed-012 2.14 / seed-160 CLI-fallback / rendered install step 7 + upgrade Step 0; tests `RemoveRootBootstrapFileTests` (5, incl. `test_extract_phase_wires_the_cleanup_after_extractall`); full suite 4711 green. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Delete the root `install-wavefoundry.md` after install/upgrade rather than move it into `.wavefoundry/`. | Transient single-use bootstrap file; canonical instructions live in `docs/prompts/install-wavefoundry.prompt.md`; a `.wavefoundry/` copy would go stale and be re-dropped each upgrade. | Move to `.wavefoundry/install-wavefoundry.md` (rejected — stale duplicate, re-created each upgrade). Stop shipping it at the zip root (rejected — breaks bootstrap discovery + `test_build_pack.py` AC-7). |
| 2026-07-06 | Upgrade cleanup in `upgrade_wavefoundry.py` (code); install cleanup as a seed-012 step. | Upgrade has a mechanical script (MCP `wave_upgrade` + `wf upgrade` CLI both run it) so code makes it automatic; install is agent-driven with no finalizing script, so a seed step is the right home. | Code-only for both (rejected — no install finalizer script). Seed-only for both (rejected — the upgrade code path should not depend on the agent remembering). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The removal deletes a file the operator actually authored named `install-wavefoundry.md` | The name is framework-reserved (the packaged bootstrap file); it is only removed on the install/upgrade paths that produced it, and removal is logged so it is visible. |
| Unlink error (permissions, race) aborts the upgrade | Best-effort: catch `OSError`, log, and continue — the removal is cosmetic hygiene, never a gate. |
| Idempotent re-extract skip leaves a stale copy | Make the removal run whenever a zip was applied (and no-op when absent), so a stale copy from a prior run is still cleared on the next real extract. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
