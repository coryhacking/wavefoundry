# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `244fi memory-review-active-audit`
Title: Memory Review Active Audit

## Objective

Review memories audits a bounded batch of active records each run against the current tree and retires those whose knowledge is now encoded in code, tests or seeds, so the active corpus can shrink toward its budget. Each run reviews the least recently reviewed records first, and a kept record is re-stamped so it moves to the back of the queue. Records are never retired on age alone, and protected kinds keep their eligibility confirmation.

## Changes

Change ID: `244fh-enh memory-review-active-record-audit`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `244fi` (Memory Review Active Audit) delivered one change: Memory review audits a bounded batch of active records.

**Changes delivered:**

- **Memory review audits a bounded batch of active records** (`244fh-enh memory-review-active-record-audit`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Fix the gap in the framework, then run the review here; Add one ordering option to queryless `memory_search` and audit a bounded batch.

## Watchpoints

- Watchpoint: open `framework_edit_allowed` and `seed_edit_allowed` around the edits and close them after.
- Watchpoint: do not mutate this repository's memory records during the wave; the operator will run the improved review after close.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 244fi-cr-fragile-order | do_now | no | completed | — |
| 244fi-cr-skip-vs-cap | do_now | no | completed | — |
| 244fi-cr-sort-before-cap-unpinned | do_now | no | completed | — |
| 244fi-docs-changelog-updated-regex-scope | do_now | no | completed | — |
| 244fi-qa-fragile-pass-ordering | do_now | no | completed | — |
| 244fi-qa-skip-window-stall | do_now | no | completed | — |
| DOCS-RDY-1 | do_now | no | completed | — |

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

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 78 | 1,034,184 |
| implement | 54 | 2,186,921 |
| review | 45 | 318,063 |
| **Total** | **177** | **3,539,168** |

<!-- wave:context-efficiency-state {"generation":161,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":54,"content_source_credit":2210758,"derived_artifact_credit":1347,"direct_net":2186921,"estimated_tokens_saved":2186921,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1894,"response_debit":28424,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5134},"plan":{"calls":78,"content_source_credit":1266267,"derived_artifact_credit":2314,"direct_net":1034184,"estimated_tokens_saved":1034184,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36560,"response_debit":208632,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10795},"review":{"calls":45,"content_source_credit":451373,"derived_artifact_credit":1436,"direct_net":318063,"estimated_tokens_saved":318063,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18285,"response_debit":123239,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":177,"content_source_credit":3928398,"derived_artifact_credit":5097,"direct_net":3539168,"estimated_tokens_saved":3539168,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56739,"response_debit":360295,"source_credit_count":187,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":22707},"wave_id":"244fi memory-review-active-audit"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
