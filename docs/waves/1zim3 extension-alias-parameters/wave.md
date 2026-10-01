# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `1zim3 extension-alias-parameters`
Title: Extension Alias Parameters

## Objective

Let a distribution with a renamed vocabulary serve tools whose parameter names match its vocabulary, with renamed and pinned parameters on an alias, while every name-keyed control stays on the canonical tool, and let an override delegate to the core handler without copying internals.

## Changes

Change ID: `1zim0-feat extension-alias-parameter-mapping`
Change Status: `planned`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: none

## Wave Summary

One change: `1zim0-feat extension-alias-parameter-mapping`.

## Watchpoints

- Watchpoint: readiness should include a spike proving the translated argument model on `wf_add_change` and `wf_review_wave`.
- Follow-up: test-suite portability under a distribution's declarations is planned in `1zim1`.

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
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
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
| plan | 6 | 1,238 |
| **Total** | **6** | **1,238** |

<!-- wave:context-efficiency-state {"generation":6,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":6,"content_source_credit":0,"derived_artifact_credit":1147,"direct_net":1238,"estimated_tokens_saved":1238,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":127,"response_debit":889,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":6,"content_source_credit":0,"derived_artifact_credit":1147,"direct_net":1238,"estimated_tokens_saved":1238,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":127,"response_debit":889,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107},"wave_id":"1zim3 extension-alias-parameters"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
