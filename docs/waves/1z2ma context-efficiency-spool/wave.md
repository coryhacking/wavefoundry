# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z2ma context-efficiency-spool`
Title: Context Efficiency Spool

## Objective

A failed context-efficiency write is kept in a spool file and replayed later instead of opening the store-wide accounting gap, so transient failures delay the numbers without blanking them. A closed wave still never publishes an undercount as healthy. Before the 1.27.0 release.

## Changes

Change ID: `1z2m9-enh context-efficiency-failed-write-spool`
Change Status: `review`

## Participants

- Coordinator: operator session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-26

## Wave Summary

Wave `1z2ma` (Context Efficiency Spool) delivered one change: Spool Failed Context-Efficiency Writes Instead of Opening a Gap.

**Changes delivered:**

- **Spool Failed Context-Efficiency Writes Instead of Opening a Gap** (`1z2m9-enh context-efficiency-failed-write-spool`) — 5 ACs completed. Key decisions: One file per event, replayed without a lock, status kept `healthy` (readiness findings B1 to B5); A late replay into a sealed wave follows the live general-bucket rule
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
| plan | 45 | 1,101,883 |
| implement | 24 | 580,032 |
| review | 9 | 32,665 |
| **Total** | **78** | **1,714,580** |

<!-- wave:context-efficiency-state {"generation":74,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":24,"content_source_credit":603790,"derived_artifact_credit":0,"direct_net":580032,"estimated_tokens_saved":580032,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":872,"response_debit":22886,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":45,"content_source_credit":1208091,"derived_artifact_credit":2462,"direct_net":1101883,"estimated_tokens_saved":1101883,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3017,"response_debit":112164,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":9,"content_source_credit":47634,"derived_artifact_credit":1467,"direct_net":32665,"estimated_tokens_saved":32665,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2137,"response_debit":16615,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":78,"content_source_credit":1859515,"derived_artifact_credit":3929,"direct_net":1714580,"estimated_tokens_saved":1714580,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6026,"response_debit":151665,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1z2ma context-efficiency-spool"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 3,683,031 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":3683031,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
