# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23zmr focused-review-and-qualification`
Title: Focused Review And Qualification

## Objective

Builders and reviewers catch contract regressions early, repair equivalent reports together without losing their sources, and distinguish preserved behavior from demonstrated improvement. Release qualification retains its full coverage.

## Changes

Change ID: `23ze8-doc targeted-verification-guidance`
Change Status: `implemented`

## Participants

- Coordinator: Wave coordinator
- Write-owning roles: Technical writer
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `23zmr` (Focused Review And Qualification) delivered one change: Target verification at the reported failure.

Intent outcome: achieved for the three decisions in spec 23ze8. The targeted registry test passed intact, failed on the predicted omission of the installed Prepare prompt, and passed after restoration. The guidance groups observations with a common failure, fix and outcome while retaining separate observations, and classifies two equal passes as preservation. QA independently checks those decisions during delivery review. The scenarios establish how to act on the instructions. They do not measure time saved in other projects.

**Changes delivered:**

- **Target verification at the reported failure** (`23ze8-doc targeted-verification-guidance`) — AC-1, AC-2 and AC-3 completed. Key decisions: Extend the existing review guidance.

## Watchpoints

- Watchpoint: keep qualification coverage and existing typed review history intact.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| R1-23ze8-fast-check-control | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-21: Intent outcome: achieved for the three decisions in spec 23ze8. The targeted registry test passed intact, failed on the predicted omission of the installed Prepare prompt, and passed after restoration. The guidance groups observations with a common failure, fix and outcome while retaining separate observations, and classifies two equal passes as preservation. QA independently checks those decisions during delivery review. The scenarios establish how to act on the instructions. They do not measure time saved in other projects.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 24 | 22,461 |
| implement | 7 | 1,827 |
| review | 31 | 75,297 |
| **Total** | **62** | **99,585** |

<!-- wave:context-efficiency-state {"generation":56,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1827,"estimated_tokens_saved":1827,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":236,"response_debit":1327,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3390},"plan":{"calls":24,"content_source_credit":75072,"derived_artifact_credit":2518,"direct_net":22461,"estimated_tokens_saved":22461,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4427,"response_debit":56630,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":31,"content_source_credit":97508,"derived_artifact_credit":1281,"direct_net":75297,"estimated_tokens_saved":75297,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2521,"response_debit":31345,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10374}},"store_instance_id":"d7abf27ead434ad6953e0e7306733763","totals":{"calls":62,"content_source_credit":172580,"derived_artifact_credit":3799,"direct_net":99585,"estimated_tokens_saved":99585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7184,"response_debit":89302,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19692},"wave_id":"23zmr focused-review-and-qualification"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
