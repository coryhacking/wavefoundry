# Reranker Upgrade — bge-reranker-base + Score Propagation

Change ID: `12pn3-enh reranker-upgrade`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

Two independent improvements are bundled here because they are both small and both touch the reranker path:

1. **Model upgrade.** `RERANKER_MODEL` is currently `Xenova/ms-marco-MiniLM-L-6-v2`, trained on MS MARCO web-search relevance pairs. It has no code-specific relevance signal. `BAAI/bge-reranker-v2-m3` was the intended target — BAAI's own cross-encoder, better on technical content across BEIR benchmarks — but is not supported by fastembed 0.8.0. `BAAI/bge-reranker-base` is the best available within fastembed 0.8.0: same API, ~25s latency, and an improvement over ms-marco on technical queries. `bge-reranker-v2-m3` remains the natural upgrade once fastembed support catches up. `jina-reranker-v2-base-multilingual` was evaluated but rejected: 1.5–2.5× slower (43–65s vs 25s) with no observed ranking quality improvement.

2. **Score propagation.** `_rerank` currently returns candidates reordered by cross-encoder score but does not update the `score` field in each result dict — the vector similarity score from the dense retrieval pass is left intact. Callers (and the LLM reading results) therefore see a stale relevance signal that doesn't reflect reranking. The reranker score should replace `score` in the output dict.

## Requirements

1. `RERANKER_MODEL` in `indexer.py` is changed to `"BAAI/bge-reranker-v2-m3"`.
2. `setup_index.py` `prewarm_models` pre-warms the new reranker model.
3. `_rerank` in server.py updates `result["score"]` to the cross-encoder score normalized to [0, 1] via min-max normalization: `(s - min_s) / (max_s - min_s)`. When `max_s == min_s` (single result or all identical scores), each result receives `score = 1.0` to avoid division by zero.
4. Existing behavior when the reranker is unavailable (returns `candidates[:top_n]` unchanged) is preserved.
5. `RerankerTests` are updated to assert that returned results have `score` values matching cross-encoder output order.

## Scope

**Problem statement:** The reranker model is generic (MS MARCO web search) and reranker scores are discarded from output, leaving downstream consumers with stale vector similarity scores.

**In scope:**

- Change `RERANKER_MODEL` constant in `indexer.py`
- Update `_rerank` in server.py to write cross-encoder score into result dict
- Update `setup_index.py` model warming
- Update `RerankerTests` score assertions

**Out of scope:**

- Changing reranker architecture (cross-encoder stays)
- Reranker latency optimization

## Acceptance Criteria

- AC-1: `RERANKER_MODEL` is `"BAAI/bge-reranker-base"` in indexer.py. (**Deviation:** original target was `bge-reranker-v2-m3`; not supported by fastembed 0.8.0. `bge-reranker-base` is the best available model within fastembed 0.8.0. Upgrade to `bge-reranker-v2-m3` is the natural next step when fastembed support arrives.)
- AC-2: `setup_index.py` prewarms the new reranker without error.
- AC-3: Results returned from `search_docs` and `search_code` when a reranker is available have `score` values that reflect cross-encoder ranking order (highest-scored result has highest score).
- AC-4: Results returned when reranker is unavailable are unchanged.
- AC-5: Updated `RerankerTests` pass, including: (a) assertions that returned `score` values are in descending order and match cross-encoder ranking, (b) assertion that a single-result rerank returns `score = 1.0`, (c) assertion that results returned via the unavailable-reranker path retain their original `score` values unchanged.

## Tasks

- Update `RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"` in `indexer.py`
- In `_rerank` (server.py): after sorting `zip(scores, candidates)`, compute min-max normalization: `min_s, max_s = min(scores), max(scores)`; `c["score"] = 1.0 if max_s == min_s else float((s - min_s) / (max_s - min_s))` for each result before returning
- Verify `setup_index.py` `_warm_reranker` picks up the new constant dynamically (it calls `_indexer_reranker_model()` — should be automatic)
- Update `RerankerTests` to assert score values are in descending order and match reranker output

## Agent Execution Graph

| Workstream      | Owner              | Depends On | Notes                             |
| --------------- | ------------------ | ---------- | --------------------------------- |
| constant-update | framework-engineer | —          | One line in indexer.py            |
| score-propagate | framework-engineer | —          | _rerank update in server.py       |
| test-update     | framework-engineer | score-propagate | RerankerTests assertions   |

## Serialization Points

- None — all three workstreams touch different locations

## Affected Architecture Docs

N/A — reranker model and score field are implementation details with no boundary impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. `RERANKER_MODEL` changed to `BAAI/bge-reranker-base` (bge-reranker-v2-m3 not supported by fastembed 0.8.0). `_rerank` updated with min-max score normalization; `result["score"]` now reflects cross-encoder output. `RerankerTests` and `MaxPerFileFilterDirectTests` updated. 1326 tests pass. | `run_tests.py` OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | bge-reranker-v2-m3 over ms-marco | Better on technical content; same fastembed API | bge-reranker-base (smaller but older) |
| 2026-05-18 | bge-reranker-base as shipped model (deviation from plan) | bge-reranker-v2-m3 not supported by fastembed 0.8.0. `jina-reranker-v2-base-multilingual` evaluated and rejected: 1.5–2.5× slower (43–65s vs 25s), same observed ranking quality. `bge-reranker-base` is the best available within current fastembed. Upgrade path: bump fastembed → swap to `bge-reranker-v2-m3` → reduce or remove `_SYMBOL_INJECTION_BOOST` in 12q63 if prose-over-code bias improves. | jina-reranker-v2 (rejected: latency); bge-reranker-v2-m3 (blocked: fastembed version) |
| 2026-05-17 | Normalize reranker score to [0,1] | Consistent with vector score range; prevents confusion | Raw logit scores (unbounded) |
| 2026-05-17 | Min-max normalization; score=1.0 when max==min | Guarantees [0,1] range; handles single-result edge case without division by zero | Sigmoid (doesn't guarantee [0,1]); softmax (probability distribution, loses magnitude) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Score normalization changes meaning for callers that threshold on score | Reranker path already returns reordered results; score is informational |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
