# Graph Query Surface

Change ID: `12xs4-feat graph-query-surface`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-29
Wave: `12xr2 graph-query-surface`

## Rationale

Wave `12xr1 graph-index-extraction-and-visualization` closed with persisted
`project-graph.json` / `framework-graph.json` artifacts, dashboard visualization, and
Leiden community clustering. Agents and the dashboard still cannot **query** that graph
structurally: blast radius, call neighborhoods, orphan docs, high fan-in nodes, or
cross-layer framework↔project references require manual JSON inspection or re-deriving
relationships from scratch.

This change adds a read-only graph query layer on top of the persisted artifacts and exposes
it through new MCP tools plus an opt-in `graph=true` augmentation on existing navigation
tools. Default behavior of every pre-wave tool remains unchanged.

**Relationship to existing `code_impact(path)`:** The file-level import-heuristic
`code_impact` shipped in wave `12nbr` and must remain backward-compatible. Graph-backed
symbol traversal is added via **`symbol=` parameters** on new graph modes (and a new
`code_callgraph` tool), not by breaking the existing `path=` contract.

## Requirements

1. **Graph query library** — new `graph_query.py` under `.wavefoundry/framework/scripts/`:
   - Load project and/or framework graph JSON from the index sidecar paths (reuse
     `dashboard_lib.graph_path` / `graph_indexer.read_graph_payload` conventions).
   - Build an in-memory adjacency index (dict-based; optional `networkx` for union compose
     only) without mutating persisted artifacts.
   - **`load_union(root)`** — compose project + framework graphs at query time via
     `networkx.compose()` (or equivalent); tag each node with its `layer` attribute; do not
     persist the union. Document memory budget (~50k combined nodes).
   - Traversal helpers: BFS/DFS by relation filter (`calls`, `imports`, `defines`,
     `doc_references_code`; forward and reverse), hop limits, cycle-safe visited sets.
2. **`code_impact` graph mode** — extend the existing MCP tool (or add parallel entrypoint
   documented in tool schema) to accept **`symbol`** (qualified graph node id or resolvable
   symbol) plus **`max_hops`** (default 3). Returns affected files/symbols by traversing
   reverse dependency edges in the graph. When **`path=`** is supplied without **`symbol=`**,
   existing import-heuristic behavior is unchanged (`method: "heuristic"`).
   When **`symbol=`** is supplied, response includes `method: "graph"` and cites edge
   relation + confidence from the graph payload.
3. **`code_callgraph` MCP tool** — new read-only tool: **`symbol`**, optional **`depth`**
   (default 1), **`direction`** (`callers` | `callees` | `both`), **`layer`**
   (`project` | `framework` | `union`). Returns direct (and optionally deeper) call edges
   from the graph `calls` relation.
4. **`wave_graph_report` MCP tool** — structural summary over the loaded graph:
   - Top nodes by fan-in (callers) and fan-out (callees)
   - Orphan doc nodes (doc/seed kind with zero edges, or doc nodes with no
     `doc_references_code` outbound — define precisely in implementation)
   - High fan-out chokepoints (configurable threshold)
   - Cross-layer edges (project ↔ framework) when `layer=union`
   - Optional `community_id` breakdown when cluster artifact is present
5. **Opt-in augmentation** — add optional boolean **`graph`** parameter (default `false`) to
   `code_keyword`, `code_search`, `code_definition`, and `code_references`. When
   `graph=true`, append a clearly labeled supplemental section with immediate graph neighbors
   (1-hop) for matched symbols/paths. When `graph=false` or omitted, tool output is
   byte-for-byte identical to pre-wave behavior (hard constraint).
6. **Missing graph graceful degradation** — when graph files are absent or stale, graph tools
   return structured diagnostics (`graph_not_ready`) without raising; augmentation section
   omitted silently or with a one-line advisory.
7. **Tests** — unit tests for loader, union compose, traversals, each MCP tool, and
   augmentation on/off paths in `test_server_tools.py` / dedicated `test_graph_query.py`.
8. **Documentation** — `AGENTS.md` MCP table, architecture/search docs, seed references as
   needed.

## Scope

**Problem statement:** Persisted graph artifacts exist but are not queryable through MCP;
agents cannot ask structural questions without re-implementing traversal.

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` — load, union, traverse, report helpers
- `.wavefoundry/framework/scripts/server_impl.py` — MCP tool wiring, augmentation hooks
- `.wavefoundry/framework/scripts/server.py` — tool registration if separate from impl
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` (new)
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — MCP integration tests
- Optional dependency: `networkx` (union compose only; guard import with clear setup message)
- Docs: `AGENTS.md`, `docs/architecture/search-architecture.md` (graph query subsection)

**Out of scope:**

- Graph **extraction** changes (owned by `12xr1`, `12ynp-enh`)
- Dashboard visualization overhaul (`12yro-enh`) — may consume these tools later
- Promoting `graph=true` to default (`12xr3 graph-augmentation-promotion`)
- Semantic/LLM-derived edges
- Persisting union graph to disk

## Tool Contracts (sketch)

### `code_impact`

| Parameter | Existing | New (graph mode) |
| --------- | -------- | ---------------- |
| `path` | Repo-relative file; import heuristics | Unchanged |
| `symbol` | — | Graph node id or resolvable symbol |
| `max_hops` | — | Reverse traversal depth (default 3) |
| `layer` | — | `project` \| `framework` \| `union` (default `project`) |
| `relations` | — | Optional filter list |

Response always includes `method`: `"heuristic"` | `"graph"`.

### `code_callgraph`

| Parameter | Description |
| --------- | ----------- |
| `symbol` | Required graph node id |
| `depth` | Expansion depth (default 1) |
| `direction` | `callers` \| `callees` \| `both` |
| `layer` | `project` \| `framework` \| `union` |

### `wave_graph_report`

| Parameter | Description |
| --------- | ----------- |
| `layer` | `project` \| `framework` \| `union` |
| `limit` | Max rows per ranking section (default 20) |
| `sections` | Optional subset: `fan_in`, `fan_out`, `orphan_docs`, `chokepoints`, `cross_layer` |

### Augmentation (`graph=true`)

Append JSON field or markdown section:

```json
"graph_neighbors": {
  "present": true,
  "layer": "project",
  "nodes": [...],
  "edges": [...],
  "note": "1-hop structural neighbors; opt-in via graph=true"
}
```

Only when matches exist and graph is loaded; otherwise omit field entirely (not `null`) to
preserve byte-identical default output.

## Acceptance Criteria

- [ ] AC-1: `graph_query.load_graph(root, layer="project")` returns nodes/edges from
  `project-graph.json`; missing file returns empty graph + diagnostic.
- [ ] AC-2: `load_union(root)` composes project + framework graphs; every node retains
  `layer`; no file written under `.wavefoundry/index/`.
- [ ] AC-3: `code_impact(symbol="src/foo.py::bar", max_hops=2)` returns graph-backed
  affected symbols/files with `method: "graph"` and edge provenance.
- [ ] AC-4: `code_impact(path="src/foo.py")` behavior unchanged from pre-wave (import
  heuristic, `method: "heuristic"`).
- [ ] AC-5: `code_callgraph(symbol=..., depth=1, direction="both")` returns callers and
  callees from `calls` edges only.
- [ ] AC-6: `wave_graph_report(layer="union")` returns fan-in ranking, orphan docs list,
  and cross-layer edge summary on fixture graph.
- [ ] AC-7: `code_keyword(..., graph=false)` output matches pre-wave snapshot tests;
  `graph=true` adds supplemental neighbor section without altering base result ordering.
- [ ] AC-8: Same augmentation contract for `code_search`, `code_definition`,
  `code_references`.
- [ ] AC-9: All new tools registered as read-only; full framework test suite passes.
- [ ] AC-10: `networkx` (or documented fallback) covered by tests; setup path documented
  when union compose unavailable.

## Tasks

- [ ] Add `networkx` to tool-venv / setup dependencies (union compose only).
- [ ] Implement `graph_query.py`: load, adjacency index, union, BFS traversals, report
  aggregations.
- [ ] Wire `code_impact` graph mode (`symbol`, `max_hops`, `layer`, `relations`).
- [ ] Implement `code_callgraph` MCP tool.
- [ ] Implement `wave_graph_report` MCP tool.
- [ ] Add `graph: bool = False` to four existing tools; implement 1-hop neighbor appendix.
- [ ] Add `test_graph_query.py` + extend `test_server_tools.py`.
- [ ] Update `AGENTS.md` and architecture docs.
- [ ] Open/close `framework_edit_allowed` gate for framework script edits.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| graph_query library | framework-maintainer | — | Pure module; test first |
| code_impact graph mode | framework-maintainer | library | Preserve path= heuristic |
| code_callgraph + wave_graph_report | framework-maintainer | library | New MCP tools |
| graph=true augmentation | framework-maintainer | library | Hard byte-identical default |
| tests + docs | qa-reviewer | all above | Snapshot tests for default path |


## Serialization Points

- `graph_query.py` API must stabilize before MCP wiring and augmentation hooks land.
- Augmentation tests must use golden snapshots captured **before** implementation to prove
  `graph=false` byte identity.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — graph query tools and augmentation contract
- `docs/architecture/data-and-control-flow.md` — query-time union compose (read-only)
- `AGENTS.md` — MCP tool table entries

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Loader is foundation for all query tools |
| AC-2 | required | Union view is wave deliverable |
| AC-3 | required | Graph-backed impact is primary value |
| AC-4 | required | Hard backward-compat constraint for existing code_impact |
| AC-5 | required | code_callgraph is named wave deliverable |
| AC-6 | important | wave_graph_report structural summary |
| AC-7 | required | graph=false byte identity — hard wave constraint |
| AC-8 | required | Augmentation must cover all four named tools |
| AC-9 | required | Read-only registration + test suite green |
| AC-10 | important | networkx dependency path documented |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-29 | Change doc authored for wave 12xr2 admission. | `12xr1` closed; graph artifacts validated in dashboard |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-29 | Extend `code_impact` with `symbol=` graph mode; keep `path=` heuristic | Avoid breaking 12nbr contract | New tool `code_graph_impact` |
| 2026-05-29 | Union graph query-time only via networkx.compose | Matches wave spec; no persisted third artifact | Manual merge in graph_query |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Union graph memory > budget on large repos | Default `layer=project`; document limits; profile in Prepare wave |
| `graph=true` accidentally changes default output | Golden snapshot tests; separate code path gated on explicit true |
| Symbol id resolution ambiguity | Accept qualified ids; reuse `code_definition` resolution where possible |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
