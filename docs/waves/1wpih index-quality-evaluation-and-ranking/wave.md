# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-31
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wpih index-quality-evaluation-and-ranking`
Title: Index Quality Evaluation And Ranking

## Objective

Improve measured lexical relevance and architectural graph orientation after correctness repairs are in place, while adding representative evaluation that prevents those quality improvements from becoming unmeasured heuristics.

## Changes

Change ID: `1wpid-enh lexical-ranking-robustness`
Change Status: `planned`

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `planned`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit later index-quality work; Prepare must still review the user-visible ranking/community behavior.

## Wave Summary

This later wave uses production baselines to select bounded lexical token/fusion improvements and to establish graph precision/recall measurement before isolating machine evidence from architecture rankings. Both changes are evaluation-first and must demonstrate value without weakening safety, topology, latency, or determinism.

## Watchpoints

- Do not tune lexical ranking against calibration queries and then report those same cases as validation evidence.
- Do not remove evidence JSON from graph indexing merely to improve community presentation.
- Any ranking or community policy change requires before/after Recall/MRR/nDCG or precision/recall plus latency/size evidence.
- Evidence-first gate: QA freezes calibration and holdout corpora and their digests, captures the predecessor-state baseline before production edits, permits mechanism selection against calibration only, and runs the untouched holdout only for delivery evidence. The live whole-repository census is supplemental, not holdout authority.
- Serialization watchpoint: both admitted changes touch `.wavefoundry/framework/scripts/server_impl.py`; lexical and graph-report edits require one write owner and ordered integration, while their fixtures, metrics, runners, and implementation abstractions remain separate.

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
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| performance-reviewer | pending | no current executed approval | record approval evidence for performance-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Depends on completion of `1seaw retrieval-intent-golden-queries` for the production-path retrieval gate.
- Depends on completion of `1wpif index-content-and-retrieval-correctness` for trustworthy lexical/candidate state.
- Depends on completion of `1wpig graph-correctness-and-trust-contracts` for corrected graph edges and public contracts.

## Current Assumptions

- The twelve-token FTS safety cap remains in force.
- Existing embedding and reranking models remain unchanged.
- Evidence/data nodes remain queryable even if separated from production architecture rankings.

## Outputs Produced or Expected

- Identifier-aware bounded FTS query selection and measured cross-table fusion.
- Mixed-artifact graph ground truth with per-relation precision/recall.
- Evidence/Data community or equivalent measured report isolation preserving topology.
- Baselines, holdout results, latency/size ceilings, and updated architecture/testing contracts.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked for lexical ranking and graph-quality evaluation. Seeded lexical/edge collision fixtures must detect the known-bad state while the corrected baseline reports zero corresponding false positives; calibration and holdout sets remain separate; production graph results stay in `communities`, with machine evidence exposed through a typed `evidence_communities` partition rather than relabeling the same top-N.
- **Prepare-phase Wave Council review — 2026-08-30: REVIEWED, READINESS DEFERRED** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; strongest-challenge: combining two evaluation-first tracks could create one unbounded ranking abstraction and obscure their different evidence contracts; resolved by separate fixtures, metrics, runners, and implementation abstractions plus one ordered write owner for the shared `server_impl.py` boundary; strongest-alternative: remove evidence/data nodes from graph indexing — rejected because targeted queries and topology still need them, so fixed auxiliary classification and response partitioning preserve the source graph). Architecture verdict: approved, high confidence. Readiness remains dependency-gated on completed `1seaw`, `1wpif`, and `1wpig`.
- **Prepare re-review — 2026-08-31: PLAN REPAIRED, READINESS DEFERRED.** Independent red-team, docs-contract, and QA reviews retained the single wave and repaired its evidence contract: separate frozen calibration/holdout artifacts with a leak scan; a bounded disposable degraded/fusion runner covering all three mixed-table carriers; an exact dual-array `evidence_communities` schema; pre-top-N partitioning across every promised production ranking; a mandatory cluster-builder v11→v12 rebuild boundary; relation/public-tool scoring; and precommitted determinism, latency, size, and evidence-identity thresholds. Readiness remains blocked until `1seaw`, `1wpif`, and `1wpig` close and their final artifacts and identities are verified.
- Prepare: after all three predecessor waves close, verify their baseline artifacts, fixture/evaluator/production identities, corpus digests, and corrected graph/index state before recording readiness. Plan/council review may complete earlier.
- Mid-wave: QA review of calibration/holdout separation and graph ground-truth labels before implementation selection.
- Delivery: independent relevance/fidelity replay plus hostile-input, determinism, latency, topology, and artifact-size controls.

## Completion Criteria

- Every required AC in both admitted changes is `[x]` or operator-rationalized `[~]`.
- Holdout lexical metrics hold or improve, graph fidelity metrics are published, and evidence no longer dominates production community orientation.
- Full framework tests, docs validation, deterministic graph builds, and operational ceilings pass.

## Handoff or Next-Wave Notes

- Future ranking/model proposals use these standing retrieval and graph-quality baselines rather than bespoke anecdotal checks.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 46 | 1,275,971 |
| review | 2 | 0 |
| **Total** | **48** | **1,275,971** |

<!-- wave:context-efficiency-state {"generation":48,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":46,"content_source_credit":1404190,"derived_artifact_credit":10,"direct_net":1275971,"estimated_tokens_saved":1275971,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1387,"response_debit":128158,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"review":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1586,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38,"response_debit":1548,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":48,"content_source_credit":1404190,"derived_artifact_credit":10,"direct_net":1274385,"estimated_tokens_saved":1275971,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1425,"response_debit":129706,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"wave_id":"1wpih index-quality-evaluation-and-ranking"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
