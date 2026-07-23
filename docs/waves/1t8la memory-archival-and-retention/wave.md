# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1t8la memory-archival-and-retention`
Title: Memory Archival And Retention

## Objective

Move inactive agent-memory bodies into a version-controlled local archive while
keeping compact active pointers for deliberate historical discovery. Default
memory retrieval must become smaller and more trustworthy without losing the
evidence, provenance, or recovery guarantees of prior learning.

## Changes

Change ID: `1t8l9-enh memory-archival-and-retention-lifecycle`
Change Status: `planned`

## Wave Summary

This wave establishes the physical archive, explicit retention policy, and
restart-safe lifecycle for agent memory. Retrieval scoring changes are excluded
and remain owned by the companion adaptive-freshness plan.

## Watchpoints

- Archive bodies must be excluded from every normal docs, graph, and advisory
  path; status filtering alone is insufficient.
- Every move must be a state-derived, fenced rename with interruption recovery;
  do not use copy/delete or an in-memory migration map.
- Preserve source-event dispositions so backfill and close-time proposal never
  regenerate archived learning.

## Participants

- Product owner: operator — selected physical Git-visible archival with active
  pointers and authorized planning/readiness work.
- Council moderator: wave-council.
- Readiness seats: red-team, docs-contract-reviewer.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: moving records under an archive folder does not by itself remove their bodies from normal docs, graph, or advisory retrieval, so an apparent archive could still pollute the active corpus; strongest-alternative: status-only archival — rejected because it leaves the bodies where default indexing can reach them)
- Council evidence: the plan makes full-path exclusion, active pointers, fenced state-derived rename recovery, and upgrade/backfill coherence required acceptance criteria. Red-team required crash-window coverage and rejected status-only archival; docs-contract-reviewer found the archive-body/pointer distinction, retention protections, and explicit history contract consistent across requirements, scope, ACs, and decision log.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 2 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 34 | 108,096 |
| review | 12 | 331,535 |
| **Total** | **46** | **439,631** |

<!-- wave:context-efficiency-state {"generation":26,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":34,"content_source_credit":150005,"derived_artifact_credit":1056,"direct_net":108096,"estimated_tokens_saved":108096,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":795,"response_debit":45361,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":12,"content_source_credit":346950,"derived_artifact_credit":287,"direct_net":331535,"estimated_tokens_saved":331535,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1029,"response_debit":14673,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":46,"content_source_credit":496955,"derived_artifact_credit":1343,"direct_net":439631,"estimated_tokens_saved":439631,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1824,"response_debit":60034,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"wave_id":"1t8la memory-archival-and-retention"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
