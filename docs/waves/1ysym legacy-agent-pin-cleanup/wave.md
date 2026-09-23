# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ysym legacy-agent-pin-cleanup`
Title: Legacy Agent Pin Cleanup

## Objective

Make removal of verified inherited model/effort defaults the preferred upgrade cleanup while preserving deliberate operator pins and unknown-provenance values.

## Changes

Change ID: `1ysyl-enh prefer-legacy-agent-pin-cleanup`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-22

## Wave Summary

Wave `1ysym` (Legacy Agent Pin Cleanup) delivered one change: Prefer Legacy Agent Pin Cleanup During Upgrade.

**Changes delivered:**

- **Prefer Legacy Agent Pin Cleanup During Upgrade** (`1ysyl-enh prefer-legacy-agent-pin-cleanup`) — 2 ACs completed. Key decisions: Prefer guided removal of verified inherited defaults
## Watchpoints

- Watchpoint: no package rebuild, version change, pin removal in external repositories, or renderer mutation. Preserve existing package metadata edits.

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
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 27 | 50,535 |
| implement | 18 | 81,956 |
| review | 53 | 136,484 |
| **Total** | **98** | **268,975** |

<!-- wave:context-efficiency-state {"generation":90,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":18,"content_source_credit":89999,"derived_artifact_credit":26,"direct_net":81956,"estimated_tokens_saved":81956,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":611,"response_debit":9060,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1602},"plan":{"calls":27,"content_source_credit":69237,"derived_artifact_credit":1898,"direct_net":50535,"estimated_tokens_saved":50535,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2081,"response_debit":25030,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":53,"content_source_credit":206575,"derived_artifact_credit":1879,"direct_net":136484,"estimated_tokens_saved":136484,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6008,"response_debit":68278,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":365811,"derived_artifact_credit":3803,"direct_net":268975,"estimated_tokens_saved":268975,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8700,"response_debit":102368,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10429},"wave_id":"1ysym legacy-agent-pin-cleanup"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 5,321,055 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":5321055,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
