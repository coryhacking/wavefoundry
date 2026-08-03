# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ua8v model-download-recovery-guidance`
Title: Model Download Recovery Guidance

## Objective

When automatic model acquisition cannot complete, give operators a precise offline recovery path: the exact model asset, the existing discovery locations, and the rerun action. Keep the current automatic download and verified materialization behavior unchanged.

## Changes

Change ID: `1ua8u-enh model-download-recovery-guidance`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, architecture-reviewer

Completed At: 2026-08-03

## Wave Summary

Wave `1ua8v` (Model Download Recovery Guidance) delivered one change: Model Download Recovery Guidance.

**Changes delivered:**

- **Model Download Recovery Guidance** (`1ua8u-enh model-download-recovery-guidance`) — 3 ACs completed. Key decisions: Reuse standard distribution directories rather than introduce a special model location.
## Watchpoints

- Watchpoint: recovery wording must match the existing local bundle discovery locations and must not imply that the archive should be unpacked manually.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 16 records; 3 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare Council evidence — 2026-08-03:** red-team found no scope-expansion path after checking the existing model failure and local-bundle seams; docs-contract-reviewer found no contract conflict after checking the planned exact asset, locations, and no-replacement wording.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: recovery wording could drift from the exact discovery behavior or imply a new downloader or special cache location; strongest-alternative: add a downloader or dedicated model directory — rejected because the current verified local-bundle flow and standard discovery locations already provide the needed recovery path.)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 23 | 1,656 |
| implement | 10 | 3,329 |
| review | 75 | 1,840,235 |
| **Total** | **108** | **1,845,220** |

<!-- wave:context-efficiency-state {"generation":107,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":7658,"derived_artifact_credit":0,"direct_net":3329,"estimated_tokens_saved":3329,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":52,"response_debit":5708,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":23,"content_source_credit":16569,"derived_artifact_credit":1392,"direct_net":1656,"estimated_tokens_saved":1656,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3506,"response_debit":16164,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":75,"content_source_credit":1986944,"derived_artifact_credit":2272,"direct_net":1840235,"estimated_tokens_saved":1840235,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8799,"response_debit":141528,"source_credit_count":116,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":108,"content_source_credit":2011171,"derived_artifact_credit":3664,"direct_net":1845220,"estimated_tokens_saved":1845220,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12357,"response_debit":163400,"source_credit_count":136,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6142},"wave_id":"1ua8v model-download-recovery-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 4,002,475 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4002475,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
