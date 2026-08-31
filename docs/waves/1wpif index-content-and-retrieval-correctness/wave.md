# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-31
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wpif index-content-and-retrieval-correctness`
Title: Index Content And Retrieval Correctness

## Objective

Restore trustworthy indexed content and retrieval behavior: distinct source chunks remain searchable, source ranges are accurate, FTS state heals honestly, filters are honored during candidate generation, and ANN settings match measured runtime behavior.

## Changes

Change ID: `1wngv-bug chunk-identity-source-range-integrity`
Change Status: `planned`

Change ID: `1wpag-bug fts-reconciliation-query-honesty`
Change Status: `planned`

Change ID: `1wpah-bug retrieval-candidate-generation-correctness`
Change Status: `planned`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit the audited findings into waves; no new end-user feature scope is introduced.

## Wave Summary

Three coupled correctness changes repair chunk identity/source metadata, lexical-state recovery, and candidate-generation filtering. The wave deliberately excludes later relevance tuning so correctness and truthful diagnostics can be verified against a stable production-path evaluation baseline.

## Watchpoints

- Activation dependency: implement `1sear` first so chunking/filter/ANN changes have a standing production-path baseline and holdout gate; plan/council review may complete earlier, but readiness is recorded only after the baseline artifact exists.
- Baseline authority: readiness requires two current-schema, same-generation `1sear` baseline runs plus their comparison receipt, with matching fixture/evaluator/production identities and the final pre-`1wpif` index generation recorded.
- Watchpoint: preserve unaffected chunk IDs and compare full versus incremental builds before accepting the compatibility bump.
- Watchpoint: FTS recovery and filter pushdown share state-store/query boundaries; serialize overlapping edits and run parity tests after both land.
- Watchpoint: no index rebuild should publish as evidence until the new collision, parity, and exact-search checks are available.

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
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| performance-reviewer | pending | no current executed approval | record approval evidence for performance-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Depends on `1seaw retrieval-intent-golden-queries`, specifically completion and baseline publication for `1sear-enh golden-query-retrieval-eval-suite`.
- Within the wave, establish `1wngv` and `1wpag` integrity invariants before final `1wpah` relevance/latency comparison.

## Current Assumptions

- The current Snowflake embedding and MiniLM reranker stack remains fixed.
- SQLite FTS5 and Lance remain the lexical/vector stores.
- A one-time deterministic rebuild is acceptable after the compatibility/version change.

## Outputs Produced or Expected

- Collision-free chunks with absolute source ranges and stable unaffected IDs.
- Self-healing, honestly diagnosed FTS state.
- Filter-aware candidate generation with measured ANN settings.
- Regression fixtures, corpus censuses, before/after retrieval metrics, and updated architecture contracts.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked across chunk identity/source ranges, FTS recovery/query honesty, and candidate generation. Resolved branches pin source-derived range payloads separately from breadcrumbs, make healthy-semantic/failed-lexical hybrid behavior non-destructive but diagnostic, preserve typed failure for lexical-only/degraded substrate failure, and require individually frozen evaluation runs with a recorded two-generation controlled rebuild comparison.
- **Prepare-phase Wave Council review — 2026-08-30: REVIEWED, READINESS DEFERRED** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; strongest-challenge: the wave cannot claim a trustworthy before/after improvement without the production-path `1sear` baseline it explicitly depends on; strongest-alternative: remove the dependency and use local bespoke fixtures only — rejected because the wave changes indexed content, filtering, and ANN behavior together and therefore needs the standing end-to-end gate). Security verdict: approved-with-notes, no credible threat under the local/operator-owned model; keep degraded fault injection on copied stores, all refill/probe work hard-bounded, query filters parameterized, and read-only retrieval paths non-healing. No readiness approval is recorded until `1sear` publishes its baseline.
- **Prepare re-review — 2026-08-31: PLAN REPAIRED, READINESS DEFERRED.** Independent red-team, code, and performance reviews confirmed the dependency blocker and found four underspecified contracts. The packet now freezes deterministic chunk/dedupe identity, equal-count keyed FTS integrity with epoch-cached O(1) healthy reads, a four-round/240-row refill ceiling with typed termination, and exact ANN recall/latency/payload thresholds. Readiness still requires the final current-schema `1sear` two-run baseline pair and comparison receipt; no typed readiness approval is recorded before that evidence exists.
- Prepare: after `1sear` lands, confirm its two-run baseline pair and comparison receipt, compatibility/rebuild plan, and public diagnostic contracts. Each before/after evaluation run is individually generation-frozen; a controlled chunker rebuild comparison records its two generations explicitly.
- Mid-wave: review the shared state-store/server boundary after chunk/FTS repairs and before ANN/ranking measurements.
- Delivery: replay duplicate-ID, wrong-line, missing-FTS, rank-31 language, per-file fill, and exact-versus-ANN probes.

## Completion Criteria

- Every required AC in all three admitted changes is `[x]` or operator-rationalized `[~]`.
- Production-path golden evaluation holds or improves on its required metrics.
- Full framework tests, docs validation, full/incremental equivalence, and deterministic rebuild evidence pass.

## Handoff or Next-Wave Notes

- After closure, `1wpih index-quality-evaluation-and-ranking` may use the corrected lexical/candidate baseline for measured relevance improvements.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 106 | 2,461,983 |
| review | 33 | 1,662,898 |
| **Total** | **139** | **4,124,881** |

<!-- wave:context-efficiency-state {"generation":43,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":106,"content_source_credit":2563460,"derived_artifact_credit":6383,"direct_net":2461983,"estimated_tokens_saved":2461983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3000,"response_debit":368274,"source_credit_count":144,"source_credit_drop_count":0,"structural_source_credit":262098,"workflow_prompt_credit":1316},"review":{"calls":33,"content_source_credit":1751546,"derived_artifact_credit":0,"direct_net":1662898,"estimated_tokens_saved":1662898,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1292,"response_debit":87356,"source_credit_count":57,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":139,"content_source_credit":4315006,"derived_artifact_credit":6383,"direct_net":4124881,"estimated_tokens_saved":4124881,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4292,"response_debit":455630,"source_credit_count":201,"source_credit_drop_count":0,"structural_source_credit":262098,"workflow_prompt_credit":1316},"wave_id":"1wpif index-content-and-retrieval-correctness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
