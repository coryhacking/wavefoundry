# Code/docs retrieval: quick follow-up evaluation

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Decision

Pursue a bounded evaluation of candidate selection and relevance signaling. Do not ship a smaller reranking window or transplant the memory cutoff based on this probe. There is a measurable CPU cost opportunity, but the current candidate order puts useful material beyond the first five or ten entries, and raw relevance alone still admits unsupported near-topic results.

## Method and boundaries

Twelve coordinator-authored exploratory questions: four code and four docs questions about existing behavior, plus four questions requesting absent capabilities or guarantees. These are development probes, not an independent holdout or measured answer-quality improvement. Code owner hints are navigation expectations, not complete relevance labels.

Invoked the current `code_search_response` and `docs_search_response` handlers with limit five through a fresh `WaveIndex`, without starting server monitors. Captured the 30 pre-rerank candidates and scored the first five and ten separately with the identical CPU model. Subset logits matched the corresponding full-pool logits within 0.0001. Three calls per question; timing summaries below exclude the first call for each question. All public calls were reranked, successful and free of fallback. Completed index epoch 1545 remained unchanged across the run.

CPU model: `cross-encoder/ms-marco-MiniLM-L-6-v2`, `CPUExecutionProvider`, local cached artifacts, offline mode. The ordinary reranker cache was pinned to this CPU instance for the experiment; this is not default GPU qualification. No repository code, index contents, settings or model parameters were changed. The attached MCP runtime remains stale, so the probe used fresh-process public handlers.

`code_search` uses dense/FTS fusion before reranking; `docs_search` uses dense retrieval before reranking. `code_ask` has a separate selection/confidence path and was not evaluated. No summary representation or candidate-diversity ablation was run.

## Measured cost

Median milliseconds, 12 warm measurements per tool:

| Tool | Current public call, 30 candidates | Current reranking stage | Rerank first 10 | Rerank first 5 |
| --- | ---: | ---: | ---: | ---: |
| code_search | 535.4 | 484.1 | 162.7 | 80.4 |
| docs_search | 540.5 | 483.4 | 161.1 | 80.2 |

Ten-candidate reranking cuts this stage's median cost by about 66%; five cuts it by about 83%. Candidate variants did not run through a complete modified public handler, so these are stage savings, not measured end-to-end improvement. Fixed execution order and the small sample also preclude a tail-latency claim.

## Retrieval observations

- Restricting to the first five candidates retains the full-pool top-ranked result for only **3/8** answerable questions; ten retains it for **6/8**. This measures rank-winner retention, not recall or support. Some replacements remain useful, but equivalence is not established.
- On the post-pull setup question, the current framework README's direct operational guidance occurs at candidate 18 and is the full reranker's second result. Both smaller windows omit it. A five-result budget should not imply only five records get considered.
- On the stale-writer question, the leading code result discusses stale codebase-map rendering, and another high result is a historical review report. Neither locates the expected index-compatibility owner. This points to candidate/authority quality, not just excessive reranking cost.
- All four absent-fact queries return results in the current public paths, each with a leading normalized score of 1.0. This is relative normalization, not proof of support or necessarily a search-contract defect.
- Applying memory's raw-logit cutoff of -4 to the full-pool top five empties **2/4** absent-fact responses. It still accepts a local retrieval-evaluation module for a hosted multi-region replication question, and historical benchmark percentages for a universal recall-guarantee question. Neither answers the requested fact.
- The hosted-price query retrieves the architecture statement that no hosted database is required. Although no price exists, that record can help an agent correct the premise. Treating every nonempty negative response as a failure would penalize useful evidence. Score direct answers, premise corrections and merely adjacent material separately.

## Proposed next evaluation

1. Establish independently judged code/docs questions and per-record support labels, including historical-versus-current evidence and false-premise questions. Keep answer support distinct from similarity and navigation value.
2. Compare the current 30-candidate path with ten/twenty candidates selected for symbol/section diversity and current source coverage. Avoid whole-file deduplication that could discard complementary functions.
3. Compare bounded full excerpts against informative representations appropriate to code/docs; memory summaries are not a substitute for source evidence.
4. Test relevance diagnostics or abstention separately from fusion, preserving evidence that corrects a false premise. Do not interpret min-max scores or sigmoid values as calibrated probabilities.
5. Measure the complete public paths, including `code_ask`, with useful-answer retention, all-return support judgments and CPU/provider-specific timing before deciding on implementation.

Raw query/candidate captures were archived during the [evidence cleanup](retrieval-evaluation-evidence-retention.md). The method, measurements, conclusions and limitations above are retained; the original JSON is recoverable from the recorded Git snapshot. Scratch captures were not maintained test infrastructure or a reproducible frozen corpus. This report does not alter the closed memory wave's qualification.
