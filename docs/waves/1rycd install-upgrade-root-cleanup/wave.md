# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-06

wave-id: `1rycd install-upgrade-root-cleanup`
Title: Install Upgrade Root Cleanup

## Objective

**Stop install and upgrade from leaving the bootstrap `install-wavefoundry.md` in the operator's project root (operator-reported 2026-07-06).** The distribution zip ships that single-use bootstrap file at the zip root by design (the install agent discovers it before `.wavefoundry/` is known), but nothing ever removes the extracted copy — install leaves it, and every upgrade re-extracts + re-leaves it (prune only covers `.wavefoundry/framework/`). This wave adds a fail-safe post-extract removal in `upgrade_wavefoundry.py`, a final install-cleanup step in the install seed, and the matching CLI-fallback doc — deleting the file (not moving it; it is transient and the canonical instructions live in `docs/prompts/install-wavefoundry.prompt.md`). The zip-root packaging contract is preserved. When this wave closes: a fresh install and every upgrade leave the project root free of `install-wavefoundry.md`.

## Changes

Change ID: `1rxyi-bug cleanup-root-install-bootstrap-file`
Change Status: `implemented`

Completed At: 2026-07-06

## Wave Summary

Wave `1rycd` (Install Upgrade Root Cleanup) delivered one change: Install/upgrade leave the bootstrap install-wavefoundry.md in the project root. Notable adjustments during implementation: Install/upgrade leave the bootstrap install-wavefoundry.md in the project root: Operator-reported: install/upgrade leave `install-wavefoundry.md` in the project root; requested delete or move to `.wavefoundry/`. Scoped to a post-install/upgrade cleanup (the zip-root ship location is a deliberate bootstrap contract). Chose delete.; Install/upgrade leave the bootstrap install-wavefoundry.md in the project root: Implemented + delivery-reviewed (clean, no blocking findings). Confirmed scope: only `install-wavefoundry.md` actually lands at the project root (the released zip has exactly one root file; `wavefoundry-install-log.md` is a permitted-name allowance, not written; the live log lives at `.wavefoundry/install-log.md`). Review F1 (low, wiring untested) CLOSED in-session with a source-assertion wiring-lock test; F2 (info, wording) accepted.

**Changes delivered:**

- **Install/upgrade leave the bootstrap install-wavefoundry.md in the project root** (`1rxyi-bug cleanup-root-install-bootstrap-file`) — 5 ACs completed. Key decisions: Delete the root `install-wavefoundry.md` after install/upgrade rather than move it into `.wavefoundry/`.; Upgrade cleanup in `upgrade_wavefoundry.py` (code); install cleanup as a seed-012 step.
## Journal Watchpoints

- Watchpoint (preserve the packaging contract): `install-wavefoundry.md` must STILL ship at the **zip root** (`build_pack.py` — the bootstrap-discovery contract; `test_build_pack.py` AC-7). This wave only removes the EXTRACTED copy post-install/upgrade — do not touch where the zip places it.
- Watchpoint (fail-safe): the upgrade removal is best-effort — catch `OSError`, log, continue; a missing file is a no-op. It must NEVER fail or gate the upgrade (cosmetic hygiene only).
- Watchpoint (seed-first): edit the seeds (012 install cleanup, 160 upgrade CLI-fallback), then re-render `docs/prompts/{install,upgrade}-wavefoundry.prompt.md`; verify parity. Do not hand-edit the rendered docs as a substitute for the seed.
- Watchpoint (delete, not move): remove the file rather than relocating into `.wavefoundry/` (a `.wavefoundry/` copy would go stale and be re-dropped each upgrade) — operator gave the choice; delete is the decision.

## Participants

- code-reviewer — the `upgrade_wavefoundry.py` post-extract removal + the seed/rendered-doc edits
- qa-reviewer — required for bug fixes (`review_policies.require_qa_reviewer_for_bug_fixes`); AC priority table present
- docs-contract-reviewer — seed-first + rendered-prompt parity for the install/upgrade surfaces

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; strongest-challenge: the removal must not delete a legitimately operator-authored root file or fail the upgrade — resolved by scoping to the framework-reserved bootstrap name on the install/upgrade paths that produced it, making the unlink best-effort/fail-safe, and logging it; strongest-alternative: move the file into `.wavefoundry/` instead of deleting — rejected because the copy would go stale and be re-dropped each upgrade, whereas the canonical instructions already live in `docs/prompts/install-wavefoundry.prompt.md`)
- Council seat notes: reality-checker — verified against source: the zip ships `install-wavefoundry.md` at the zip root (`build_pack.py:828`), the upgrade re-extracts it (`upgrade_wavefoundry.py:2627` `extractall`), and prune is MANIFEST-scoped to `.wavefoundry/framework/` so it never removes a root file; `test_build_pack.py` AC-7 asserts the zip-root ship location (must stay green). docs-contract-reviewer — seed-first for both surfaces (012 install cleanup step, 160 upgrade CLI-fallback), then re-render + parity; do not hand-edit rendered docs. qa-reviewer — deterministic tests: present→gone after extract, absent→no-op (fail-safe), packaging-unchanged; qa-reviewer required and rostered. red-team — the only real risk is deleting a wrong file or aborting the upgrade, both closed by the reserved-name scope + best-effort catch. seat_agreement: unanimous; single small single-file code change + docs; no challenge round.
- AC priority: confirmed at prepare as proposed (AC-1..5 required). qa-reviewer assigned per `review_policies.require_qa_reviewer_for_bug_fixes`. Product-owner acknowledgment: operator-reported and operator-directed.

## Review Evidence

- wave-council-readiness: approved 2026-07-06 — prepare council synthesis verdict READY. Load-bearing claims verified against source (zip-root ship, extractall re-drop, MANIFEST-scoped prune, AC-7). Delete-not-move decided; removal is fail-safe and reserved-name-scoped; seed-first with rendered parity. Seats unanimous; no amendment. Full synthesis in Review Checkpoints.
- wave-council-delivery: approved (2026-07-06 — moderator: wave-council; adversarial delivery review against the actual code, tests, and docs; no blocking findings. Verified clean: the removal is fail-safe (`path.exists()` inside the try; only `OSError` subclasses possible from `unlink`/`stat`, all caught+logged+swallowed; missing file is a genuine no-op); scope-safe (deletes exactly the hardcoded `install-wavefoundry.md` at the passed `root`, which is the same `root` given to `extractall` — a wrong root would break extraction first; an adjacent `README.md` survives); correctly wired (the call sits outside the `_tree_already_at` if/else at 12-space indent, so it runs on BOTH the real-extract and the idempotent-skip branches, cleaning a stale copy either way); packaging contract preserved (`build_pack.py` unchanged, `test_build_pack` 90/90 incl. AC-7); docs parity intact across seed-012/seed-160/both rendered prompts on all three load-bearing points (delete-not-move; automatic on `wave_upgrade`/`wf upgrade`; manual only for hand-run `unzip`). Two findings: F1 (low) — the extract-phase wiring had no regression test (the helper was only unit-tested; no harness reaches `main()`'s extract block) → CLOSED in-session with `test_extract_phase_wires_the_cleanup_after_extractall` (asserts the call exists AFTER `zf.extractall` in the module source). F2 (informational) — the rendered install step-7 lead reads "Removes … once install completes" for a manual agent step; accepted as consistent with the agent-performed "What Init Does" list framing, and the next upgrade's code path is the eventual-consistency safety net. Full framework suite green: 4711 tests.)
- operator-signoff: approved 2026-07-06 — operator confirmed close ("close it now") to bundle into the 1.11.1 release.

## Dependencies

- No external wave dependencies.
