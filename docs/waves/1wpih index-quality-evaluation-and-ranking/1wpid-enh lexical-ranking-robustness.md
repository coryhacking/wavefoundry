# Improve Long-Query Token Selection and Cross-Table Lexical Fusion

Change ID: `1wpid-enh lexical-ranking-robustness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

The safe twelve-token FTS cap currently keeps the first twelve whitespace tokens, so a distinctive identifier later in a natural-language question can be discarded. Direct and degraded searches also merge raw BM25 values from independently normalized docs and code tables; unrelated corpus growth in one table can reverse otherwise identical result ordering. Healthy hybrid search reranking mitigates the second effect, so this is planned relevance work rather than an immediate correctness repair.

## Requirements

1. FTS query construction SHALL retain at most twelve literal terms while prioritizing distinctive identifier-shaped terms independent of position.
2. Safety properties SHALL remain unchanged: every term is quoted, FTS operators remain literal, and hostile-input latency remains bounded.
3. Docs and code lexical rankings SHALL combine through rank-based or empirically normalized fusion rather than direct comparison of incomparable raw BM25 values.
4. Per-table BM25 values SHALL remain observable for diagnostics.
5. The selected behavior SHALL be gated by long-query and mixed-table relevance measurements.
6. QA SHALL freeze `docs/evals/lexical-ranking-calibration.json` and `docs/evals/lexical-ranking-holdout.json` plus their digests before production edits, capture `docs/reports/lexical-ranking-baseline.json` through `.wavefoundry/framework/scripts/lexical_ranking_eval.py`, permit mechanism selection against calibration only, and reserve the untouched holdout for `docs/reports/lexical-ranking-post.json` delivery evidence. The standing `.wavefoundry/framework/scripts/retrieval_eval.py` gate SHALL also run before and after. Reports SHALL bind fixture, evaluator, production, index-generation, and environment identities.
7. `_fts_match_expression` SHALL remain the single bounded literal-query constructor, and the selected mixed-table fusion semantics SHALL apply consistently to `WaveIndex._lexical_candidates`, `_fts_degraded_serve` whenever it serves more than one table (including model-disabled `code_ask`), and public `code_lexical(table="both")` behavior. Single-table docs/code fallbacks SHALL remain unchanged.
8. Before ranking code changes, QA SHALL freeze a bounded disposable-store lexical evaluation runner and corpus that can score degraded Recall/MRR/nDCG and perform controlled one-table corpus-growth probes. The corpus SHALL contain at most 256 rows per table, keep calibration and holdout in separate artifacts, record both digests before implementation, permit only QA to execute holdout for delivery, and fail a leak scan when an exact holdout query appears in implementation tests, prompts, or calibration data.
9. Performance evidence SHALL use one untimed warm-up plus exactly three measured repetitions and nearest-rank p95. Hostile lexical p95 SHALL remain at or below 1,000 ms and shall not regress more than `max(25%, 3 * baseline jitter ratio)`; any timeout fails. Response envelopes remain subject to the standing 256 KiB ceiling, and the disposable component runner SHALL finish within 30 seconds.

## Scope

**Problem statement:** Positional token truncation loses high-information terms, and cross-table raw-score merging is sensitive to unrelated corpus size.

**In scope:** Token selection inside the existing cap, docs/code lexical fusion, direct and degraded paths, safety tests, and relevance fixtures.

**Out of scope:** Raising or removing the token cap, tokenizer replacement, path indexing, embedding/reranker changes, and FTS health recovery.

## Acceptance Criteria

- [ ] AC-1: A fixed known-bad query containing exactly twelve ordinary terms followed by one unique indexed identifier currently misses and then achieves Recall@5 after repair, without increasing the twelve-term MATCH limit.
- [ ] AC-2: Malformed syntax and operator-like input remain literal and parameterized, MATCH expressions stay at or below twelve terms, and the fixed three-repetition p95 contract in Requirement 9 passes.
- [ ] AC-3: Adding a fixed unrelated-row batch to one FTS table does not reverse the relative fused order of unchanged equally relevant docs/code fixtures through `_lexical_candidates`, mixed-table `_fts_degraded_serve`, or `code_lexical(table="both")`.
- [ ] AC-4: Representative Recall@k, MRR, and nDCG hold or improve for direct lexical and model-disabled `code_search`/`code_ask` degraded retrieval; per-table BM25 diagnostics remain observable.
- [ ] AC-5: Existing short-query, compound-identifier, Unicode-normalization, kind, and table filters remain compatible; tie ordering is deterministic and per-table BM25 diagnostics remain present; full tests pass.
- [ ] AC-6: Versioned baseline and post-change reports prove separate calibration/holdout artifacts were frozen before implementation, the exact-query leak scan is clean, calibration alone selected the mechanism, QA alone ran untouched holdout for delivery, and standing latency/payload gates pass.
- [ ] AC-7: The disposable-store runner detects the current tail-token miss and raw-BM25 corpus-growth reversal, scores degraded public paths, rejects a deliberately leaked holdout query, and completes within the fixed corpus/runtime bounds.

## Tasks

- [ ] Add long-query and corpus-size-invariance fixtures.
- [ ] Build and freeze the bounded disposable-store degraded/fusion evaluation runner, split artifacts, digests, and holdout leak scan before ranking edits.
- [ ] Implement stable identifier-aware bounded token selection.
- [ ] Evaluate RRF versus measured score normalization and select the smaller sufficient mechanism.
- [ ] Apply fusion consistently to direct and degraded mixed-table search.
- [ ] Record before/after relevance and latency evidence.
- [ ] Freeze corpus/report digests and production identity before editing the ranking path.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluation fixtures | qa-reviewer | — | Establish failure and baseline |
| Ranking implementation | implementer | Evaluation fixtures | Token selection and table fusion |
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

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Keep the safety cap, select informative terms within it, and evaluate rank-based fusion before changing score math. | Addresses both measured weaknesses with bounded, explainable mechanisms. | **Raise the term cap:** increases cost and still favors position. **Merge docs and code into one FTS table:** larger migration and weakens corpus separation. **Leave raw BM25 merging:** preserves corpus-size instability. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Identifier heuristics overfavor noisy tokens. | Gate on calibration/holdout relevance cases and preserve stable ordering for ties. |
| RRF loses useful score magnitude. | Compare against a normalization alternative and require non-regression metrics. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
