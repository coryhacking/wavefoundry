# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2423b correct-dashboard-recent-changes`
Title: Correct Dashboard Recent Changes

## Objective

Operators see each recent spec once with its latest genuine progress update and can open the source document.

## Changes

Change ID: `2423a-bug dashboard-recent-changes-unique-specs`
Change Status: `implemented`

## Participants

- Coordinator: dashboard coordinator
- Write-owning roles: dashboard implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `2423b` (Correct Dashboard Recent Changes) delivered one change: Show each recently updated spec once.

Intent outcome: achieved for 2423a and the wave Objective. QA replayed both documents in the screenshot and exercised clicks and keyboard activation on two specs with the same ID and different paths. The live dashboard returned ten distinct paths in date order and served the first card's source document byte for byte. Review caught escaped pipes hiding the latest updates in five historical specs and literal backticks hiding other entries. After repair, an independent comparison across 1,278 local wave and plan documents retained all 5,984 previously recognized progress rows and recovered 35 more. The dashboard checks ran on this checkout.

**Changes delivered:**

- **Show each recently updated spec once** (`2423a-bug dashboard-recent-changes-unique-specs`) — AC-1, AC-2 and AC-3 completed. Key decisions: Preserve the event feed and add a distinct-spec summary.

## Watchpoints

- Watchpoint: keep legitimate progress events available while the dashboard summarizes distinct documents.


## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D-2423a-escaped-pipe | do_now | no | completed | code-reviewer |
| D-2423a-literal-backticks | do_now | no | completed | code-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: approved by operator instruction on 2026-11-22.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-22: The Progress Log fixtures now cover escaped pipes and literal backticks, and the delivery review records the comparison against historical documents. Those tests and the typed repair history preserve the lesson. The close memory preview proposed no additional record.

2026-11-21: Intent outcome: achieved for 2423a and the wave Objective. QA replayed both documents in the screenshot and exercised clicks and keyboard activation on two specs with the same ID and different paths. The live dashboard returned ten distinct paths in date order and served the first card's source document byte for byte. Review caught escaped pipes hiding the latest updates in five historical specs and literal backticks hiding other entries. After repair, an independent comparison across 1,278 local wave and plan documents retained all 5,984 previously recognized progress rows and recovered 35 more. The dashboard checks ran on this checkout.

2026-11-21: Prepare selected code review and QA for this dashboard bug. The lightweight adversarial primer replayed the screenshot against spec 1x8e1. Code and QA separately exercised a valid date in an evidence table and one busy spec crowding out another. The council approved AC-1 through AC-3 for the admitted spec and wave Objective. The final live click remains a delivery check.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 31 | 110,214 |
| implement | 15 | 1,297 |
| review | 61 | 172,573 |
| **Total** | **107** | **284,084** |

<!-- wave:context-efficiency-state {"generation":96,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1297,"estimated_tokens_saved":1297,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":255,"response_debit":1776,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3328},"plan":{"calls":31,"content_source_credit":141709,"derived_artifact_credit":2028,"direct_net":110214,"estimated_tokens_saved":110214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3216,"response_debit":36235,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":61,"content_source_credit":255803,"derived_artifact_credit":2132,"direct_net":172573,"estimated_tokens_saved":172573,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11529,"response_debit":80549,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6716}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":107,"content_source_credit":397512,"derived_artifact_credit":4160,"direct_net":284084,"estimated_tokens_saved":284084,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15000,"response_debit":118560,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15972},"wave_id":"2423b correct-dashboard-recent-changes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 5 | 1,198,972 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":1198972,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
