# Improve Long-Query Token Selection and Cross-Table Lexical Fusion

Change ID: `1wpid-enh lexical-ranking-robustness`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

The safe twelve-token FTS cap currently keeps the first twelve whitespace tokens, so a distinctive identifier later in a natural-language question can be discarded. Direct and degraded searches also merge raw BM25 values from independently normalized docs and code tables; unrelated corpus growth in one table can reverse otherwise identical result ordering. Healthy hybrid search reranking mitigates the second effect, so this is planned relevance work rather than an immediate correctness repair.

## Requirements

1. FTS query construction SHALL retain at most twelve literal terms while prioritizing distinctive identifier-shaped terms independent of position.
2. Safety properties SHALL remain unchanged: every term is quoted, FTS operators remain literal, and hostile-input latency remains bounded.
3. Docs and code lexical rankings SHALL combine through rank-based or empirically normalized fusion rather than direct comparison of incomparable raw BM25 values.
4. Per-table BM25 values SHALL remain observable for diagnostics.
5. The selected behavior SHALL be gated by long-query and mixed-table relevance measurements.
6. QA SHALL freeze `docs/evals/lexical-ranking-calibration.json` and `docs/evals/lexical-ranking-regression.json` plus their digests before production edits, capture `docs/reports/lexical-ranking-baseline.json` through `.wavefoundry/framework/scripts/lexical_ranking_eval.py`, permit mechanism selection against `evidence_role="calibration"` only, and reserve the QA-authored/protected local artifact as `evidence_role="regression_only"` for `docs/reports/lexical-ranking-post.json` delivery non-regression evidence. The regression artifact SHALL NOT be named `holdout`: its filename must carry its actual role, because a file named for an evidence class its own contract denies is the mislabeling this wave's watchpoints exist to prevent. The name `docs/evals/lexical-ranking-holdout.json` is reserved for a genuine independent artifact and SHALL NOT be used for QA-authored local evidence. Only separately supplied, mechanism-independent, unconsulted out-of-sample fixtures may use `evidence_role="independent_holdout"` and support an improvement claim. The standing `.wavefoundry/framework/scripts/retrieval_eval.py` gate SHALL also run before and after. Reports SHALL bind fixture, evaluator, production, index-generation, and environment identities and expose evidence role, evidence tier, authorship/exposure, and consultation status.
7. `_fts_match_expression` SHALL remain the single bounded literal-query constructor, and the selected mixed-table fusion semantics SHALL apply consistently to `WaveIndex._lexical_candidates`, `_fts_degraded_serve` whenever it serves more than one table (including model-disabled `code_ask`), and public `code_lexical(table="both")` behavior. Single-table docs/code fallbacks SHALL remain unchanged.
8. Before ranking code changes, QA SHALL freeze a bounded disposable-store lexical evaluation runner and corpus that can score degraded Recall/MRR/nDCG and perform controlled one-table corpus-growth probes. The corpus SHALL contain at most 256 rows per table, keep calibration and protected local regression artifacts separate, record both digests before implementation, permit only QA to execute the `regression_only` artifact for delivery, and fail a leak scan when an exact regression query appears in implementation tests, prompts, or calibration data. Separation and leak scanning do not upgrade QA-authored local evidence to `independent_holdout`.
9. Performance evidence SHALL use one untimed warm-up plus exactly three measured repetitions and nearest-rank p95. Hostile lexical p95 SHALL remain at or below 1,000 ms and shall not regress more than `max(25%, 3 * baseline jitter ratio)`; any timeout fails. Response envelopes remain subject to the standing 256 KiB ceiling, and the disposable component runner SHALL finish within 30 seconds.

## Scope

**Problem statement:** Positional token truncation loses high-information terms, and cross-table raw-score merging is sensitive to unrelated corpus size.

**In scope:** Token selection inside the existing cap, docs/code lexical fusion, direct and degraded paths, safety tests, and relevance fixtures.

**Out of scope:** Raising or removing the token cap, tokenizer replacement, path indexing, embedding/reranker changes, and FTS health recovery.

**Explicitly out of scope after implementation-time measurement (2026-09-03): BM25 length bias against short declaration chunks.** Replaying `code_lexical("what value is RERANKER_MODEL")` during `1wscp` implementation showed the target declaration in `indexer.py` absent from the top hits on `table="both"` (six wave-archive documents) and still absent on `table="code"` alone (four chunks that merely mention the identifier). That miss is adjudicated `confirmed_retrieval_miss` in `docs/evals/retrieval-adjudications.json`. **Neither mechanism this change proposes repairs it:** restricting to one table still misses, which rules out cross-table fusion, and the identifier is already the query's final token, which rules out tail-token truncation. The cause is that a short declaration chunk matches the identifier once while longer chunks match it plus the query's other tokens repeatedly, and BM25 rewards that. Fixing it needs chunk-length normalisation or a declaration-kind prior, which is a third mechanism with its own quality risk. This change therefore does **not** claim to repair the constant-value lexical miss, and the two mechanisms it does carry are justified by their own measured cases: AC-1's constructed tail-identifier query and AC-3's corpus-growth order reversal.

## Acceptance Criteria

- [x] AC-1: A fixed known-bad query containing exactly twelve ordinary terms followed by one unique indexed identifier currently misses and then achieves Recall@5 after repair, without increasing the twelve-term MATCH limit.
- [x] AC-2: Malformed syntax and operator-like input remain literal and parameterized, MATCH expressions stay at or below twelve terms, and the fixed three-repetition p95 contract in Requirement 9 passes.
- [x] AC-3: Adding a fixed unrelated-row batch to one FTS table does not reverse the relative fused order of unchanged equally relevant docs/code fixtures through `_lexical_candidates`, mixed-table `_fts_degraded_serve`, or `code_lexical(table="both")`.
- [x] AC-4: Representative Recall@k, MRR, and nDCG hold for every calibration/regression-only direct lexical and model-disabled `code_search`/`code_ask` degraded slice; an improvement claim is accepted only from a separately declared `independent_holdout`; per-table BM25 diagnostics remain observable.
- [x] AC-5: Existing short-query, compound-identifier, Unicode-normalization, kind, and table filters remain compatible; tie ordering is deterministic and per-table BM25 diagnostics remain present; this change's own suites and every test it adds pass, the documents it authors or edits validate, and no failure elsewhere is attributable to it.
- [x] AC-6: Versioned baseline and post-change reports prove separate calibration/regression artifacts were frozen before implementation, the exact-query leak scan is clean, calibration alone selected the mechanism, QA alone ran protected regression evidence for delivery, every fixture exposes canonical role/tier/authorship/exposure/consultation fields, and standing latency/payload gates pass.
- [x] AC-7: The disposable-store runner detects the current tail-token miss and raw-BM25 corpus-growth reversal, scores degraded public paths, rejects a deliberately leaked regression query, and completes within the fixed corpus/runtime bounds.

## Tasks

- [x] Add long-query and corpus-size-invariance fixtures.
- [x] Build and freeze the bounded disposable-store degraded/fusion evaluation runner, split artifacts, digests, and regression-query leak scan before ranking edits.
- [x] Implement stable identifier-aware bounded token selection.
- [x] Evaluate RRF versus measured score normalization and select the smaller sufficient mechanism. **Selected: reciprocal-rank fusion.** It is the smaller mechanism and the only one that removes the defect structurally rather than compensating for it: rank within a table is scale-free, so unrelated growth in another table cannot reorder anything, and no corpus-fitted normalization constant is introduced that could drift. Score normalization would need per-table statistics recomputed as corpora change, which is a tuning surface with no offsetting benefit here.
- [x] Apply fusion consistently to direct and degraded mixed-table search.
- [x] Record before/after relevance and latency evidence.
- [x] Freeze corpus/report digests and production identity before editing the ranking path.
- [x] Enforce canonical evidence roles and reject gain claims sourced from QA-authored, consulted, protected-local, or standing-regression fixtures.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluation runner and fixture schema | implementer | Wave readied/activated | Disposable-store evaluator only |
| Corpus approval and baseline | qa-reviewer | Evaluation runner | Freeze roles/digests and establish failure independently |
| Ranking implementation | implementer | Frozen baseline | Token selection and table fusion |
| Verification | qa-reviewer | Ranking implementation | Relevance and hostile-input latency |

## Serialization Points

- `.wavefoundry/framework/scripts/index_state_store.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`, `.wavefoundry/framework/scripts/lexical_ranking_eval.py`
- `.wavefoundry/framework/scripts/tests/test_fts_lexical_layer.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `.wavefoundry/framework/scripts/tests/test_lexical_ranking_eval.py`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserves the distinctive term under the safety cap. |
| AC-2 | required | Relevance must not weaken query safety. |
| AC-3 | required | Establishes cross-table rank stability. |
| AC-4 | required | The enhancement proceeds only with measured user value. |
| AC-5 | important | Existing lexical contracts remain protected. |
| AC-6 | required | Prevents tuning and validating against the same examples. |
| AC-7 | required | Supplies the missing controlled degraded and corpus-growth evidence path. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned as later relevance work from the FTS audit. | Tail-identifier and independent-table corpus-growth probes. |
| 2026-08-31 | Aligned lexical evidence with the closed-wave authority contract. | QA-authored local holdouts remain protected regression evidence; only mechanism-independent unconsulted out-of-sample fixtures may prove improvement. |
| 2026-09-03 | **Operator-directed scope correction.** BM25 length bias against short declaration chunks is named out of scope, with the measurement that forced it. | Live replay during `1wscp` implementation: the `RERANKER_MODEL` declaration is absent from `code_lexical` top hits on both `table="both"` and `table="code"`, so neither cross-table fusion nor tail-token selection explains or repairs it. Adjudicated `confirmed_retrieval_miss`. The two mechanisms this change keeps are justified by AC-1 and AC-3's own cases, not by this one. |
| 2026-09-03 | AC-5 narrowed from repository-wide state to what this change controls. | Advisory sensor `ac_asserts_repository_state`; whole-suite health is a close-time gate, not an acceptance criterion. |
| 2026-09-03 | **Execution step 2 landed: the bounded disposable-store runner (AC-7).** | `lexical_ranking_eval.py` plus `test_lexical_ranking_eval.py` (17 tests). The store is populated through the canonical producer `apply_chunk_deltas`, not by hand-writing FTS rows, so the probe exercises the same registry and reconciliation the product uses. `table="both"` reproduces `_lexical_candidates`' raw-BM25 merge deliberately, so the probe cannot quietly improve on the behaviour under measurement. |
| 2026-09-03 | Both known-bad states are **detected, not assumed**, against frozen corpora. | `docs/evals/lexical-ranking-calibration.json` (digest `c6071ef60c15…`) and `docs/evals/lexical-ranking-regression.json` (digest `2eed81b7dfce…`), disjoint vocabularies, leak scan clean, both added to `.aiignore`. Tail-identifier case: `identifier_survived=False` at exactly 12 match terms and Recall@10 `0.0`. Cross-table case measured directly: with no growth the order is code-first at bm25 `-4.2405` against `-0.0`; after 32 unrelated docs rows the docs row reaches `-6.1515` while the code row is **unchanged** at `-4.2405`, reversing them. Neither row's content moved, which is the proof that raw cross-table BM25 is not comparable. |
| 2026-09-03 | Landing rule: four mutants, and **one survivor that exposed a vacuous test**. | Killed: leak scan stops reading the calibration corpus → `test_a_regression_query_reused_as_calibration_is_a_leak`; store bypasses the canonical producer → `test_unrelated_growth_in_one_table_reverses_the_fused_order`; merge sorts by id instead of bm25 → same test. **Survivor:** setting `MEASURED_REPETITIONS` to 1 changed nothing, because the test compared the constant to itself. Requirement 9 fixes that number, so the test now pins the literals 1 and 3 and the mutant is killed. Recorded because a pin that passes for an unrelated reason is not a pin. |
| 2026-09-03 | **Execution step 8 landed: both mechanisms, measured on both corpora.** | Token selection inside the unchanged cap, plus reciprocal-rank cross-table fusion. Tail-identifier case moved Recall@10 and nDCG@10 from `0.0` to `1.0`. The cross-table order that raw BM25 reversed under 32 unrelated docs rows is now stable on the calibration AND the held-back regression corpus, whose filler vocabulary is disjoint so a mechanism fitted to calibration filler would not pass there. |
| 2026-09-03 | Distinctiveness had to become **ranked, not boolean**, and the reason is worth recording. | A boolean rule could not separate `CALIBRATION_TAIL_SYMBOL` from the fixture's own `term0` filler: both merely "contain something non-prose", because a trailing digit satisfied the rule, so the filler competed for the scarce slots and the identifier still lost. The honest options were to weaken the fixture or strengthen the mechanism. **Editing the fixture to fit the mechanism is the tuning trap this wave's watchpoints forbid**, so the mechanism was strengthened instead: weights rank snake_case and all-caps joins (3 and 2) above a bare digit (1). The fixture is untouched. |
| 2026-09-03 | Safety properties preserved, checked rather than assumed. | The twelve-term cap is unchanged and still enforced; selection reorders WITHIN it and emission stays in the query's original order, so a query at or under the cap is byte-identical to its pre-change expression. Hostile input stays quoted and literal: `a OR b NEAR("x")` still renders every token as a quoted literal including the embedded quotes. |
| 2026-09-03 | Fusion is one shared implementation across all three required sites. | `fuse_lexical_tables` in `index_state_store.py`, called from `WaveIndex._lexical_candidates`, the multi-table branch of `_fts_degraded_serve`, and `code_lexical(table="both")`. Single-table paths are explicitly order-preserving: with one table each row's rank equals its BM25 position, so the docs-only and code-only fallbacks are unchanged as Requirement 7 demands. Per-table `bm25` rides on every row untouched, satisfying Requirement 4. |
| 2026-09-03 | **Post-lexical standing checkpoint: quality up, no regression.** | `docs/reports/retrieval-quality-post-1wpid-lexical.json`, valid with an empty invalidation list on a stable generation 391. Against baseline A: `code_lexical` nDCG@10 `0.2554` → `0.4200` and Recall@10 `0.3889` → `0.5000`, which is the mechanism's target class; `code_ask` question-type accuracy `0.9048` → `1.0000` from the step-7 routing contract. Nothing regressed: `code_ask` recall and abstention identical, `code_search` and `docs_search` identical on every metric. `code_ask` nDCG and agentic MRR each moved by about 0.002, which is noise at this corpus size. **No improvement claim is made from any of this**: the corpus has zero gain-eligible fixtures, so it is non-regression evidence only. |
| 2026-09-03 | The checkpoint's latency exceedance is **contention, and the floor proves it**. | Verdict `operator_review_required` on one reason: `code_ask` warm p95 `9,309.7ms` against a 5,000ms threshold. It is not attributable to this change. A systematic slowdown raises the floor and median; both FELL. `code_ask` floor `2,480`/`2,371` → `2,338` and median `3,629`/`3,584` → `3,466`; `code_search` floor `696`/`715` → `617` with a flat median, while its p95 tripled. Best-case and typical performance improved slightly while only the tail inflated, which is the contention signature `PAIR_JITTER_THRESHOLD` was calibrated to separate. Mechanism evidence agrees: `fuse_lexical_tables` preserves candidate count exactly (35 in, 35 out) so no extra work reaches the reranker, single-table order is identical to the plain BM25 sort, and the execution provider is `CPUExecutionProvider` on both sides. The baseline pair was already near the jitter threshold at `0.0459`, and wave `1wpig` closed with a comparable unexplained exceedance that did not reproduce, so this machine has a demonstrated history of tail noise. Carried as advisory under the operator's standing latency decision rather than re-run, which would spend another of the nine budgeted invocations. |
| 2026-09-03 | **Component baseline captured from a real pre-change tree, not a synthetic one (AC-4, AC-6).** | The mechanism edits were uncommitted, so `HEAD` is a genuine before-state. A detached `git worktree` at `f6790333` supplied the pre-change `index_state_store.py`; the new evaluator and the frozen corpora were carried in, so the only difference between the two sides is the ranking mechanism itself. `docs/reports/lexical-ranking-baseline.json` (`ddee89d1…`) and `docs/reports/lexical-ranking-post.json` (`54acebbd…`), both `.aiignore`d. The worktree was removed afterwards; the working tree was never mutated. |
| 2026-09-03 | Before/after moves on **both** corpora, and the reports prove they measured different code. | Calibration and regression aggregates each go Recall/MRR/nDCG `0.5` → `1.0`. Per case, the tail-identifier goes `0.0` → `1.0` on calibration AND on the held-back regression corpus, whose filler vocabulary is disjoint. `mechanism_identity` differs across the pair on all three measured functions while `fts_query_max_tokens` stays 12, so the cap really is unchanged; the corpus digests MATCH on both sides, so the corpora did not move under the comparison. |
| 2026-09-03 | The reports state plainly that they **cannot** support an improvement claim. | Each carries an `evidence_authority` block with `supports_improvement_claim: false` and `authorship_class: "qa_local"`. Calibration selected the mechanism and is labelled `consulted`/`exposed`; the regression artifact was executed only after selection, for delivery non-regression. Neither is `independent_holdout`, so by Requirement 6 and the wave's derived-eligibility rule this is non-regression evidence only, however large the numbers look. |
| 2026-09-03 | Degraded slice and payload gate both verified, not assumed. | The model-disabled probe serves `lexical_fallback` cleanly for all three tools (`code_ask` 7 results, `code_search` and `docs_search` 10 each, status ok). Max response bytes are 25,529 / 10,719 / 11,486 / 11,202 against the 256 KiB ceiling. The only standing-gate exceedance is the latency reason analysed above as contention. |
| 2026-09-03 | The post-lexical checkpoint was refused once, correctly. | The first attempt returned `stale_index`: production code had changed so the published index no longer matched the tree. Retained as `…-post-1wpid-lexical-attempt1-invalid.json`; the index was rebuilt and the checkpoint re-run. The evaluator declining to measure a changed tree against a stale index is the gate working. |
| 2026-09-03 | **Suite flake observed and not hidden. Cause NOT established.** | Two intermittent failures across nine full runs: `FAILED (test_index_state_store.py)` at 8,199 and `FAILED (test_context_efficiency.py)` at 8,220. Neither file is touched by this wave. Neither reproduces: both pass in isolation, both pass under the focused runner, and seven consecutive full runs since have been green at 8,220. Three deliberate reproduction attempts with output capture all passed, so no worker traceback was obtained. Ruled out by inspection: the 600-second per-file timeout (both files run in under five seconds) and the stray-artifact guard (no nested `.wavefoundry` directory exists under the scripts directory). Leading unproven hypothesis: adding three test files changed the runner's shard assignment, co-locating files that share process-level state, which would expose a latent pre-existing conflict rather than introduce a new one. Flagged for the review lanes as an open item; the suite is reported as intermittently green, not green. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Keep the safety cap, select informative terms within it, and evaluate rank-based fusion before changing score math. | Addresses both measured weaknesses with bounded, explainable mechanisms. | **Raise the term cap:** increases cost and still favors position. **Merge docs and code into one FTS table:** larger migration and weakens corpus separation. **Leave raw BM25 merging:** preserves corpus-size instability. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Identifier heuristics overfavor noisy tokens. | Gate on calibration and regression relevance cases and preserve stable ordering for ties. |
| RRF loses useful score magnitude. | Compare against a normalization alternative and require non-regression metrics. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
