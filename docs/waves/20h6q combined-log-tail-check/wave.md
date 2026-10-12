# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-10-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `20h6q combined-log-tail-check`
Title: Combined Log Tail Check

## Objective

Make the large two-pipe log regression deterministic while preserving the existing combined bounded-log retention contract. Follow up the release qualification exception without changing production logging or uv.

## Changes

Change ID: `20gz6-bug deterministic-combined-log-tail-check`
Change Status: `planned`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (after readiness)
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: none

## Wave Summary

Planned test-only follow-up. Implementation and reviews are deferred; no source change is part of the current release.

## Watchpoints

- Preserve the 1 MiB cap and 64 KiB combined suffix; do not introduce per-stream file retention.
- Use bounded synchronization for asserted marker ordering and preserve real deadline controls.
- Operator approved the 1.29.0 release with this follow-up and timing analysis deferred.
- No performance conclusions while other reviews run on the host; no permanent routine evidence folder.

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
| council-readiness | pending | no current executed approval | record approval evidence for council-readiness |
| council-delivery | pending | no current executed approval | record approval evidence for council-delivery |
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
| plan | 62 | 1,371,806 |
| **Total** | **62** | **1,371,806** |

<!-- wave:context-efficiency-state {"generation":7,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":62,"content_source_credit":1460130,"derived_artifact_credit":2292,"direct_net":1371806,"estimated_tokens_saved":1371806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2018,"response_debit":89705,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":62,"content_source_credit":1460130,"derived_artifact_credit":2292,"direct_net":1371806,"estimated_tokens_saved":1371806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2018,"response_debit":89705,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107},"wave_id":"20h6q combined-log-tail-check"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
