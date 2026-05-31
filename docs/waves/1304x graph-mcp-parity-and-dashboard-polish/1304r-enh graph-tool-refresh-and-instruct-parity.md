# Graph-Tool Refresh-and-Instruct Parity

Change ID: `1304r-enh graph-tool-refresh-and-instruct-parity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1304x graph-mcp-parity-and-dashboard-polish

## Rationale

Wave `12xr3` change `1301h` established a consistent pattern for `code_definition` when the graph index is the source of truth:

1. Try the graph first.
2. If the graph has no candidate for the query, run an incremental graph update (~4ms when nothing has changed).
3. If the refreshed graph still has no candidate, return a fast not-found with clear instructions.
4. If the graph is entirely absent, run a degraded fallback and emit an advisory diagnostic recommending `wave_index_build(content='graph')`.

This pattern works — `code_definition` went from 42s cold to <300ms in the common case, and the not-found and missing-graph paths both surface clear operator signals. **No other graph-using MCP tool implements the same pattern.** The result is inconsistent behavior: some tools refresh, some don't; some emit `graph_not_ready` diagnostics, some don't; some silently degrade. Operators don't have a single mental model for graph-tool behavior, and recoverable misses (recently-added code that's not yet in the graph) require manual rebuilds rather than auto-correcting.

This change applies the `1301h` pattern uniformly across all MCP surfaces that read the graph.

Source: wave `12xr3` close-review observation (2026-05-30) and the audit table comparing `code_definition` against the seven other graph-using tools.

## Requirements

1. A single helper `_graph_refresh_then_recheck(root, recheck_fn)` must encapsulate the incremental refresh + recheck pattern: try `wave_index_build_response(root, content='graph', mode='update')`, then call `recheck_fn()` and return its result. On exception, return `None`. This is the one place the refresh side-effect lives.
2. `code_references_response()` must adopt the full `1301h` shape: when `_graph_references_candidate_files()` returns `None`, attempt a refresh-then-recheck before falling through to a full repo walk. When the graph is entirely absent, emit a `graph_index_missing_degraded` advisory diagnostic on the response.
3. `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()`, `code_graph_path_response()` must attempt a refresh-then-recheck when `index.resolve_symbol(symbol)` returns `None` before emitting suggestions and the not-found diagnostic. On refresh-then-still-missing, the existing suggestions + not-found behavior is preserved; refresh just shrinks the window where recently-added symbols look unresolvable.
4. `code_graph_community_response()` must attempt a graph refresh (which also re-runs clustering on changed files) when the requested `community_id` is absent from the cluster artifact, before emitting the suggestions-and-not-found response.
5. `wave_graph_report_response()` must attempt a refresh-then-recheck when the graph is absent at first read — handles the recently-built case where the graph was created between the operator's `wave_index_build` and their first report query.
6. A single diagnostic shape must be used across the seven tools for graph-related misses: code `graph_index_missing_degraded` when graph is absent and a fallback ran; code `graph_not_ready` when graph is absent and no fallback exists (existing `gq.graph_not_ready_diagnostic()`); code `graph_symbol_not_found` when refresh ran and the symbol still doesn't resolve. Each diagnostic must carry `recovery_tools` and `recovery_usage` so agents can self-correct.
7. The refresh attempt must not block-and-retry repeatedly — exactly one refresh per call, then proceed. If the refresh raises, the tool falls through to its existing not-found / walk path as today.

## Scope

**Problem statement:** Graph-using MCP tools have inconsistent miss behavior. `code_definition` (after `1301h`) auto-refreshes on miss and emits advisory diagnostics; the other seven graph-using tools either silently degrade or return suggestions without attempting recovery. Operators don't have a uniform mental model. Recently-added code that's not yet in the graph requires manual rebuilds for every graph tool except `code_definition`.

**In scope:**

- `server_impl.py` — new `_graph_refresh_then_recheck(root, recheck_fn)` helper
- `server_impl.py` — `code_references_response()` adopts `1301h` shape: refresh + advisory + degraded fallback
- `server_impl.py` — `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()`, `code_graph_path_response()` add refresh-then-recheck on `resolve_symbol` miss before emitting suggestions
- `server_impl.py` — `code_graph_community_response()` adds graph refresh before the not-found branch (refresh re-runs clustering on changed files via the same incremental build path)
- `server_impl.py` — `wave_graph_report_response()` adds refresh-on-absent at first index load
- `server_impl.py` — diagnostic codes consolidated: `graph_index_missing_degraded`, `graph_not_ready`, `graph_symbol_not_found`
- `tests/test_server_tools.py` — parity tests for each tool: refresh attempt happens on miss; advisory diagnostic emitted on graph-absent (where applicable); response shape preserved
- `docs/architecture/graph-index-system.md` — new subsection: "Graph-Tool Miss Behavior — Refresh-and-Instruct Contract" documenting the uniform pattern

**Out of scope:**

- Changing the synchronous nature of the refresh — it stays inline (~4ms when nothing has changed). Background refresh is a separate concern.
- Caching the refresh attempt within a session — every call attempts it independently; cheap when no changes, expensive only when files actually changed
- Refresh on `code_keyword`, `code_search` — these are graph-augmented, not graph-primary; the augmentation already degrades gracefully when graph is absent
- Refactoring the augmentation `_maybe_append_graph_neighbors()` path to also refresh — augmentation seeds are best-effort; if they miss, the lean response is still correct
- Changing the cluster artifact rebuild trigger conditions — the existing `wave_index_build(content='graph', mode='update')` already invalidates clusters when graph changes
- Adding a "force refresh" override parameter to any tool — operators who want a forced rebuild call `wave_index_build` directly

## Acceptance Criteria

- [x] AC-1: `_graph_refresh_then_recheck(root, recheck_fn)` exists; calls `wave_index_build_response(root, content='graph', mode='update')`, then `recheck_fn()`; returns the recheck result; returns `None` on any exception. Refresh attempt is bounded to one call per outer tool invocation. Verified by `TestGraphRefreshThenRecheck` (4 tests). A companion convenience helper `_graph_refresh_and_resolve(root, symbol, layer)` was added for the common case where the recheck both reloads the index and re-resolves the symbol — returns `(fresh_index, node_id)` on hit or `(None, None)` on miss; verified by `TestGraphRefreshAndResolve` (3 tests).
- [x] AC-2: `code_references_response()` adopts the refresh-then-recheck pattern when `_graph_references_candidate_files()` returns `None` on the first query. Implementation deliberately preserves the existing 176ms-range fast path (no `lookup_method` field added on success); the change is purely additive on the miss path. Advisory-degraded shape from `1301h` not duplicated here because `code_references` already gracefully falls back to a full walk when no graph data is present — the fast path is the win.
- [x] AC-3: `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()`, `code_graph_path_response()` each attempt `_graph_refresh_and_resolve()` when their initial symbol resolution returns `None`. If the refresh produces a resolved node, the tool swaps in the fresh index and proceeds normally; otherwise existing suggestions + not-found behavior is preserved. Response shape unchanged.
- [x] AC-4: `code_graph_community_response()` attempts a `_graph_refresh_then_recheck()` cycle on the cluster artifact before emitting the not-found branch. If the refreshed payload contains the community, the tool proceeds normally; otherwise existing suggestions + not-found is preserved.
- [x] AC-5: `wave_graph_report_response()` attempts a refresh-then-recheck on the `index.present` flag before returning `graph_not_ready`. If the refreshed index is present, the report proceeds normally.
- [x] AC-6: Diagnostic vocabulary consolidated to three codes carried uniformly across the seven graph-using tools. (1) `graph_index_missing_degraded` — graph absent, fallback ran (`code_definition` from 1301h). (2) `graph_not_ready` — graph layer absent and no fallback exists (`code_callhierarchy`, `code_callgraph`, `code_impact` graph mode, `code_graph_path`, `wave_graph_report` via `gq.graph_not_ready_diagnostic`). (3) `graph_symbol_not_found` (new, this change) — incremental refresh ran and the symbol still doesn't resolve; emitted by `code_callhierarchy`, `code_callgraph`, `_code_impact_graph_response`, `code_graph_path`. Each diagnostic carries `recovery_tools` and `recovery_usage`. `code_graph_community` retains `not_found` for community misses (semantic mismatch — communities aren't symbols).
- [x] AC-7: Latency budget — refresh helpers run synchronously and add ~4ms when no files have changed (measured during wave 12xr3 close-review and unchanged here). Fast paths gate the refresh behind the miss, so no overhead is added to successful symbol resolution.
- [x] AC-8: Test coverage — `TestGraphRefreshThenRecheck` (4 tests) and `TestGraphRefreshAndResolve` (3 tests) cover the helper unit behavior including the refresh-raises and recheck-still-empty cases. `TestGraphToolRefreshOnMiss` (8 tests) verifies each of the seven graph-using tools triggers exactly one refresh call on its miss path by patching `wave_index_build_response` and asserting `call_count == 1`; includes a regression test for the A1 close-review finding (`test_code_graph_path_refreshes_when_only_one_symbol_missing`). The 1301h test suite continues to pass, confirming `code_definition` was not regressed by the helper extraction (`code_definition` was not refactored to use the new helpers — its existing inline pattern was preserved deliberately to avoid touching the wave-12xr3 contract during this wave).
- [x] AC-9: Architecture doc updated. `docs/architecture/graph-index-system.md` gains a "Graph-Tool Miss Behavior — Refresh-and-Instruct Contract" subsection (in the `code_definition_response` MCP Integration block, immediately after the 1301h contract description). The subsection documents the two shared helpers, per-tool miss behavior for all seven tools, the three-code diagnostic vocabulary with recovery hints, the latency budget, and the test coverage.

## Tasks

- [ ] Add `_graph_refresh_then_recheck(root, recheck_fn)` helper in `server_impl.py` near `_maybe_append_graph_neighbors()`
- [ ] Update `code_references_response()` to call `_graph_refresh_then_recheck(root, lambda: _graph_references_candidate_files(root, symbol))` when the first candidate query returns `None`; add `lookup_method` to the response (`graph_narrowed | graph_narrowed_after_refresh | graph_index_missing_degraded`); emit `graph_index_missing_degraded` advisory diagnostic on the response when graph is absent
- [ ] Update `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()`, `code_graph_path_response()` to call `_graph_refresh_then_recheck(root, lambda: index.resolve_symbol(symbol))` (or both symbols for path) when initial resolution returns `None`; if the post-refresh resolution succeeds, proceed normally; otherwise preserve existing suggestions + not-found behavior
- [ ] Update `code_graph_community_response()` to call `_graph_refresh_then_recheck()` before the not-found branch
- [ ] Update `wave_graph_report_response()` to call `_graph_refresh_then_recheck()` before returning `graph_not_ready`
- [ ] Consolidate diagnostic vocabulary: ensure all three codes (`graph_index_missing_degraded`, `graph_not_ready`, `graph_symbol_not_found`) carry `recovery_tools` and `recovery_usage`
- [ ] Add `TestGraphRefreshHelper` to `tests/test_server_tools.py` — covers helper unit behavior
- [ ] Add or extend per-tool tests for the refresh-on-miss path (seven tools)
- [ ] Run framework tests; confirm all green
- [ ] Reload MCP and smoke-test each tool's refresh path
- [ ] Update `docs/architecture/graph-index-system.md` with the contract subsection
- [ ] Mark change `implemented` in this doc and in the host wave's `wave.md`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The shared helper is the contract for refresh side-effect; without it, the seven tools duplicate the same try/except pattern |
| AC-2 | required | `code_references` is the closest analogue to `code_definition`; bringing it to parity is the headline win |
| AC-3 | required | The four core graph-traversal tools share resolve-symbol semantics; refresh-on-miss makes recently-added symbols auto-resolve |
| AC-4 | important | `code_graph_community` refresh is a smaller win (cluster artifact is the source); worth doing for uniformity but lower priority than tool resolve paths |
| AC-5 | important | `wave_graph_report` refresh-on-absent handles the just-built case; without it operators get `graph_not_ready` even after a successful build |
| AC-6 | required | Diagnostic vocabulary uniformity is the operator-facing contract; without it agents can't write generic recovery logic |
| AC-7 | required | Latency budget guards the fast path; if refresh adds >20ms cold the change is a regression |
| AC-8 | required | Test coverage for each tool's refresh path; otherwise we have no regression guard |
| AC-9 | important | Architecture doc is the canonical reference for the uniform pattern |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Single helper, called by each tool at its miss site | Refresh logic is identical across tools; centralizing avoids drift if the refresh side-effect needs to change | Per-tool inline refresh (rejected — duplicates the same try/except pattern in 7 places) |
| 2026-05-30 | Synchronous refresh inline (not background) | Operator validation in 12xr3 showed incremental refresh is ~4ms when nothing has changed; background adds complexity for no measurable win on the common case | Background refresh + return stale-not-found (rejected — needs polling/retry semantics for callers, and the user just verified 4ms is fine inline) |
| 2026-05-30 | Three consolidated diagnostic codes instead of one | Different miss reasons want different recovery actions: `graph_index_missing_degraded` → "build the graph"; `graph_not_ready` → same but stricter (no fallback ran); `graph_symbol_not_found` → "check the symbol or look in non-indexed file types" | Single diagnostic code (rejected — would conflate "build the graph" and "fix your query" recovery paths) |
| 2026-05-30 | No refresh on augmentation path (`_maybe_append_graph_neighbors`) | Augmentation is best-effort; missed seeds → lean response is correct, not degraded | Always refresh on augmentation (rejected — would charge every default-on query for refresh) |

## Risks

| Risk | Mitigation |
|---|---|
| Synchronous refresh on every miss adds latency when files HAVE changed (incremental build does work) | The refresh is gated behind the miss path; common case (symbol in graph) is unchanged. Worst case is the operator's first call after a large code change, which already pays the refresh cost on the next `code_definition` call after `1301h` |
| Refresh raises an exception mid-call | Helper catches all exceptions and returns `None`; the tool falls through to its existing not-found path |
| Two callers race on the same refresh | The existing `_index_build_lock` serializes refreshes; the second caller waits briefly or sees a stale-but-consistent graph |
| `code_graph_community` refresh is more expensive than other tools (re-runs clustering) | Acceptable — community misses are rare and the refresh still terminates quickly when no files changed |

## Related Work

- **Wave `12xr3` change `1301h`** — established the pattern for `code_definition`; this change generalizes it across the remaining seven graph-using MCP tools
- **Wave `12xr2` change `12xs4`** — introduced `_graph_references_candidate_files()`, which this change extends with the refresh-and-instruct shape
- **Wave `12xr3` change `13006`** — `code_graph_path` is one of the seven tools updated by this change

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
