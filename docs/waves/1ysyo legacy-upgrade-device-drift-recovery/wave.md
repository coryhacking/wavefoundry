# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-24
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

Completed At: 2026-09-23

## Wave Summary

Wave `1ysyo` (Legacy Upgrade Device Drift Recovery) delivered one change: Guide recovery from an older upgrade reader after device drift. Notable adjustments during implementation: Guide recovery from an older upgrade reader after device drift: Operator narrowed the follow-up to guidance because few users are affected. Removed all proposed package mode, staging, transaction-entry and runtime changes before readiness or source edits.; Guide recovery from an older upgrade reader after device drift: Readback: add diagnosis and reviewed operator-assisted repair guidance only (AC-1–3). Before: mismatch may prompt receipt edits; after: collect identity/source evidence, stop uncertain cases, obtain exact reviewed repair and scoped approval. Only seed 160, local upgrade prompt and changelog change.

**Changes delivered:**

- **Guide recovery from an older upgrade reader after device drift** (`1ysyn-bug legacy-upgrade-device-drift-recovery`) — 3 ACs completed. Key decisions: Ship diagnosis and reviewed operator-assisted repair guidance only
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
| plan | 34 | 178,879 |
| implement | 35 | 243,749 |
| review | 29 | 76,550 |
| **Total** | **98** | **499,178** |

<!-- wave:context-efficiency-state {"generation":77,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":264352,"derived_artifact_credit":0,"direct_net":243749,"estimated_tokens_saved":243749,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1086,"response_debit":21293,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1776},"plan":{"calls":34,"content_source_credit":231182,"derived_artifact_credit":1991,"direct_net":178879,"estimated_tokens_saved":178879,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2666,"response_debit":58139,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":29,"content_source_credit":119775,"derived_artifact_credit":1308,"direct_net":76550,"estimated_tokens_saved":76550,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6354,"response_debit":40495,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":615309,"derived_artifact_credit":3299,"direct_net":499178,"estimated_tokens_saved":499178,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10106,"response_debit":119927,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10603},"wave_id":"1ysyo legacy-upgrade-device-drift-recovery"} -->
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
