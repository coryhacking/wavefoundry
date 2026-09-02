# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-02
review-evidence-source: events.jsonl

review-policy-reprepare-required: true
wave-id: `1wpih index-quality-evaluation-and-ranking`
Title: Index Quality Evaluation And Ranking

## Objective

Improve measured lexical, semantic-candidate, confidence, and architectural graph quality after correctness repairs are in place, while making evidence roles, exact references, and public confidence auditable enough that aggregate gains cannot conceal weak or contaminated user evidence.

## Changes

Change ID: `1wpid-enh lexical-ranking-robustness`
Change Status: `planned`

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `planned`

Change ID: `1wsc8-enh ann-reference-and-tuning-certification`
Change Status: `planned`

Change ID: `1wscp-enh retrieval-evidence-adjudication-and-confidence-contracts`
Change Status: `planned`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit later index-quality work; Prepare must still review the user-visible ranking/community behavior.

## Wave Summary

This later wave uses immediate production baselines to adjudicate standing evidence, repair confidence/routing contracts, certify ANN behavior against exact search, select bounded lexical token/fusion improvements, and establish graph precision/recall measurement before isolating provenance-backed machine evidence from architecture rankings. All four changes are evaluation-first and must demonstrate value without weakening safety, topology, latency, or determinism.

## Watchpoints

- Do not tune lexical ranking against calibration queries and then report those same cases as validation evidence.
- Do not describe consulted, implementation-authored, protected-local, or standing-regression fixtures as independent improvement evidence.
- Do not remove evidence JSON from graph indexing merely to improve community presentation, and do not classify evidence from path/shape/co-clustering alone.
- Any ranking or community policy change requires before/after Recall/MRR/nDCG or precision/recall plus latency/size evidence.
- Evidence-first gate: QA freezes calibration and holdout corpora and their digests, captures the predecessor-state baseline before production edits, permits mechanism selection against calibration only, and runs the untouched holdout only for delivery evidence. The live whole-repository census is supplemental, not holdout authority.
- Closed-`1seaw` residuals remain visible until adjudicated: zero architecture-review/enumeration/exact-identifier strata, constant-value classifier mismatch, evaluator-source contamination, and lead/confidence disagreement cannot be erased by aggregate improvement.
- Serialization watchpoint: all four admitted changes touch or depend on `.wavefoundry/framework/scripts/server_impl.py` and shared evaluation carriers. After readiness/activation, use one production write owner and this order: land the retrieval evidence/adjudication, ANN reference, lexical-ranking, and graph-quality measurement/schema scaffolds with no production behavior change; freeze/index all four; capture one immediate same-state baseline A/B; then confidence/routing; lexical; each of at most three ANN candidates; graph policy/public projection; final standing replay. No production ranking/community edit precedes A/B. Any later index-eligible evaluator scaffold invalidates A/B and blocks further production work until operator-approved rebaselining is incorporated within a revised bounded checkpoint budget.

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
- Prepare: after `1wpif` and `1wpig` close, verify their final artifacts and implementation identities, then re-Prepare and ready this plan without modifying repository code or indexes. After activation, the implementer lands all four evaluator-only scaffolds first; QA freezes/indexes them and captures immediate baseline A/B before any production ranking/community change.
- Mid-wave: QA review of calibration/holdout separation and graph ground-truth labels before implementation selection.
- Delivery: independent relevance/fidelity replay plus hostile-input, determinism, latency, topology, and artifact-size controls.

## Completion Criteria

- Every required AC in all four admitted changes is `[x]` or operator-rationalized `[~]`.
- Standing/per-class retrieval holds, ANN is certified or defaults remain, holdout lexical metrics hold or improve, graph fidelity metrics are published, confidence describes the lead evidence, and Evidence/Data no longer dominates production community orientation.
- Full framework tests, docs validation, deterministic graph builds, and operational ceilings pass.

## Handoff or Next-Wave Notes

- Future ranking/model proposals use these standing retrieval and graph-quality baselines rather than bespoke anecdotal checks.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 49 | 1,271,173 |
| review | 2 | 0 |
| **Total** | **51** | **1,271,173** |

<!-- wave:context-efficiency-state {"generation":51,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":49,"content_source_credit":1404190,"derived_artifact_credit":10,"direct_net":1271173,"estimated_tokens_saved":1271173,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1424,"response_debit":132919,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"review":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1586,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38,"response_debit":1548,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":51,"content_source_credit":1404190,"derived_artifact_credit":10,"direct_net":1269587,"estimated_tokens_saved":1271173,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1462,"response_debit":134467,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"wave_id":"1wpih index-quality-evaluation-and-ranking"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
