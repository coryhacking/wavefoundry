# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ulnw upgrade-doc-fact-reconciliation`
Title: Upgrade Doc Fact Reconciliation

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1ulnv-bug upgrade-doc-fact-reconciliation`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-06

## Wave Summary

Wave `1ulnw` (Upgrade Doc Fact Reconciliation) delivered one change: Upgrade all lint-bound documentation facts during install.

**Changes delivered:**

- **Upgrade all lint-bound documentation facts during install** (`1ulnv-bug upgrade-doc-fact-reconciliation`) — 5 ACs completed. Key decisions: Generalize the existing conservative graph-builder seam rather than add marker regions.
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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 14 | 0 |
| implement | 6 | 8,170 |
| review | 18 | 338 |
| **Total** | **38** | **8,508** |

<!-- wave:context-efficiency-state {"generation":38,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":12369,"derived_artifact_credit":737,"direct_net":8170,"estimated_tokens_saved":8170,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":932,"response_debit":5435,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":14,"content_source_credit":7637,"derived_artifact_credit":740,"direct_net":-523,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1712,"response_debit":12602,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5414},"review":{"calls":18,"content_source_credit":26197,"derived_artifact_credit":514,"direct_net":338,"estimated_tokens_saved":338,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1510,"response_debit":26209,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":38,"content_source_credit":46203,"derived_artifact_credit":1991,"direct_net":7985,"estimated_tokens_saved":8508,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4154,"response_debit":44246,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8191},"wave_id":"1ulnw upgrade-doc-fact-reconciliation"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
