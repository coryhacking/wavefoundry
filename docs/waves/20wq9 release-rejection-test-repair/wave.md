# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20wq9 release-rejection-test-repair`
Title: Release Rejection Test Repair

## Objective

Make two release rejection tests in `test_build_pack.py` reach the checks they are named for, so the stale-artifact and single-public-package refusals are actually tested before 1.32.0.

## Changes

Change ID: `20wq8-debt release-main-rejection-tests-reach-their-checks`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator (agent)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-17

## Wave Summary

Wave `20wq9` (Release Rejection Test Repair) delivered one change: Release rejection tests reach their checks. Notable adjustments during implementation: Release rejection tests reach their checks: Implemented by copying the reviewed prototype file, byte-identical to the scratch tree, under `framework_edit_allowed`. Focused `test_build_pack` 152/152. Delivery: code and QA lanes passed with fresh scratch mutants, five AC-1 mutants plus a stale-check-moved-later mutant. Follow-up, not taken (smaller work wins): red-team mutants R1 (stale check limited to `.pyz`), R2 (an old model companion over-flagged as stale), R3 (stray `.zip` extras ignored) and R4 (removed-package check disabled) pass both tests. The Decision Log's "extra-package test catches over-flagging" holds for normal release zips only. Direct unit cases of `_reject_stale_public_build_artifacts` over a mixed before-mapping would close R1 and R2. Gapfill: scratch-copy shell edits and runs, because the prototype lived outside the indexed tree.

**Changes delivered:**

- **Release rejection tests reach their checks** (`20wq8-debt release-main-rejection-tests-reach-their-checks`) — 3 ACs completed. Key decisions: Make the tests work rather than remove them.; Readiness review folded in: model stub in the stale-artifact test, the single error-line assertion, the block-limit wording, and the mutant list in AC-1.
## Watchpoints

- Watchpoint: test edits only under `framework_edit_allowed`, closed immediately after.
- Watchpoint: no real model build in the tests.
- Follow-up: run the whole suite last; the three release qualification reports are regenerated separately before 1.32.0.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 13 | 167,725 |
| implement | 67 | 2,447,044 |
| review | 6 | 18,369 |
| **Total** | **86** | **2,633,138** |

<!-- wave:context-efficiency-state {"generation":95,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":67,"content_source_credit":2572861,"derived_artifact_credit":0,"direct_net":2447044,"estimated_tokens_saved":2447044,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2606,"response_debit":126027,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2816},"plan":{"calls":13,"content_source_credit":180935,"derived_artifact_credit":1951,"direct_net":167725,"estimated_tokens_saved":167725,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1725,"response_debit":17704,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":6,"content_source_credit":26887,"derived_artifact_credit":1023,"direct_net":18369,"estimated_tokens_saved":18369,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1855,"response_debit":10740,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":86,"content_source_credit":2780683,"derived_artifact_credit":2974,"direct_net":2633138,"estimated_tokens_saved":2633138,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6186,"response_debit":154471,"source_credit_count":92,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10138},"wave_id":"20wq9 release-rejection-test-repair"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 13 | 5,001,484 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":5001484,"surfaced_events":15} -->
<!-- wave:exploration-avoided end -->
