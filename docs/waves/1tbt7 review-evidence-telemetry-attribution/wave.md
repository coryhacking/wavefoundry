# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-23
review-evidence-source: events.jsonl

wave-id: `1tbt7 review-evidence-telemetry-attribution`
Title: Review Evidence Telemetry Attribution

## Objective

Make `wf_review_evidence` context-efficiency accounting follow its explicit,
resolved target wave without changing ambient process focus, while preserving
stage semantics, replay behavior, and sealed-wave protection.

## Changes

Change ID: `1tbt6-bug review-evidence-explicit-wave-telemetry-attribution`
Change Status: `implemented`

Completed At: 2026-07-23

## Wave Summary

Wave `1tbt7` (Review Evidence Telemetry Attribution) delivered one change: Attribute review-evidence telemetry to its explicit wave.

**Changes delivered:**

- **Attribute review-evidence telemetry to its explicit wave** (`1tbt6-bug review-evidence-explicit-wave-telemetry-attribution`) — 7 ACs completed. Key decisions: Use a per-call override; do not call `set_focus`.; Register only `wf_review_evidence`.
## Watchpoints

- **Watchpoint:** Do not implement the fix by switching and restoring global
  process focus; the override must be per call.
- **Watchpoint:** Reuse canonical target-stage derivation and retain sealed-wave
  demotion to general.
- **Watchpoint:** Do not generalize from a parameter named `wave_id`; only the
  proven `wf_review_evidence` target is in scope.
- **Watchpoint:** Targeted calls must reuse an existing durable target
  wave-stage phase so phase-scoped source-credit deduplication does not split
  across bare and numbered phase keys.

## Prepare Review Evidence

- **red-team — no blocking finding:** the strongest failure mode is allowing an
  explicit override to mutate global focus or write into sealed history. The
  plan forbids focus mutation and requires the existing sealed-wave demotion
  regression.
- **code-reviewer — no blocking finding:** the smallest safe seam is the
  existing generic cost wrapper plus an optional per-call focus passed through
  the retrieval recorder. Source/artifact extractors and event identities stay
  unchanged.
- **docs-contract-reviewer — no blocking finding:** the reference update should
  state explicit-target precedence for `wf_review_evidence`, retain sealed-wave
  demotion, and avoid implying that every tool parameter named `wave_id`
  overrides attribution.

## Review Checkpoints

- **Pre-implementation review — passed:** the plan was checked against
  `_wrap_first_party_tool_costs`, `ProcessTelemetry.record_tool_cost`,
  `record_retrieval`, `_commit_event`, canonical stage derivation, and the
  sealed-compaction tests. The change is bounded and testable.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-23: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: prevent explicit attribution from mutating ambient focus or reopening sealed history; strongest-alternative: sequence all work so the target wave remains focused — rejected because concurrent and multi-wave work makes ordering an unreliable accounting contract)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| paused-review-evidence-target-stage-undocumented | do_now | no | completed | wave-council-delivery |
| targeted-review-evidence-parallel-phase-key | do_now | no | completed | wave-council-delivery |

*Machine review evidence — 24 records; 8 runs; 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. The observed `1tamx` and `1tbt5` telemetry is
  evidence only and will not be rewritten by this wave.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 45 | 1,051,080 |
| implement | 41 | 576,423 |
| review | 94 | 1,624,808 |
| **Total** | **180** | **3,252,311** |

<!-- wave:context-efficiency-state {"generation":145,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":740509,"derived_artifact_credit":0,"direct_net":576423,"estimated_tokens_saved":576423,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1130,"response_debit":164529,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":45,"content_source_credit":1142820,"derived_artifact_credit":844,"direct_net":1051080,"estimated_tokens_saved":1051080,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1569,"response_debit":94206,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":94,"content_source_credit":1827827,"derived_artifact_credit":990,"direct_net":1624808,"estimated_tokens_saved":1624808,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13377,"response_debit":191844,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":180,"content_source_credit":3711156,"derived_artifact_credit":1834,"direct_net":3252311,"estimated_tokens_saved":3252311,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16076,"response_debit":450579,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5976},"wave_id":"1tbt7 review-evidence-telemetry-attribution"} -->
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
