# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1w3br reconciliation-disposition-key-precision`
Title: Reconciliation Disposition Key Precision

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1w3bq-bug reconciliation-disposition-key-overbreadth`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-23

## Wave Summary

Wave `1w3br` (Reconciliation Disposition Key Precision) delivered one change: Make Reconciliation Dispositions Finding-Specific.

**Changes delivered:**

- **Make Reconciliation Dispositions Finding-Specific** (`1w3bq-bug reconciliation-disposition-key-overbreadth`) — 7 ACs completed. Key decisions: Select the exact `v2:<32-lowercase-hex>` content + heading-context fingerprint, conservative duplicate refusal, and diagnostic-only legacy compatibility.; Keep the store additive and operator-owned.
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-FENCE-CLOSE-CONTEXT-001 | do_now | no | completed | wave-council-delivery, code-reviewer |
| DOCS-DEL-STATE-CONTRACT-001 | do_now | no | completed | qa-reviewer, code-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| QA-READY-V2-ORACLE-001 | do_now | no | completed | qa-reviewer, code-reviewer, docs-contract-reviewer, release-reviewer, wave-council-readiness |
| RED-READY-LEGACY-RETARGET-001 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, docs-contract-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 52 | 65,867 |
| implement | 59 | 219,393 |
| review | 263 | 3,924,007 |
| **Total** | **374** | **4,209,267** |

<!-- wave:context-efficiency-state {"generation":379,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":59,"content_source_credit":311453,"derived_artifact_credit":0,"direct_net":219393,"estimated_tokens_saved":219393,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2180,"response_debit":92902,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3022},"plan":{"calls":52,"content_source_credit":238224,"derived_artifact_credit":381,"direct_net":65867,"estimated_tokens_saved":65867,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35330,"response_debit":140914,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":263,"content_source_credit":4759880,"derived_artifact_credit":1208,"direct_net":3924007,"estimated_tokens_saved":3924007,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48799,"response_debit":789628,"source_credit_count":149,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":374,"content_source_credit":5309557,"derived_artifact_credit":1589,"direct_net":4209267,"estimated_tokens_saved":4209267,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":86309,"response_debit":1023444,"source_credit_count":216,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7874},"wave_id":"1w3br reconciliation-disposition-key-precision"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 4 | 2,931,716 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":2931716,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
