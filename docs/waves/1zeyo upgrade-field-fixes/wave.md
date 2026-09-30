# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zeyo upgrade-field-fixes`
Title: Upgrade Field Fixes

## Objective

Fix three defects found by the 1.28.0+ptgj field upgrade before the official 1.28.0 release: `wf_upgrade` returns an error after success, a 1.27-driven upgrade crashes in the memory hook on stale modules, and a crash after the docs gate is mislabelled with no targeted recovery.

## Changes

Change ID: `1zedi-bug wf-upgrade-contextvar-after-reload`
Change Status: `complete`

Change ID: `1zesi-bug memory-hook-stale-modules`
Change Status: `complete`

Change ID: `1zeyn-bug post-docs-gate-failure-recovery`
Change Status: `complete`

## Participants

- Coordinator: wave coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zeyo` (Upgrade Field Fixes) delivered 3 changes: wf_upgrade Reports an Error When a Mid-Call Reload Swaps the Navigation ContextVar, Upgrade Memory Hook Uses Stale Modules When an Older Server Drives the Upgrade, and A Crash After the Docs Gate Is Mislabelled and Blocks Every Targeted Recovery. Notable adjustments during implementation: wf_upgrade Reports an Error When a Mid-Call Reload Swaps the Navigation ContextVar: Readiness review: B4 adopted (`wf_reload_mcp` is an async runner tool the wrapper skips; only `wf_upgrade` reaches the reload, via `_reload_live_runner`); Requirement 2, AC-2, Rationale and Goal corrected. R1 adopted: transition wording (the reload installs the fixed wrapper; 1.27.0 never carried the variable). QA: run the real reload through `load_thin_runner` / `perform_mcp_reload`; reverting to the module-global lookup must fail AC-1 and AC-2; A Crash After the Docs Gate Is Mislabelled and Blocks Every Targeted Recovery: Post-approval review (DEL-1ZEYO-R2), two defects. (1) `--resume-after-gate` cleared `failed_phase` before the memory checkpoint was recorded, so a bootstrap, reconciliation or unknown-state failure left a lock no recovery accepted. The resume now relabels the lock `post_docs_gate` once the gate passes, restores that label after a backstop failure (except `review_sidecar_cleanup`, whose recovery differs), and clears it only in the checkpoint write. (2) `_post_docs_gate_failure_phase` read the predicate from a cached `upgrade_wavefoundry`, which an MCP reload does not refresh (a 1.27 copy has none), so the envelope fell back to "pre-flight check failed". The handler now carries its own copy, pinned to the runner and bundle copies by the parity test. Tests: failure then retry for three faults from both starting labels; the envelope with a stale cached runner module. Mutants: marker cleared early, no restamp after a backstop error, no final clear, cached-module lookup, handler copy drift; all caught. An `except` restamp was removed as dead code (its mutant was equivalent); A Crash After the Docs Gate Is Mislabelled and Blocks Every Targeted Recovery: Implemented. `upgrade_wavefoundry`: `POST_DOCS_GATE_PHASE` and `_is_post_docs_gate_failure(lock)` (failed_phase `post_docs_gate`, or the pre-1.28 shape `awaiting_memory_validation` + `current_phase: docs_gate_complete` + no `action_required`, with or without a run id); `main` labels the hook and in-process memory bootstrap `post_docs_gate` until the memory run is recorded in the lock; `resume_after_gate` accepts it; `_unrecovered_review_or_docs_gate` refuses it with a `--resume-after-gate` pointer; `_docs_gate_summary_line` reports PASSED; the cleanup retained-lock hint and `_finalize_failed_upgrade` recovery text name the resume. `upgrade_handlers`: `_post_docs_gate_failure_phase(root)` reads the retained lock with the same predicate; the failure envelope names `post_docs_gate` and `resume_after_gate` and sets `next_step`; `wf_upgrade` docstrings (handler and tool) corrected. Seed 160 and the prompt twin carry the same clause (seed gate). Tests: `UpgradeManifestRecoveryTests.test_a_post_docs_gate_hook_crash_is_labelled_as_its_own_phase` (real `main` default path, AC-1); `ResumeAfterGateTests` post-docs-gate, 1.27 shape with and without run id, real-pause refusal (both discriminators), index/cleanup refusal, summary and finalize (AC-2); `WaveUpgradeMcpToolTests` both lock shapes and a real pre-flight failure keeping its label (AC-3). Mutants (scratch mut-1zeyo): hook labelled as pause, 1.27 shape ignored, `action_required` check dropped (caught after adding the armed-with-gate-complete case), refusal removed, summary NOT RUN, handler label removed; all caught. Gapfill: none for retrieval.

**Changes delivered:**

- **wf_upgrade Reports an Error When a Mid-Call Reload Swaps the Navigation ContextVar** (`1zedi-bug wf-upgrade-contextvar-after-reload`) — 4 ACs completed. Key decisions: Capture the ContextVar locally in the wrapper
- **Upgrade Memory Hook Uses Stale Modules When an Older Server Drives the Upgrade** (`1zesi-bug memory-hook-stale-modules`) — 5 ACs completed. Key decisions: Refresh the pure runtime closure in place, leaf-first; never reload stateful modules; Fix in `upgrade_extensions.py` (new-pack code) rather than tolerate a missing `archive` attribute in `memory_backfill`
- **A Crash After the Docs Gate Is Mislabelled and Blocks Every Targeted Recovery** (`1zeyn-bug post-docs-gate-failure-recovery`) — 5 ACs completed. Key decisions: New `post_docs_gate` failed phase resumed by `resume_after_gate`
## Watchpoints

- Watchpoint: `upgrade_wavefoundry.py` and `server_impl.py` are fragile files (memories `1u8q3-mem`, `1u8q1-mem`); `1zesi` and `1zeyn` both touch the upgrade path, so implement `1zesi` first and run the Phase 4 and resume test clusters after each.
- Watchpoint: old-code window. `1zesi` applies on the installing upgrade (new-pack `upgrade_extensions`); `1zeyn`'s labelling lags one upgrade; `1zedi` needs a restarted server.
- Watchpoint: the working tree carries the uncommitted local 1.28.0 build stamps (`VERSION`, prompt-surface manifest, `CHANGELOG.md` section heading); keep them out of this wave's edits.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZEYO-ADVISORIES | do_now | no | completed | qa-reviewer, code-reviewer, wave-council-delivery |
| DEL-1ZEYO-R2 | do_now | no | completed | — |
| DEL-1ZEYO-R3 | do_now | no | completed | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: fixing only the memory hook would not reach a 1.27-driven upgrade, because the v1.27.0 runner re-imports `memory_backfill` itself after the hook; an in-place, leaf-first reload of the pure runtime closure fixes both, and AC-1b pins it; strongest-alternative: a defensive `getattr(roots, "archive", None)` in `memory_backfill` on top of the reload, rejected because it fixes only one field)
- Prepare council seat evidence (2026-09-30): red-team blocked round 1 on B1 (reproduced in scratch against the v1.27.0 `record_paths`) and approved the revised plans; docs-contract-reviewer approved, with advisories D1 (seed 160 and prompt edited by hand), D2 (CHANGELOG under `## [1.28.0]`) and D3 (docstring) adopted.
- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: refreshing `record_paths` in place under a live 1.27 runner could split class identity for code that from-imported it; first recorded as refuted, then shown REAL by an independent post-approval review: after the reload the old function looks up the new exception class, so `wave_lint_lib/helpers.py`'s `except` missed it; repaired in DEL-1ZEYO-R2 by keeping exception class identity across the reload; strongest-alternative: tolerate a missing field with `getattr(roots, "archive", None)` instead of reloading, rejected as a one-field fix; disagreements: none. Provenance: the independent delivery review (context 1zeyo-delivery-r1) ran the lanes and both seats; its advisories were repaired and reverified in context 1zeyo-reverify-r1.)
- Delivery council seat evidence (2026-09-30): red-team approved after DEL-1ZEYO-R2 (challenge above; the census of from-imports in v1.27.0 code stands, the refutation did not); docs-contract-reviewer approved (seed 160 and prompt sentence identical, CHANGELOG under `## [1.28.0]`, `wf_validate_docs` clean).

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 40 | 713,777 |
| implement | 98 | 955,425 |
| review | 74 | 1,324,543 |
| **Total** | **212** | **2,993,745** |

<!-- wave:context-efficiency-state {"generation":212,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":98,"content_source_credit":1156654,"derived_artifact_credit":227,"direct_net":955425,"estimated_tokens_saved":955425,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3182,"response_debit":199832,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1558},"plan":{"calls":40,"content_source_credit":745171,"derived_artifact_credit":5100,"direct_net":713777,"estimated_tokens_saved":713777,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2662,"response_debit":43045,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":74,"content_source_credit":1569920,"derived_artifact_credit":5148,"direct_net":1324543,"estimated_tokens_saved":1324543,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18335,"response_debit":234506,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":212,"content_source_credit":3471745,"derived_artifact_credit":10475,"direct_net":2993745,"estimated_tokens_saved":2993745,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24179,"response_debit":477383,"source_credit_count":152,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13087},"wave_id":"1zeyo upgrade-field-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 17 | 0 | 10 | 6,045,995 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":6045995,"surfaced_events":17} -->
<!-- wave:exploration-avoided end -->
