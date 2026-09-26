# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z2m4 context-efficiency-gap-recovery`
Title: Context Efficiency Gap Recovery

## Objective

One lock timeout no longer blanks Context Efficiency for every later wave: busy writes are retried for up to 10 seconds, the gap records why it began, and an operator command clears it while keeping affected waves marked. Fixed before the 1.27.0 release.

## Changes

Change ID: `1z1vu-bug context-efficiency-gap-permanent-and-unexplained`
Change Status: `implemented`

## Participants

- Coordinator: operator session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-26

## Wave Summary

Wave `1z2m4` (Context Efficiency Gap Recovery) delivered one change: Retry, Explain and Clear the Context-Efficiency Accounting Gap. Notable adjustments during implementation: Retry, Explain and Clear the Context-Efficiency Accounting Gap: Delivery review (no blocking findings) repairs: a `.clearing` file left by a committed clear no longer marks healthy waves (N1); instrumentation exception text is dropped from the sentinel (N2); the clear reports `new_gap_recorded` (N3); docs say the marking and set-aside share one transaction (N5); flush non-transient test added (N6); the sentinel is linked from a temp file (N7). A mutant that restores the N1 defect fails `test_clear_ignores_a_set_aside_file_left_by_a_committed_clear`.

**Changes delivered:**

- **Retry, Explain and Clear the Context-Efficiency Accounting Gap** (`1z1vu-bug context-efficiency-gap-permanent-and-unexplained`) — 4 ACs completed. Key decisions: The clear action is a command-line entry on `context_efficiency.py`, not an MCP tool or `wf` subcommand; Clearing marks every unsealed wave `accounting_gap` rather than refusing while waves are open (readiness finding F4)
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 19 | 0 |
| implement | 1 | 0 |
| review | 22 | 97,374 |
| **Total** | **42** | **97,374** |

<!-- wave:context-efficiency-state {"generation":42,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-47,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1,"response_debit":46,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":19,"content_source_credit":19963,"derived_artifact_credit":1353,"direct_net":-2840,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3725,"response_debit":24240,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":22,"content_source_credit":133143,"derived_artifact_credit":3449,"direct_net":97374,"estimated_tokens_saved":97374,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5011,"response_debit":36523,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":42,"content_source_credit":153106,"derived_artifact_credit":4802,"direct_net":94487,"estimated_tokens_saved":97374,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8737,"response_debit":60809,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1z2m4 context-efficiency-gap-recovery"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
