# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wpih index-quality-evaluation-and-ranking`
Title: Index Quality Evaluation And Ranking

## Objective

Improve measured lexical, semantic-candidate, confidence, and architectural graph quality after correctness repairs are in place, while making evidence roles, exact references, and public confidence auditable enough that aggregate gains cannot conceal weak or contaminated user evidence.

## Changes

Change ID: `1wpid-enh lexical-ranking-robustness`
Change Status: `complete`

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `complete`

Change ID: `1wsc8-enh ann-reference-and-tuning-certification`
Change Status: `complete`

Change ID: `1wscp-enh retrieval-evidence-adjudication-and-confidence-contracts`
Change Status: `complete`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit later index-quality work; Prepare must still review the user-visible ranking/community behavior.

Completed At: 2026-09-04

## Wave Summary

Wave `1wpih` (Index Quality Evaluation And Ranking) delivered 4 changes: Improve Long-Query Token Selection and Cross-Table Lexical Fusion, Evaluate Graph Fidelity and Isolate Machine Evidence Communities, Add Exact ANN Reference and Tuning Certification, and Add Retrieval Evidence Adjudication and Confidence-Basis Contracts. Notable adjustments during implementation: Improve Long-Query Token Selection and Cross-Table Lexical Fusion: **Operator-directed scope correction.** BM25 length bias against short declaration chunks is named out of scope, with the measurement that forced it.; Add Exact ANN Reference and Tuning Certification: Incidental finding, outside this wave's scope.; Add Retrieval Evidence Adjudication and Confidence-Basis Contracts: **Scope boundary reached for this pass.** AC-5 and AC-6 are production edits to confidence and routing, which the wave's serialization watchpoint places AFTER the frozen baseline A/B pair; AC-1 and AC-8 ARE that baseline. None of them can honestly land until all four scaffolds exist and the index is frozen, and three of those four scaffolds are unwritten. Recorded here rather than left implicit so the remaining order is unambiguous.

**Changes delivered:**

- **Improve Long-Query Token Selection and Cross-Table Lexical Fusion** (`1wpid-enh lexical-ranking-robustness`) — 7 ACs completed. Key decisions: Keep the safety cap, select informative terms within it, and evaluate rank-based fusion before changing score math.
- **Evaluate Graph Fidelity and Isolate Machine Evidence Communities** (`1wpie-enh graph-quality-evaluation-and-evidence-isolation`) — 11 ACs completed. Key decisions: Establish the fidelity corpus first, classify evidence as a fixed auxiliary domain while retaining its graph nodes, and report it outside the production community ranking.; Place the Evidence/Data positive control under this wave's own evidence tree, and guard every classification assertion with a presence assertion.
- **Add Exact ANN Reference and Tuning Certification** (`1wsc8-enh ann-reference-and-tuning-certification`) — 8 ACs completed. Key decisions: Create a dedicated ANN certification change and admit it to `1wpih`.; Keep `1wq0b` separate.
- **Add Retrieval Evidence Adjudication and Confidence-Basis Contracts** (`1wscp-enh retrieval-evidence-adjudication-and-confidence-contracts`) — 9 ACs completed. Key decisions: Adjudicate evidence before fixing ranking and make confidence lead-aware.; Keep findings-register access in `1wq0b`.
## Watchpoints

- Do not tune lexical ranking against calibration queries and then report those same cases as validation evidence.
- Do not describe consulted, implementation-authored, protected-local, or standing-regression fixtures as independent improvement evidence.
- Do not remove evidence JSON from graph indexing merely to improve community presentation, and do not classify evidence from path/shape/co-clustering alone.
- Any ranking or community policy change requires before/after Recall/MRR/nDCG or precision/recall plus latency/size evidence.
- Evidence-first gate: QA freezes calibration and holdout corpora and their digests, captures the predecessor-state baseline before production edits, permits mechanism selection against calibration only, and runs the untouched holdout only for delivery evidence. The live whole-repository census is supplemental, not holdout authority.
- Closed-`1seaw` residuals remain visible until adjudicated: zero architecture-review/enumeration/exact-identifier strata, constant-value classifier mismatch, evaluator-source contamination, and lead/confidence disagreement cannot be erased by aggregate improvement.
- Serialization watchpoint: all four admitted changes touch or depend on `.wavefoundry/framework/scripts/server_impl.py` and shared evaluation carriers. After readiness/activation, use one production write owner and this order: land the retrieval evidence/adjudication, ANN reference, lexical-ranking, and graph-quality measurement/schema scaffolds with no production behavior change; freeze/index all four; capture one immediate same-state baseline A/B; then confidence/routing; lexical; each of at most three ANN candidates; graph policy/public projection; final standing replay. No production ranking/community edit precedes A/B. Any later index-eligible evaluator scaffold invalidates A/B and blocks further production work until operator-approved rebaselining is incorporated within a revised bounded checkpoint budget.

## Execution Order

Operator-set on 2026-09-03. The serialization watchpoint states the constraint; this states the concrete steps in order. **The binding rule is the index boundary:** every index-eligible file must land before the baseline, because a later one invalidates it (Requirement 8 of `1wscp`). New `.py` evaluator modules ARE index-eligible; new corpora are NOT, provided each is added to `.aiignore` when created, as `docs/evals/retrieval-adjudications.json` was.

| # | Step | Lands | Gate before proceeding |
| --- | --- | --- | --- |
| 1 | Evidence authority, adjudication receipts, carrier contamination | `1wscp` AC-2, AC-3, AC-4 | **DONE** 2026-09-02/03; 12 mutants killed |
| 2 | `lexical_ranking_eval.py` + disposable-store runner + frozen calibration/regression corpora + leak scan | `1wpid` AC-7 | Corpora `.aiignore`d; runner under 30s |
| 3 | `ann_reference_eval.py` + exact-mode seam on `LanceVectorQueryBuilder` + golden corpus | `1wsc8` AC-1, AC-2 | Query-builder spy proves `bypass_vector_index()` ran |
| 4 | `graph_quality_eval.py` + mixed-artifact corpus + relation/public-tool matrix | `1wpie` AC-1, AC-9 | Corpus within 128 files / 2,000 nodes / 5,000 edges |
| 5 | **Index freeze:** one `index_build` rebuild, then record digests | none | `index_health` current; all four scaffold corpora excluded |
| 6 | **Baseline A/B:** two standing runs on the frozen state | `1wscp` AC-1; `1wsc8` AC-6 | Pair jitter under threshold, else re-run once |
| 7 | Confidence basis + citation selection reason + constant-value navigational routing | `1wscp` AC-5, AC-6, AC-7 | **DONE**; AC-7 deferred, phrasing never committed |
| 8 | Lexical token selection + cross-table fusion | `1wpid` AC-1..AC-6 | **DONE**; `1wpid` complete, all 7 criteria met |
| 9 | ANN candidates, at most three, each certified or rejected | `1wsc8` AC-3, AC-4, AC-5, AC-7, AC-8 | Checkpoints 5-7; fail-closed expected |
| 10 | Graph evidence partition across all five section pairs + docs | `1wpie` AC-2..AC-8, AC-10, AC-11 | Checkpoint 8 |
| 11 | Final standing replay + checkpoint-budget proof | `1wscp` AC-8, AC-9, AC-10; `1wpid` AC-6 | Checkpoint 9 of 9 |

Steps 2-4 are order-independent among themselves and must all precede step 5. Steps 7-10 must each precede the next because they share one production write owner in `server_impl.py`. No production ranking or community edit may precede step 6.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | — |
| CODE-DEL-1 | do_now | no | completed | — |
| CODE-DEL-2 | do_now | no | completed | — |
| CODE-DEL-3 | do_now | no | completed | — |
| DOCS-DEL-1 | do_now | no | completed | — |
| DOCS-RDY-1 | maybe_later | no | completed | — |
| QA-DEL-1 | do_now | no | completed | — |
| QA-DEL-2 | do_now | no | completed | — |
| QA-DEL-4 | do_now | no | completed | — |
| RED-DEL-1 | not_issue | no | not_required | — |
| RED-RDY-1 | do_now | no | completed | — |
| RED-RDY-2 | do_now | no | completed | — |

*Machine review state — 12 findings; current: do_now 10, maybe_later 1, dont_do_later 0, not_issue 1*
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
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1seaw retrieval-intent-golden-queries` is complete. Its historical predecessor authority is the 35-fixture corpus digest `bda675468d4da0184a97a94c4396cf8f379981a19339c1ad4958ba50f9466312`, evaluator digest `61ec60daeb5347984f1e2c3e6f47a48d74931df11edf6f78ce84acb219c9207a`, production digest `dab71287550d9e541b8f36d734ae34b44df84ef83ad8b5b4139c611409cbbae4`, index attempt `8916932ce45d4cd48e725493bf21eb20`, standing pair `docs/reports/retrieval-quality-baseline-run1.json` plus `docs/reports/retrieval-quality-baseline.json`, and production-change receipt `docs/reports/retrieval-quality-post-1seas-vs-before.json`. These artifacts are regression provenance, not authority for the changed predecessor state.
- Depends on completion of `1wpif index-content-and-retrieval-correctness` for trustworthy lexical/candidate state and on completion of `1wpig graph-correctness-and-trust-contracts` for corrected graph edges/public contracts. After both close, verify their final production/index/artifact identities and re-Prepare this reviewed plan. Only after `1wpih` is readied and activated may the implementer add all four measurement/schema scaffolds (retrieval evidence, ANN reference, lexical ranking, and graph quality); QA then freezes/indexes all four and captures the immediate same-generation pair before any `1wpih` production ranking or graph-community change.
- Scope intake (2026-08-31, from the `1wpif` prepare council): ANN measurement is owned by admitted change `1wsc8`, with exact Lance reference mode, slice-level ANN overlap, fail-closed certification, and fixed cost ceilings. No ANN setting may be retained from the historical `1seaw` generation or without the immediate baseline pair.
- `1wq0b-enh findings-register-assessment-surface` remains a separate staged public-surface plan and is not a readiness dependency. This wave must not reintroduce its rejected report-path prior or synthetic score into organic `code_ask` ranking.

## Current Assumptions

- The twelve-token FTS safety cap remains in force.
- Existing embedding and reranking models remain unchanged.
- Evidence/data nodes remain queryable even if separated from production architecture rankings.

## Outputs Produced or Expected

- Identifier-aware bounded FTS query selection and measured cross-table fusion.
- Evidence-role/adjudication receipts, carrier-contamination checks, and lead-aware confidence/selection bases.
- Exact ANN reference reports, slice-level overlap, and a fail-closed tuning certificate or explicit retention of library defaults.
- Mixed-artifact graph ground truth with per-relation precision/recall.
- Provenance-backed Evidence/Data community isolation preserving topology and excluding canonically ignored standing artifacts from the graph entirely.
- Baselines, holdout results, latency/size ceilings, and updated architecture/testing contracts.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked for lexical ranking and graph-quality evaluation. Seeded lexical/edge collision fixtures must detect the known-bad state while the corrected baseline reports zero corresponding false positives; calibration and holdout sets remain separate; production graph results stay in `communities`, with machine evidence exposed through a typed `evidence_communities` partition rather than relabeling the same top-N.
- **Prepare-phase Wave Council review — 2026-08-30: REVIEWED, READINESS DEFERRED** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; strongest-challenge: combining two evaluation-first tracks could create one unbounded ranking abstraction and obscure their different evidence contracts; resolved by separate fixtures, metrics, runners, and implementation abstractions plus one ordered write owner for the shared `server_impl.py` boundary; strongest-alternative: remove evidence/data nodes from graph indexing — rejected because targeted queries and topology still need them, so fixed auxiliary classification and response partitioning preserve the source graph). Architecture verdict: approved, high confidence. Readiness remains dependency-gated on completed `1seaw`, `1wpif`, and `1wpig`.
- **Prepare re-review — 2026-08-31: PLAN REPAIRED, READINESS DEFERRED.** Independent red-team, docs-contract, and QA reviews retained the single wave and repaired its evidence contract: separate frozen calibration/holdout artifacts with a leak scan; a bounded disposable degraded/fusion runner covering all three mixed-table carriers; an exact dual-array `evidence_communities` schema; pre-top-N partitioning across every promised production ranking; predecessor-relative cluster-builder invalidation; relation/public-tool scoring; and precommitted determinism, latency, size, and evidence-identity thresholds. Readiness remains blocked until `1wpif` and `1wpig` close and their final artifacts and identities are verified.
- **Closed-`1seaw` results intake — 2026-08-31: WAVE EXPANDED; RE-PREPARE REQUIRED.** Added admitted ANN exact-reference/certification (`1wsc8`) and retrieval evidence-adjudication/confidence (`1wscp`) changes. Graph evidence classification now requires explicit provenance and graph-absence controls for ignored standing artifacts; cluster invalidation is relative to the landed `1wpig` version. Final plan review also made evidence roles machine-derived, bounded every evaluator/rebuild sequence, defined five typed Evidence/Data ranking carriers, and separated post-activation measurement scaffolds from candidate/production edits. The earlier review predates these boundaries and is no longer sufficient for readiness.
- **Post-intake plan review — 2026-08-31: APPROVED, READINESS DEFERRED.** Independent code, QA/performance, architecture/docs-contract, and adversarial reviews approved the four-change packet after repair. The final contract lands all four index-eligible measurement scaffolds after activation but before shared A/B, derives gain authority from authorship/consultation/exposure, bounds standing/ANN/graph evidence, preserves the `1wpif` no-tuning default seam unless a candidate certifies, and exposes exact parallel Evidence/Data arrays for every partitioned graph ranking. No implementation or index mutation was performed. Formal Prepare remains deferred until `1wpif` and readied `1wpig` close and their final identities are verified.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: no plan claim about the current tree could be trusted until re-derived, which proved out — the graph-quality rationale's motivating census was stale in both rank and count after the predecessor rebuilds, and the required Evidence/Data positive control had no named location while the natural one contributes zero graph nodes, so that criterion could have passed vacuously; strongest-alternative: leave the evidence positive control's location to implementer judgement, rejected because the graph-absence requirement and the classification requirement pull toward opposite trees and only an explicit indexed location plus a presence precondition makes the criterion falsifiable)
  - Dependency gate satisfied: `1wpif` and `1wpig` both closed. Verified post-predecessor identities: fixture digest `bda67546…` unchanged through both waves, production digest moved to `cd05ed04…`, graph builder 46, cluster builder 12.
  - Three findings raised, all terminal. Two blocking: the stale census, and the vacuously-passable evidence control. One non-blocking: an artifact named for the evidence class its own contract denies. All three repaired and independently reverified by a separate actor that re-derived every figure itself and refused the naming repair on its first pass, forcing a second.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a re-Prepare after delivery repairs is where a change document quietly stops describing the delivered system, so every figure the four documents assert about the current tree was re-derived rather than read — the graph builder version had drifted to 49 while one performance note still said 48, and that note is now dated to its measurement; strongest-alternative: leave the delivery-repair record in the ledger alone and re-ready on the existing prose, rejected because the ledger is the sole review authority on a declared wave and four repaired defects had no ledger records at all, so the prose and the authority disagreed)
  - Receipt rebind only: the change documents were edited during delivery repair, which rotated the review-policy receipt to `review-policy-473208787d393c794b21` and moved the rotating seat to docs-contract-reviewer. No scope, requirement, or acceptance-criterion text changed in this pass.
  - red-team seat: challenged every current-tree claim in the four documents. `docs/evals/` and `docs/reports/` contribute zero graph nodes (re-derived after a clean rebuild; the two new graph-quality reports HAD leaked and were the reason `.aiignore` gained its missing entry). The corpus-fitting claim against the standing retrieval gate was refuted with a HEAD diff and three injected fitting mutants, and recorded as `RED-DEL-1` with disposition `not_issue`.
  - docs-contract-reviewer seat: every symbol named in the documentation resolves — `build_report`, `write_report`, `verify_report_pair`, `assert_report_is_excluded_from_the_corpus` and `production_identity` in `graph_quality_eval.py`; `community_evidence_share`, `is_evidence_community` and `EVIDENCE_COMMUNITY_MAJORITY` in `graph_query.py`; `render_graph_communities_markdown` in `server_impl.py`. Requirement 9's two report paths exist and are ignored by the index. The catalog contract in `AGENTS.md` and `docs/specs/mcp-tool-surface.md` matches the rendered output.
  - Five delivery findings were recorded to the typed ledger in this pass (`ARCH-DEL-1`, `CODE-DEL-2`, `CODE-DEL-3`, `QA-DEL-2`, `QA-DEL-4`), each repaired and independently reverified; `RED-DEL-1` closed as not an issue.
- Prepare: after `1wpif` and `1wpig` close, verify their final artifacts and implementation identities, then re-Prepare and ready this plan without modifying repository code or indexes. After activation, the implementer lands all four evaluator-only scaffolds first; QA freezes/indexes them and captures immediate baseline A/B before any production ranking/community change.
- Mid-wave: QA review of calibration/holdout separation and graph ground-truth labels before implementation selection.
- Delivery: independent relevance/fidelity replay plus hostile-input, determinism, latency, topology, and artifact-size controls.

## Completion Criteria

- Every required AC in all four admitted changes is `[x]` or operator-rationalized `[~]`.
- Standing/per-class retrieval holds, ANN is certified or defaults remain, holdout lexical metrics hold or improve, graph fidelity metrics are published, confidence describes the lead evidence, and Evidence/Data no longer dominates production community orientation.
- Full framework tests, docs validation, deterministic graph builds, and operational ceilings pass.

## Handoff or Next-Wave Notes

- Future ranking/model proposals use these standing retrieval and graph-quality baselines rather than bespoke anecdotal checks.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 99 | 2,091,518 |
| implement | 148 | 1,305,931 |
| review | 91 | 2,948,084 |
| **Total** | **338** | **6,345,533** |

<!-- wave:context-efficiency-state {"generation":329,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":148,"content_source_credit":1388196,"derived_artifact_credit":0,"direct_net":1305931,"estimated_tokens_saved":1305931,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4221,"response_debit":87835,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9791},"plan":{"calls":99,"content_source_credit":2304851,"derived_artifact_credit":918,"direct_net":2091518,"estimated_tokens_saved":2091518,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22304,"response_debit":197643,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":91,"content_source_credit":2844446,"derived_artifact_credit":1401,"direct_net":2948084,"estimated_tokens_saved":2948084,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36092,"response_debit":122849,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":259289,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":338,"content_source_credit":6537493,"derived_artifact_credit":2319,"direct_net":6345533,"estimated_tokens_saved":6345533,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62617,"response_debit":408327,"source_credit_count":225,"source_credit_drop_count":0,"structural_source_credit":259289,"workflow_prompt_credit":17376},"wave_id":"1wpih index-quality-evaluation-and-ranking"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 3,197,648 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":3197648,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
