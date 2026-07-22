# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-21
review-evidence-source: events.jsonl

wave-id: `1t9ti memory-publication-receipt`
Title: Memory Publication Receipt

## Objective

Make the historical-memory index publication survive the trailing build passes that legitimately follow it: record publication success at the compare-and-set instead of re-deriving it from the mutable last-build row, and stop the memory gate from refusing trailing epochs once no memory work is pending. Field-confirmed 1.14.0 release blocker (the pdsk pack under test carries it); the publish waits on this wave plus a fresh pack build.

## Changes

Change ID: `1t9th-bug memory-publication-receipt-trailing-pass`
Change Status: `implemented`

Completed At: 2026-07-21

## Wave Summary

Wave `1t9ti` (Memory Publication Receipt) delivered one change: Memory Publication Receipt Survives Trailing Build Passes. Notable adjustments during implementation: Memory Publication Receipt Survives Trailing Build Passes: Drafted from the operator's field report; both legs verified at source (reconcile exact-match at memory_backfill.py:759-766 against the single build-state row; trailing-pass refusal via authorize_index_finalize consulted on every in-scope finalize at index_state_store.py:2300-2310).; Memory Publication Receipt Survives Trailing Build Passes: Implemented. Live-caught design correction on the first test run: the stored run state can lag validation (still `awaiting_validation` after a promote), so the finalize gate must NOT pre-read state to decide whether to authorize — only `publishing_index`/`indexed` short-circuit as trailing passes and unknown runs fail closed; everything else routes through `authorize_index_finalize`, which re-syncs the census exactly as before. Five tests added/retargeted (field reproduction; pending-validation refusal; unknown-run refusal; authorized-attempt-only success record; aliasing test retargeted at the CAS-to-record crash window, plus the setup-retry recovery test retargeted the same way). Known-bad probe reconstructing the pre-fix finalize (always-authorize, no success record) flipped the field reproduction to failure. Modules: memory_backfill 41 OK, index_state_store 36 OK, upgrade 340 OK.

**Changes delivered:**

- **Memory Publication Receipt Survives Trailing Build Passes** (`1t9th-bug memory-publication-receipt-trailing-pass`) — 4 ACs completed. Key decisions: Record publication success at CAS time instead of re-deriving it later from the build-state row.; Retarget the receipt anti-aliasing test at the crash window instead of deleting it.
## Journal Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-21 (single change, crash-safety scope; every load-bearing claim verified against the tree, not the plan's prose):

- reality-checker: both defect legs resolve exactly as claimed — `reconcile_index_publication` requires the CURRENT build-state row to equal the receipt (`memory_backfill.py:759-766`, exact attempt_id + generation match on the single id=1 row), and `finalize_build_epoch` consults `authorize_index_finalize` on EVERY in-scope finalize (`index_state_store.py:2300-2310`), which refuses once the run is `publishing_index` because authorize demands `ready_for_index` (:699-710). The trailing pass sites are real: graph/idle/optimize/fts epochs all mint their own attempts through the same row (indexer.py:1970, :2816, :4305, :4538). The operator's field failure is the deterministic consequence.
- red-team: strongest challenge — does recording success at CAS time weaken the gate's crash story? The authorize census freeze (zero-pending under BEGIN IMMEDIATE) is untouched; the success record matches the authorized attempt id only; a crash between the CAS commit and the success record leaves `publishing_index` with a now-unmatchable receipt, which reconcile resets to `ready_for_index` for a clean re-publication, exactly today's recovery. Second challenge — ungated `publishing_index`/`indexed` finalizes: in both states the zero-pending census has already been frozen, so no pending memory work can be published past the gate; `awaiting_validation`, `inventory_pending`, and unknown runs stay refused, fail-closed.
- qa-reviewer: the field report supplies the deterministic reproduction (content pass then graph-only pass inside one publication scope) and AC-1 pins that it must fail pre-fix; gate-integrity and authorized-attempt-mismatch cases are enumerated as AC-2; AC-3 pins the existing recovery tests (crash-window reconcile, history-changed requeue, update-index bypass) unchanged. Per the standing independent-delivery-verification feedback for crash-safety waves, AC-4 requires executed reproductions, not green-units-only.
- docs-contract-reviewer: requirements, ACs, decisions, and risks are internally consistent; no schema or contract growth (requirement 6); Affected Architecture Docs N/A holds.

Synthesis verdict: READY. Two seams, both under the existing single-writer lock, with the field failure itself as the executable regression boundary.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the six-window crash walk, sharpest on the CAS-to-record window — resolved by the intact-receipt reconcile recovery proven in the retargeted tests; strongest-alternative: pre-reading run state to route the first pass — live-refuted by the stale-state test failure and replaced with authorize-first routing.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: recording success at CAS time could weaken the crash story — resolved because the census freeze is untouched, the record matches the authorized attempt only, and the CAS-to-record crash window still reconciles to a clean re-publication; strongest-alternative: a receipt-history table surviving overwrites — rejected as schema growth for one consumer, per the Decision Log.)

## Delivery Review Evidence

Delivery council pass, 2026-07-21, over the landed diff (memory_backfill.py `run_state` + `record_publication_success`; index_state_store.py finalize gate routing + post-CAS success record; five tests added/retargeted in test_memory_backfill.py):

- reality-checker: the landed routing matches the plan with one live-caught correction, recorded in the change doc — the stored run state can lag validation, so only `publishing_index`/`indexed` short-circuit (trailing pass) and unknown runs fail closed; every other state routes through `authorize_index_finalize`, preserving the census-refresh semantics byte-for-byte on the first pass. The success record is keyed to run_id + `publishing_index` + the authorized attempt id, under the same `review_event_write_lock` that wraps the whole finalize.
- red-team (crash-window adversarial walk, all six windows): (1) crash after authorize before CAS → reconcile resets to `ready_for_index` for a clean re-publication, unchanged; (2) crash after CAS before the success record → reconcile matches the intact receipt and recovers `indexed` without a second index pass — proven by the retargeted setup-retry test; the trailing-overwrite variant of the same window resets for re-publication — proven by the retargeted aliasing test; (3) crash after the record → the resume's already-complete path returns clean (and clears the 1t550 `index_update` marker); (4) a trailing-pass CAS miss after a recorded success leaves the publication durable, strictly better than pre-fix; (5) pending work created after the frozen census belongs to the next run and meets the gate at its own publication; (6) a success-record write failure propagates as a build error while the intact receipt recovers via window 2. No window loses a publication or forces revalidation.
- qa-reviewer: the field reproduction (content pass then trailing graph-only pass inside one scope) passes and the known-bad probe reconstructing the pre-fix finalize (always-authorize, no success record) flips it to failure; gate-integrity tests cover pending-validation refusal, unknown-run refusal, and the authorized-attempt-only success record; the two retargeted tests keep their original guarantees (anti-aliasing; no-second-pass recovery) aimed at the crash window where they still apply. Modules 41/36/340 OK; full suite 6,118/6,118 OK on the final tree.
- docs-contract-reviewer: real-time tracking held (routing correction, retarget decision, and AC evidence all in the change doc as they happened); requirement 6 holds — no new states, no schema change, `mark_indexed`/`sync_inventory`/upgrade orchestration untouched.

Synthesis verdict: PASS. Zero findings.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

operator-signoff: approved (2026-07-21, operator confirmed the upgrade tested clean and requested close and commit in the current session)
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 14 | 589,751 |
| implement | 9 | 17,062 |
| review | 2 | 214 |
| **Total** | **25** | **607,027** |

<!-- wave:context-efficiency-state {"generation":20,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":9,"content_source_credit":23883,"derived_artifact_credit":265,"direct_net":17062,"estimated_tokens_saved":17062,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1341,"response_debit":5745,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":14,"content_source_credit":613418,"derived_artifact_credit":663,"direct_net":589751,"estimated_tokens_saved":589751,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1037,"response_debit":26490,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3197},"review":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":214,"estimated_tokens_saved":214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18,"response_debit":857,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1089}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":25,"content_source_credit":637301,"derived_artifact_credit":928,"direct_net":607027,"estimated_tokens_saved":607027,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2396,"response_debit":33092,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4286},"wave_id":"1t9ti memory-publication-receipt"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
