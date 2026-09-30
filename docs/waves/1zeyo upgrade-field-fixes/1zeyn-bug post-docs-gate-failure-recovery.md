# A Crash After the Docs Gate Is Mislabelled and Blocks Every Targeted Recovery

Change ID: `1zeyn-bug post-docs-gate-failure-recovery`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zeyo upgrade-field-fixes

## Rationale

Field report, following the `post_docs_gate` crash of change `1zesi-bug memory-hook-stale-modules`: the retained lock read `current_phase: docs_gate_complete`, `failed_phase: awaiting_memory_validation`, `action_required: null`, with no `memory_backfill_run_id` (the hook crashed before `ensure_run`). Every targeted recovery then refused:

- `memory_backfill(mode="create", entry_path="upgrade")`: blocked while Upgrade is at `docs_gate_complete`.
- `wf_upgrade(phase="resume_after_memory")`: no memory run to resume, and `docs_gate_complete` is not an accepted checkpoint.
- `wf_upgrade(phase="resume_after_gate")`: accepts only `failed_phase` `docs_gate`.

Only a full rerun of the same pack recovered it. The labels also misled: the MCP diagnostic said `preflight_to_docs_gate failed: pre-flight check failed`, and `failed_phase: awaiting_memory_validation` is the name of the normal historical-memory pause, which seed 160 calls action-required, not a failure.

Cause, verified in code: `upgrade_wavefoundry.main` sets `current_phase = "awaiting_memory_validation"` before `_run_hook("post_docs_gate", ...)`, and `_run_hook` turns a hook exception into `sys.exit(3)`, which the failure handler finalizes under that phase.

Goal: a crash between the docs gate and the memory run is labelled as what it is and has a targeted recovery. Consumer: operators and agents recovering a failed upgrade. Success: the lock and the `wf_upgrade` diagnostic name the failing step, and one documented recovery command resumes from after the docs gate.

## Requirements

1. **Honest label.** A failure in the `post_docs_gate` hook, or anywhere between the docs gate passing and the memory run being recorded, is finalized with its own `failed_phase` (`post_docs_gate`), never `awaiting_memory_validation`, which stays reserved for the real memory pause.
2. **Targeted recovery.** `wf_upgrade(phase="resume_after_gate")` (and `--resume-after-gate`) also accepts a retained lock with `failed_phase` `post_docs_gate` when the docs gate had passed (`current_phase` `docs_gate_complete`). It re-runs the docs gate, then establishes the memory checkpoint, without re-extracting or re-rendering. The set is every reader of `failed_phase` that decides eligibility or recovery wording (derived from the code; today `resume_after_gate`, `resume_after_memory` and `_unrecovered_review_or_docs_gate`, which gates `update_index`/`rebuild_index`/`cleanup`, plus `_finalize_failed_upgrade`, the cleanup retained-lock hint and `_docs_gate_summary_line`). `post_docs_gate` is refused by index and cleanup with a pointer to `--resume-after-gate`, and the summary reports the docs gate as PASSED.
3. **Accurate diagnostic.** The `wf_upgrade` failure envelope names the phase that failed (from the retained lock's `failed_phase`, or from the output when no lock), not a generic pre-flight failure.
4. **Documentation.** Seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` name the `post_docs_gate` failure and its recovery command.
5. **Platforms.** Same on Windows, macOS, Linux and WSL2.
6. **Transition.** The labelling in `main` runs in the orchestrator, so on the default `wf upgrade` / `wf_upgrade()` paths it applies from the upgrade after the one that installs it. `wf_upgrade` spawns `upgrade_wavefoundry.py` from disk, so `resume_after_gate` runs the newly extracted code immediately, even from an unrestarted 1.27 server; only the handler's diagnostic (AC-3) lags until a reload or restart. An upgrade from 1.27 that fails here still carries the old label, so Requirement 2 also accepts that shape as a post-docs-gate failure when `failed_phase` is `awaiting_memory_validation`, `current_phase` is `docs_gate_complete` and `action_required` is absent, whether or not a `memory_backfill_run_id` is present (an existing run id is reused by the resume). A real pause always writes `action_required` with `current_phase` `awaiting_memory_validation`. The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** a crash after the docs gate is labelled as the memory pause and no targeted recovery accepts it.

**In scope:**

- Failure labelling around `post_docs_gate` in `upgrade_wavefoundry.main`; `resume_after_gate` eligibility; the `wf_upgrade` failure diagnostic in `wf_server/upgrade_handlers.py`; seed 160 and its prompt twin; tests; CHANGELOG.

**Out of scope:**

- The stale-module cause of the crash (change `1zesi-bug memory-hook-stale-modules`).
- Memory backfill blocking rules outside the upgrade checkpoint.

## Acceptance Criteria

- [x] AC-1: a `post_docs_gate` hook exception on the default path leaves `failed_phase: post_docs_gate` and `current_phase: docs_gate_complete` in the lock, not `awaiting_memory_validation`.
- [x] AC-2: `--resume-after-gate` on that lock, and on the 1.27-shaped lock (`failed_phase: awaiting_memory_validation`, `current_phase: docs_gate_complete`, no `action_required`, with and without a memory run id), re-runs the docs gate and establishes the memory checkpoint without re-extracting; a real memory pause (`action_required` present, `current_phase: awaiting_memory_validation`) is still refused and routed to `resume_after_memory`; `update_index`, `rebuild_index` and `cleanup` refuse a `post_docs_gate` lock with a pointer to `--resume-after-gate`, and the summary reports the docs gate as PASSED.
- [x] AC-3: the `wf_upgrade` failure envelope for that failure names `post_docs_gate` and the recovery command.
- [x] AC-4: seed 160 and the prompt twin carry the same recovery clause for the `post_docs_gate` failure (edited by hand in both; no byte-parity test covers this section).
- [x] AC-5: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Label and finalize a post-docs-gate failure as `post_docs_gate`.
- [x] Extend `resume_after_gate` eligibility (both lock shapes); keep the memory-pause refusal; add `post_docs_gate` handling to every other `failed_phase` reader in Requirement 2.
- [x] `wf_upgrade` diagnostic names the failed phase; fix the `wf_upgrade` docstring's stale `review_status_projection` phase name while editing it.
- [x] Seed 160 (seed gate), prompt twin, CHANGELOG; tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Labelling and resume | implementer | readiness | Fragile file: exercise the phase-transition cluster |
| Diagnostic and docs | implementer | Labelling and resume | |
| Review | code-reviewer, qa-reviewer, release-reviewer, docs-contract-reviewer | both | |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- CHANGELOG.md

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (upgrade path): the post-docs-gate failure and its resume, if the path's failure states are described there; otherwise N/A with the check recorded.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The mislabel |
| AC-2 | required | The missing recovery, including the 1.27 shape |
| AC-3 | important | Agents read the envelope first |
| AC-4 | required | Operator-facing recovery guidance |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Reverification of DEL-1ZEYO-R2 (independent, fresh context): items 1 to 3 resolved, 8 mutants, one survivor (the `review_sidecar_cleanup` carve-out, untested; now pinned). It also found DEL-1ZEYO-R3: a `--resume-after-gate` that ends at `awaiting_validation` exits 4 without arming `action_required`, so `wf_upgrade` downgraded it to "review-state projection or docs gate failed" and pointed at a retry that is then refused. Older than this wave, but this wave routes every post-gate crash through it. The resume now arms the same typed pause (kind, state, resume_phase, run_id, token, compatibility lease) the full upgrade writes. Test: the real resume writes the lock, then the handler with exit 4 reports `awaiting_memory_validation` and `resume_after_memory`. Mutant (no arming) caught | focused tests OK |
| 2026-09-30 | Post-approval review (DEL-1ZEYO-R2), two defects. (1) `--resume-after-gate` cleared `failed_phase` before the memory checkpoint was recorded, so a bootstrap, reconciliation or unknown-state failure left a lock no recovery accepted. The resume now relabels the lock `post_docs_gate` once the gate passes, restores that label after a backstop failure (except `review_sidecar_cleanup`, whose recovery differs), and clears it only in the checkpoint write. (2) `_post_docs_gate_failure_phase` read the predicate from a cached `upgrade_wavefoundry`, which an MCP reload does not refresh (a 1.27 copy has none), so the envelope fell back to "pre-flight check failed". The handler now carries its own copy, pinned to the runner and bundle copies by the parity test. Tests: failure then retry for three faults from both starting labels; the envelope with a stale cached runner module. Mutants: marker cleared early, no restamp after a backstop error, no final clear, cached-module lookup, handler copy drift; all caught. An `except` restamp was removed as dead code (its mutant was equivalent) | 153 focused tests OK |
| 2026-09-30 | Delivery review: all lanes and seats APPROVE; advisories taken. (1) `upgrade_bundle._recovery` offered a full rerun for a post-docs-gate lock: now `_post_docs_gate_failure(state)` routes it to `--resume-after-gate`, with `tests/test_upgrade_protocol` covering both labels and a parity test pinning the bundle predicate to `upgrade_wavefoundry._is_post_docs_gate_failure` across eight lock shapes. (2) `--resume-after-gate` help text updated. (3) Survivor mutants closed: `test_an_in_process_memory_bootstrap_crash_is_labelled_post_docs_gate` (N2), the `current_phase` discriminator case in `test_a_real_memory_pause_is_not_treated_as_a_crash` (N5), and (1zesi) `test_every_other_installed_reload_refreshes_a_v1_27_record_paths_first` for `_fresh_installed_module` and `repair_declaring_scaffold` (S5, S6). Rerun in scratch against a baseline with one known scratch-layout error: N2, N5, S5, S6 and two bundle mutants each add a named failing test. Not taken: (4) the phase_cleanup hint is unreachable but harmless; (5) the envelope reads the retained lock, and its recovery pointer stays correct; (6) the narrow 1.27 window between its lock writes fails safe to a full rerun | scratch mut-1zeyo-r2 |
| 2026-09-30 | Implemented. `upgrade_wavefoundry`: `POST_DOCS_GATE_PHASE` and `_is_post_docs_gate_failure(lock)` (failed_phase `post_docs_gate`, or the pre-1.28 shape `awaiting_memory_validation` + `current_phase: docs_gate_complete` + no `action_required`, with or without a run id); `main` labels the hook and in-process memory bootstrap `post_docs_gate` until the memory run is recorded in the lock; `resume_after_gate` accepts it; `_unrecovered_review_or_docs_gate` refuses it with a `--resume-after-gate` pointer; `_docs_gate_summary_line` reports PASSED; the cleanup retained-lock hint and `_finalize_failed_upgrade` recovery text name the resume. `upgrade_handlers`: `_post_docs_gate_failure_phase(root)` reads the retained lock with the same predicate; the failure envelope names `post_docs_gate` and `resume_after_gate` and sets `next_step`; `wf_upgrade` docstrings (handler and tool) corrected. Seed 160 and the prompt twin carry the same clause (seed gate). Tests: `UpgradeManifestRecoveryTests.test_a_post_docs_gate_hook_crash_is_labelled_as_its_own_phase` (real `main` default path, AC-1); `ResumeAfterGateTests` post-docs-gate, 1.27 shape with and without run id, real-pause refusal (both discriminators), index/cleanup refusal, summary and finalize (AC-2); `WaveUpgradeMcpToolTests` both lock shapes and a real pre-flight failure keeping its label (AC-3). Mutants (scratch mut-1zeyo): hook labelled as pause, 1.27 shape ignored, `action_required` check dropped (caught after adding the armed-with-gate-complete case), refusal removed, summary NOT RUN, handler label removed; all caught. Gapfill: none for retrieval | test_upgrade_wavefoundry, test_server_tools classes OK |
| 2026-09-30 | Readiness review: B2 adopted (full `failed_phase` reader set, including `_unrecovered_review_or_docs_gate`, `_finalize_failed_upgrade`, the cleanup hint and `_docs_gate_summary_line`); B3 adopted (the 1.27 shape is recognised by `current_phase: docs_gate_complete` and no `action_required`, with or without a run id). R2: `resume_after_gate` runs new code immediately; it re-runs the docs gate then establishes the memory checkpoint. D1: seed and prompt edited by hand; D2: CHANGELOG under `## [1.28.0]`; D3: docstring | readiness review |
| 2026-09-30 | Planned from the 1.27 → 1.28.0+ptgj field upgrade. Verified: `main` sets `current_phase = "awaiting_memory_validation"` before `_run_hook("post_docs_gate")`; `_run_hook` converts a hook exception to `sys.exit(3)`; `resume_after_gate` accepts only `failed_phase` `docs_gate` (corrected at readiness) | code reading |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | New `post_docs_gate` failed phase resumed by `resume_after_gate` | Reuses the existing after-gate recovery command; keeps `awaiting_memory_validation` meaning the real pause | Write the memory checkpoint before the hook (still leaves a mislabelled crash if `ensure_run` itself fails); a new resume phase (one more command to learn) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Accepting the 1.27-shaped lock could treat a real pause as a crash | Only when there is no memory run id and no `action_required`; AC-2 pins the real pause's refusal |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
