# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-02
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

The wave pairs extraction-time type/provenance guards with query-time filtering, versioned cluster-artifact support, and trust metadata. It repairs false graph facts and the public surfaces agents use to judge those facts without broadening into general community or graph-relevance research.

## Watchpoints

- Watchpoint: stricter resolution must preserve positive callable, constructor, and runtime-config edges; false-positive removal cannot be accepted by edge-count reduction alone.
- Watchpoint: unfiltered graph-report rankings must remain stable while filtered rankings refill correctly.
- Watchpoint: hierarchy metadata additions must remain schema-compatible and payload-bounded.
- Watchpoint: filtered betweenness refill requires a versioned complete persisted order; preserve the compatibility top-N view and measure compressed artifact/rebuild cost.
- Watchpoint: the closed `1seaw` standing gate identifies graph extraction/query modules as production retrieval code, but its evaluator does not yet bind cluster code/version or per-fixture regressions. Add/freeze that scaffold first, capture a fresh post-`1wpif` run A/B pair, then require exact-baseline run C with graph-carrier evidence and explicit controlled cross-generation results.

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

- Plan readiness may be reviewed independently, but implementation follows completion of `1wpif` so the required immediate-predecessor standing pair isolates graph-wave effects from content/retrieval-correctness changes.
- The wave remains planned/readied while `1wpif` owns the single OPEN slot; activation occurs only after `1wpif` closes and its final production/index identities are available.
- Within the wave, ordering is mandatory: evaluator scaffold → freeze/index successor evaluator → exclusive-create run A → run B against caller-declared A → `1wpai` extraction edits → `1wpaj` query/cluster edits → graph/cluster rebuild → run C against caller-declared B. No graph production edit may precede successful A/B.

## Current Assumptions

- JSON/YAML structural nodes remain useful graph content and will not be removed wholesale.
- `EXTRACTED` edges remain a supported fallback when no stronger attribution exists.
- Existing graph schema can carry the corrected edges and response metadata without a wholesale format rewrite.

## Outputs Produced or Expected

- Relation-compatible call/config edges with bounded before/after fidelity census.
- Correctly filled filtered graph reports.
- Call hierarchies exposing stable node and per-edge trust metadata.
- Frozen-corpus standing retrieval run A/B/C chain bound to graph/query/cluster production identity, builder versions, the exact predecessor receipt, and exercised graph-carrier evidence.
- Graph architecture updates and full/incremental regression evidence.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked for extraction-time edge fidelity and query-time trust contracts. Resolved branches require relation-compatible code-origin call targets, provenance-backed config reads, a `GRAPH_BUILDER_VERSION` bump with unchanged-corpus re-extraction, pre-truncation filtering for every affected report view, and compact per-node/per-edge hierarchy metadata.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: fixing the extractor without a builder-version bump leaves cached graphs carrying the same phantom edges indefinitely; strongest-alternative: use a broad name-based suppression list, rejected in favor of versioned invalidation and a conservative relation-specific code-origin/provenance matrix)
- Readiness synthesis: READY. Architecture verdict: approved-with-notes, high confidence; keep unfiltered ranking stable, preserve positive callable/constructor/runtime-config controls, and keep hierarchy metadata payload-bounded.
- **Closed-wave evidence intake — 2026-08-31: PLAN AMENDED; RE-PREPARE REQUIRED.** Closed `1seaw` proved that graph production modules can alter `code_ask` citations. Fresh code/QA review then found the historical evaluator did not bind cluster identity, could mask a per-fixture regression, and could not by itself prove immediate-predecessor provenance. `1wpaj` now requires a successor evaluator scaffold followed by uniquely named post-`1wpif` run A/B and exact-baseline post-rebuild run C, while retaining the closed evaluator digest as provenance only. The 2026-08-30 readiness receipt predates this gate and is not current authority.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-31: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a self-selected or replaced predecessor, escaped/aliased report path, aggregate-masked fixture regression, concurrent artifact publication, or unexercised graph carrier could make an internally consistent receipt green without proving the graph change safe; strongest-alternative: hold a run-wide publication lock, rejected in favor of a confined single-handle sequence driver with atomic exclusive writes and bounded around-call lock/token/artifact fences that fail closed without lock inversion)
- Readiness synthesis: APPROVED. Independent code and QA lanes approved the successor evaluator and exact A/B/C chain after repair; performance approved the bounded evaluator/rebuild sequences; red-team and security seats approved externally declared predecessor identity, confined/exclusive report I/O, per-fixture oracles, persisted builder/artifact evidence, publication-race mutants, and the fixed carrier-loss mutant. A supplemental architecture review approved the graph/cluster version sequence and rejected split sidecar authority. Implementation remains ordered after `1wpif` closure.
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
| plan | 216 | 2,611,348 |
| implement | 1 | 0 |
| review | 11 | 466,326 |
| **Total** | **228** | **3,077,674** |

<!-- wave:context-efficiency-state {"generation":69,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-407,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19,"response_debit":388,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":216,"content_source_credit":2684504,"derived_artifact_credit":4935,"direct_net":2611348,"estimated_tokens_saved":2611348,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14181,"response_debit":531545,"source_credit_count":198,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":7886},"review":{"calls":11,"content_source_credit":474286,"derived_artifact_credit":0,"direct_net":466326,"estimated_tokens_saved":466326,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":211,"response_debit":7749,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":228,"content_source_credit":3158790,"derived_artifact_credit":4935,"direct_net":3077267,"estimated_tokens_saved":3077674,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14411,"response_debit":539682,"source_credit_count":206,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":7886},"wave_id":"1wpig graph-correctness-and-trust-contracts"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
