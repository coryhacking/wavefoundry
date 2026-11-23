# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `242ys flush-projection-budget-median`
Title: Flush Projection Budget Median

## Objective

The lifecycle flush/projection timing budget stops failing when one or two samples stall on disk contention, while a sustained slowdown still fails it. The row judges its median against 50 ms; the two CPU-only estimator rows keep their p95 budgets.

## Changes

Change ID: `242yr-bug flush-projection-budget-disk-contention`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `242ys` (Flush Projection Budget Median) delivered one change: Assert the lifecycle flush/projection timing row on its median.

**Changes delivered:**

- **Assert the lifecycle flush/projection timing row on its median** (`242yr-bug flush-projection-budget-disk-contention`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Change only the flush/projection row; Assert the flush row's median against 50 ms nominal.

## Watchpoints

- Watchpoint: keep the `lifecycle flush/projection warm` label, the `timing_budget` routing and the 242yq census pin unchanged.
- Watchpoint: open `framework_edit_allowed` around the test edit and close it after.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 31 | 102,849 |
| implement | 39 | 1,244,455 |
| review | 5 | 0 |
| **Total** | **75** | **1,347,304** |

<!-- wave:context-efficiency-state {"generation":70,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":39,"content_source_credit":1279123,"derived_artifact_credit":2694,"direct_net":1244455,"estimated_tokens_saved":1244455,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1639,"response_debit":39861,"source_credit_count":59,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4138},"plan":{"calls":31,"content_source_credit":143029,"derived_artifact_credit":3422,"direct_net":102849,"estimated_tokens_saved":102849,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7151,"response_debit":42749,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":5,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-3679,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48,"response_debit":10409,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":75,"content_source_credit":1422152,"derived_artifact_credit":6116,"direct_net":1343625,"estimated_tokens_saved":1347304,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8838,"response_debit":93019,"source_credit_count":83,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17214},"wave_id":"242ys flush-projection-budget-median"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 878,782 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":878782,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
