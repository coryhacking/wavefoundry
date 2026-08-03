# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u7dq compact-wave-outcome-metrics`
Title: Compact Wave Outcome Metrics

## Objective

Expose a compact, read-only outcome bundle for each returned wave: existing
Context Efficiency totals, review-ledger totals, and memory-advisory totals.
The wave makes these signals comparable without adding a model field, a new
ledger, or any other tracking surface.

## Changes

Change ID: `1u6uk-enh wave-outcome-metrics`
Change Status: `implemented`

Change ID: `1u8jb-enh risk-tiered-delivery-review`
Change Status: `implemented`

Change ID: `1u8jc-enh transition-only-review-evidence`
Change Status: `implemented`

Change ID: `1u7uy-enh active-memory-budget-and-consolidation`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-02

## Wave Summary

Wave `1u7dq compact-wave-outcome-metrics` (Compact Wave Outcome Metrics) delivered 4 changes: Compact Wave Outcome Metrics, Risk-tiered delivery review, Transition-only review evidence, and Active-memory budget and consolidation. Notable adjustments during implementation: Transition-only review evidence: Scope narrowed during implementation: retain ordering records, simplify projection only.; Active-memory budget and consolidation: Added the active-50 budget and read-only same-file curation candidates to `memory_brief`.

**Changes delivered:**

- **Compact Wave Outcome Metrics** (`1u6uk-enh wave-outcome-metrics`) — 6 ACs completed. Key decisions: Reuse existing authorities in one read-only `wf_list_waves` bundle.
- **Risk-tiered delivery review** (`1u8jb-enh risk-tiered-delivery-review`) — 5 ACs completed. Key decisions: Use the existing `targeted` policy mode as the default and add only explicit high-risk triggers.
- **Transition-only review evidence** (`1u8jc-enh transition-only-review-evidence`) — 5 ACs completed. Key decisions: Keep one typed ledger and reduce its operator-facing projection to current state.
- **Active-memory budget and consolidation** (`1u7uy-enh active-memory-budget-and-consolidation`) — 5 ACs completed. Key decisions: Use a fixed 50-record active cap with explicit curation and file-target grouping.
## Watchpoints

- Watchpoint: do not add a telemetry schema, a `wave.md` projection, or a
  model/host field.
- Watchpoint: keep the response page-bounded and scalar-only; missing optional
  data must be represented as unavailable rather than inferred.

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
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 116 | 1,459,377 |
| implement | 48 | 667,433 |
| review | 227 | 1,211,791 |
| **Total** | **391** | **3,338,601** |

<!-- wave:context-efficiency-state {"generation":383,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":783153,"derived_artifact_credit":244,"direct_net":667433,"estimated_tokens_saved":667433,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4775,"response_debit":112620,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":116,"content_source_credit":1741595,"derived_artifact_credit":3699,"direct_net":1459377,"estimated_tokens_saved":1459377,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6774,"response_debit":290704,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11561},"review":{"calls":227,"content_source_credit":1470089,"derived_artifact_credit":2746,"direct_net":1211791,"estimated_tokens_saved":1211791,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20714,"response_debit":241676,"source_credit_count":166,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":391,"content_source_credit":3994837,"derived_artifact_credit":6689,"direct_net":3338601,"estimated_tokens_saved":3338601,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":32263,"response_debit":645000,"source_credit_count":327,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14338},"wave_id":"1u7dq compact-wave-outcome-metrics"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 21 | 0 | 9 | 11,512,620 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":11512620,"surfaced_events":21} -->
<!-- wave:exploration-avoided end -->
