# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1tskc context-efficiency-projection-freshness`
Title: Context Efficiency Projection Freshness

## Objective

Keep the portable Context Efficiency checkpoint current during long implementation and review work
without changing the durable accounting model. Add verified turn-end projection where supported and
a cross-host 120-second unchanged-generation safety net while retaining every lifecycle hard barrier.

## Changes

Change ID: `1tsjh-enh context-efficiency-turn-end-projection`
Change Status: `planned`

## Wave Summary

This wave adds an accounting-neutral projection cadence: Claude's verified turn-end event is the
prompt path, an MCP-owned generation-stable quiet-period monitor covers unsupported or missed hook
paths, and lifecycle/reload/upgrade projection remains authoritative. It also reconciles the
configuration, platform, concurrency, failure, performance, and documentation contracts.

## Watchpoints

- The automatic projector must never meter itself or create a new pending generation.
- Turn-end handling is non-blocking and fail-safe; lock contention leaves durable work pending.
- The quiet clock resets on every generation change and defaults to 120 seconds, with a 90-second
  lower bound and configuration through 600 seconds.
- Do not invent native hook surfaces for hosts without a verified end-turn contract.
- Preserve the shared publication lock, atomic marker replacement, generation compare-and-set,
  project-authored prose, close sealing/compaction, and reload/upgrade refusal behavior.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 0 records; 0 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
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

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 20 | 416,853 |
| **Total** | **20** | **416,853** |

<!-- wave:context-efficiency-state {"generation":2,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":20,"content_source_credit":465946,"derived_artifact_credit":0,"direct_net":416853,"estimated_tokens_saved":416853,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":441,"response_debit":49960,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1308}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":20,"content_source_credit":465946,"derived_artifact_credit":0,"direct_net":416853,"estimated_tokens_saved":416853,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":441,"response_debit":49960,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1308},"wave_id":"1tskc context-efficiency-projection-freshness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
