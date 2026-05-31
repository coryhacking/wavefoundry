# Graph MCP Layer Improvements (Graphify Analysis)

Change ID: `12zxl-enh graph-mcp-layer-improvements`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 12xr2 graph-query-surface

## Rationale

A comparative review of the graphify-mcp-tools project against our graph MCP layer surfaced eight concrete improvements: three high-priority gaps that reduce tool failure rates and analysis precision, three medium-priority capability additions that close missing query patterns, and two low-priority polish items. The changes are all additive (no breaking signature changes) and operate entirely within the existing `graph_query.py` + `server_impl.py` layer.

Source: `docs/architecture/graph-index-system.md`, graphify-mcp-tools v0.1.0 server.ts + tool implementations.

## Requirements

1. When any graph tool fails to resolve a symbol, the response must include up to 3 fuzzy-matched alternative node labels/ids rather than a bare error, so agents can self-correct without a separate lookup.
2. `code_impact` graph mode must accept an `include_tests` boolean parameter (default `False`) that filters resolved affected nodes whose `source_file` matches the test-path patterns already defined in `graph_cluster.py`.
3. `wave_graph_report` must support `betweenness` as a valid `sections` value, returning the top-N nodes ranked by igraph betweenness centrality (igraph is already a hard dependency for Leiden clustering). If the graph has more than 10,000 nodes, the section must skip computation and return `diagnostic: "graph_too_large_for_betweenness"` rather than blocking; latency must be under 5 seconds on graphs up to 10,000 nodes.
4. A new `code_graph_path` tool must resolve two symbol names to graph node ids and return the shortest connecting node-and-edge chain using BFS over the adjacency index, with an optional `relations` filter.
5. A new `code_graph_community` tool must accept a `community_id` parameter and return all member nodes of that community from the cluster artifact ranked by degree. This is a separate tool, not a parameter on `wave_graph_report`, so that each tool has a single coherent behavior.
6. Node dicts in `code_impact` (`affected`) and `code_callhierarchy` (`incoming`/`outgoing`) responses must include a `community` field (community label string, or `null`) sourced from the cluster artifact loaded once per call.
7. A new MCP Resource `wavefoundry://graph/status` must be registered that returns a markdown summary of the project graph payload metadata (present, node/edge/file counts, builder version, graph path) by calling `read_graph_payload()` with no edge traversal.
8. `code_callhierarchy` must accept an optional `context_depth: int` parameter (default `0`) that, when > 0, performs one additional BFS hop on the immediate callers/callees result set and appends the expanded neighbors as a `context` list in the response.

## Scope

**Problem statement:** The graph MCP tool layer has several gaps relative to mature code-graph tools: symbol resolution errors give agents no recovery path, production blast-radius analysis is polluted by test callers, no tool can find the shortest dependency path between two symbols, and community membership is invisible in per-symbol responses.

**In scope:**

- `server_impl.py` — server-layer `_suggest_near_symbols()` helper; `code_impact_response()` test filter; `wave_graph_report_response()` betweenness section; `code_callhierarchy_response()` community field + context_depth; new `code_graph_path`, `code_graph_community` tools and `wavefoundry://graph/status` resource registration
- `graph_query.py` — `graph_impact()` `include_tests` param; `report()` betweenness section with node-count guard; new `shortest_path()` function; `resolve_symbol()` signature unchanged
- Test coverage for each new behavior in `tests/test_graph_query.py` and `tests/test_server_tools.py`
- `docs/architecture/graph-index-system.md` — update MCP Integration section and Implementation Paths table for new tool and resource

**Out of scope:**

- SQLite FTS pre-index (graphify's search database approach) — not needed given our existing `code_search` / `code_keyword` tools
- Pre-computing betweenness at graph build time — computed at report time using igraph; acceptable latency for an infrequent report call
- Multi-metric hotspot DB schema (graphify stores in_degree/out_degree/betweenness in SQLite) — not adopted; our in-memory approach is sufficient
- `code_callgraph` community field — deferred; callgraph returns raw edge lists, community enrichment is higher value on callhierarchy/impact
- `format: markdown|json` on `code_outline` — out of scope for this change

## Acceptance Criteria

- [x] AC-1: When a graph tool (code_callhierarchy, code_impact, code_callgraph, code_graph_path) cannot resolve a symbol, the response includes a `suggestions` list of up to 3 `{id, label, kind}` dicts sourced from suffix and label fuzzy matching in `resolve_symbol()`.
- [x] AC-2: `code_impact(symbol=..., include_tests=True/False)` correctly includes or excludes affected nodes whose `source_file` matches test path patterns; default is `False` (tests excluded from production blast-radius view); `include_tests` is documented in the tool docstring.
- [x] AC-3: `wave_graph_report(sections=["betweenness"])` returns a `betweenness` key containing the top-`limit` nodes ranked by igraph betweenness centrality; the section is skipped gracefully when igraph is unavailable; when graph node count > 10,000 the section returns `diagnostic: "graph_too_large_for_betweenness"` without computing.
- [x] AC-4: `code_graph_path(from_symbol=..., to_symbol=..., relations=None, max_hops=10)` always returns `{found, path_nodes, path_edges, hop_count, suggestions}` — empty lists and `hop_count: 0` when not found, `suggestions` populated when either symbol is unresolvable. Response shape is consistent regardless of `found`.
- [x] AC-5: A new `code_graph_community(community_id=...)` tool returns `{community_id, label, node_count, nodes: [{id, label, kind, source_file, degree}]}` sorted by degree descending; returns a clear not-found error when the community_id is absent from the cluster artifact.
- [x] AC-6: `incoming` and `outgoing` entries in `code_callhierarchy` responses, and `affected` entries in `code_impact` graph-mode responses, each carry a `community` string field (or `null` when clustering has not been run or the node is unmatched).
- [x] AC-7: `wavefoundry://graph/status` MCP Resource is listed by `ListResources` and readable via `ReadResource`; returns a markdown block with `present`, node/edge/file counts, `GRAPH_BUILDER_VERSION`, and `graph_path` when the artifact exists; returns a rebuild prompt when `present=False`.
- [x] AC-8: `code_callhierarchy(symbol=..., context_depth=1)` appends a `context` list of `{id, label, kind, source_file, relation}` dicts representing one additional BFS hop from the direct callers/callees; expansion is performed as a single combined traversal (all immediate caller/callee ids gathered first, then one `traverse(max_hops=1)` call) rather than N per-node calls; `context_depth=0` (default) produces no `context` key in the response.
- [x] AC-9: Tool docstrings for `code_graph_path` (new), `code_graph_community` (new), and updated `code_impact` and `code_callhierarchy` each contain a "Prefer when" clause, a "Response fields" section, and an "Args" section following the existing tool docstring pattern.

## Tasks

- [x] Add `_suggest_near_symbols(index, query, n=3)` helper in `server_impl.py` — suffix and label fuzzy scan of all node ids when `resolve_symbol()` returns `None`; `resolve_symbol()` signature in `graph_query.py` is unchanged
- [x] Wire `_suggest_near_symbols()` into all graph tool error paths in `server_impl.py`: `code_callhierarchy`, `code_impact`, `code_callgraph`, `code_graph_path`; include `suggestions` list in each tool's not-found response
- [x] Add `include_tests` param to `code_impact_response()` and `_code_impact_graph_response()`; filter `affected` list using test-path pattern set from `graph_cluster.py`
- [x] Add `betweenness` section to `graph_query.py :: report()`; skip if node count > 10,000 and return `diagnostic: "graph_too_large_for_betweenness"`; compute via `igraph.Graph.betweenness()` on calls-only subgraph when within threshold; handle igraph import failure gracefully
- [x] Add `shortest_path(from_symbol, to_symbol, relations=None, max_hops=10)` to `GraphQueryIndex` in `graph_query.py` using BFS with path tracking; always return `{found, path_nodes, path_edges, hop_count}` with empty lists and `hop_count: 0` when no path
- [x] Register `code_graph_path` tool in `server_impl.py`; call `index.shortest_path()`; wire `_suggest_near_symbols()` for both `from_symbol` and `to_symbol`; always return `{found, path_nodes, path_edges, hop_count, suggestions}` shape
- [x] Register `code_graph_community` tool in `server_impl.py`; load cluster artifact; return `{community_id, label, node_count, nodes}` sorted by degree; return not-found error when community_id absent
- [x] Load cluster artifact once per `code_callhierarchy_response()` and `_code_impact_graph_response()` call; build `node_id → community_label` lookup dict; attach `community` field to each node dict in the response
- [x] Add `context_depth` param to `code_callhierarchy_response()`; when > 0, gather all immediate caller/callee node ids into a single set and call `index.traverse(max_hops=1)` once; deduplicate results and append as `context` list
- [x] Register `wavefoundry://graph/status` `@mcp.resource` in `server_impl.py`; call `read_graph_payload(root, layer="project")`; format as markdown with present, counts, builder version, graph path
- [x] Write "Prefer when", "Response fields", "Args" docstrings for `code_graph_path` and `code_graph_community`; update docstrings for `code_impact` (`include_tests` param) and `code_callhierarchy` (`context_depth` param, `community` field in response fields)
- [x] Add/update tests in `tests/test_graph_query.py`: `shortest_path` (found + not-found + max_hops exceeded), `report` betweenness section (normal + node-count guard + igraph unavailable)
- [x] Add/update tests in `tests/test_server_tools.py`: `code_graph_path` (consistent response shape), `code_impact` include_tests param, `code_callhierarchy` community field + context_depth
- [x] Update `docs/architecture/graph-index-system.md` — MCP Integration section and Implementation Paths table for `code_graph_path`, `code_graph_community`, and `wavefoundry://graph/status`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| _suggest_near_symbols helper | implementer | — | Server-layer only; no graph_query.py change; all error-path workstreams depend on this |
| include_tests filter | implementer | _suggest_near_symbols | Single-parameter addition to graph_impact path |
| betweenness section | implementer | — | Requires igraph; node-count guard; graceful skip when unavailable |
| shortest_path + code_graph_path | implementer | _suggest_near_symbols | New graph_query.py function + new MCP tool |
| code_graph_community tool | implementer | — | Independent; reads cluster artifact only |
| community field on callhierarchy/impact | implementer | code_graph_community (cluster load pattern) | Reuses same cluster artifact load logic |
| context_depth on callhierarchy | implementer | community field | Single combined traversal; extend same response builder |
| graph/status resource | implementer | — | Independent; reads graph payload header only |
| Docstrings | implementer | all workstreams | Write after behavior is finalized |
| Tests | qa | all workstreams | Run after all implementation tasks |
| Docs update | implementer | all workstreams | Update arch doc last |

## Serialization Points

- `_suggest_near_symbols()` helper in `server_impl.py` must land before any error-path workstream wires it into a tool response
- Cluster artifact load pattern (community field workstream) should be written as a shared helper before `code_graph_community` and `context_depth` workstreams both consume it

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — MCP Integration section: add `code_graph_path_response()`, `code_graph_community_response()`, and `wavefoundry://graph/status` entries; update Implementation Paths table with new tool and resource rows

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Fuzzy suggestions eliminate agent retry loops on every symbol miss; affects all graph tools |
| AC-2 | required | Test-caller noise makes `code_impact` misleading for production blast-radius decisions |
| AC-3 | important | Betweenness surfaces bridge nodes that fan_in/fan_out miss; igraph already present |
| AC-4 | important | Shortest path is the only query pattern completely absent from our current layer |
| AC-5 | important | Community drill-down as a dedicated tool closes the gap between report-level and node-level graph inspection without overloading wave_graph_report |
| AC-6 | important | Community field on node dicts makes agent context-building significantly cheaper |
| AC-7 | nice-to-have | Resource is free to read; useful for ambient status checks at session start |
| AC-8 | nice-to-have | Context expansion reduces round-trips; lower priority since two-call pattern works today |
| AC-9 | required | Docstrings are part of the MCP contract; agents rely on them for tool selection |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-30 | Change doc created from graphify MCP layer comparative analysis | graphify-mcp-tools v0.1.0 server.ts, tool implementations, dev.to review |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | BFS (not Dijkstra) for code_graph_path | Edges are unweighted in our schema; BFS gives true shortest hop count; Dijkstra adds complexity with no benefit | Dijkstra with uniform weight=1 (equivalent result, more code) |
| 2026-05-30 | Betweenness computed at report time, not stored in graph artifact | igraph already loaded for Leiden; report is infrequent; avoids schema version bump | Pre-compute at build time and store in graph JSON sidecar |
| 2026-05-30 | include_tests defaults to False | Production blast-radius is the primary use case; test callers create noise; opt-in for full picture | Default True (backward-compatible but less useful) |
| 2026-05-30 | Server-layer _suggest_near_symbols() instead of resolve_symbol() tuple return | Keeps graph_query.py library API stable (resolve_symbol() stays → node_id \| None); suggestions are UX/error-recovery logic that belongs at the presentation layer; no existing call sites or tests need updating | resolve_symbol() returns (id, suggestions) tuple — invasive; breaks all existing call sites and tests simultaneously |
| 2026-05-30 | code_graph_community as a separate tool, not a param on wave_graph_report | wave_graph_report has a single coherent behavior (structural summary); adding community_id drill-down creates two incompatible behaviors in one tool; separate tool is cleaner and consistent with graphify's graph_community design | community_id param on wave_graph_report — behaviorally overloaded |

## Risks

| Risk | Mitigation |
|---|---|
| _suggest_near_symbols scans all node ids — O(N) on large graphs | Called only on resolution failure (uncommon path); cap at 3 results; acceptable for error recovery |
| igraph betweenness is O(VE) — slow on large graphs | Node-count guard at 10,000; only computed when `betweenness` explicitly in `sections`; not in default set |
| Cluster artifact may be absent (graph built but not clustered) | community field returns `null` gracefully; code_graph_community returns not-found error; no crash |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
