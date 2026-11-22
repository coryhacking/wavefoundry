# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `241c3 writing-guide-sentence-structure`
Title: Writing Guide Sentence Structure

## Objective

Writers keep each sentence to one action or point, each checkable item to one result, noun phrases readable and status records in complete sentences, so readers of specs, changelogs, handoffs and review evidence recover meaning without reconstructing it. The change is guidance in the writing guide only; no linter, gate or sentence limit is added.

## Changes

Change ID: `240wz-doc writing-guide-sentence-structure`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer, docs-contract-reviewer, code-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `241c3` (Writing Guide Sentence Structure) delivered one change: Add Sentence-Structure Guidance to the Writing Guide.

Intent outcome: The delivered guide and its three pointers establish the writing guidance described in change 240wz and the wave Objective. The live presence check found all 22 expected strings. Removing the split instruction produced one named failure. After at least three post-release waves contribute 700 spec sentences, the operator can check whether the share over 25 words falls from 18.0% to 14.0% or lower. A lower share still leaves bundled short tasks and reader comprehension unmeasured.

**Changes delivered:**

- **Add Sentence-Structure Guidance to the Writing Guide** (`240wz-doc writing-guide-sentence-structure`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Add the accepted sentences to the existing paragraphs they qualify, and keep the report's ADOPT 1 wording; Coordinator decision 2026-11-21: use a reviewer presence check as the known-bad oracle, not a repository test that pins prose, consistent with the operator's no-linter rule.

## Watchpoints

- Watchpoint: the writing guide lives under `.wavefoundry/framework/docs/`; open `framework_edit_allowed` around the edit and close it after.
- Watchpoint: the operator rejected any prose linter, sensor or gate; reviewers must not accept one as a repair.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1-240wz-secondary-small-samples | do_now | no | completed | code-reviewer |
| D2-240wz-spec-corpus-includes-supporting-docs | do_now | no | completed | code-reviewer |
| R1-240wz-item-exception-undecidable | do_now | no | completed | — |
| R1-240wz-list-rule-unscoped | do_now | no | completed | — |
| R1-240wz-measure-no-decision-rule | do_now | no | completed | — |
| R1-240wz-word-count-hard-limit | do_now | no | completed | — |
| R2-240wz-gate-order-blocks-pointer-edits | do_now | no | completed | — |

*Machine review state — 7 findings; current: do_now 7, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

The wave retains the [original writing assessment](source-review.md) because it includes the sampled judgments that led to this change. The [measurement instructions](evidence/README.md) and accompanying scripts let a later maintainer repeat the study. The original guide is also available in commit `23a98b65`. Its SHA-256 is `b6fe46fde7e415e757b8c0c2aa38454f48fb303a84c75030378348da90311a9d`. The review scratch checkout, generated tables and temporary logs can expire at close.

Retrospective: Replaying the edit hook established when to close each edit gate. Replaying the measurement on a sparse corpus exposed a failure the original dataset hid. The active memory `240wz-rerun-writing-guide` records the post-release decision. The team declined a second memory for gate ordering because the canonical edit hook and the repaired task sequence already document that behavior.

2026-11-21: Intent outcome: The delivered guide and its three pointers establish the writing guidance described in change 240wz and the wave Objective. The live presence check found all 22 expected strings. Removing the split instruction produced one named failure. After at least three post-release waves contribute 700 spec sentences, the operator can check whether the share over 25 words falls from 18.0% to 14.0% or lower. A lower share still leaves bundled short tasks and reader comprehension unmeasured.

The operator requested completion and closure. The second bounded repair moves the framework-gate closing task below the two local prompt edits. The seed gate closes immediately after the seed edit. The code reviewer will repeat the gate-order probe, and the council and required reviewers will assess the effect of this change on their readiness decisions.

2026-11-21: The council approved readiness on receipt `review-policy-d4a3c0d70e4612287378`. The standard red-team primer challenged the link between sentence length and reader comprehension. QA and the reality checker examined the measurement. The rotating docs-contract seat checked the guide and its three pointers. The code reviewer verified the edit sequence. Architecture and security had no changed boundary in this repair. All three required reviewers approved the amended plan, and all five findings are terminal. The chair found that the plan establishes the wave's intended guidance and a way to observe subsequent writing. Its post-release measure can show a change in sentence length. Reader comprehension remains unmeasured.

2026-11-21: The delivery council approved the guide, its three pointers and the measurement instructions. The lightweight red-team primer asked whether shorter sentences could still contain independently verifiable tasks. Architecture checked the writing steps and the seed used by target repositories. Security checked the authority and local data use of the hand-run helpers. QA checked all nine acceptance criteria. The rotating docs-contract reviewer reconstructed the exact guide edits and detected each of 22 single deletions. That reviewer proposed sampling whether readers can identify the actor, outcome and common proof in a task. Such a sample would take reviewer time and would apply only to the passages read.

The reality checker challenged the primary measure because it included supporting prose. The code and QA reviewers confirmed the defect. After repair, 55 additional sentences in the wave record and 99 in a supporting report left the spec row unchanged. Independent threshold controls produced a wait at 699 sentences and a keep decision at 700 sentences with 13.7% over 25 words. The code reviewer also found that small samples crashed the secondary helpers. Replaying the original helpers reproduced the failures, and the repaired helpers distinguished an absent observation from a measured zero. All seven finding heads are terminal. The chair recorded `intent_fit=establishes` for delivery of the guidance and the means to measure subsequent writing. The canonical suite recorded 13,194 tests across 253 files, including all five writing-guide delivery tests, with 12 skips.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 87 | 318,177 |
| implement | 70 | 0 |
| review | 222 | 648,427 |
| **Total** | **379** | **966,604** |

<!-- wave:context-efficiency-state {"generation":330,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":70,"content_source_credit":220,"derived_artifact_credit":4,"direct_net":-13411,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2797,"response_debit":15560,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4722},"plan":{"calls":87,"content_source_credit":659831,"derived_artifact_credit":2842,"direct_net":318177,"estimated_tokens_saved":318177,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28296,"response_debit":322128,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":222,"content_source_credit":1332041,"derived_artifact_credit":1581,"direct_net":648427,"estimated_tokens_saved":648427,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24847,"response_debit":667064,"source_credit_count":141,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6716}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":379,"content_source_credit":1992092,"derived_artifact_credit":4427,"direct_net":953193,"estimated_tokens_saved":966604,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55940,"response_debit":1004752,"source_credit_count":210,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17366},"wave_id":"241c3 writing-guide-sentence-structure"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 2,636,098 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":2636098,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
