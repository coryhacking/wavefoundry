# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21j63 intent-fit-review`
Title: Intent Fit Review

## Objective

Operators get a reviewer's judgement of whether the plan, and then the delivered work, meets the stated intent before close: an intent-fit verdict in the readiness and delivery council output, with the `Intent outcome:` paragraph drafted before delivery review. A council approval cannot be recorded without that verdict, and the qa-reviewer independently maps each AC to the intent at readiness. A delivery that honestly did not establish its intent can still close; Review and Close show that verdict to the operator before sign-off. Boundary: close behaviour is otherwise unchanged; the tool checks that a verdict was given and is consistent with approving, not that it is right, and historical ledgers stay valid.

## Changes

Change ID: `21j62-enh review-intent-fit-at-prepare-and-delivery`
Change Status: `implemented`

Change ID: `21kk5-enh require-intent-fit-on-council-approvals`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-25

## Wave Summary

Wave `21j63` (Intent Fit Review) delivered two changes: Review Intent Fit at Prepare and Delivery and Require intent fit on council approvals and give QA an intent-coverage duty. Notable adjustments during implementation: Review Intent Fit at Prepare and Delivery: Readiness repair (one bounded pass): code-reviewer F1/F2, docs-contract F1-F3 and council notes 1-3 folded in as Requirements 3-6, AC-2/3/4 wording and seeds 160/100 scope. No finding was blocking.; Review Intent Fit at Prepare and Delivery: Implemented. Seed 215 Responsibilities + Output Shape `intent_fit`; seeds 160 (seed 209 prepare/review baseline bullet) and 100 (intent summary); Prepare/Review lifecycle templates and rendered copies; backticked `## Review checkpoints` references in edited files now exact. Discovered during implementation and kept in Requirement 1/6 scope: this repo's rendered copies of the same carriers, `docs/agents/specialists/council-chair.md` (Output Shape) and `docs/prompts/upgrade-wavefoundry.prompt.md` (same baseline bullet), updated identically and covered by the new carrier test. Scaffold: `## Review Checkpoints` appended after `## Dependencies` (last scaffold section; the context-efficiency projection may append its own section later). Tests: `IntentFitCarrierTests` (render suite, 193 OK) and `test_scaffold_carries_review_checkpoints_for_the_intent_composer` (lifecycle, 655 OK). Known-bad in a scratch copy: scaffold heading removed fails the scaffold test (`0 != 1`); the review-wave clause removed fails the carrier test; both pass on clean code. Gapfill: prompt and seed text edited by short scripts (bulk-mechanical string insertion), and the mutation copy run by shell.; Review Intent Fit at Prepare and Delivery: Delivery review. code-reviewer APPROVE (lifecycle 655 OK, render 193 OK, scratch mutants killed, `create_wave` is the only wave-record writer; advisory: lifecycle fixtures that append a second checkpoints heading). docs-contract APPROVE (`wf_validate_docs` clean). Delivery council PASS, `intent_fit` confirmed the drafted `partial` Intent outcome. Editorial repairs inline from council notes: L1 added the seed 215 Responsibilities bullet to `docs/agents/specialists/council-chair.md`; L2 added "after release" to both Prepare prompts' measure clause. L3 (`docs/contributing/review-and-evals.md` has no intent_fit wording) is self-hosted drift outside this change, left as a follow-up.

Intent outcome: partial, updated after independent delivery review and final qualification of Requirement 13. Both Review prompts now assign the independent outcome check from the current required delivery roster: QA when present, otherwise one existing required reviewer, and an explicit no-independent-lane-check note when the roster is empty. Required Council still judges the same draft and reuses an assessment when available. Seed 100, seed 160, rendered upgrade guidance, review-and-evals and CHANGELOG now agree with the Review prompts; QA carriers and Review prompts distinguish substantive intent shortfalls (typed findings) from wording-only corrections (editorial). The operator agreed to retain existing roles. Eighteen focused tests passed in 2.395s; the actual selector fixtures cover QA, fallback and empty rosters; both saved QA-only prompt bodies and the stale install/upgrade/summary baseline fail the new checks. Full docs validation passed. Independent delivery review passed: 18 focused tests in 2.614s, all ten hashes unchanged, both QA-only baselines and all five stale carriers rejected. The code, QA, docs-contract and focused-Council judgments share one disclosed fresh independent context. This is evidence of instruction consistency and reachability, not autonomous reviewer reliability. Final canonical qualification passed 12,132 tests across 209 files with 12 existing skips in 616.333s, exit 0; all ten reviewed source hashes remained unchanged and the runner wrote a green receipt. All affected specialist and focused Council delivery approvals are current; Council retains intent_fit partially because repeated reviewer adherence and later-wave benefit remain unestablished. The earlier completed run and its bookkeeping rejection remain historical evidence; receipt-reconciliation plan 21lue remains separate and unimplemented.

**Changes delivered:**

- **Review Intent Fit at Prepare and Delivery** (`21j62-enh review-intent-fit-at-prepare-and-delivery`) — 5 ACs completed. Key decisions: Make intent fit a named council-chair output item at both phases, and draft `Intent outcome:` before `council-delivery`; Mechanism efficacy
- **Require intent fit on council approvals and give QA an intent-coverage duty** (`21kk5-enh require-intent-fit-on-council-approvals`) — 11 ACs completed. Key decisions: Carry `intent_fit` in the existing `evidence` payload, not a new tool parameter; Require at write, optional at read
## Watchpoints

- Watchpoint: seed edits need `seed_edit_allowed`; other framework edits need `framework_edit_allowed`.
- Watchpoint: this wave dogfoods the guidance (AC-4): readiness states `intent_fit`, and `Intent outcome:` is drafted before `council-delivery`.

## Review Checkpoints

2026-10-25: Operator supplied a separate review and requested continuation. Confirmed: QA is not universal in the delivery roster; remaining installation/upgrade/summary carriers still describe the former Council-first placement; substantive outcome corrections need an explicit finding/editorial distinction. Requirement 13 and AC-11 own one combined guidance repair. The prior readiness approvals and independent delivery review were current when checked; this new scope requires re-Prepare. Prior seed/framework gate opens preceded the IR-1 edits and their closes followed them; a currently closed gate does not establish an unauthorized earlier edit. Keep 21lue's receipt-acceptance plan separate.

2026-10-25: Operator-directed bounded correction of IR-1 before closure: draft the outcome in every delivery review, have QA independently confirm or correct it, and let required Council reuse the assessment. Admitted in 21kk5 Requirement 12 / AC-10. Allocation: coordinator owns the five guidance/test paths; an independent focused readiness reviewer assesses code-test, QA, docs-contract and council effects with shared context disclosed; a fresh delivery reviewer independently verifies the repair. No new runtime enforcement, universal Council or delivery experiment. Optional IR-4 wording is not included; IR-2/IR-3 evaluation remains outside this correction.

2026-10-25: Independent outcome review (standalone improvement review; advisory, no lifecycle signoff). Assessment: useful intent-review machinery delivered, but consistent achievement of the original goal remains partially established. IR-1: the pre-delivery outcome draft and council judgment are conditional on `council-delivery` in the Review prompt; targeted delivery can omit that council. Recommend an outcome judgment by an existing required reviewer on the non-council path, without adding a council or approval type. IR-2: AC-6 demonstrates one readiness gap detection and one clean-control result, not delivery detection of passing ACs that miss the goal; retain the deterministic tests and add one bounded matched delivery example rather than more phrase pins. IR-3: later verdict/finding presence measures adoption, not useful decisions or recurring cost; sample real waves for a concrete decision improved, false alarms and added review effort. IR-4: every intent gap currently takes formal triage, explicitly bypassing the readiness finding bar; preserve triage for real shortfalls, deduplicate by outcome and distinguish agreed after-release measurement from a defect. Verification: 11 `test_intent_fit_approvals` tests passed in 2.378s; a direct current-source `delivery_council_required` probe returned false for targeted/no triggers and true for universal. This is source review plus focused verification, not a new full-suite qualification or proof of agent reliability. No implementation repair or wave closure was performed.

2026-10-24: Readiness council (red-team primer, rotating docs-contract seat, chair synthesis) PASS, unanimous, max severity low. intent_fit: establishes, for 21j62 and the Objective; measure of success (later waves show readiness intent_fit lines and a dated pre-delivery Intent outcome) readable from wave records and events.jsonl to the day. One bounded repair pass folded in the code-reviewer, docs-contract and council notes.

2026-10-25: Change 21kk5 readiness escalation. After one bounded repair and focused verification, code-reviewer, qa-reviewer and docs-contract-reviewer approved; the council blocked (R1: refusing `does_not` on `council-delivery` would stop an honestly not-established wave from closing, contradicting the Objective's close boundary). Operator decision: "refuse on readiness and accept at delivery with user acknowledgment". Scope: one further bounded repair (Requirements 1, 4, 6 and 10, AC-1, AC-6 wording, AC-8, Risks, Decision Log, Objective) and one focused verification round.

2026-10-25: Operator simplification of 21kk5 after the second focused round passed: the operator asked for "as little overhead as possible" and approved replacing the acknowledgment field and close gate with a non-blocking Review and Close advisory; the existing operator sign-off is the acknowledgment. Scope: Requirement 10, AC-8, Decision Log, Objective sentence, and one focused verification round.

2026-10-25: Operator direction during implementation of 21kk5: "when we encounter issues with intent, they need to be evaluated like we do a bug. They don't have to stop like that, but we need to evaluate them and determine whether they should be fixed now, etc." Scope: Requirement 11, AC-9 and one task (seeds 215 and 239, rendered copies, review-and-evals, carrier test), and one focused verification round.

2026-10-24: Intent outcome: partial. Delivered and exercised once: seed 215 and this repo's council-chair role doc name `intent_fit` for readiness and delivery; both Prepare and Review prompt pairs, seed 160 and its rendered upgrade prompt, and seed 100 carry the readiness verdict condition and the dated pre-delivery draft step; `wf_create_wave` scaffolds `## Review Checkpoints` last (IntentFitCarrierTests, the scaffold composer test, known-bad mutants in a scratch copy, full suite 12116 OK). This wave's own readiness council recorded `intent_fit: establishes` in its typed approval, and this paragraph was drafted before `council-delivery`. Not established: whether later waves act on the guidance. The plan's measure of success (later waves show readiness `intent_fit` lines and a dated `Intent outcome:` before `council-delivery`) can be read only after release. Limitation: the guidance advises the council; no gate checks it. The delivery council judged this paragraph supported (`intent_fit`: partial confirmed).

2026-10-25: Intent outcome: partial, for both changes and the wave Objective. Delivered and exercised: the council-chair reports `intent_fit` at readiness and delivery and the coordinator drafts this paragraph before the delivery council (21j62); council approvals must now carry that verdict as `intent_fit`, the worst across every admitted change and the Objective, readiness refuses `does_not` as a finding route, delivery accepts it with a non-blocking Review and Close advisory once that approval is current, the Prepare council template, guided schema and guided actions name the field, the qa-reviewer maps each required AC to the intent at readiness, and intent issues are typed findings triaged under seed 209 like any defect (21kk5; test_intent_fit_approvals, IntentFitApprovalCarrierTests, the golden refresh, scratch-copy mutants killed, all 321 repository ledgers still valid). This wave used it on itself: one readiness council approval carries `intent_fit` through the new check (to be re-recorded against the current receipt with the delivery council approval, AC-7), and the delivery intent issues went through the standard finding flow (21KK5-DEL-AC6, 21KK5-DEL-AC1, 21KK5-DEL-CURRENCY and 21J63-DEL-OUTCOME-PLACEMENT, each repaired and independently reverified or dispositioned). The qa-reviewer's independent intent check caught the declared gap on a mis-aimed plan and, on an operator-directed follow-up, raised no intent-coverage finding on an independently authored and vetted gap-free control (21KK5-DEL-AC6 repaired and reverified; AC-6 met). Not established: reliability beyond one sample each way on simple plans, and whether later reviewers set the verdict honestly rather than by reflex, which is outside what the tool checks. The measure of success (later council approvals carrying `intent_fit`; intent issues recorded as findings with derived dispositions) can be read only after release from later `events.jsonl` ledgers.

2026-10-25: Intent outcome: partial, for both changes and the wave Objective, updated for independent delivery review of IR-1. The four guidance carriers now require the coordinator's outcome draft and QA's independent confirmation or correction on every delivery review, including the targeted path without Council; required Council reuses the same draft and assessment. No runtime gate or approval type changed. The correction passed 17 focused tests (2.535s coordinator; 3.541s fresh independent reviewer); both saved pre-fix prompts and all four conditional-placement/removed-QA controls were rejected. Independent code, QA, docs-contract and focused Council assessments approve the final hashes, with shared reviewer context disclosed. The canonical run completed all 209 test files successfully (12,131 tests, 12 existing skips, 635.267s), but qualification failed solely because the coordinator corrected local prompt list numbering and closed the edit gates during execution. The final numbering edit was independently confirmed; no valid current green receipt is claimed. The operator prohibited an unchanged full-suite repeat; the attempted repeat was cancelled before starting and no test process remained. This establishes instruction coverage, not repeated reviewer adherence or delivery judgment reliability. Later-wave benefit/cost remains unestablished. Receipt reconciliation is separately staged as 21lue; no receipt was rewritten and the wave remains unclosed.

2026-10-25: Intent outcome: partial, updated after independent delivery review and final qualification of Requirement 13. Both Review prompts now assign the independent outcome check from the current required delivery roster: QA when present, otherwise one existing required reviewer, and an explicit no-independent-lane-check note when the roster is empty. Required Council still judges the same draft and reuses an assessment when available. Seed 100, seed 160, rendered upgrade guidance, review-and-evals and CHANGELOG now agree with the Review prompts; QA carriers and Review prompts distinguish substantive intent shortfalls (typed findings) from wording-only corrections (editorial). The operator agreed to retain existing roles. Eighteen focused tests passed in 2.395s; the actual selector fixtures cover QA, fallback and empty rosters; both saved QA-only prompt bodies and the stale install/upgrade/summary baseline fail the new checks. Full docs validation passed. Independent delivery review passed: 18 focused tests in 2.614s, all ten hashes unchanged, both QA-only baselines and all five stale carriers rejected. The code, QA, docs-contract and focused-Council judgments share one disclosed fresh independent context. This is evidence of instruction consistency and reachability, not autonomous reviewer reliability. Final canonical qualification passed 12,132 tests across 209 files with 12 existing skips in 616.333s, exit 0; all ten reviewed source hashes remained unchanged and the runner wrote a green receipt. All affected specialist and focused Council delivery approvals are current; Council retains intent_fit partially because repeated reviewer adherence and later-wave benefit remain unestablished. The earlier completed run and its bookkeeping rejection remain historical evidence; receipt-reconciliation plan 21lue remains separate and unimplemented.

2026-10-25: Memory retrospective: reviewed the one proposed roster-repair candidate and selected none. The canonical Review/QA/install/upgrade guidance and regression tests already carry its future action; a second memory would duplicate them. No memory file created.

2026-10-25: Closure reconciliation: retain the admitted change docs, authoritative ledger and AC-6 experiment evidence in place; the declared gap, distinct test plans, control declaration and results substantiate unique review claims. Routine repair packets and suite logs remain in temporary storage. No wave-owned disposable repository artifacts identified for deletion. Operator explicitly authorized closure after reviewing the recorded limits; no new implementation change or suite rerun is needed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21J63-DEL-NONCOUNCIL-INTENT | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, council-delivery |
| 21J63-DEL-OUTCOME-PLACEMENT | do_now | no | completed | council-delivery |
| 21J63-DEL-ROSTER-CARRIERS | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, council-delivery |
| 21KK5-DEL-AC1 | do_now | no | completed | qa-reviewer |
| 21KK5-DEL-AC6 | do_now | no | completed | qa-reviewer |
| 21KK5-DEL-CURRENCY | do_now | no | completed | code-reviewer |

*Machine review state — 6 findings; current: do_now 6, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 68 | 2,459,594 |
| implement | 91 | 1,838,942 |
| review | 277 | 2,719,891 |
| **Total** | **436** | **7,018,427** |

<!-- wave:context-efficiency-state {"generation":434,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":91,"content_source_credit":1912602,"derived_artifact_credit":1271,"direct_net":1838942,"estimated_tokens_saved":1838942,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2845,"response_debit":78922,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6836},"plan":{"calls":68,"content_source_credit":2561656,"derived_artifact_credit":2155,"direct_net":2459594,"estimated_tokens_saved":2459594,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3008,"response_debit":125074,"source_credit_count":158,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":23865},"review":{"calls":277,"content_source_credit":3357307,"derived_artifact_credit":15218,"direct_net":2719891,"estimated_tokens_saved":2719891,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56450,"response_debit":599474,"source_credit_count":216,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3290}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":436,"content_source_credit":7831565,"derived_artifact_credit":18644,"direct_net":7018427,"estimated_tokens_saved":7018427,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62303,"response_debit":803470,"source_credit_count":427,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":33991},"wave_id":"21j63 intent-fit-review"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 32 | 0 | 11 | 21,869,608 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":21869608,"surfaced_events":32} -->
<!-- wave:exploration-avoided end -->
