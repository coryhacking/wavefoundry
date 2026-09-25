# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yzj9 sensor-advisory-decisions`
Title: Sensor Advisory Decisions

## Objective

Record, on field data, that the AC-locality docs-lint sensor stays advisory, and give the sensor registry a standing-decision field so the warning text and release checklist stop describing a pending flip.

## Changes

Change ID: `1yzj8-maint ac-locality-sensor-stays-advisory`
Change Status: `planned`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

## Wave Summary

A `decided_wave` registry field with validation and warning-suffix wording, applied to both advisory sensors, plus guidance, release-checklist and changelog updates.

## Watchpoints

- Watchpoint: no sensor changes polarity, detection or scope.
- Watchpoint: undecided advisory sensors keep today's warning suffix and stay on the release checklist.

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
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
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
| plan | 15 | 657,643 |
| **Total** | **15** | **657,643** |

<!-- wave:context-efficiency-state {"generation":15,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":15,"content_source_credit":681621,"derived_artifact_credit":1292,"direct_net":657643,"estimated_tokens_saved":657643,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1788,"response_debit":26184,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2702}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":15,"content_source_credit":681621,"derived_artifact_credit":1292,"direct_net":657643,"estimated_tokens_saved":657643,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1788,"response_debit":26184,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2702},"wave_id":"1yzj9 sensor-advisory-decisions"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
