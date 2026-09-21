# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yljp explicit-precision-rebuild`
Title: Explicit Precision Rebuild

## Objective

Ordinary index updates refuse an unrequested embedding precision conversion before re-embedding or changing the published epoch. A transient provider failure must not turn a small update into a full corpus rebuild; explicit full rebuild remains available.

## Changes

Change ID: `1yljo-bug provider-fallback-rebuild-cascade`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (indexer and focused tests), technical-writer (update guidance)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-09-21

## Wave Summary

Wave `1yljp` (Explicit Precision Rebuild) delivered one change: Refuse implicit precision-changing index rebuilds. Notable adjustments during implementation: Refuse implicit precision-changing index rebuilds: Readback: an ordinary update against full-class vectors currently switches to INT8 and rebuilds when provider selection falls back to CPU; after this change it returns a clear failure without embedding or altering the published epoch. Explicit full conversion and compatible incremental updates remain available. AC-1–4 cover the boundary and its consumers. Scope is indexer/setup, focused tests and update guidance; provider factories, query ranking and handler extraction are unchanged.; Refuse implicit precision-changing index rebuilds: Implemented current-schema explicit full/int8 preflight before targeted/scoped escalation; original full intent is retained. Both setup paths now report nonzero build failure without inferring epoch/reader state. Twenty-one focused tests passed in 13.383s: real producer matrix, both directions, full/docs/code/graph/dry-run/targeted/rechunk/sibling, unchanged canonical SQL state and zero model/epoch entry, compatible changed-file reuse, explicit conversion, fresh non-full CPU install, real provider predictor, revision/legacy controls, guard-removal mutant, and real CLI/setup/MCP refusal consumers. Full indexer/setup modules remain running.; Refuse implicit precision-changing index rebuilds: Observe: the second canonical full run exposed two old fixtures (three failing assertions) that changed precision while testing fingerprint/model currency. Repair preserves producer precision for fingerprint mutation and pins recorded precision for targeted identity variation; original assertions remain and an explicit no-failure assertion was added. Both independent contexts rechecked these exact tests successfully; product/docs hashes unchanged.

**Changes delivered:**

- **Refuse implicit precision-changing index rebuilds** (`1yljo-bug provider-fallback-rebuild-cascade`) — 4 ACs completed. Key decisions: Refuse implicit precision conversion; use existing explicit full request.; Separate incident repair from handler wave.
## Watchpoints

- Watchpoint: inspect untouched semantic layers before scoped convergence and preserve caller full intent before internal escalation.
- Watchpoint: no live full rebuild is needed to validate this guard; use small producer-built test indexes and embedding spies.
- Follow-up: handler extraction wave 1ymzk is paused until this repair is delivered.

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
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: legacy precision parser defaults cannot establish known identity; strongest-alternative: preserve full precision on CPU, rejected as a broader factory/cache policy change). Two independent contexts reviewed code/QA and architecture/docs respectively; [readiness evidence](readiness-review.md).

## Delivery Review Checkpoints

- **Delivery Wave Council [delivery-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; seat-agreement: unanimous; max-severity: none). Targeted receipt roster; two independent contexts also covered required code/QA/architecture lanes. The real-predictor and ordinary fresh-CPU primer questions were verified; compatible CPU full-precision fallback was weighed as a broader alternative. See [delivery evidence](delivery-review.md).
- Red-team/code/QA: no findings in the delivered boundary; six mutants killed and the child-process isolation repair independently rechecked, including a child mutant that fails the parent assertion. Same reviewer context across these perspectives, not three independent reviews.
- Docs-contract/architecture: no findings; canonical storage/recovery ownership and user guidance checked; six mutants killed, fresh CPU control passed and final isolation repair independently rechecked. These two perspectives share one independent context.
- Focused readiness refresh after the operator's benchmark waiver approved receipt `review-policy-b230afcc648d7c87f358`; behavioral requirements unchanged. Benchmark reports retained as invalid, not passing evidence. No memory candidates were proposed.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 15 | 3,177 |
| implement | 34 | 366,443 |
| review | 36 | 176,228 |
| **Total** | **85** | **545,848** |

<!-- wave:context-efficiency-state {"generation":87,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":34,"content_source_credit":418900,"derived_artifact_credit":1049,"direct_net":366443,"estimated_tokens_saved":366443,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3272,"response_debit":52243,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2009},"plan":{"calls":15,"content_source_credit":13405,"derived_artifact_credit":2109,"direct_net":3177,"estimated_tokens_saved":3177,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1607,"response_debit":17472,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6742},"review":{"calls":36,"content_source_credit":219235,"derived_artifact_credit":2395,"direct_net":176228,"estimated_tokens_saved":176228,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7359,"response_debit":40359,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":85,"content_source_credit":651540,"derived_artifact_credit":5553,"direct_net":545848,"estimated_tokens_saved":545848,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12238,"response_debit":110074,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11067},"wave_id":"1yljp explicit-precision-rebuild"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 3 | 3,204,425 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":3204425,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
