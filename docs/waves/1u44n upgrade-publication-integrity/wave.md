# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u44n upgrade-publication-integrity`
Title: Upgrade Publication Integrity

## Objective

Close the upgrade's publication-integrity gap. When this wave closes, an upgrade whose historical-memory work is already complete publishes the index instead of being refused by its own stale checkpoint, and no upgrade summary field reports a phase outcome the phase did not achieve. Now, because the defect is field-reproduced on consecutive upgrades and the false-success `index_update` field actively suppresses the `index_health` check that would catch it.

## Changes

Change ID: `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (single `fix` workstream)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-01

## Wave Summary

Wave `1u44n` (Upgrade Publication Integrity) delivered one change: Memory Gate Blocks Index Publication While the Summary Reports Success. Notable adjustments during implementation: Memory Gate Blocks Index Publication While the Summary Reports Success: Prepare council (red-team, docs-contract-reviewer) DISPROVED the plan's original causal story (a failed 1tz6l empty-worklist auto-continue) by code-grounded tracing, and supplied a replacement seam: the unconditional lock write at `:4238-4249` versus the pause branch at `:4250` and the local-only advance at `:4273`. Corrections folded into requirements, Scope, ACs, tasks, and the architecture-doc list.; Memory Gate Blocks Index Publication While the Summary Reports Success: OPERATOR CORRECTION folded in: there is always a zip file for upgrades. The rewrite had justified the standalone in-runner scope by citing `_load_extension_module` returning `None` when `zip_path is None`; those branches exist in code (the staged-tree direct-merge path) but do not occur in practice and must not shape the design. Requirement 3, the Old-code window note, and Decision Log alternative (b) restated: the `pre_index_update` bridge is the PRIMARY delivery mechanism for already-upgraded targets, and the in-runner repair is durable because every subsequent upgrade runs the new parent code.; Memory Gate Blocks Index Publication While the Summary Reports Success: Code-reviewer prepare lane REFUTED that corrected plan with an executable probe and recorded no approval. `begin_build_epoch` refuses on checkpoint PRESENCE, not on the phase value: phase `awaiting_memory_validation` raises, phase `index_update` also raises, no checkpoint succeeds, staged-child receipt succeeds. Re-authored: AC-1 and requirement 1 now target authorized-publisher status at the `begin_build_epoch` boundary; `index_state_store.begin_build_epoch` and the staged-receipt path are in scope; the `publication_control.py` non-goal is narrowed to the guard predicate with the message tail explicitly in scope; the blast radius is restated as every upgrade with real index work; the release lane's `pre_index_update` bridge is adopted as requirement 3; the resume allow-list, the two extra summary writers, the third swallow site, the `resume_after_gate` audit, the test-vacuity traps, the file misattribution in Serialization Points, and the changelog task are all folded in.

**Changes delivered:**

- **Memory Gate Blocks Index Publication While the Summary Reports Success** (`1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`) — 8 ACs completed. Key decisions: Filed from reproduced field feedback; Target authorized-publisher status at `begin_build_epoch`, not the lock's `current_phase`
## Watchpoints

- Blocking guard: the repair belongs at the authorized-publisher boundary in `index_state_store.begin_build_epoch` (owner pid or staged receipt), not at the lock-advance seam and not in `publication_control`'s predicate. The code-reviewer prepare lane refuted the lock-advance design by executable probe: advancing `current_phase` changes only the refusal text. Seed-160 (line 511) makes "every other registered publisher fails fast with `upgrade_in_progress`" the documented invariant at `awaiting_memory_validation`; the predicate stays byte-identical, and the correct repair is to send an authorized publisher, not to widen who may publish.
- Watchpoint: a phase advance is CONDITIONAL in the rewritten plan (requirement 4): if any advance is delivered, `index_update` must join the `resume_after_memory` allow-list at `upgrade_wavefoundry.py:3481` in the same change, and no advance may land on the paused/`resume_after_gate` paths, or agent-driven memory recovery is blocked.
- Watchpoint: `upgrade_wavefoundry.py` is a named fragile file (`1u0dl-mem`): all six 1tz6l repairs sat on phase-transition state seams. Rerun the seam test cluster together, not just the touched phase's tests.
- Watchpoint: requirement 2's refusal text must branch on `memory_backfill_pending`. The `resume_after_memory` → `cleanup` → `index_build` sequence is correct only when memory work is already complete; emitting it during a genuine pause would tell the operator to skip validation.
- Watchpoint: requirement 6's audit surface is bounded and enumerable: the 18 keys returned by `_build_upgrade_summary` (`upgrade_wavefoundry.py:2712-2748`), plus `resume_after_gate` (`:3852-3885`) and the four sibling checkpoint writers (`upgrade_wavefoundry.py:3441-3452`, `:3533-3543`; `upgrade_extensions.py:654-664`, `:708-716`). Audit those lists, not an open-ended sweep.
- Follow-up for the coordinator: the prepare dry-run's review-policy receipt lists `council_seats: [red-team, security-reviewer]`, while the same response's `council_brief` names `[red-team, docs-contract-reviewer]`. This council ran the brief's seats. Reconcile before delivery, and note the receipt's required delivery lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer.

## Review Checkpoints

- **Supersession note (2026-07-31):** the council checkpoint below is retained as history. Its resolution ("re-pointing requirement 1 at the lock-advance seam") was subsequently REFUTED by the code-reviewer prepare lane's executable probe: `begin_build_epoch` refuses on checkpoint presence at any phase value, so the plan was re-authored to target authorized-publisher status (owner pid or staged receipt) at the `begin_build_epoch` boundary. See the change doc's Progress Log and Decision Log for the current design.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-31: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's stated crux — that the 1tz6l empty-worklist auto-continue failed to fire — is disproven by code-grounded tracing; in the field scenario the auto-continue at `upgrade_wavefoundry.py:4207-4226` is never reached, because a run already at `indexed` short-circuits at `memory_backfill.py:686` and a fresh zero-work run lands `ready_for_index` with `candidates_drafted == 0`, so the real defect is the unconditional lock write at `:4238-4249` that leaves `current_phase` at `awaiting_memory_validation` while control falls through to Phase 4, where the `setup_index.py` subprocess is neither the lock-owning pid nor a staged child and `index_state_store.begin_build_epoch:2276` raises — resolved by re-pointing requirement 1 at the lock-advance seam and dropping its redundant canonical-zero re-derivation, since the branch at `:4250` has already made that determination; strongest-alternative: relax `publication_control`'s memory-phase exemption to admit `index_build` when `memory_backfill_pending == 0` — rejected because seed-160 line 511 makes fail-fast-for-every-other-publisher the documented invariant at that phase, and the correct repair is to not be at that phase when publishing. Both seats verified claims code-grounded and executably: the false-success field claim HOLDS at both emit sites (`_emit_primary_phase_summary:2787` hardcodes `ran_index_rebuild=True`; the cleanup path derives `_cl_rebuilt` at `:3719` from an `index_rebuilt_at` written unconditionally at `:4287`), with the failure swallowed as a warning at `:2059`; a temp-dir probe confirmed the refusal fires with `memory_backfill_pending: 0` on the checkpoint and names none of `resume_after_memory`, `cleanup`, or `index_health`; contract companions named for `docs/specs/mcp-tool-surface.md` lines 917-918 and seed-160 line 51, with seed-160's "continues automatically to Phase 4" confirmed already correct — this is a code defect against a documented contract, not a contract change.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 24 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 96 | 2,578,399 |
| implement | 4 | 0 |
| review | 133 | 2,805,791 |
| **Total** | **233** | **5,384,190** |

<!-- wave:context-efficiency-state {"generation":239,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":4,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-277,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":404,"response_debit":1304,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":96,"content_source_credit":2816056,"derived_artifact_credit":2499,"direct_net":2578399,"estimated_tokens_saved":2578399,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31763,"response_debit":215856,"source_credit_count":116,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7463},"review":{"calls":133,"content_source_credit":3102515,"derived_artifact_credit":2411,"direct_net":2805791,"estimated_tokens_saved":2805791,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11091,"response_debit":289390,"source_credit_count":128,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":233,"content_source_credit":5918571,"derived_artifact_credit":4910,"direct_net":5383913,"estimated_tokens_saved":5384190,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43258,"response_debit":506550,"source_credit_count":244,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10240},"wave_id":"1u44n upgrade-publication-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 6 | 8,155,008 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":8155008,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
