# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-11-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `24buu memory-revalidation-upgrade-delivery`
Title: Memory Revalidation Upgrade Delivery

## Objective

Maintainers who upgrade a target repository to 1.52.0 learn how many of its memory records need revalidation, and its agents follow the new keep rule in Review memories and Close wave. Upgrade still never curates records. Track 5 of arc `244cm-arc memory-quality`.

## Changes

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: none

## Wave Summary

Deliver the 249ar keep rule and revalidation signals through upgrade: read-only revalidation counts in `memory_brief`, and seed 160 guidance that merges the keep rule into existing prompts and recommends Review memories on unresolved or churned targets.

## Watchpoints

- Implement only after wave `248o5` closes: it edits seed 160, `memory_handlers.py` and the tool-surface contract.
- Spec `24but-enh deliver-memory-revalidation-through-upgrade` is not yet admitted: the host's spec admission tool needs its allow rule updated after the `248o5` rename.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | pending | no current executed approval | record approval evidence for council-readiness |
| council-delivery | delivery | pending | no current executed approval | record approval evidence for council-delivery |
| operator-signoff | delivery | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 3 | 3,646 |
| **Total** | **3** | **3,646** |

<!-- wave:context-efficiency-state {"generation":3,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":3,"content_source_credit":3320,"derived_artifact_credit":0,"direct_net":3646,"estimated_tokens_saved":3646,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18,"response_debit":1457,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1801}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":3,"content_source_credit":3320,"derived_artifact_credit":0,"direct_net":3646,"estimated_tokens_saved":3646,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18,"response_debit":1457,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1801},"wave_id":"24buu memory-revalidation-upgrade-delivery"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
