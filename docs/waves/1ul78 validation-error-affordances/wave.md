# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ul78 validation-error-affordances`
Title: Validation Error Affordances

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1ul77-enh validation-errors-carry-their-allowed-values`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-06

## Wave Summary

Wave `1ul78` (Validation Error Affordances) delivered one change: Validation Errors Carry Their Allowed Values. Notable adjustments during implementation: Validation Errors Carry Their Allowed Values: Noted, out of scope: `TERMINAL_CHANGE_STATUSES` contains `done`, which is absent from the transition-table keys, so the terminal and transition vocabularies disagree independently of the `implemented` divergence; Validation Errors Carry Their Allowed Values: Noted at close, out of scope: the close gate uses a FOURTH vocabulary, a hardcoded blocklist rather than a constant, which is why `implemented` closes waves despite belonging to no status constant.

**Changes delivered:**

- **Validation Errors Carry Their Allowed Values** (`1ul77-enh validation-errors-carry-their-allowed-values`) — 7 ACs completed. Key decisions: Derive the printed set from the checked constant at runtime; Append to existing messages rather than rewrite them
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
| plan | 25 | 398,439 |
| implement | 23 | 465 |
| review | 11 | 56,380 |
| **Total** | **59** | **455,284** |

<!-- wave:context-efficiency-state {"generation":54,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":23,"content_source_credit":5164,"derived_artifact_credit":240,"direct_net":465,"estimated_tokens_saved":465,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1356,"response_debit":5676,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2093},"plan":{"calls":25,"content_source_credit":428155,"derived_artifact_credit":1289,"direct_net":398439,"estimated_tokens_saved":398439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7116,"response_debit":27254,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":11,"content_source_credit":73227,"derived_artifact_credit":406,"direct_net":56380,"estimated_tokens_saved":56380,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4642,"response_debit":13957,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":59,"content_source_credit":506546,"derived_artifact_credit":1935,"direct_net":455284,"estimated_tokens_saved":455284,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13114,"response_debit":46887,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6804},"wave_id":"1ul78 validation-error-affordances"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
