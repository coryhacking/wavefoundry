# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ua8t memory-checkpoint-reporting`
Title: Memory Checkpoint Reporting

## Objective

Make a normal historical-memory checkpoint observable as an action-required pause rather than an index failure, including on the installing upgrade that still runs a prior parent runner. Preserve the existing safety and recovery contracts for genuine publication failures.

## Changes

Change ID: `1u9lf-bug memory-checkpoint-reported-as-upgrade-failure`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-03

## Wave Summary

Wave `1ua8t` (Memory Checkpoint Reporting) delivered one change: Report historical-memory checkpoint as action required, not upgrade failure.

**Changes delivered:**

- **Report historical-memory checkpoint as action required, not upgrade failure** (`1u9lf-bug memory-checkpoint-reported-as-upgrade-failure`) — 6 ACs completed. Key decisions: Treat the report as a bug, not a documentation-only nit.; Keep this as a separate small wave.

**Release follow-up:** `wavefoundry-1.15.0.pgl2.zip` predates the final `runner_stale: null` clarification. Rebuild and re-verify a package before publication; no implemented behavior is deferred.
## Watchpoints

- The incoming extension is the only new code that executes inside the installing old parent; its bridge must remain one-shot and fail closed.
- Dashboard is stopped before runtime-lock cutover; the newly installed dashboard must still preserve an action-required dead-PID lock after reload.
- Do not conflate observed non-memory index-publication refusal with thrown receipt-owned publication failure.
- Follow-up: re-run independent readiness review after the legacy-parent fixture design is recorded, before any framework edit gate opens.

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
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
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
| plan | 25 | 3,655 |
| implement | 138 | 3,032,185 |
| review | 65 | 2,142,043 |
| **Total** | **228** | **5,177,883** |

<!-- wave:context-efficiency-state {"generation":178,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":138,"content_source_credit":3385533,"derived_artifact_credit":0,"direct_net":3032185,"estimated_tokens_saved":3032185,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4902,"response_debit":349877,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":25,"content_source_credit":18935,"derived_artifact_credit":1400,"direct_net":3655,"estimated_tokens_saved":3655,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2916,"response_debit":17129,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":65,"content_source_credit":2274156,"derived_artifact_credit":1283,"direct_net":2142043,"estimated_tokens_saved":2142043,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4785,"response_debit":128611,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":228,"content_source_credit":5678624,"derived_artifact_credit":2683,"direct_net":5177883,"estimated_tokens_saved":5177883,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12603,"response_debit":495617,"source_credit_count":129,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4796},"wave_id":"1ua8t memory-checkpoint-reporting"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 5 | 4,945,517 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":4945517,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
