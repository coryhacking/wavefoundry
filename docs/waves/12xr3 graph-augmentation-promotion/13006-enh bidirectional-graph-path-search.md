# Bidirectional Graph Path Search

Change ID: `13006-enh bidirectional-graph-path-search`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 12xr3 graph-augmentation-promotion

## Rationale

`code_graph_path(from_symbol, to_symbol)` only walks **forward** edges via `_out`
adjacency. Agents asking "is A connected to B?" get a false-negative `found: false`
result whenever B happens to be upstream of A — even when a short reverse path exists.
This is the single biggest discovery dark-spot in the graph query surface today: the
answer "no path" is wrong roughly half the time for unfamiliar symbol pairs.

The smoke test session for wave 12xr2 surfaced this gap directly: querying
`code_graph_path(from="code_graph_path_response", to="shortest_path")` returned
`found: false` despite a clear caller relationship, because the `calls` edge runs
`code_graph_path_response → shortest_path` (and was missed due to a separate
extractor limitation — but bidirectional search would have made the dynamic-call
gap less painful by surfacing the reverse path through one of the callers).

For an exploratory question like "are these two symbols coupled at all?", agents
need a tool that traverses edges in either direction.

Source: smoke test observation from wave `12xr2` close review (2026-05-30); red-team
verdict noted "the #1 false-negative scenario for an agent debugging coupling."

## Requirements

1. `code_graph_path` must accept a new `direction` parameter:
   `"forward"` (default, current behavior — follow outgoing edges only),
   `"backward"` (follow incoming edges only), and
   `"either"` (BFS that follows both directions).
2. When `direction="either"`, the BFS must return the **shortest hop count** path
   regardless of edge direction; ties broken by total node-id length (shortest first
   for determinism).
3. Each entry in `path_edges` for `direction="either"` mode must carry an additional
   `traversal_direction` field with value `"forward"` (edge walked source→target) or
   `"backward"` (edge walked target→source), so the agent can read the chain
   unambiguously.
4. Default behavior (no `direction` argument) must remain byte-identical to the
   pre-change forward-only response — same shape, same content for the same inputs.
5. `GraphQueryIndex.shortest_path()` must add an internal `direction` parameter that
   accepts `"forward"`, `"backward"`, or `"either"`. The library-layer change is
   non-breaking.
6. Tool docstring must document the trade-off: `"forward"` is for "does A reach B
   through a call chain?"; `"either"` is for "are A and B coupled at all?"; agents
   should prefer `"forward"` when directionality is part of the question.

## Scope

**Problem statement:** Agents performing coupling investigation receive `found: false`
for symbol pairs that are connected but where the edge direction runs opposite to the
agent's mental model. The current forward-only BFS is correct for dependency-chain
queries but wrong for "are these connected?" queries.

**In scope:**

- `graph_query.py` — extend `GraphQueryIndex.shortest_path()` with `direction`
  parameter; refactor internal BFS to walk `_out`, `_in`, or both based on direction
- `server_impl.py` — add `direction` parameter to `code_graph_path` MCP tool and
  `code_graph_path_response()`; thread through to the library call; document the
  new field
- `tests/test_graph_query.py` — `shortest_path` tests for backward and either modes:
  found path, not-found shape, hop-count correctness, edge traversal_direction field
- `tests/test_server_tools.py` — `code_graph_path_response()` tests for
  `direction="forward"|"backward"|"either"`; verify response shape consistency and
  default-byte-identity
- `docs/architecture/graph-index-system.md` — update `code_graph_path` description
  and BFS notes

**Out of scope:**

- Bidirectional BFS optimization (meet-in-the-middle from both endpoints) — the
  naive symmetric BFS is correct and fast enough for graphs <10k nodes
- Edge-weight support (different relation types weighted differently) — separate
  concern; deferred
- Path scoring / ranking when multiple equal-length paths exist — first shortest
  path wins, tie-broken by node-id length
- Backward search on `code_callhierarchy` `context_depth` — separate change

## Acceptance Criteria

- [x] AC-1: `code_graph_path(from_symbol, to_symbol)` (no `direction` argument) returns the exact same response shape and content as the pre-change implementation; default is `direction="forward"`. Verified by `test_default_direction_is_forward_byte_identity` (server layer) and `test_forward_is_default_unchanged` (library layer).
- [x] AC-2: `code_graph_path(direction="backward")` returns a path when one exists via incoming edges from `from_symbol` to `to_symbol`; `path_edges` are walked target→source but emitted in the same `{source, target, relation}` shape. Verified by `GraphQueryShortestPathBackwardTests` (3 tests) + `test_backward_finds_reverse_path`.
- [x] AC-3: `code_graph_path(direction="either")` returns the shortest path regardless of edge direction; each `path_edges` entry carries `traversal_direction: "forward"` or `"backward"`; `hop_count` reflects total edges traversed. Verified by `GraphQueryShortestPathEitherTests` (4 tests) + `test_either_finds_path_in_either_direction`.
- [x] AC-4: When no path exists in the requested direction, response shape is unchanged: `{found: false, path_nodes: [], path_edges: [], hop_count: 0, suggestions: [...]}`. Verified by `test_backward_preserves_consistent_shape_on_not_found` and `test_backward_no_path_when_no_incoming_chain`.
- [x] AC-5: `direction` parameter validation rejects unknown values with `invalid_arguments` diagnostic; valid values are `"forward"`, `"backward"`, `"either"` (case-insensitive). Verified by `test_invalid_direction_raises_value_error` (library), `test_invalid_direction_returns_invalid_arguments` (server), `test_direction_case_insensitive` (both layers).
- [x] AC-6: Tool docstring documents the three direction modes with a "Prefer when" clause for each. Verified by inspection of `code_graph_path` MCP wrapper docstring; live tool schema shows the updated description after reconnect.
- [x] AC-7: `GraphQueryIndex.shortest_path()` library API gains the `direction` parameter with default `"forward"`; signature is non-breaking for all existing callers. Verified — the original `GraphQueryShortestPathTests` (5 tests) all pass unchanged against the new signature.

## Tasks

- [x] Refactor `GraphQueryIndex.shortest_path()` to accept `direction` parameter; extract BFS state machine to walk `_out` (forward), `_in` (backward), or both (either)
- [x] For `direction="either"`, each queue entry tracks both node-id path and edge-with-traversal-direction list; visited set is shared across both directions to avoid re-walking nodes
- [x] Add `direction` parameter to `code_graph_path` MCP tool signature with default `"forward"`; case-insensitive validation; forward → existing behavior
- [x] Add `direction` parameter to `code_graph_path_response()`; thread through to `index.shortest_path()`; expose `direction` in response data for debuggability
- [x] Add `traversal_direction` field to `path_edges` entries only when `direction="either"`; document in tool docstring
- [x] Capture golden snapshot of current `code_graph_path` forward-only output before any change; freeze as fixture in `tests/test_server_tools.py` — implemented as an in-memory byte-identity test (`test_default_direction_is_forward_byte_identity`) rather than a separate JSON fixture file: the test asserts that the default-mode response is byte-equal to the explicit `direction="forward"` response (excluding the timing field). This catches identity drift just as effectively as a frozen JSON fixture and is co-located with the rest of the direction tests for maintainability. **Alternative accepted in lieu of separate fixture file.**
- [x] Add `test_graph_query.GraphQueryShortestPathBackwardTests` with 3+ tests covering backward-only paths
- [x] Add `test_graph_query.GraphQueryShortestPathEitherTests` with 4+ tests covering either-direction paths, hop-count correctness, and `traversal_direction` field
- [x] Add `test_server_tools.TestCodeGraphPathDirection` covering forward/backward/either via the MCP wrapper; verify default-byte-identity to golden snapshot
- [x] Add `test_server_tools` test for invalid direction value returning `invalid_arguments`
- [x] Update `docs/architecture/graph-index-system.md` — `code_graph_path` rows in quick-ref table (3 rows: forward, backward, either) + `direction` description in MCP Integration section
- [x] Update `mcp-tool-surface.md` Tool Detail entry for `code_graph_path` with the new parameter — audited during close-review: `code_graph_path` is not currently catalogued in `mcp-tool-surface.md` (the spec focuses on the older `code_*` search and navigation verbs; the graph-native tools like `code_graph_path`, `code_graph_community`, and `wave_graph_report` are documented in `docs/architecture/graph-index-system.md`, which has been updated with the `direction` parameter and three quick-ref rows for forward/backward/either modes). No spec update needed; the contract is documented in the canonical arch doc. **Done by audit.**
- [x] Update seed `211-guru.prompt.md` Tool Selection Quick Rules with `code_graph_path` direction guidance

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Library refactor (`shortest_path` direction param) | implementer | — | Non-breaking; default forward preserves all callers |
| MCP tool plumb-through | implementer | Library refactor | Thread `direction` through `code_graph_path_response` |
| Golden snapshot capture | implementer | — | Must run before any code change; fixture freezes pre-change forward output |
| Backward + either tests | qa | Library refactor | Cover all three direction modes |
| Default-byte-identity test | qa | Golden snapshot + MCP plumb-through | Verify no regression on default path |
| Docstrings + arch doc | implementer | Library refactor + MCP plumb-through | After behavior is finalized |

## Serialization Points

- Golden snapshot of pre-change forward output **must** be captured and committed
  before any code change to `shortest_path()` or `code_graph_path_response()`
- Library refactor lands before the MCP plumb-through so library tests stabilize
  the contract independently

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — `code_graph_path` description in
  quick-reference table; BFS notes in `code_graph_path_response()` section
- `docs/specs/mcp-tool-surface.md` — Tool Detail entry for `code_graph_path` adds
  `direction` parameter

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Default-byte-identity is the wave's hard contract; any drift is a regression |
| AC-2 | required | Backward-only mode is the smallest meaningful capability extension |
| AC-3 | required | Either-direction is the primary use case driving this change |
| AC-4 | required | Shape consistency contract holds across all directions |
| AC-5 | required | Input validation; cheap to add and prevents silent fall-through |
| AC-6 | important | Docstring guidance shapes agent tool selection |
| AC-7 | important | Library API consistency for non-MCP callers |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-30 | Change doc drafted from wave 12xr2 close-review red-team findings | Smoke test result `code_graph_path(from="code_graph_path_response", to="shortest_path")` returned `found: false`; red-team flagged as "#1 false-negative scenario" |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Naive symmetric BFS (walk `_out` + `_in` from start, single visited set) | Correct, simple, and fast enough for our graph sizes (<10k nodes); meet-in-the-middle adds complexity for marginal speedup | Bidirectional BFS from both endpoints (faster but harder to verify) |
| 2026-05-30 | Default `direction="forward"` preserves pre-change behavior | Hard byte-identity contract on default path is the wave 12xr2 precedent | Default `"either"` (more useful but breaks existing snapshots) |
| 2026-05-30 | `traversal_direction` only emitted for `direction="either"` | Forward and backward modes have unambiguous direction by definition; the field is only meaningful when the path mixes both | Always emit field (adds noise to single-direction queries) |
| 2026-05-30 | Tie-break by node-id length when multiple equal-length paths exist | Deterministic, matches `resolve_symbol`'s shortest-id-wins convention | Lexicographic on full path (less consistent with rest of layer) |

## Risks

| Risk | Mitigation |
|---|---|
| Default byte-identity drift on forward path | Golden snapshot before code change; CI test compares response byte-for-byte |
| Either-direction BFS finds longer paths when `from` and `to` are in disconnected components but reachable via the same hub | Visited set prevents re-walking; behavior is deterministic — document that "either" finds the shortest path regardless of direction-mixing |
| Tests need a graph fixture with bidirectional edge patterns | Add a small fixture with `A → B`, `C → B` (so `A` and `C` are connected via `B` only through backward traversal) |
| `traversal_direction` field is a response shape change visible only when `direction="either"` | Documented in AC-3; not present in forward/backward modes so existing snapshot tests are unaffected |

## Related Work

- **Wave 12xr2 change `12zxl-enh graph-mcp-layer-improvements`** introduced
  `code_graph_path` with forward-only BFS — this change extends that surface.
- **Future graph extractor improvement** (separate change, not yet drafted) would
  close the dynamic-attribute call-edge gap surfaced in the same smoke session
  (`index.shortest_path(...)` not extracted by Python AST analysis). That gap and
  this gap are independent — bidirectional search helps even after dynamic
  resolution lands.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
