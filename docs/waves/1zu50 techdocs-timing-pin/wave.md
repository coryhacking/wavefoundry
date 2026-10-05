# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zu50 techdocs-timing-pin`
Title: Techdocs Timing Pin

## Objective

Make the techdocs ancestor-walk test prove its property by counting regex matches instead of timing one call, so a busy machine can no longer fail the close-time receipt run.

## Changes

Change ID: `1zu4z-bug techdocs-ancestor-walk-timing-flake`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-04

## Wave Summary

Wave `1zu50` (Techdocs Timing Pin) delivered one change: Pin The Techdocs Ancestor-Walk Skip By Match Count Instead Of Wall Clock.

**Changes delivered:**

- **Pin The Techdocs Ancestor-Walk Skip By Match Count Instead Of Wall Clock** (`1zu4z-bug techdocs-ancestor-walk-timing-flake`) — 3 ACs completed. Key decisions: Count regex `match` calls instead of raising the cap
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`; the mutant check runs in a scratch copy.

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
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 16 | 802 |
| implement | 14 | 0 |
| review | 6 | 4,879 |
| **Total** | **36** | **5,681** |

<!-- wave:context-efficiency-state {"generation":36,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2359,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":464,"response_debit":2207,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":312},"plan":{"calls":16,"content_source_credit":13018,"derived_artifact_credit":2200,"direct_net":802,"estimated_tokens_saved":802,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2375,"response_debit":15850,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":6,"content_source_credit":11327,"derived_artifact_credit":508,"direct_net":4879,"estimated_tokens_saved":4879,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":742,"response_debit":8530,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":36,"content_source_credit":24345,"derived_artifact_credit":2708,"direct_net":3322,"estimated_tokens_saved":5681,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3581,"response_debit":26587,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6437},"wave_id":"1zu50 techdocs-timing-pin"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
