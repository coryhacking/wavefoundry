# Semantic Search: Combined Retrieval with Cross-Encoder Reranker

Change ID: `12mha-enh semantic-search-reranker`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

The current search pipeline has two problems. First, cosine similarity is a weak final ranker — it scores chunks independently of query intent and promotes topically-adjacent chunks rather than directly-answering ones. Second, `docs_search` and `code_search` are fully siloed: a query that needs both (e.g. "where is X documented and where is it implemented?") requires two calls and gets no cross-index ranking. A cross-encoder reranker (BAAI/bge-reranker-base) fixes both at once: it scores `(query, text)` pairs using full attention over both, and because it's score-blind to the source index, it naturally normalizes across a combined docs+code candidate pool. The two indices stay separate (no rebuild required); candidates are pooled at query time and the reranker is the final arbiter.

## Requirements

1. `RERANKER_MODEL = "BAAI/bge-reranker-base"` must be added to `indexer.py` alongside `DOCS_MODEL` and `CODE_MODEL`.
2. `VECTOR_TOP_K = 40` must be defined as a constant in `server.py` — the number of candidates fetched from each index before pooling and reranking.
3. The default `limit` for `docs_search_response` and `code_search_response` must change from `5` to `7`. The `top_n` default on `search_docs()` and `search_code()` must change from `5` to `7`. The new `search_combined()` method must define its default `top_n` as `7`.
4. `WaveIndex` must expose a `_get_reranker()` method that lazy-loads `fastembed.rerank.cross_encoder.TextCrossEncoder` with `RERANKER_MODEL` in offline mode, following the same pattern as `_get_embedder()`. Returns `None` on any failure — no exception propagated.
5. `WaveIndex` must expose a `_rerank(query, candidates, top_n)` method that scores each `(query, candidate["text"])` pair and returns the top `top_n` sorted by reranker score descending.
6. `WaveIndex` must expose a `search_combined(query, top_n)` method that: (a) fetches up to `VECTOR_TOP_K` candidates from both the docs and code indices, (b) pools all candidates, (c) reranks the combined pool, (d) returns the top `top_n`. When the reranker is unavailable, fall back to cosine scores merged via Reciprocal Rank Fusion (RRF).
7. `code_ask_response` must use `search_combined()` as its primary retrieval pass instead of separate `search_docs` + `search_code` calls.
8. `search_docs()` and `search_code()` on `WaveIndex` must apply the expand→rerank→slice pipeline within their own index: fetch `max(top_n, VECTOR_TOP_K)` candidates from `_cosine_search()`, rerank, return top `top_n`. When the reranker is unavailable, fall back silently to cosine-ranked results.
9. `docs_search_response` and `code_search_response` must include `"reranked": true/false` in the response data reflecting whether the reranker ran.
10. `setup_index.py` must download and verify the reranker model unconditionally (not gated on `--include-code`) as part of the standard `prewarm_models()` step. This requires: (a) a `_warm_reranker(model_name)` function that instantiates `TextCrossEncoder` and runs a test pair through it; (b) `RERANKER_MODEL` read from `indexer.py` via a dedicated `_indexer_reranker_model()` function (separate from `_indexer_models()` which is semantically for embedding models). The reranker is treated as a required model, not optional.
11. `search_combined` responses must include `"reranked": true` when the reranker ran, `"reranked": false` when falling back to RRF cosine merge.

## Scope

**Problem statement:** Cosine search is siloed (docs or code, not both) and is a weak final ranker. Relevant chunks from the other index are invisible, and even within one index the top-N by cosine often aren't the most answering chunks.

**In scope:**

- `RERANKER_MODEL` constant in `indexer.py`
- `VECTOR_TOP_K` constant in `server.py`
- `_get_reranker()` and `_rerank()` on `WaveIndex`
- `search_combined()` on `WaveIndex` — combined docs+code retrieval with reranking
- RRF fallback merge in `search_combined()` when reranker unavailable
- `code_ask_response` updated to use `search_combined()`
- Expand→rerank→slice in `search_docs()` and `search_code()` single-index methods
- `"reranked"` field in `docs_search_response`, `code_search_response`, and `search_combined` responses
- `setup_index.py` unconditional reranker download (`_warm_reranker()` + `prewarm_models()` update)
- Tests in `test_server_tools.py`

**Out of scope:**

- Exposing `search_combined` as a new public MCP tool — not this wave
- `VECTOR_TOP_K` as a caller parameter
- Reranker model selection via `workflow-config.json`

## Acceptance Criteria

- AC-1: `code_ask` retrieval uses `search_combined()` — results draw from both docs and code indices in a single ranked list.
- AC-2: `docs_search` and `code_search` responses include `"reranked": true` when the cross-encoder ran on their single-index result set.
- AC-3: `search_combined()` response includes `"reranked": true` when the cross-encoder ran across the pooled docs+code candidates.
- AC-4: When the reranker model is not cached, all three paths complete successfully with no exception raised: `docs_search` and `code_search` return cosine-ranked results with `"reranked": false`; `search_combined` returns RRF-merged results with `"reranked": false`.
- AC-5: `setup_index.py` downloads and verifies `BAAI/bge-reranker-base` unconditionally during `prewarm_models()` — running `setup_index.py` without `--include-code` still caches the reranker.
- AC-6: Final result count from all search paths does not exceed `top_n`.
- AC-7: `docs_search` and `code_search` MCP tools return at most 7 results when the caller does not specify `limit`.

## Tasks

- [ ] Add `RERANKER_MODEL = "BAAI/bge-reranker-base"` to `indexer.py` after `CODE_MODEL` (line 32)
- [ ] Change `limit: int = 5` to `limit: int = 7` in `docs_search_response` (server.py:2094) and `code_search_response` (server.py:2190); change `top_n: int = 5` to `top_n: int = 7` in `search_docs`, `search_code`, and `search_combined`
- [ ] Add `VECTOR_TOP_K = 40` constant to `server.py` (near top of `WaveIndex` or as module-level constant)
- [ ] Add `self._reranker = None` to `WaveIndex.__init__`
- [ ] Verify `TextCrossEncoder.__init__` accepts `local_files_only` kwarg in the installed fastembed version before coding (check fastembed changelog or source; fall back to env-var approach used by `_get_embedder()` if kwarg is absent)
- [ ] Add `_get_reranker()` to `WaveIndex`: lazy-load `TextCrossEncoder(model_name=RERANKER_MODEL, local_files_only=True)` inside `_offline_model_env()`; catch `ImportError` and all model errors; cache in `self._reranker`; return `None` on failure
- [ ] Add `_rerank(query, candidates, top_n)` to `WaveIndex`: call `reranker.rerank(query, [c["text"] for c in candidates])` once with the full list (batched, not per-document); zip scores back; sort descending; return top `top_n`
- [ ] Add `_rrf_merge(ranked_lists, top_n, k=60)` to `WaveIndex`: standard RRF formula `score = Σ 1/(k + rank)`; dedup by chunk id; return top `top_n` — used as reranker fallback
- [ ] Modify `search_docs()`: expand cosine fetch to `max(top_n, VECTOR_TOP_K)`; attempt rerank; slice to `top_n`; return `(results, reranked: bool)`
- [ ] Modify `search_code()`: expand cosine fetch to `max(n, VECTOR_TOP_K)` (where `n` already accounts for language/max_per_file over-fetch); apply rerank after language/max_per_file filtering; slice to `top_n`; return `(results, reranked: bool)`
- [ ] Update callers of `search_docs()` and `search_code()` to unpack the new `(results, reranked)` tuple return: `docs_search_response` (server.py:2119), `code_search_response` (server.py:2226 and 2229). Lines 6832/6838 are replaced entirely by `search_combined` and do not need tuple-unpack updates.
- [ ] Update `docs_search_response()` and `code_search_response()` to unpack the `reranked` flag and include it in the response data
- [ ] Add `search_combined(query, top_n)` to `WaveIndex`: fetch `VECTOR_TOP_K` from `_cosine_search` on both docs and code indices; pool; attempt rerank; fall back to RRF on failure; return `(results, reranked: bool)`
- [ ] Update `code_ask_response` (server.py:6838) to call `index.search_combined()` instead of separate `search_docs` + `search_code` calls; propagate `reranked` flag into response. Note: the `max_per_file=2` constraint from the old `search_code` call is intentionally dropped — the reranker handles result diversity. The conditional keyword pass (server.py:~6860, triggered when `len(citations) < 2`) is independent and untouched.
- [ ] Add `_warm_reranker(model_name)` to `setup_index.py`: instantiate `TextCrossEncoder(model_name, local_files_only=False)` to download; verify with `_offline_env()` + `local_files_only=True`; run a test pair through `reranker.rerank(query, [doc])` to confirm it works
- [ ] Add `_indexer_reranker_model()` to `setup_index.py` (separate from `_indexer_models()`, which is for embedding models only) to read `RERANKER_MODEL` from `indexer.py` via the existing dynamic import pattern
- [ ] Update `prewarm_models()` to call `_warm_reranker(reranker_model)` unconditionally after the embedding model loop
- [ ] Add tests: `docs_search` reranked when available; `code_search` reranked when available; combined results draw from both indices; RRF fallback when unavailable; `reranked` flag correct in all three paths; result count ≤ top_n in all paths; lexical fallback path unaffected

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| indexer-constant | implementer | — | indexer.py only; framework_edit_allowed gate |
| wave-index-reranker | implementer | indexer-constant | `_get_reranker`, `_rerank`, `_rrf_merge`, `search_docs`, `search_code`, `search_combined` in server.py |
| single-index-responses | implementer | wave-index-reranker | `docs_search_response`, `code_search_response` — unpack `reranked` flag |
| code-ask-update | implementer | wave-index-reranker | Update `code_ask_response` to use `search_combined` |
| setup-prewarm | implementer | indexer-constant | setup_index.py reranker prewarm |
| tests | implementer | single-index-responses, code-ask-update | test_server_tools.py |

## Serialization Points

- `framework_edit_allowed` gate required for `indexer.py`, `server.py`, `setup_index.py`, and `test_server_tools.py`.
- `RERANKER_MODEL` must land in `indexer.py` before `server.py` work begins (server reads it via `_indexer_constant()`).

## Affected Architecture Docs

`docs/architecture/search-architecture.md` and `docs/architecture/embedding-model.md` — both describe the current single-stage siloed pipeline; need a combined-retrieval + reranker section after implementation is verified.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core fix — cross-index retrieval is the primary recall improvement |
| AC-2 | required | Observable proof the reranker ran on single-index paths |
| AC-3 | required | Observable proof the reranker ran on the combined path |
| AC-4 | required | Graceful fallback non-negotiable — offline environments must still search |
| AC-5 | required | Without prewarm the model won't be cached and AC-4 always fires |
| AC-6 | required | Result count invariant — callers rely on `top_n` being respected |
| AC-7 | required | Default limit change is a behavioral contract; agents that omit `limit` must get 7 results, not 5 |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped; design revised from per-index reranking to combined retrieval | Search pipeline traced: `_cosine_search` (server.py:583), `search_docs` (605), `search_code` (623), `code_ask_response` (6838), `docs_search_response` (2094), `code_search_response` (2190); DOCS_MODEL/CODE_MODEL in indexer.py:31-32 |
| 2026-05-14 | Wave Council readiness review completed; 5 blocking findings resolved | (1) Duplicate requirement 9 fixed; (2) `_indexer_reranker_model()` separation clarified; (3) AC-7 added for default limit change; (4) AC-4 tightened to specify fallback per path; (5) caller blast radius inventoried in tasks (server.py:2119, 2226, 2229) |
| 2026-05-14 | Red-team interrogation completed; 4 additional issues addressed | `TextCrossEncoder local_files_only` API verification added as pre-coding task; batched inference clarified in `_rerank` task; RRF empty-list edge case added to risks; `max_per_file=2` behavioral change in `code_ask` documented in task note |
| 2026-05-14 | Wave Council readiness review — 1 blocking finding resolved | Requirement 3 wording fixed: `search_combined()` is new, so its default is defined as 7 (not changed from 5) |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Keep two separate indices, merge candidates at query time | No rebuild required; each index can remain specialized; reranker normalizes across pools naturally; code chunks don't drown doc chunks | Single unified index — requires rebuild, code chunks dominate, loses selective querying |
| 2026-05-14 | RRF as reranker fallback | RRF handles non-comparable score distributions between indices better than score averaging; well-established in hybrid search | Simple score merge — docs/code cosine scores have different distributions |
| 2026-05-14 | `VECTOR_TOP_K = 40` per index (80 total candidates) | 40 per index gives each side fair representation; 80 total is manageable for cross-encoder inference | Single pool of 40 — underrepresents whichever index has fewer matching chunks |
| 2026-05-14 | `search_combined` not exposed as MCP tool yet | `code_ask` is the primary beneficiary; expose as standalone tool in a follow-on wave once quality is validated | New `search` MCP tool now — premature before validating combined retrieval quality |
| 2026-05-14 | Default `top_n`/`limit` raised from 5 to 7 | Reranker precision makes each result slot more valuable; 7 gives agents a slightly larger buffer without meaningfully increasing noise; still well under the 20 ceiling | Keep at 5 — sufficient but leaves agents with no margin; raise to 10 — too much tail noise |
| 2026-05-14 | Reranker downloaded unconditionally in setup_index.py | Same guarantee as embedding models — any user who ran setup has it cached; RRF fallback is an edge-case safety net, not the expected path | Optional/gated download — would mean RRF fires routinely for users who skipped `--include-code` |
| 2026-05-14 | Silent RRF fallback at query time if reranker still not cached | Covers edge cases (running from source before setup, distribution lag) without breaking search | Error on missing reranker — too disruptive |
| 2026-05-14 | `fastembed.rerank.cross_encoder.TextCrossEncoder` | Already in the fastembed dependency; no new package required | `FlagEmbedding` cross-encoder — new dependency |

## Risks

| Risk | Mitigation |
|------|------------|
| `fastembed.rerank` unavailable in older fastembed versions | Guard import with try/except; treat as fallback condition |
| Cross-encoder latency (~50–200ms for 80 candidates) | Acceptable for interactive use; document in arch docs |
| Docs and code chunks have very different text lengths | bge-reranker-base handles variable length well up to 512 tokens; long code chunks truncated naturally |
| RRF receives an empty ranked list (one index returns zero results) | `_rrf_merge` must handle empty input lists gracefully — skip empty lists in the rank accumulation loop, not a hard error |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
