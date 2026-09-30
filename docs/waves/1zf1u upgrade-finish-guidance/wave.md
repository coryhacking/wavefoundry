# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zf1u upgrade-finish-guidance`
Title: Upgrade Finish Guidance

## Objective

Make the end of an upgrade say what actually remains: one index update per normal upgrade, a cleanup log that reads as complete, a lifecycle lock file that records its release, and named withheld members. Fixes a field report on 1.28.0+pthj before the 1.28.0 release.

## Changes

Change ID: `1zf1t-bug upgrade-finish-guidance`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zf1u` (Upgrade Finish Guidance) delivered one change: Upgrade Finish Guidance Repeats the Index Update and Ends With Stale Next Steps. Notable adjustments during implementation: Upgrade Finish Guidance Repeats the Index Update and Ends With Stale Next Steps: Delivery review (independent, Opus): D1 blocking (DEL-1ZF1U-D1): the primary next_step claimed "This run already updated the index" on every envelope for that phase, including a dependency-provisioning failure (index not run) and an exit-2 render failure. Repaired: the text now says "A completed run already updated the index" and conditions `update_index` on edited indexed files or a publication failure in `data.summary.index_update`; seed 160 and the twin say the same and route a dependency failure to `wf setup`. Advisories taken: the release stamp is nested in `try/finally: lock.release()` so an interrupt during the stamp still releases; the failing-stamp test now spies on `release` (Q1: the in-process `_free()` probe was vacuous); CHANGELOG transition note for the withheld names; "a server without this change" replaces "older than 1.28". Declined: seed step 12's unconditional `index_build` and the line-340 shorthand wording predate this change and are outside its scope. Tests: dependency-failure envelope; interrupt during the stamp. Mutants: false claim restored, `release()` deleted, old stamp structure; all caught.

**Changes delivered:**

- **Upgrade Finish Guidance Repeats the Index Update and Ends With Stale Next Steps** (`1zf1t-bug upgrade-finish-guidance`) — 5 ACs completed. Key decisions: Fix the guidance; do not add a freshness short-circuit to `--update-index`; Record `released_at` rather than delete the lock file
## Watchpoints

- Watchpoint: seed 160 and the prompt twin are edited by hand under `seed_edit_allowed`.
- Watchpoint: the cleanup backstops must keep running without the extra `update_index` call (they already run in `phase_cleanup` and the `--cleanup` branch).
- Watchpoint: the sentinel summary JSON must not change.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZF1U-ACQUIRE-METADATA | do_now | no | completed | — |
| DEL-1ZF1U-D1 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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

- **Independent current-tree follow-up — 2026-09-30: REQUEST CHANGES, one P2 finding (`DEL-1ZF1U-ACQUIRE-METADATA`).** Focused reviewers: code-reviewer (lock acquisition/release), qa-reviewer (cleanup, extraction and sentinel parity), red-team (guidance/failure envelopes and cleanup backstops); coordinator replayed the new lock finding. No reviewer implemented this wave; prior unrelated review contexts were retained. This is not a replacement council or a new delivery approval.
  - New finding: `lifecycle_mutation_lock` constructs acquisition metadata at `lifecycle_lock.py:62` after taking the OS lock but before entering the release-protected `try`. Injecting `KeyboardInterrupt` through its local `time.time` prevents the body from starting and bypasses `release()`. An independent child entering the same real context reports `BUSY` while the caught exception traceback is retained, then `FREE` after `traceback.clear_frames`. The previous implementation constructed this metadata inside `try`. Required repair: keep acquisition metadata construction within the release-protected region and add a non-reentrant interruption regression oracle. The probe used only a temporary root; no source edits or real OS signals. Native Windows was not run.
  - Other reviewed mechanisms passed: four release-stamp tests, six cleanup/extraction checks and ten guidance/backstop checks (overlapping batches, no skips). In-memory negative controls caught deleted release, unnested stamp cleanup, the old cleanup block, uncapped/missing withheld names, unconditional indexing and the false current-run index claim. Six old/current sentinel comparisons were byte-identical. The failed-cleanup recovery text precedes the summary/sentinel rather than literally being the final log line; the admitted requirement to omit the editing-pass block on failure is satisfied.
  - The canonical runner confirmed the current 10,163-test green receipt at 2026-09-30 17:21:17 UTC; this follow-up did not repeat the full suite. Reviewed Git blob hashes remained unchanged: `lifecycle_lock.py` `81c9ba5474eaa8ac72e4cacbcbf3da1c2f02b649`; `upgrade_wavefoundry.py` `7eb4f4cff7767b23453a8710c8104eab07790051`; `wf_server/upgrade_handlers.py` `8dff6e03da65c46a7ca9ca40c4e3d226ac5eb29f`; lock tests `64b1fd298a1549f74ee0410d1ceeed4d36d9e07e`; upgrade tests `40fac0af7640d0145a1ef4ef71639972f187afaf`; server tests `3b50184ef99753f83ee5b3ea7a6d79ade32f64c1`.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: skipping the second `update_index` could lose the new-code backstops when a pre-1.28 runner performs the primary run; refuted, both backstops also run in the cleanup path and the hooks and outcome record run in the primary Phase 4; strongest-alternative: a freshness short-circuit in `--update-index`, rejected because the redundant call comes from the instructions and a skip could bypass the backstops)
- Prepare council seat evidence (2026-09-30): red-team approved (backstop census of the `--update-index` branch against `phase_cleanup` and the `--cleanup` branch); docs-contract-reviewer approved (seed 160 MCP-first paragraph contradicts mental-model step 4; both prompt copies carry it; sentinel JSON emitted before the block).

- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the reused primary next_step claimed the index was updated on a dependency-failure or render-failure envelope (DEL-1ZF1U-D1), repaired and independently reverified; strongest-alternative: gate the text on the envelope outcome, rejected for a conditional wording that is true in every outcome; disagreements: none)
- Delivery council seat evidence (2026-09-30): red-team raised and then cleared D1 after reverification; docs-contract-reviewer approved (seed and twin sentence byte-identical, CHANGELOG under `## [1.28.0]` with transition notes).

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 35 | 334,654 |
| implement | 7 | 0 |
| review | 75 | 579,943 |
| **Total** | **117** | **914,597** |

<!-- wave:context-efficiency-state {"generation":106,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-451,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":63,"response_debit":388,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":35,"content_source_credit":386820,"derived_artifact_credit":2594,"direct_net":334654,"estimated_tokens_saved":334654,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2808,"response_debit":61165,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":75,"content_source_credit":850743,"derived_artifact_credit":3838,"direct_net":579943,"estimated_tokens_saved":579943,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10799,"response_debit":266155,"source_credit_count":60,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":117,"content_source_credit":1237563,"derived_artifact_credit":6432,"direct_net":914146,"estimated_tokens_saved":914597,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13670,"response_debit":327708,"source_credit_count":83,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11529},"wave_id":"1zf1u upgrade-finish-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 5 | 4,538,782 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":4538782,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
