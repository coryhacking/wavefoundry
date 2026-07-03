# FTS No-Position Query Shape

Change ID: `1p9j1-enh fts-no-position-query-shape`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-02
Wave: `1p9jn retrieval-lookup-hardening`

## Rationale

Wavefoundry's LanceDB full-text indexes currently store positional data even though the retrieval path primarily uses FTS for candidate recall over docs, code chunks, identifiers, and symbols rather than true phrase/proximity search. A local benchmark recorded in `docs/reports/index-compression-and-fts-2026-07-02.md` showed that disabling FTS positions reduces FTS storage by about 69% for docs and 72% for code while preserving practical overlap when queries are token-shaped instead of phrase-shaped.

The benchmark also exposed a production-relevant hazard: the current `_fts_query` path wraps identifier-like queries in quotes. No-position FTS cannot satisfy those phrase queries. Therefore this change must update the index setting and query shape together; changing only `with_position` would mask a production bug.

## Product Intent

Reduce local index disk footprint without degrading the code/docs retrieval behavior operators rely on for MCP search, Guru answers, and agent navigation. The retrieval contract remains "high-quality candidate recall for reranked semantic workflows," not exact phrase-search semantics.

Evidence anchor: `docs/reports/index-compression-and-fts-2026-07-02.md`.

## Requirements

1. FTS index creation for docs and code tables MUST use `with_position=False`.
2. FTS query construction MUST avoid issuing quoted phrase queries that require positions when the production index is no-position.
3. Identifier-like searches, dotted names, underscored names, natural-language queries, and code-symbol queries MUST still return useful FTS candidates where they did before.
4. The change MUST preserve the current tokenizer, lower-case, stemming, stop-word, and max-token-length choices unless implementation discovery finds a blocking compatibility issue.
5. FTS failures MUST remain contained to the FTS branch of hybrid retrieval; dense retrieval and rerank behavior must not regress.
6. Tests MUST verify both the no-position index configuration and the query-shape behavior that prevents quoted phrase failures.

## Scope

**Problem statement:** FTS positions consume significant disk space for little observed value in Wavefoundry's retrieval workload, but the current quoted identifier query shape is incompatible with no-position FTS.

**In scope:**

- Update `.wavefoundry/framework/scripts/indexer.py` `_create_fts_index` to build no-position FTS indexes.
- Update `.wavefoundry/framework/scripts/server_impl.py` FTS query construction so identifier-like queries do not require positional phrase matching.
- Add focused regression tests in `.wavefoundry/framework/scripts/tests/test_indexer.py` and `.wavefoundry/framework/scripts/tests/test_server_tools.py`.
- Update relevant retrieval/indexing docs if implementation changes an externally visible behavior contract.
- Rebuild or refresh the local index after implementation only as verification evidence, not as part of this plan.

**Out of scope:**

- Changing vector compression defaults such as `IVF_HNSW_SQ`.
- Changing FTS tokenizer, stemming, stop-word removal, lower-casing, or `max_token_length`.
- Adding a user-facing phrase-search product feature.
- Masking or working around the separate CoreML reranker native crash found during the benchmark.

## Acceptance Criteria

- [x] AC-1: `_create_fts_index` creates FTS indexes with `with_position=False`, verified by a unit test that inspects the `create_fts_index` call arguments.
- [x] AC-2: Identifier-like FTS queries such as `build_pack.version`, `SORT_WINDOW_SIZE`, and `wave_index_build_status` are not emitted as quoted phrase queries on the no-position path, verified by direct tests of the query builder or FTS search wrapper.
- [x] AC-3: Natural-language FTS queries remain token-search compatible and continue to flow through `_lance_fts_search` without changing dense retrieval or rerank call sites, verified by existing search tests plus a focused FTS query-shape test.
- [x] AC-4: Hybrid retrieval still degrades cleanly when FTS search raises, preserving dense results rather than failing the whole search, verified by an existing or added server-side test.
- [x] AC-5: A local rebuild of docs and code indexes completes and reports healthy semantic layers after the change, with verification recorded in the progress log.
- [x] AC-6: A small post-change FTS smoke check covers docs and code queries for identifiers, dotted names, underscored names, and natural-language terms, with no no-position phrase-query failures.
- [x] AC-7: Documentation that describes FTS behavior or index storage is updated if the implementation changes a public or operator-visible contract.

## Tasks

- [x] Confirm the exact LanceDB behavior for no-position FTS query syntax in the installed version before editing code.
- [x] Change `_create_fts_index` in `.wavefoundry/framework/scripts/indexer.py` to use `with_position=False` and update the nearby explanatory comment.
- [x] Revise `_fts_query` or the FTS search wrapper in `.wavefoundry/framework/scripts/server_impl.py` so no-position indexes do not receive phrase-shaped identifier queries.
- [x] Add `test_indexer.py` coverage for the FTS index creation arguments.
- [x] Add `test_server_tools.py` coverage for identifier-like, dotted, underscored, and natural-language FTS query shaping.
- [x] Run the focused tests for indexer and server FTS behavior.
- [x] Run the full framework test suite with `python3 .wavefoundry/framework/scripts/run_tests.py`.
- [x] Rebuild or refresh the semantic index and run an index-health check.
- [x] Update docs if implementation discovery shows an externally visible FTS contract changed.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| FTS behavior confirmation | implementer | - | Verify no-position query syntax against installed LanceDB before changing production code. |
| Index configuration | implementer | FTS behavior confirmation | Single-file change in `indexer.py`. |
| Query-shape fix | implementer | FTS behavior confirmation | Single-file change in `server_impl.py`; must not alter dense/rerank semantics. |
| Regression tests | implementer | Index configuration, query-shape fix | Focused tests in existing indexer and server test modules. |
| Verification | qa-reviewer | Regression tests | Focused tests, full suite, index rebuild/health, FTS smoke queries. |
| Review | code-reviewer, performance-reviewer | Verification | Confirm no silent phrase-query failures and storage win remains justified. |

## Serialization Points

- `_fts_query` and `_lance_fts_search` must be reviewed together with `_create_fts_index`; splitting the changes would either preserve wasted storage or introduce no-position phrase-query failures.
- Index rebuild verification must happen after both code and tests land.
- Documentation updates, if needed, should happen after implementation confirms the final query-shape contract.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` may need an update if it describes FTS/hybrid retrieval flow.
- `docs/architecture/testing-architecture.md` may need an update if new index verification expectations become durable.
- `docs/specs/mcp-tool-surface.md` may need an update if FTS behavior is described in user-visible search semantics.
- `docs/ARCHITECTURE.md` hub should be checked only if any child architecture doc changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | The storage win depends on the index setting changing. |
| AC-2 | required | Prevents the production bug identified by the benchmark. |
| AC-3 | required | Preserves the main docs/code retrieval use case. |
| AC-4 | required | Maintains existing hybrid retrieval resilience. |
| AC-5 | required | Confirms the rebuilt index is usable, not just unit-test green. |
| AC-6 | important | Provides corpus-shaped confidence for the observed benchmark conclusion. |
| AC-7 | important | Keeps operator-visible guidance aligned if behavior changes. |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-07-02 | Planned from local FTS benchmark showing no-position storage savings and query-shape hazard. | `docs/reports/index-compression-and-fts-2026-07-02.md` |
| 2026-07-02 | Admitted into wave `1p9jn retrieval-lookup-hardening` and prepared/readied. | `docs/waves/1p9jn retrieval-lookup-hardening/wave.md` |
| 2026-07-02 | Implemented no-position FTS creation and no-position-safe query shaping. | `_create_fts_index` now passes `with_position=False`; `_fts_query` no longer emits quoted phrase queries for identifier-like input and strips explicit quote wrappers. |
| 2026-07-02 | Verified focused and full tests. | `IndexReclaimTests`, `FtsQueryShapeTests`, and `BulkWaveGetChangeTests` passed; full framework suite passed (`4161 tests across 41 files`). |
| 2026-07-02 | Rebuilt the local docs/code indexes and verified health/smoke behavior. | Foreground rebuild completed: docs `17,690` rows, code `12,518` rows, graph `10,739` nodes / `30,791` edges; health reported `semantic_ready=true`, no missing/stale layers, and lock not held; FTS smoke returned results for `semantic code embeddings`, `wave_get_change`, `FTS`, `build_pack.version`, `SORT_WINDOW_SIZE`, and `wave_index_build_status` with no phrase-query failures. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-07-02 | Selected paired no-position FTS plus query-shape fix. | Produces the measured storage win while directly addressing the quoted phrase incompatibility. | Rejected "change only `with_position=False`" because it would introduce/retain phrase-query failures. Rejected "keep positions" because it leaves a 69-72% FTS storage savings opportunity unused. Rejected "also tune tokenizer/stemming/stop words" because the benchmark did not show enough evidence to broaden this change. |

## Risks

| Risk | Mitigation |
|------|------------|
| Removing positions eliminates true phrase/proximity search support. | Confirm this is acceptable for current Wavefoundry use cases: candidate recall for docs/code search, identifiers, symbols, and hybrid retrieval rather than exact phrase search. |
| Query-shape changes could reduce BM25 precision for exact identifiers. | Keep dense retrieval and rerank unchanged; add identifier and symbol smoke tests; compare post-change behavior against the benchmark report. |
| LanceDB query syntax varies by version. | Confirm behavior against the installed LanceDB package before implementation and keep tests pinned to the local behavior contract. |
| FTS exceptions could silently remove useful lexical candidates. | Keep focused coverage for FTS exception containment and add smoke checks for representative docs/code queries. |

## Session Handoff

This change is admitted into readied wave `1p9jn retrieval-lookup-hardening`. Before implementation, open the wave through the normal single-OPEN-gated implementation path. See `docs/agents/session-handoff.md` for current session state.
