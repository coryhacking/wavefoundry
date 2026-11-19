# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23tct first-feature-workflow`
Title: First Feature Workflow

## Objective

A team can define its first useful outcome, pause before technical planning, and resume the same spec through delivery review. Readers and agents can identify the requested step in ordinary language and distinguish delivery evidence from later field observations.

## Changes

Change ID: `23rgx-enh identify-first-useful-outcome`
Change Status: `implemented`

Change ID: `23s4d-enh guide-first-feature-and-route-planning-requests`
Change Status: `implemented`

## Participants

- Coordinator: Codex coordinator
- Write-owning roles: Documentation implementer
- Requested review lanes: none
- Required review lanes: docs-contract-reviewer

Completed At: 2026-11-19

## Wave Summary

Wave `23tct` (First Feature Workflow) delivered two changes: Identify the first useful outcome in Plan spec and Guide a first feature from definition through delivery review.

Intent outcome: The export planning trial maps independent outcomes to ACs and reserves support trends for later observation. The reader recovered the health example handoffs. Calendar-request trials preserved the same draft across the planning pause, and customized catalog reconciliation preserved local names and instructions. These exercises support the intended behavior on the cases tested. Human onboarding and cross-host effectiveness remain unmeasured. The independent docs-contract reviewer confirmed this assessment, checked five old/current wording cases and inspected the exercise diffs. Final framework suite: 13,052 tests across 251 files, 12 skips, 859.215 seconds.

**Changes delivered:**

- **Identify the first useful outcome in Plan spec** (`23rgx-enh identify-first-useful-outcome`) — AC-1 and AC-2 completed. Key decisions: Extend the existing Product Intent instruction.
- **Guide a first feature from definition through delivery review** (`23s4d-enh guide-first-feature-and-route-planning-requests`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Use a worked conversation and a short context-sensitive routing instruction.

## Watchpoints

- Watchpoint: Operator endorsed both specs. One writer reconciles seeds and local prompts. Keep existing lifecycle authority and alternate workflows intact.

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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-19: Closure retrospective: the routing trial exposed the need to say when technical planning resumes. The command catalog and seed now carry that lesson; memory proposal found no additional candidate. Both changes are implemented, with no deferred criteria or outstanding findings.

2026-11-19: Intent outcome: The export planning trial maps independent outcomes to ACs and reserves support trends for later observation. The reader recovered the health example handoffs. Calendar-request trials preserved the same draft across the planning pause, and customized catalog reconciliation preserved local names and instructions. These exercises support the intended behavior on the cases tested. Human onboarding and cross-host effectiveness remain unmeasured. The independent docs-contract reviewer confirmed this assessment, checked five old/current wording cases and inspected the exercise diffs. Final framework suite: 13,052 tests across 251 files, 12 skips, 859.215 seconds.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 39 | 125,768 |
| implement | 48 | 70,853 |
| review | 11 | 4,195 |
| **Total** | **98** | **200,816** |

<!-- wave:context-efficiency-state {"generation":71,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":83288,"derived_artifact_credit":0,"direct_net":70853,"estimated_tokens_saved":70853,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1513,"response_debit":14740,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3818},"plan":{"calls":39,"content_source_credit":165220,"derived_artifact_credit":3159,"direct_net":125768,"estimated_tokens_saved":125768,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2787,"response_debit":45752,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":11,"content_source_credit":15086,"derived_artifact_credit":569,"direct_net":4195,"estimated_tokens_saved":4195,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1802,"response_debit":16220,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":263594,"derived_artifact_credit":3728,"direct_net":200816,"estimated_tokens_saved":200816,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6102,"response_debit":76712,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16308},"wave_id":"23tct first-feature-workflow"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
