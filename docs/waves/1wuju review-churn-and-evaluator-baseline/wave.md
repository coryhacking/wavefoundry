# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wuju review-churn-and-evaluator-baseline`
Title: Review Churn And Evaluator Baseline

## Objective

Remove the three sources of rework that wave `1wur7` paid for five times over: guards claimed landed without a test that fails on their deletion, review rounds run against a moving tree with unbudgeted lane sweeps and deferred external blockers, and a standing retrieval baseline that costs two quiet runs on a shared machine. When this wave closes, the seeds state the landing rule, the round protocol, the lane budget, and the blocker rule with pins; new docs-lint sensors ship advisory with a recorded flip, starting with the AC-locality sensor; and one evaluator run is a usable baseline.

## Changes

Change ID: `1wujr-enh review-cycle-churn-controls`
Change Status: `implemented`

Change ID: `1wujs-enh advisory-first-blocking-sensors`
Change Status: `implemented`

Change ID: `1wujt-enh one-run-evaluator-baseline`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer


Completed At: 2026-09-01

## Wave Summary

Wave `1wuju` (Review Churn And Evaluator Baseline) delivered 3 changes: Review-Cycle Churn Controls: Mutation Evidence, Tree Freeze, Lane Budgets, Blocker Escalation, Advisory-First Shipping for New Blocking Sensors, and One-Run Evaluator Baseline. Notable adjustments during implementation: Review-Cycle Churn Controls: Mutation Evidence, Tree Freeze, Lane Budgets, Blocker Escalation: Implemented (seed gate opened and closed around the edits; `wf_sync_surfaces` run afterwards). Seed 209: three Briefing Packet required fields (`tree_fingerprint` by `git hash-object` over `files_in_scope`, `time_budget`, `sweep_rule`), the **Frozen tree per round** and **External blocker escalation** harness behaviours with the `tree_moved_under_review` process finding and the statement that `frozen_boundary` and `policy_input_digest` freeze neither code, the once-per-round repair sentence under Repair re-verification, the **Landing rule for guards** under Code-Grounded Verification bound to qa condition 5's `focused-mutation` vocabulary, and the census re-derivation sentence. Seed 180: the landing rule beside "Reading code is not executing it" and the blocker rule on the coordinator Escalation bullet. Seed 190: the `tree_moved_under_review` closure guardrail. Seeds 214, 221, 239: the mutation-table requirement in each Verdict Format as the prose projection of `known_bad_detection_method: focused-mutation`. Reconciled outside renderer-owned regions: `implement-wave.prompt.md` (two guardrails), `review-wave.prompt.md` (packet fields and frozen-tree sub-bullets under step 2), `close-wave.prompt.md` (closure bullet), `docs/agents/{architecture,qa}-reviewer.md` Output Shape and `code-reviewer.md` Review Rubric; `testing-architecture.md` gained a Landing Rule section; CHANGELOG bullet added. Pinned sentences (each an `assertIn` in `ReviewCycleChurnControlPinTests`): the three packet rows; the Frozen-tree sentence; the neither-freezes-code sentence; the `tree_moved_under_review` sentence; the External-blocker heading and its same-message sentence; the once-per-round sentence; the Landing-rule sentence and its focused-mutation binding; the census sentence; the seed-180 landing and escalation sentences; the seed-190 guardrail; the three lane-seed mutation-table sentences; the two implement-wave guardrails; the two review-wave sub-bullets; the close-wave bullet; the two role-doc bullets and the code-reviewer rubric line; the architecture section heading; the CHANGELOG bullet. Prose pins are landed by construction (deleting the sentence fails its assertion), which is the honest limit of a seed-text change.; Review-Cycle Churn Controls: Mutation Evidence, Tree Freeze, Lane Budgets, Blocker Escalation: Delivery round 2. DOCS-DEL-2: every clause the round-1 repair added to the prompts, role docs, and `testing-architecture.md`, and the report-at-budget tail on seeds 209/214/221/239, is now pinned by an extended `assertIn` (each was deletable with the pins green). The plan-feature prompt says "decided, not forgotten" as seed 170 does; the allowlist comment in `wave_validators.py` no longer says a false positive is a hard stop today.; Advisory-First Shipping for New Blocking Sensors: Delivery round 1. CODE-DEL-1 / ARCH-DEL-1: `wf_close_wave` keyed its early error return on list non-emptiness, so an advisory `docs_lint_warning` blocked the close; the predicate now ignores `advisory: true` entries and the success envelope carries them, pinned by `test_advisory_lint_warning_never_blocks_review_or_close` (closable legacy fixture: review `ok`, close `dry_run`, one advisory diagnostic each), which fails on the pre-repair predicate. ARCH-DEL-2: `wf_audit_install` renders the warnings on every envelope (the earlier "carry no wave documents" rationale was false: the install audit runs the full-corpus lint, `docs/waves` included); the spec and `testing-architecture.md` name it. Landing-rule pins added for the incremental changed-docs CLI sink (`test_incremental_changed_wave_record_routes_an_advisory_finding_to_warnings`; the AC sensors run from the wave-record branch, so the changed path is `wave.md`), the changed-event-wave sink (`test_incremental_changed_ledger_revalidates_the_owning_wave_through_the_sink`, a top-level copy of the fixture wave with an `events.jsonl`-only change), the readiness-phase render (`review_prepare` subtest), and the unregistered-sensor branch (`test_an_unregistered_sensor_stays_a_failure`). `SENSOR_POLARITIES` is now load-bearing: the router raises `ValueError` on an unknown polarity (`test_an_unknown_polarity_fails_loudly`). DOCS-DEL-1 / QA-DEL-1: the sensor docstring and the allowlist comment no longer call the polarity blocking; the sanctioned-site census message says nine sites.

**Changes delivered:**

- **Review-Cycle Churn Controls: Mutation Evidence, Tree Freeze, Lane Budgets, Blocker Escalation** (`1wujr-enh review-cycle-churn-controls`) — 4 ACs completed. Key decisions: Readiness council amendments adopted (RT-RDY-9, RT-RDY-10, DOCS-RDY-1, DOCS-RDY-2, DOCS-RDY-3, DOCS-RDY-11): seed 209 owns the round protocol and the briefing fields; the mutation table is the prose projection of the existing `known_bad_*` evidence fields, not a new ledger field; the fingerprint command is named; the three lane role docs join the reconciled set; a CHANGELOG bullet is added.; Seed rules and pins first; no mutation-testing tool in this change.
- **Advisory-First Shipping for New Blocking Sensors** (`1wujs-enh advisory-first-blocking-sensors`) — 5 ACs completed. Key decisions: OPERATOR-APPROVED reversal of `1wur7` REL-DEL-3 on timing: the AC-locality sensor is registered advisory. REL-DEL-3 kept blocking polarity and explicitly rejected "advisory for one release"; the new facts are zero field data at that decision, five review rounds in which every unpinned member was a hard stop on a compliant criterion, and the upgrade-day halt for consumers. The flip condition is recorded: field data from at least one release with no false-positive report, decided at the release checklist step Requirement 5 adds. Approved by the operator's instruction to prepare, review, and implement the presented plan, which named this reversal as the operator's decision; the operator may veto at readiness.; Advisory-first for NEW sensors only; existing blocking validators keep their polarity.
- **One-Run Evaluator Baseline** (`1wujt-enh one-run-evaluator-baseline`) — 4 ACs completed. Key decisions: No within-run jitter estimator (RT-RDY-1). Replay of the committed fixture with the evaluator's own helpers, three estimators (A: repetition-index pseudo-arms; B: per-case relative range, median across cases; C: half-corpus split), threshold 0.05: contended `code_search` PAIR 0.181 but A 0.020/0.025, B 0.024/0.022; contended `docs_search` PAIR 0.208 but A 0.017/0.017, B 0.017/0.021; contended `code_ask` PAIR 0.250, A 0.258/0.151, B 0.179/0.149; quiet `1seaw` `code_ask` PAIR 0.017 but A 0.257/0.266, B 0.196/0.196; quiet `before-1seas` `code_ask` PAIR 0.009 but A 0.125/0.130, B 0.198/0.196; quiet `code_search` and `docs_search` at or below 0.014 under every estimator. No estimator separates: A and B miss two of four contended tools and flag every quiet `code_ask` run; C compares different fixtures. A per-tool threshold near 0.012 would be fitted to one contended run.; Keep whole-module byte binding for `evaluator_identity` (RT-RDY-4).
## Watchpoints

- Watchpoint (seed gate): `1wujr` and `1wujs` edit seeds under `.wavefoundry/framework/seeds/`; open `seed_edit_allowed` immediately before and close it immediately after each edit batch, and hand-reconcile the project prompt surfaces the same day.
- Watchpoint (apply the landing rule to itself): every guard, registry branch, and estimator this wave adds is landed only when a named test fails with it deleted; record the mutant and the failing test in the Progress Log before requesting review. The lanes are briefed with the sweep rule and budget from `1wujr` even though that seed text lands in this same wave.
- Watchpoint (frozen tree per round): no edits under the reviewed paths while a lane runs; collect every lane's findings, repair once, re-snapshot once, and record the fingerprints in the briefs.
- Watchpoint (polarity decision, operator-approved at prepare): `1wujs` registers the AC-locality sensor advisory, reversing `1wur7` REL-DEL-3 on timing only; the operator approved the presented plan that named this reversal and may veto at readiness; the flip to blocking is a later recorded change decided at the release checklist.
- Retro disposition (readiness RT-RDY-11): census re-derivation lands in `1wujr` as one seed-209 sentence; docs-from-code drift is out of scope here (the constants lint from `1seax` covers numeric claims, and behavioural claims stay a docs-contract lane responsibility stated in seed 209 already); compaction-summary errors are a harness property with no seed remedy and are not dispositioned by this wave; the mutation-testing tool waits for field data from the `1wujr` rule.
- Watchpoint (evaluator identity): `1wujt` changes `retrieval_eval.py`, which moves `evaluator_identity`; the standing pair recorded by `1wur7` already no longer binds. Record the new one-run baseline LAST, after every edit, and never while a lane or a suite is running. Requirement 5's identity-granularity choice is a prepare-council item with a Decision Log row as the deliverable.
- Watchpoint (no gate shaping): none of the three changes may loosen a retrieval-quality floor or the response-size ceiling; only latency and contention are advisory, per the `1wur7` close decision.
- Follow-up (delivery review DOCS-DEL-1, out of this wave's scope): the change-document scaffold guidance in seeds `170`, `040`, `160`, and the install plan template does not warn that a root-level file (a bare `CHANGELOG.md`) or a glob inside a `Serialization Points` bullet turns the whole bullet into prose and silently drops the lanes it declares; the parser requires a path containing `/` and no `*`. Add the one sentence to each scaffold in a later seed wave; `test_declaration_change_loses_no_lane_anywhere_in_the_corpus` catches the symptom in this repository only.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-01: PASS with amendments** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1wujt` as drafted rested on a within-run jitter estimator that the committed fixture refutes, since robust floor and median statistics cannot see contention from inside one run and `code_ask` carries 12% to 27% intrinsic spread on a quiet machine, so the estimator would have recorded contention judgements wrong in both directions on the receipt the standing gate reads; strongest-alternative: accept a single receipt as a baseline at the existing 25% floor with contention recorded as not judged and whole-module identity binding kept, which is smaller, fits no threshold, and records nothing it cannot defend; ADOPTED as the change's Requirements 1 to 5).
- Seat evidence — red-team (adversarial primer, standard depth): replayed `warm_sample_pairs.json` through the evaluator's own helpers under three estimators and produced the refutation table now in `1wujt`'s Decision Log (RT-RDY-1); showed the within-run ratio would be inert or harmful in the band (RT-RDY-2); found the fixture is pooled and case-major only by the append-site order (RT-RDY-3); decided whole-module identity binding stays (RT-RDY-4); found only `wf_validate_docs` renders warnings today so an advisory sensor's findings would be invisible at Prepare, Review, and Close (RT-RDY-5); required an operator-approved Decision Log row for the REL-DEL-3 reversal (RT-RDY-6); corrected two false rationale sentences and an undelivered mitigation (RT-RDY-7, RT-RDY-8, RT-RDY-11); bound the mutation table to the existing `known_bad_detection_method` vocabulary and named the fingerprint command (RT-RDY-9, RT-RDY-10); judged the wave's self-application coherent (RT-RDY-12). Every load-bearing claim verified against the tree; two refuted ("no sensor uses the warnings channel", "three pairs, none quiet").
- Seat evidence — docs-contract-reviewer (rotating seat): mapped every surface each change names to its real owner and render mode, moving the round protocol from seed 190 to seed 209 (DOCS-RDY-1), the mutation table onto the lane seeds' verdict sections as prose over the existing evidence fields (DOCS-RDY-2), and the three lane role docs into the reconciled set because the renderer owns only their marker regions (DOCS-RDY-3); enumerated exactly what the warnings channel has and lacks, including the `advisory: true` diagnostic flag (DOCS-RDY-4); listed every sentence on every surface that still calls the sensor blocking (DOCS-RDY-5) and put the gate contract in the tool-surface spec (DOCS-RDY-6); found the fixture pooled (DOCS-RDY-7) and the estimator under-specified (DOCS-RDY-8); raised the docs AC to required because the listed sentences become false, not incomplete (DOCS-RDY-9); fixed decision provenance and two wording faults (DOCS-RDY-10 to DOCS-RDY-13). Ran the AC-locality sensor over the three documents: zero findings.
- Council synthesis: PASS with amendments, all applied before readiness was recorded: `1wujr` Requirements 1 to 5, AC-1, AC-3, Tasks, Serialization Points, and a Decision Log row; `1wujs` Rationale, Requirements 1 to 5, AC-1, AC-3, new AC-5, Scope, Serialization Points, the operator-approved Decision Log row, and the Risks row; `1wujt` retitled, Rationale, Requirements 1 to 5, Scope, all ACs, Tasks, the execution graph, AC Priority, two Decision Log rows carrying the refutation table and the identity decision, and Risks; this record's Wave Summary, the polarity watchpoint, and the retro disposition.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | not_issue | no | not_required | — |
| ARCH-DEL-2 | not_issue | no | not_required | — |
| ARCH-RV2-1 | not_issue | no | not_required | — |
| CODE-DEL-1 | not_issue | no | not_required | — |
| CODE-DEL-2 | not_issue | no | not_required | — |
| CODE-DEL-3 | not_issue | no | not_required | — |
| DOCS-DEL-1 | not_issue | no | not_required | — |
| DOCS-DEL-2 | not_issue | no | not_required | — |
| DOCS-FIN-1 | not_issue | no | not_required | — |
| QA-DEL-1 | not_issue | no | not_required | — |
| QA-DEL-2 | not_issue | no | not_required | — |

*Machine review state — 11 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 11*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
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
| plan | 50 | 1,142,123 |
| implement | 164 | 3,508,039 |
| review | 75 | 1,218,771 |
| **Total** | **289** | **5,868,933** |

<!-- wave:context-efficiency-state {"generation":286,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":164,"content_source_credit":3806349,"derived_artifact_credit":0,"direct_net":3508039,"estimated_tokens_saved":3508039,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5521,"response_debit":292789,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":50,"content_source_credit":1246833,"derived_artifact_credit":2843,"direct_net":1142123,"estimated_tokens_saved":1142123,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3165,"response_debit":110084,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":75,"content_source_credit":1359558,"derived_artifact_credit":1645,"direct_net":1218771,"estimated_tokens_saved":1218771,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42940,"response_debit":103270,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":289,"content_source_credit":6412740,"derived_artifact_credit":4488,"direct_net":5868933,"estimated_tokens_saved":5868933,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51626,"response_debit":506143,"source_credit_count":264,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9474},"wave_id":"1wuju review-churn-and-evaluator-baseline"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 6 | 5,243,973 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":5243973,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
