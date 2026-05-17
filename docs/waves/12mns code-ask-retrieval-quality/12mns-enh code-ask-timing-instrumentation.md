# code_ask: Per-Query Timing Instrumentation

Change ID: `12mns-enh code-ask-timing-instrumentation`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-14
Wave: `12mns code-ask-retrieval-quality`

## Rationale

After shipping the cross-encoder reranker (`12mha-enh`), there is no way to evaluate whether the latency increase is acceptable in practice, or to measure the tradeoff when VECTOR_TOP_K changes. Field feedback confirmed that per-query timing data was unavailable when requested. This change adds `vector_ms`, `rerank_ms`, and `total_ms` to the `code_ask` response payload and to the server log — providing the instrumentation needed to validate VECTOR_TOP_K scaling decisions in `12mns-enh dynamic-vector-top-k`.

## Requirements

1. `code_ask_response` must capture three timing values in milliseconds (integer, rounded):
   - `total_ms`: wall time from function entry to response assembly
   - `vector_ms`: time spent in `search_combined()` vector fetch only
   - `rerank_ms`: time spent in reranker inference only (or RRF fallback time when reranker unavailable)
2. All three values must be included in the `code_ask` response payload at the top level alongside `answer`, `citations`, `confidence`, etc.
3. When the reranker did not run (`reranked: false`), `rerank_ms` must still be present and reflects the RRF merge time.
4. Timing must be logged to the server log as a single line per query: `[wavefoundry] code_ask timing: total={total_ms}ms vector={vector_ms}ms rerank={rerank_ms}ms`.
5. Timing capture must use `time.monotonic()` — not `time.time()` — to avoid wall-clock drift.
6. Timing values must not appear in `docs_search` or `code_search` responses — `code_ask` only.

## Scope

**Problem statement:** No per-query timing data is captured for `code_ask`, making it impossible to evaluate reranker latency impact or validate VECTOR_TOP_K scaling decisions.

**In scope:**

- `time.monotonic()` timestamps in `code_ask_response` around vector and rerank phases
- `vector_ms`, `rerank_ms`, `total_ms` in `code_ask` response payload
- Server log line per query
- Tests in `test_server_tools.py`

**Out of scope:**

- Timing for `docs_search`, `code_search`, or `code_keyword`
- Exposing timing via a separate MCP tool or dashboard metric
- Percentile aggregation or rolling statistics

## Acceptance Criteria

- AC-1: `code_ask` response includes `total_ms`, `vector_ms`, `rerank_ms` as integers.
- AC-2: `total_ms >= vector_ms + rerank_ms` (total includes overhead beyond vector and rerank).
- AC-3: When `reranked: false`, `rerank_ms` is still present and reflects RRF merge time.
- AC-4: Server log contains the timing line for each `code_ask` invocation.
- AC-5: `docs_search` and `code_search` responses do not include timing fields.

## Tasks

- [ ] Add `time.monotonic()` capture at entry of `code_ask_response`
- [ ] Instrument `search_combined()` to return timing breakdown — expand return to `(results, reranked, vector_ms, rerank_ms)`; update `code_ask_response` caller
- [ ] Add timing log line in `code_ask_response`
- [ ] Include `total_ms`, `vector_ms`, `rerank_ms` in response data dict
- [ ] Update tests: timing fields present and typed correctly; `total_ms >= vector_ms + rerank_ms`; timing absent from `docs_search`/`code_search`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| search-combined-timing | implementer | — | Add timing return to `search_combined()` |
| code-ask-response | implementer | search-combined-timing | Capture total, log line, response fields |
| tests | implementer | code-ask-response | `test_server_tools.py` |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.
- `search_combined()` return type changes — coordinate with `12mns-enh question-type-aware-retrieval` if both are implemented in the same session.

## Affected Architecture Docs

N/A — instrumentation only, no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | All three timing fields in the response — the primary deliverable; `dynamic-vector-top-k` depends on `rerank_ms` |
| AC-2 | required  | Timing correctness invariant — `total_ms` must not be less than its component parts |
| AC-3 | required  | `rerank_ms` must be present even when reranker is unavailable — consumers must not branch on field presence |
| AC-4 | important | Server log line is observability infrastructure; useful for profiling but not a consumer-facing correctness gate |
| AC-5 | required  | `docs_search` and `code_search` must not leak timing fields — scope boundary |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped from field feedback | "No timing data is captured per query" — field report |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | `time.monotonic()` not `time.time()` | Monotonic clock is immune to wall-clock adjustments | `time.time()` — vulnerable to NTP adjustments mid-request |
| 2026-05-14 | Return timing from `search_combined()` | Vector and rerank phases are internal; external measurement conflates keyword fallback time | Measure externally — less precise |

## Risks

| Risk | Mitigation |
|------|------------|
| `search_combined` return type change breaks callers | Only one caller (`code_ask_response`); update in same commit |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
