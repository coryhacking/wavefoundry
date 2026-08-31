# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-31
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wpig graph-correctness-and-trust-contracts`
Title: Graph Correctness And Trust Contracts

## Objective

Restore graph fidelity and consumer trust by preventing cross-domain phantom edges, applying report filters before truncation, and preserving per-edge confidence metadata in public call hierarchies.

## Changes

Change ID: `1wpai-bug graph-edge-resolution-guards`
Change Status: `planned`

Change ID: `1wpaj-bug graph-query-contract-correctness`
Change Status: `planned`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit the audited graph correctness findings; behavior restores documented contracts.

## Wave Summary

The wave pairs extraction-time type/provenance guards with query-time filtering and trust metadata. It repairs false graph facts and the public surfaces agents use to judge those facts, without broadening into clustering or general graph-relevance research.

## Watchpoints

- Watchpoint: stricter resolution must preserve positive callable, constructor, and runtime-config edges; false-positive removal cannot be accepted by edge-count reduction alone.
- Watchpoint: unfiltered graph-report rankings must remain stable while filtered rankings refill correctly.
- Watchpoint: hierarchy metadata additions must remain schema-compatible and payload-bounded.
- Watchpoint: filtered betweenness refill requires a versioned complete persisted order; preserve the compatibility top-N view and measure compressed artifact/rebuild cost.

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
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| performance-reviewer | pending | no current executed approval | record approval evidence for performance-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No hard external wave dependency; this wave may be readied independently.
- Recommended implementation order places it after `1wpif` only to respect the single-OPEN-wave rule and the overall index-audit priority sequence.
- Within the wave, extraction repair (`1wpai`) precedes final public query replay for `1wpaj` so hierarchy evidence is evaluated on corrected edges.

## Current Assumptions

- JSON/YAML structural nodes remain useful graph content and will not be removed wholesale.
- `EXTRACTED` edges remain a supported fallback when no stronger attribution exists.
- Existing graph schema can carry the corrected edges and response metadata without a wholesale format rewrite.

## Outputs Produced or Expected

- Relation-compatible call/config edges with bounded before/after fidelity census.
- Correctly filled filtered graph reports.
- Call hierarchies exposing stable node and per-edge trust metadata.
- Graph architecture updates and full/incremental regression evidence.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked for extraction-time edge fidelity and query-time trust contracts. Resolved branches require relation-compatible code-origin call targets, provenance-backed config reads, a `GRAPH_BUILDER_VERSION` bump with unchanged-corpus re-extraction, pre-truncation filtering for every affected report view, and compact per-node/per-edge hierarchy metadata.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: fixing the extractor without a builder-version bump leaves cached graphs carrying the same phantom edges indefinitely; strongest-alternative: use a broad name-based suppression list, rejected in favor of versioned invalidation and a conservative relation-specific code-origin/provenance matrix)
- Readiness synthesis: READY. Architecture verdict: approved-with-notes, high confidence; keep unfiltered ranking stable, preserve positive callable/constructor/runtime-config controls, and keep hierarchy metadata payload-bounded.
- Prepare: confirm target-kind compatibility rules, provenance boundary, and public response compatibility.
- Mid-wave: architecture/QA review of negative and adjacent positive edge fixtures.
- Delivery: replay `os.cpu_count`, schema/config, filtered fan-in, and hierarchy confidence probes through public tools.

## Completion Criteria

- Every required AC in both admitted changes is `[x]` or operator-rationalized `[~]`.
- Named phantom edges are absent, positive controls remain, and filtered reports fill their limits.
- Full/incremental graph equivalence, framework tests, and docs validation pass.

## Handoff or Next-Wave Notes

- The corrected graph becomes the baseline for `1wpih` mixed-artifact fidelity evaluation and evidence-community isolation.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 190 | 2,556,497 |
| implement | 1 | 0 |
| review | 7 | 9,170 |
| **Total** | **198** | **2,565,667** |

<!-- wave:context-efficiency-state {"generation":39,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-407,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19,"response_debit":388,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":190,"content_source_credit":2601839,"derived_artifact_credit":2177,"direct_net":2556497,"estimated_tokens_saved":2556497,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10955,"response_debit":502009,"source_credit_count":180,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":5696},"review":{"calls":7,"content_source_credit":14537,"derived_artifact_credit":0,"direct_net":9170,"estimated_tokens_saved":9170,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":61,"response_debit":5306,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":198,"content_source_credit":2616376,"derived_artifact_credit":2177,"direct_net":2565260,"estimated_tokens_saved":2565667,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11035,"response_debit":507703,"source_credit_count":185,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":5696},"wave_id":"1wpig graph-correctness-and-trust-contracts"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
