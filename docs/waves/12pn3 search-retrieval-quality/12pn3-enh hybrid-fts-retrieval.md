# Hybrid FTS + Dense Retrieval

Change ID: `12pn3-enh hybrid-fts-retrieval`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

The current query path is pure dense (vector) retrieval, with lexical search only as a fallback when the semantic index is unavailable. Code queries are frequently exact-match dominated — identifiers, error messages, constant names — where BM25/FTS consistently outperforms dense retrieval. LanceDB ships a Tantivy-based full-text search engine; calling `table.create_fts_index(["text", "path", "section"])` at build time enables O(log n) keyword search with no additional dependencies. Running FTS and dense in parallel on every query, then fusing with the existing `_rrf_merge`, is expected to yield 5–10% recall improvement on code search and eliminates the full-scan O(n) penalty on the current lexical fallback.

## Requirements

1. After `_build_lance_tables` creates each Lance table, an FTS index is created on columns `["text", "path", "section", "tags"]` for both `docs` and `code` tables.
2. After `_lance_incremental_write` completes an add/delete cycle, the FTS index is explicitly refreshed by calling `_create_fts_index(table, table_name, replace=True)` after the add and optimize steps. LanceDB's `table.optimize()` compacts data fragments but does NOT rebuild FTS indexes; without an explicit refresh, FTS results will be stale while dense results are current.
3. `search_docs` runs FTS and dense in parallel against each available table and fuses results with `_rrf_merge` before reranking.
4. `search_code` follows the same pattern.
5. `search_combined` follows the same pattern for both the docs and code candidate pools.
6. If FTS index creation fails (e.g., lancedb version without Tantivy), the build continues without error and the query path degrades gracefully to dense-only.
7. The existing `search_docs_lexical` fallback (filesystem walk + term-frequency scoring) is retained unchanged for the offline/no-index case.
8. FTS query uses the raw query string; no stemming or query rewriting is applied at this stage.

## Scope

**Problem statement:** Dense-only retrieval misses high-precision exact-match queries (function names, error codes, constants) that BM25 handles well. The current lexical fallback only fires when the semantic index is absent, not as a quality complement on every query.

**In scope:**

- FTS index creation in `_build_lance_tables` and `_lance_incremental_write` (indexer.py)
- Hybrid dense+FTS query path in `search_docs`, `search_code`, `search_combined` (server.py)
- Graceful degradation if FTS unavailable
- Tests verifying FTS index is created and hybrid path is exercised

**Out of scope:**

- Query expansion or rewriting
- BM25 parameter tuning (use LanceDB defaults)
- Replacing `search_docs_lexical` (offline fallback retained as-is)

## Acceptance Criteria

- AC-1: After a full index build, `(index_dir / "docs.lance" / "_tantivy")` directory exists (or equivalent FTS index artifact).
- AC-2: `search_docs` result set for an identifier-exact query contains the correct chunk when the identifier appears verbatim in a doc but is not semantically dominant.
- AC-3: `search_code` result set for a function name query contains the defining chunk within top-3 results.
- AC-4: FTS index creation failure does not abort the index build; a warning is printed and dense-only continues.
- AC-5: All existing search tests continue to pass (no regression).

## Tasks

- Add `_create_fts_index(table, table_name, replace=False)` helper in indexer.py; wrap in try/except; call after `create_table` in `_build_lance_tables` and after `_optimize_lance_table` in `_lance_incremental_write` (always call with `replace=True` on incremental path)
- Add `_lance_fts_search(table, query, top_n)` helper in server.py that runs `table.search(query, query_type="fts").limit(top_n).to_list()`; wrap in try/except returning `[]` on failure
- Update `search_docs`, `search_code`, `search_combined` to run dense and FTS calls in parallel via `concurrent.futures.ThreadPoolExecutor`; pass both result lists to `_rrf_merge` (confirmed compatible: `_rrf_merge` takes `list[list[dict]]` with no docs/code coupling)
- Wrap all FTS calls in try/except; log warning on failure; fall through to dense-only result
- Add unit tests for FTS index creation (indexer) and hybrid path (server)
- Add integration test: add a chunk with a unique identifier, run keyword search, assert the chunk appears in results (catches stale FTS after incremental write)

## Agent Execution Graph

| Workstream        | Owner              | Depends On      | Notes                                      |
| ----------------- | ------------------ | --------------- | ------------------------------------------ |
| indexer-fts       | framework-engineer | —               | FTS index creation in _build_lance_tables  |
| server-hybrid     | framework-engineer | —               | Hybrid query path in search_docs/code      |
| tests             | framework-engineer | indexer-fts, server-hybrid | Unit + integration tests      |

## Serialization Points

- `indexer.py` and `server.py` can be developed in parallel; tests require both

## Affected Architecture Docs

`docs/architecture/current-state.md` — update retrieval path description if it documents dense-only. Otherwise N/A.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  | Validates that FTS actually improves recall on identifier queries — without this AC, the change is "done" with zero quality validation |
| AC-3 | required  | Same rationale as AC-2 for code search |
| AC-4 | required  |           |
| AC-5 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. `_create_fts_index` helper added; FTS index built on `create_table` and rebuilt after incremental writes. `_lance_fts_search` added to server.py. `search_docs`, `search_code`, `search_combined` updated to run dense+FTS in parallel via `ThreadPoolExecutor` and fuse with `_rrf_merge`. 1326 tests pass. | `run_tests.py` OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | Use LanceDB built-in Tantivy FTS | No additional dependencies; co-located with vector data | Separate BM25 store (Elasticsearch, SQLite FTS5) |
| 2026-05-17 | Fuse with existing _rrf_merge | RRF already used for docs+code fusion; consistent | Linear score blending |
| 2026-05-17 | ThreadPoolExecutor for dense+FTS parallelism | LanceDB releases GIL on I/O; threads overlap cleanly; simpler than asyncio | asyncio, sequential |
| 2026-05-17 | Explicit FTS refresh in incremental write | `optimize()` does not rebuild FTS; confirmed by reading `_optimize_lance_table` implementation | Rely on optimize (incorrect) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| LanceDB Tantivy FTS API may differ across versions | Wrap in try/except; check lancedb version in tests |
| FTS doubles query latency if run serially | Use `concurrent.futures.ThreadPoolExecutor`; LanceDB releases GIL on I/O so threads can overlap |
| FTS stale after incremental write | Always call `_create_fts_index(table, replace=True)` after `_optimize_lance_table` in `_lance_incremental_write` — `optimize()` alone does not refresh FTS |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
