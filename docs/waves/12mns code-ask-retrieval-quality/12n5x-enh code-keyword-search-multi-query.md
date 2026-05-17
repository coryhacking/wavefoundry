# `code_keyword` Multi-Query Support

Change ID: `12n5x-enh code-keyword-search-multi-query`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: `12mns code-ask-retrieval-quality`

## Rationale

`code_keyword` currently accepts a single query string. Two-hop symbol expansion (`12n0e`) and documentation research routinely need to look up several distinct patterns at once — e.g. all the retrieval-tuning constants in `server.py`, or the definition sites of several symbols extracted from citations. Today this requires N sequential or parallel tool calls, each with its own result set to reconcile manually. A `queries` list parameter collapses that into one call, deduplicated by `(path, line)`, with each result tagged to show which query matched it.

## Requirements

1. `code_keyword` must accept an optional `queries: list[str]` parameter alongside the existing `query: str` parameter. When `queries` is supplied, `query` must be omitted (or empty); supplying both is an error.
2. When `queries` is supplied, the tool performs one keyword search per entry and merges results into a single list, deduplicated by `(path, line)` — first match wins for ordering, preserving the match order within each per-query result set.
3. Each result in the merged list must include a `matched_query` field indicating which query string produced it, so callers can distinguish which pattern surfaced which result without re-running individual queries.
4. The existing `glob` parameter applies uniformly to all queries in the batch.
5. The existing single-`query` call shape must remain fully backward-compatible — no change to callers passing a single string.
6. The `queries` parameter must be accepted by the MCP tool surface (FastMCP schema) and documented in the `code_keyword` docstring alongside the existing `query` parameter.

## Scope

**Problem statement:** Agents looking up multiple named symbols or constants in one pass must issue N separate `code_keyword` calls and manually reconcile the results. This is the pattern that caused a raw `grep` to be used instead of the MCP tool during a documentation pass — the tool simply couldn't express "find all of these at once."

**In scope:**

- `code_keyword_response()` in `server.py` — add `queries` parameter, multi-pass logic, deduplication, `matched_query` tagging
- MCP `code_keyword` tool wrapper — update signature and docstring
- Tests in `test_server_tools.py` covering: multi-query merge, deduplication, `matched_query` tagging, `glob` scoping across batch, error on both `query` and `queries` supplied

**Out of scope:**

- Parallel execution of the per-query passes (sequential is sufficient at this corpus size)
- Regex or glob patterns within individual query strings (queries remain exact substring matches)
- Ranked/scored results (keyword search is already unranked)
- Changes to `docs_search` or `code_search`

## Acceptance Criteria

- AC-1: When `queries=["FOO", "BAR"]` is passed, results include matches from both searches, deduplicated by `(path, line)`. Each result carries `matched_query: "FOO"` or `matched_query: "BAR"`. When the same `(path, line)` is matched by both queries, the result carries `matched_query` from the earlier query in the list (`"FOO"` wins over `"BAR"`).
- AC-2: When `glob` is provided alongside `queries`, all per-query passes are scoped to that glob. Results outside the glob do not appear.
- AC-3: A call with both `query="FOO"` and `queries=["BAR"]` returns a tool-level error response (status `"error"`) rather than silently ignoring one parameter.
- AC-4: A call with only the existing `query="FOO"` (no `queries`) returns results identical to the current behavior — `matched_query` is absent from result objects (not present as `null`), and no other response shape changes.
- AC-5: An empty `queries=[]` returns an empty result set with `status: "ok"` rather than an error.
- AC-6: `test_server_tools.py` covers ACs 1–5 with unit tests; all existing `code_keyword` tests continue to pass unchanged.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Core deliverable — multi-query merge and tagging |
| AC-2 | required  | Glob scoping must work in batch mode or the tool is unsafe for targeted lookups |
| AC-3 | required  | Ambiguous dual-parameter calls must fail loudly |
| AC-4 | required  | Backward compatibility — existing callers must not be broken |
| AC-5 | important | Empty list is a valid degenerate case; error would surprise callers |
| AC-6 | required  | Tests required for MCP tool changes per wave watchpoint |

## Tasks

- In `code_keyword_response()`: add `queries: list[str] | None = None` parameter; validate mutual exclusivity with `query`; loop over queries, collect results, deduplicate by `(path, line)`, tag each with `matched_query`
- In `code_keyword` MCP tool wrapper: add `queries` to signature and update docstring with parameter semantics and `matched_query` field description
- Write tests in `test_server_tools.py`: multi-query merge, dedup, tagging, glob batch scoping, dual-param error, backward-compat, empty list

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| server.py implementation | implementer | — | `code_keyword_response` + MCP wrapper |
| tests | implementer | server.py implementation | `test_server_tools.py` |

## Serialization Points

- `server.py` — sole implementation file; single workstream, no parallel conflicts

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — update `code_keyword` signature block to document `queries` parameter and `matched_query` response field. `docs/architecture/search-architecture.md` — no structural change (keyword search is Layer 2; this is a usability improvement, not a new layer). `AGENTS.md` — update `code_keyword` one-liner to mention multi-query support.

## Risks

| Risk | Mitigation |
|---|---|
| Callers passing both `query` and `queries` silently drop one | AC-3 mandates a hard error on dual-param |
| `matched_query` field absent in single-query path breaks callers that check for it | AC-4 mandates no field in single-query response; callers should not assume its presence |
| Deduplication order non-deterministic across query order | First-match-wins: results from `queries[0]` take priority; document this in the docstring |

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-15 | `queries` list alongside existing `query` string, not replacing it | Backward compatibility — existing callers pass `query`; breaking them is not acceptable |
| 2026-05-15 | `matched_query` field only in multi-query path | Single-query callers have no use for the field; adding it unconditionally would change the response shape of existing calls |
| 2026-05-15 | Sequential per-query execution, not parallel | Corpus is small; parallel execution adds complexity for negligible latency gain |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-15 | Change doc created | Identified during documentation pass for two-hop: grep used instead of MCP tool because single-query constraint forced multiple calls |
| 2026-05-15 | Implemented: `queries` list param, dedup by (path, line), `matched_query` tagging, backward-compat single-query path; 8 tests added; 1299 tests pass | `run_tests.py` → 1299 OK |
