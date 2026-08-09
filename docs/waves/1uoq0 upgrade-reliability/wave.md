# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uoq0 upgrade-reliability`
Title: Upgrade Reliability

## Objective

Stop the upgrade preflight from blocking on state the framework itself produces or ships. A downstream 1.11.0 repository failed to upgrade three times, each time on a condition the framework created: an empty `wave_review` object, retired prose inside a file the pack delivers, and an unrecognized `Wave:` placeholder. When this closes, none of the three requires an operator to hand-repair state the tool already knows.

## Changes

Change ID: `1ulr2-bug upgrade-preflight-blocks-on-state-it-owns`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-07

## Wave Summary

Wave `1uoq0` (Upgrade Reliability) delivered one change: Upgrade Preflight Blocks On State It Owns.

**Changes delivered:**

- **Upgrade Preflight Blocks On State It Owns** (`1ulr2-bug upgrade-preflight-blocks-on-state-it-owns`) — 9 ACs completed. Key decisions: Group three field failures into one change; Exclude `.wavefoundry/` by prefix rather than adding two paths
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
| plan | 16 | 17,132 |
| implement | 6 | 380,446 |
| review | 8 | 39,217 |
| **Total** | **30** | **436,795** |

<!-- wave:context-efficiency-state {"generation":33,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":387916,"derived_artifact_credit":1457,"direct_net":380446,"estimated_tokens_saved":380446,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":127,"response_debit":10231,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":16,"content_source_credit":42776,"derived_artifact_credit":1013,"direct_net":17132,"estimated_tokens_saved":17132,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5979,"response_debit":24061,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3383},"review":{"calls":8,"content_source_credit":51030,"derived_artifact_credit":863,"direct_net":39217,"estimated_tokens_saved":39217,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2658,"response_debit":11364,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":30,"content_source_credit":481722,"derived_artifact_credit":3333,"direct_net":436795,"estimated_tokens_saved":436795,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8764,"response_debit":45656,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6160},"wave_id":"1uoq0 upgrade-reliability"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 4 | 1,762,424 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":1762424,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
