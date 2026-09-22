# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yq6a memory-summary-spacing`
Title: Memory Summary Spacing

## Objective

Ensure future memory metadata updates leave exactly one blank line before Summary, without accumulating separators or rewriting historical records.

## Changes

Change ID: `1yq69-bug memory-summary-spacing`
Change Status: `complete`

## Participants

- Requested review lanes: code-reviewer, qa-reviewer
- Work allocation: coordinator implements two files; independent readiness and delivery contexts review; no model override requested.

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-22

## Wave Summary

Wave `1yq6a` (Memory Summary Spacing) delivered one change: Memory Summary Spacing.

**Changes delivered:**

- **Memory Summary Spacing** (`1yq69-bug memory-summary-spacing`) — 3 ACs completed. Key decisions: Normalize the local boundary inside the existing helper on both insert and replace
## Watchpoints

- Watchpoint: historical memory records are untouched; no migration, retrieval benchmark or rebuild.
- Keep unittest.main at the end of the existing test module so added tests execute.

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
| plan | 27 | 437,691 |
| implement | 38 | 43,890 |
| review | 49 | 443,477 |
| **Total** | **114** | **925,058** |

<!-- wave:context-efficiency-state {"generation":98,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":38,"content_source_credit":102734,"derived_artifact_credit":27,"direct_net":43890,"estimated_tokens_saved":43890,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1139,"response_debit":59316,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1584},"plan":{"calls":27,"content_source_credit":476019,"derived_artifact_credit":1895,"direct_net":437691,"estimated_tokens_saved":437691,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1594,"response_debit":42438,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":49,"content_source_credit":514063,"derived_artifact_credit":671,"direct_net":443477,"estimated_tokens_saved":443477,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2175,"response_debit":71398,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":114,"content_source_credit":1092816,"derived_artifact_credit":2593,"direct_net":925058,"estimated_tokens_saved":925058,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4908,"response_debit":173152,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7709},"wave_id":"1yq6a memory-summary-spacing"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 8 | 6,673,233 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":6673233,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
