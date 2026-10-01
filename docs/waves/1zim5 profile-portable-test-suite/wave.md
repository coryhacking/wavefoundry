# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `1zim5 profile-portable-test-suite`
Title: Profile Portable Test Suite

## Objective

Make the framework test suite verify a distribution's own vocabulary, layout profile and tool declarations: profile-aware fixture builders, a default-profile-only marker for tests whose subject is the default, an on-demand second-profile run, and a suite that stays meaningful with declarations present.

## Changes

Change ID: `1zim1-debt profile-portable-test-fixtures`
Change Status: `planned`

Change ID: `1zim4-debt suite-under-distribution-declarations`
Change Status: `planned`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: none

## Wave Summary

Two changes: `1zim1-debt profile-portable-test-fixtures` (about 1,500 failing tests in 48 files under a second profile, census 2026-09-30) and `1zim4-debt suite-under-distribution-declarations`.

## Watchpoints

- Watchpoint: large mechanical migration; builders and runner first, then file groups in census order with one owner per file.
- Follow-up: `1zim4` uses `1zim1`'s runner mode; its parameter-mapped sample waits for `1zim0`.

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
| plan | 4 | 560 |
| **Total** | **4** | **560** |

<!-- wave:context-efficiency-state {"generation":4,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":4,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":560,"estimated_tokens_saved":560,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":65,"response_debit":482,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":4,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":560,"estimated_tokens_saved":560,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":65,"response_debit":482,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1107},"wave_id":"1zim5 profile-portable-test-suite"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
