# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uwpf receipt-and-citation-contract-followups`
Title: Receipt And Citation Contract Followups

## Objective

Close the three gaps wave `1usqm` left behind: documentation that describes receipt authority as it was before that wave, the one artifact class its citation rule never reached, and a crash on an input a lower layer already handles gracefully. Each was found by a delivery-review lane there and deliberately deferred rather than folded, because repairing it was outside that wave's declared scope.

## Changes

Change ID: `1uu0f-doc receipt-authority-docs-match-shipped-behavior`
Change Status: `implemented`

Change ID: `1uu9y-doc citation-rule-reaches-review-evidence-authoring`
Change Status: `implemented`

Change ID: `1uu9z-bug prepare-crashes-on-an-undecodable-change-doc`
Change Status: `implemented`


## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-10

## Wave Summary

Wave `1uwpf` (Receipt And Citation Contract Followups) delivered 3 changes: Receipt-Authority Documentation No Longer Matches Shipped Behavior, The Symbol-Anchor Citation Rule Never Reached Review-Evidence Authoring, and Prepare And Close Crash On An Undecodable Change Document. Notable adjustments during implementation: Prepare And Close Crash On An Undecodable Change Document: Both WITHHELD lanes confirmed the folds and moved to APPROVE, making the round 6/6. The code lane re-proved the leak-fix non-vacuity independently (helper monkeypatched back to the raw formatter, read-only: test fails on the exact absolute-path assertion) and diffed the delta since its review down to the three one-line routings. Docs-contract independently re-derived all twelve census site counts from HEAD. One out-of-scope residual recorded for a future wave: `_replace_artifacts_transactionally` raises a synthetic single-arg `OSError` whose detail embeds absolute rollback paths, defeating `strerror` at the publish handler for that one exception shape; the cheap fix is at the raise site; Prepare And Close Crash On An Undecodable Change Document: REVERIFICATION ROUND, five focused lanes: readiness 2/2 APPROVE; delivery qa and architecture APPROVE, code and docs-contract WITHHELD with prescribed fixes, all folded here. The code lane found the leak repair had missed `_prepare_policy_state`'s policy-selection message — the sanitized and the leaking string sat ADJACENT in one real-config prepare envelope — and proved the leak test vacuous for prepare (its fixture had no `wave_review` config, so the leaking line was never reached). Routed through `_read_error_detail`, fixture widened with a reachability assertion, and the reverted-leak mutant now fails the test; Prepare And Close Crash On An Undecodable Change Document: The two TOCTOU-only raw interpolations (`change_metadata_repair_failed`, the publish handler) routed through the same helper, closing qa's AC-12-prose gap. qa's cause-half mutants (message drops the exception type at prepare/implement/close) now die: assertions added at all three surfaces.

**Changes delivered:**

- **Receipt-Authority Documentation No Longer Matches Shipped Behavior** (`1uu0f-doc receipt-authority-docs-match-shipped-behavior`) — 8 ACs completed. Key decisions: Withdraw the "five narrow regions" drift rather than soften it; Reconcile the documentation to the code, not the code to the documentation
- **The Symbol-Anchor Citation Rule Never Reached Review-Evidence Authoring** (`1uu9y-doc citation-rule-reaches-review-evidence-authoring`) — 7 ACs completed
- **Prepare And Close Crash On An Undecodable Change Document** (`1uu9z-bug prepare-crashes-on-an-undecodable-change-doc`) — 13 ACs completed. Key decisions: Report and REFUSE rather than degrade; SUPERSEDED — Degrade with a diagnostic rather than refuse
## Watchpoints

- **`1uu9z` DOES change a gate outcome, and the earlier claim that none of the three does was false.** `_collect_silent_unchecked_items_for_close` currently catches `OSError` and *silently skips* the document, so an unreadable change doc is excluded from the close hard gate and close proceeds. Making it visible turns that into a blocker. Disclosed rather than discovered at review.
- **`1uu0f` and `1uu9y` change no gate outcome.** One reconciles docs to shipped code, the other states an existing rule at surfaces that never carried it. Any finding that a REQUIREMENT rather than a document is wrong gets surfaced, not fixed here.
- **Two changes need the `seed_edit_allowed` gate** (`1uu0f` for seed 007, `1uu9y` for seeds 209 and 237). Open immediately before the edits and close immediately after. Both ship to every target repository, so installed repos see the corrections only at their next upgrade.
- **Watchpoint on census-before-edit:** `1uu9z` grew from one site to two while its plan was being written, and `1uu0f`'s drift class was found twice by accident during `1usqm`. Both make the census a gating requirement rather than a step. Do not assume the known site set is complete.
- **BLOCKING sequencing constraint — the earlier "disjoint files" claim was false.** Wave `1uugh advisory-diagnostic-severity` is `implementing`, not readied: its implementation is in the uncommitted working tree (`_prepare_envelope` present, `_prepare_stale_advisories` removed). `1uu9z` edits `wf_prepare_wave_response`, the exact function `1uugh` restructured. Two consequences: `1uu9z` must not start until `1uugh`'s implementation settles, and any return or diagnostic it adds inside prepare **must route through `_prepare_envelope`**, because `1uugh` AC-4 is a source-derived AST test asserting every return in that function does. `1uu0f` and `1uu9y` touch neither file and are unaffected.
- **Superseded 2026-08-10:** `1uugh` and `1usqm` are both `Status: closed`, so the single-OPEN constraint recorded here no longer applies. The sequencing it required was honored: `1uu9z` landed after `1uugh` settled, and `1uugh`'s `_prepare_envelope` AST test still passes.
- **Why these were not folded into `1uugh`:** its Requirement 8 forbids widening scope, and admitting anything would have moved its canonical text and re-opened a readiness cycle that took four review rounds. That reasoning stands; only the description of its status was wrong.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-09: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1uu0f` asserted a drift that was not one — "five narrow regions" is correct, since the document excludes carrier stabilization by its own "first stabilizes carriers … then" clause and the function's docstring matches one-for-one, so implementing the AC as written would have converted a correct sentence into a wrong one, while a real drift of the same shape ("Exactly 18" against a 20-member frozenset) sat unnamed in the same document; strongest-alternative: for `1uu9z`, degrade-and-continue on an unreadable change doc rather than refuse — declined because `_prepare_policy_state` degrades as a SELECTION helper protecting a narrow invariant, by computing the digest over a subset, whereas prepare is a DECISION tool that mints a roster and publishes a receipt over the full admitted set, so degrading there would publish a receipt whose digest silently omits an admitted change)
- **Seat evidence [red-team] — 2026-08-09:** WITHHELD with five P1s and eight lower findings, all folded. `1uu9z`'s census was wrong in both directions — five sites, not two, and neither named site was actually unguarded — and the miss was decisive: a patch simulation showed `wf_close_wave` still raises from `_generate_wf_close_wave_summary`, so AC-2 was unsatisfiable by the declared scope. `1uu0f` asserted the non-drift above and missed the real one. `1uu9z` Requirement 2 contradicted shipped behavior, since prepare already refuses via a blocking `change_doc_unreadable`. And all three documents mis-stated wave `1uugh` as readied when it is `implementing` and holds the OPEN slot, with its implementation in the uncommitted tree touching the exact function `1uu9z` edits. Verified correct: `_prepare_policy_state`'s `(OSError, UnicodeError)` catch and the `read`-only degradable set, both real `1uu0f` drifts, the seed 007 bullet and the second-writer premise, the 68-seed `artifact_or_test_id` census, and that the doc-to-code reconciliation direction is right.
- **Seat evidence [docs-contract-reviewer] — 2026-08-09:** WITHHELD with two P1s and nine lower findings, all folded. Both P1s land on `1uu9y`, which exists *because* `1urlb` shipped believing its consumer surfaces were clean and then repeated that omission at two surfaces: `docs/prompts/council-review.prompt.md`, a registered renderer carrier holding seed 237's sentence byte-identically, and `_prepare_council_instructions` in `server_impl.py`, the runtime brief a seat actually receives. Independently reached the same "five narrow regions" non-drift as red-team. Also found AC-4 unachievable (seed 211 states a materially different rule and Scope forbids re-editing it), AC-3 specifying the rendered seed 209 when the renderer emits only a carrier stub, AC-1 demanding a named insertion point without naming one, and `1uu0f` Requirement 1 omitting the `prepare_signoff_recorded` conjunct — which would have installed a second not-quite-right rule in seed 007, the failure that change exists to end. Verified clean: all three Serialization Points blocks parse to exactly their intended paths, and **zero** line citations across all three plans and the wave record, which it noted as the cleanest self-application in this arc.
- **Fold disclosure:** every P1 and P2 was folded before this verdict. The seats did **not** re-review the folded text. Three claims this wave asserted as measured fact did not survive contact with the tree, and one of them was inverted — the plans now record each as withdrawn rather than silently corrected, because the failure mode is the subject of two of the three changes.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 78 | 2,230,651 |
| implement | 82 | 2,536,816 |
| review | 1 | 0 |
| **Total** | **161** | **4,767,467** |

<!-- wave:context-efficiency-state {"generation":161,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":82,"content_source_credit":2738617,"derived_artifact_credit":0,"direct_net":2536816,"estimated_tokens_saved":2536816,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2468,"response_debit":200764,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":78,"content_source_credit":2342092,"derived_artifact_credit":4200,"direct_net":2230651,"estimated_tokens_saved":2230651,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6165,"response_debit":115172,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2071,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20,"response_debit":2051,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":161,"content_source_credit":5080709,"derived_artifact_credit":4200,"direct_net":4765396,"estimated_tokens_saved":4767467,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8653,"response_debit":317987,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7127},"wave_id":"1uwpf receipt-and-citation-contract-followups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 2 | 1,653,188 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":1653188,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
