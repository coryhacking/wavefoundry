# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-09-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ysyo legacy-upgrade-device-drift-recovery`
Title: Legacy Upgrade Device Drift Recovery

## Objective

Give the small set of affected older installations accurate device-drift diagnosis and a safe operator-assisted upgrade repair path. Preserve recovery records; add guidance only, no automated recovery mode.

## Changes

Change ID: `1ysyn-bug legacy-upgrade-device-drift-recovery`
Change Status: `implemented`

## Participants

- Coordinator: current session
- Write-owning roles: implementer (coordinator)
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

## Wave Summary

Guidance-only follow-up for an older reader rejecting a receipt before the incoming fix can run. Seed 160 and its local carrier gain diagnosis, preservation and reviewed repair instructions.

## Watchpoints

- No automated recovery, runtime patch, index rebuild or recovery-record edit.
- Watchpoint: a mismatch code alone is not a diagnosis.
- Coordinator retains writing ownership; independent reviewers use fresh contexts. Current available model is retained for bounded documentation work; runtime model/effort identity is not independently observed.

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
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 34 | 178,879 |
| implement | 35 | 243,749 |
| review | 26 | 69,003 |
| **Total** | **95** | **491,631** |

<!-- wave:context-efficiency-state {"generation":74,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":264352,"derived_artifact_credit":0,"direct_net":243749,"estimated_tokens_saved":243749,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1086,"response_debit":21293,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1776},"plan":{"calls":34,"content_source_credit":231182,"derived_artifact_credit":1991,"direct_net":178879,"estimated_tokens_saved":178879,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2666,"response_debit":58139,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":26,"content_source_credit":111035,"derived_artifact_credit":1081,"direct_net":69003,"estimated_tokens_saved":69003,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6039,"response_debit":37074,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":95,"content_source_credit":606569,"derived_artifact_credit":3072,"direct_net":491631,"estimated_tokens_saved":491631,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9791,"response_debit":116506,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8287},"wave_id":"1ysyo legacy-upgrade-device-drift-recovery"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 1,246,157 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":1246157,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
