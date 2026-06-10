# Graph Index System

Owner: Engineering
Status: active
Last verified: 2026-06-02

Architecture reference for Wavefoundry's code and documentation graph index: how it is generated, stored, traversed, clustered, and surfaced through MCP tools.

> **Line citations** reference `GRAPH_BUILDER_VERSION="25"` (current at wave 1p4eq close-out). Line numbers shift on builder version bumps — use function names as stable anchors when citing across versions.

---

## Quick Reference

| I want to… | Use this |
|---|---|
| Callers or callees of a function (one hop) | `code_callhierarchy(symbol, direction="incoming"/"outgoing")` |
| Full call tree to arbitrary depth | `code_callgraph(symbol, depth=N)` |
| Upstream blast radius of a change | `code_impact(symbol, max_hops=3)` |
| Shortest path between two symbols (forward dependency chain) | `code_graph_path(from_symbol=..., to_symbol=...)` |
| Reverse dependency chain ("who reaches me?") | `code_graph_path(from_symbol=..., to_symbol=..., direction="backward")` |
| Are two symbols connected at all (direction-agnostic) | `code_graph_path(from_symbol=..., to_symbol=..., direction="either")` |
| Members of a community cluster | `code_graph_community(community_id=...)` |
| Structural health report (fan-in/out, chokepoints, betweenness) | `wave_graph_report(layer="project"/"union", sections=["betweenness"])` |
| Graph index metadata (ambient) | MCP resource `wavefoundry://graph/status` |
| Community catalog (ambient — id, label, size, top members) | MCP resource `wavefoundry://graph/communities` |

**Layer modes**: `"project"` (project graph only), `"framework"` (framework graph only), `"union"` (merged; requires `networkx`).

**When the graph is absent**: `read_graph_payload()` returns `present=False`. All graph-backed tools degrade gracefully — `code_references` falls back to a full repository walk; `code_callhierarchy`, `code_callgraph`, `code_impact`, and `wave_graph_report` return a diagnostic response. The graph is absent until explicitly built. To build: `wave_index_build(content='graph')` (graph only) or `wave_index_build(content='all')` (graph + semantic index).

---

## Overview

The graph index is a persisted directed graph of nodes (files, symbols, and docs) and typed edges (calls, imports, defines, doc references, DI wiring). It is built separately from the semantic embedding index and stored as JSON artifacts on disk. The graph enables structural queries — call hierarchies, upstream impact analysis, cross-layer traversal, community detection — that semantic similarity search cannot answer.

The graph is **not** used for semantic search. It is used exclusively by graph-backed MCP tools and by `code_references` as a candidate-file restrictor to avoid full repository walks.

---

## Graph Schema

### Node Fields

Every node is a dict with these six fields, produced by `_node()` in `graph_indexer.py:490-506`:

| Field | Type | Description |
|---|---|---|
| `id` | str | Unique node identifier (e.g. `src/billing.py::charge`) |
| `label` | str | Short human-readable name |
| `kind` | str | Node type; see table below |
| `source_file` | str | Repo-relative path of the owning file |
| `source_location` | str | `"line:col"` offset within `source_file` |
| `layer` | str | `"project"` or `"framework"` |

Three boolean annotations are written directly onto module-level node dicts during `finalize()` at `graph_indexer.py:2076-2123`:

| Field | Meaning |
|---|---|
| `is_entry_point` | Module imported by nothing external but has outgoing edges |
| `dead_code_risk` | Module whose symbols are never externally called or imported |
| `is_chokepoint` | Articulation point in the undirected executable subgraph (requires `igraph`) |

### Node Kinds

| Kind | Source |
|---|---|
| `module` | Every file's root node; also namespaces and packages |
| `function` | Functions, methods, async functions, constructors |
| `class` | Classes, interfaces, structs, enums, traits |
| `doc` | Markdown and plain-text doc files |
| `seed` | Files under `.wavefoundry/framework/seeds/` |

External symbols (imported from outside the repo) are represented as nodes with ids prefixed `external::` (e.g. `external::pathlib.Path`). There is no explicit `kind` field for external nodes; they are identified and filtered by the `external::` id prefix.

### Edge Fields

Every edge is a dict produced by `_edge()` at `graph_indexer.py:509-525`:

| Field | Type | Description |
|---|---|---|
| `source` | str | Node id of the edge origin |
| `target` | str | Node id of the edge destination |
| `relation` | str | Edge type; see table below |
| `confidence` | str | `"EXTRACTED"`, `"AMBIGUOUS"`, or `"INFERRED"` |
| `evidence` | str? | Optional provenance string |

### Edge Relations

| Relation | Produced by | Meaning |
|---|---|---|
| `defines` | `graph_indexer.py:1179, 1344, 1511` | Module declares a symbol |
| `calls` | `graph_indexer.py:1297, 1597` | Symbol invokes another symbol |
| `imports` | `graph_indexer.py:1197, 1208, 1372, 1380, 1529` | Module imports an internal or external module |
| `doc_references_code` | `graph_indexer.py:1699` | Doc node mentions a code node |
| `doc_references_doc` | `graph_indexer.py:1735` | Doc node links or path-references another doc |
| `binds` | `graph_di_signals.py:285-293` | DI interface bound to an implementation |
| `injects` | `graph_di_signals.py:329-337` | DI consumer depends on an injected type |

---

## Generation Pipeline (`graph_indexer.py`)

### Versioning

Four constants gate incremental reuse (`graph_indexer.py:25-35`):

```
GRAPH_SCHEMA_VERSION  = "1"
GRAPH_BUILDER_VERSION = "25"
```

A full re-extraction is forced whenever any of `schema_version`, `builder_version`, `walker_version`, or `chunker_version` changes — detected by `_load_state()` at `graph_indexer.py:1044-1061`.

### Entry Point

`update_graph_index()` at `graph_indexer.py:2163-2226` is the public entry point. It instantiates a `GraphIndexSession`, detects version bumps, calls `session.record_file()` for each changed file, and calls `session.finalize()` to produce the final graph payload.

### File Types Processed

Doc extensions: `.md`, `.markdown`, `.txt`.

Code extensions: approximately 50 suffixes including `.py`, `.js`/`.jsx`/`.mjs`/`.cjs`, `.ts`/`.tsx`, `.go`, `.rs`, `.java`, `.scala`, `.cs`, `.c`/`.cpp`, `.h`/`.hpp`, `.sh`/`.bash`/`.zsh`/`.fish`, `.tf`/`.hcl`, `.kt`/`.swift`, `.rb`, `.php`, `.yaml`/`.yml`, `.toml`, `.json`/`.jsonc`, `.css`/`.scss`, `.html`/`.htm`, `.sql` variants, `.xml`/`.svg`, and special filenames (`Makefile`, `Dockerfile`, `Gemfile`). Minified files (`.min.`, `.prod.`, `.production.`, `.bundle.`, `.chunk.` in filename) are excluded (`graph_indexer.py:125-127, 271-274`).

### Call Edge Extraction

Three strategies are selected by file type (`graph_indexer.py:1621-1654`):

**Python** (`graph_indexer.py:1143-1318`): Full `ast` module walk via `CallCollector(ast.NodeVisitor)`. Resolves `ast.Call` nodes by matching `ast.Name` and `ast.Attribute` nodes against `import_aliases` and `symbol_lookup`. Confidence: `"EXTRACTED"`.

**JS/TS without tree-sitter** (`graph_indexer.py:1406-1419`): Regex `_JS_CALL_RE` scans each line. Fires only when the tree-sitter grammar is unavailable.

**All other languages with tree-sitter** (`graph_indexer.py:1479-1619`): `_extract_tree_sitter_artifact()` performs a two-pass AST walk: `walk_definitions()` builds the symbol table, then `walk_calls()` traverses call-node types identified by `_ts_is_call_node()`. Target resolution via `_ts_resolve_target()` checks `import_aliases`, then `symbol_lookup`, then falls back to an `external::name` node (`graph_indexer.py:986-1003`).

### Import Edge Extraction

- **Python**: `ast.Import` and `ast.ImportFrom` statements in `collect_imports_and_defs()` (`graph_indexer.py:1187-1208`). Creates `external::module.name` target nodes.
- **JS/TS regex fallback**: `_JS_IMPORT_RE` and `_JS_REQUIRE_RE` patterns (`graph_indexer.py:1349-1381`).
- **Tree-sitter**: `_ts_is_import_node()` pattern matching, then `_ts_relation_candidates()` extracts target names (`graph_indexer.py:1525-1530, 1567-1571`).

### `doc_references_code` Edge Extraction (`graph_indexer.py:1660-1749`)

`_extract_doc_artifact()` uses two-step symbol matching:

1. **Simple terms** (no dots): Looked up in a `simple_lower` dict (label → node id set). Only fires for terms appearing inside backtick inline spans. Minimum term length: 6 chars (`_MIN_DOC_MATCH_TERM_LEN`, `graph_indexer.py:123`). Common stop-terms are excluded (`graph_indexer.py:98-115`).

2. **Complex terms** (dotted or path-like): A combined compiled regex matches across all code contexts (fenced blocks and inline backticks), built by `_compile_doc_matcher()` (`graph_indexer.py:1787-1816`).

Confidence is `"EXTRACTED"` for unique matches of long or underscore-containing terms, `"AMBIGUOUS"` otherwise (`graph_indexer.py:390-397`).

Markdown links and backtick file paths to known files produce `doc_references_doc` edges (`graph_indexer.py:1729-1735`).

### Disk Artifacts

Written by `_write_json()` as pretty-printed JSON with sorted keys (`graph_indexer.py:554-556`):

| Artifact | Path |
|---|---|
| Project graph | `.wavefoundry/index/graph/project-graph.json` |
| Framework graph | `.wavefoundry/framework/index/graph/framework-graph.json` |
| Project state | `.wavefoundry/index/graph/project-graph-state.json` |
| Framework state | `.wavefoundry/framework/index/graph/framework-graph-state.json` |

### `read_graph_payload()` (`graph_indexer.py:2229-2254`)

Returns a dict with: `layer`, `schema_version`, `nodes` (list), `edges` (list), `counts` (files/nodes/edges ints), `present` (bool), `graph_path` (repo-relative string). When the file is absent or empty: `present=False`, empty `nodes`/`edges`.

---

## DI Signal Extraction (`graph_di_signals.py`)

### Scope

Extracts dependency-injection wiring and resolves it into `"binds"` and `"injects"` graph edges. Active only for Java/Kotlin (`.java`, `.kt`, `.kts`) and C# (`.cs`) files (`graph_di_signals.py:47-53`).

### Signals

`collect_di_signals()` dispatches to two language handlers:

**Java/Kotlin** (`graph_di_signals.py:56-134`):
- `bind().<to>()` Guice/Dagger patterns → `kind: "binds"`, confidence `"EXTRACTED"`.
- Spring stereotypes (`@Component`, `@Service`, `@Repository`, `@Controller`, etc.) on classes implementing interfaces → `kind: "binds"`, confidence `"INFERRED"`.
- Injectable constructor parameters in annotated classes → `kind: "injects"`, confidence `"INFERRED"`.
- `@Bean` methods → `kind: "binds"`, confidence `"EXTRACTED"`.

**C#** (`graph_di_signals.py:137-191`):
- `AddSingleton<I,C>()`, `AddScoped<I,C>()`, `AddTransient<I,C>()`, `AddHostedService<I,C>()` → `kind: "binds"`, confidence `"EXTRACTED"`.
- Autofac `RegisterType<C>().As<I>()` → `kind: "binds"`, confidence `"EXTRACTED"`.
- Constructor parameter injection patterns → `kind: "injects"`, confidence `"INFERRED"`.

### Integration

DI signals are collected from `_extract_code_artifact()` and stored as `artifact["di_signals"]`. During `session.finalize()`, `resolve_di_edges()` (`graph_di_signals.py:245-338`) receives the full artifact map and node map, builds a `type_index` from all class/function nodes, resolves `binds` signals first (building `binds_map`), then resolves `injects` signals using `binds_map` to find concrete implementations. Output is a list of `{source, target, relation, confidence, evidence}` dicts appended to the global edge list.

---

## Query Layer (`graph_query.py`)

### In-Memory Index (`GraphQueryIndex.__init__()`, `graph_query.py:123-141`)

Builds three structures from the payload:

| Structure | Type | Purpose |
|---|---|---|
| `_node_by_id` | `dict[str, dict]` | O(1) node lookup by id |
| `_out` | `dict[str, list[dict]]` | Source id → outgoing edges |
| `_in` | `dict[str, list[dict]]` | Target id → incoming edges |

### `resolve_symbol()` (`graph_query.py:152-176`)

Three-tier resolution:

1. **Exact match**: `symbol in _node_by_id` — returns immediately.
2. **Suffix match**: Scans all node ids for those ending with `f"::{symbol}"`. One match returns it; multiple matches return the shortest id (most-specific path prefix).
3. **Label match**: Scans all nodes for `node["label"] == symbol` or `nid.split("::")[-1] == symbol`. Returns the single result, or `None` if ambiguous.

### `traverse()` (`graph_query.py:178-225`)

BFS over the adjacency index. Parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `start_id` | required | Seed node |
| `relations` | `None` (all) | Optional set filter on `edge["relation"]` |
| `max_hops` | `1` | Stops enqueuing at `depth >= max_hops` |
| `direction` | `"callees"` | `"callees"` (`_out`), `"callers"` (`_in`), `"both"` |

Returns `(visited: set[str], traversed: list[dict], has_cycles: bool)`. Edges are deduplicated by `(source, target, relation)`. When a neighbor already in `visited` is re-encountered, `has_cycles=True` and the back-edge is still included in `traversed`.

### `one_hop_neighbors()` (`graph_query.py:227-263`)

Accepts multiple seed node ids. For each seed, collects all edges from both `_out` and `_in` (optionally filtered by relations) and includes both endpoints in the result nodes dict. Does not recurse. Returns `{present, layer, nodes, edges, note}`. Used by `code_references` graph-neighbor expansion when `graph=True`.

### `graph_impact()` (`graph_query.py:265-307`)

Resolves `symbol` → `node_id`, calls `traverse(direction="callers", relations=("imports","calls"), max_hops=max_hops)`. Default `max_hops=3`. Discards the start node from `visited`. Returns `{symbol, resolved, node_id, affected, affected_files, edges, has_cycles, max_hops, relations}`.

### `callgraph()` (`graph_query.py:309-335`)

Resolves `symbol` → `node_id`, calls `traverse(relations=("calls",), max_hops=depth, direction=direction)`. Default `depth=1`, `direction="both"`. Returns `{symbol, resolved, node_id, depth, direction, nodes, edges, has_cycles}`.

### `report()` (`graph_query.py:337-425`)

Iterates `self.edges` once, counting only `relation == "calls"` edges, then computes the requested sections:

| Section | What it computes |
|---|---|
| `fan_in` | Top-`limit` nodes by incoming call count |
| `fan_out` | Top-`limit` nodes by outgoing call count |
| `orphan_docs` | Doc/seed nodes (`_DOC_KINDS = {"doc","seed"}`) with no `doc_references_code` outgoing edge, or zero edges total |
| `chokepoints` | Nodes with `fan_out >= chokepoint_threshold` (default `_CHOKEPOINT_FAN_OUT = 20`) |
| `cross_layer` | Edges where `src_layer != tgt_layer` (only when `self.layer == "union"`) |

### `load_union()` (`graph_query.py:52-115`)

Loads project and framework payloads separately into two `nx.DiGraph` objects, tagging project nodes `layer="project"` and framework nodes `layer="framework"`. Calls `networkx.compose()` to merge them. Union mode (`layer="union"`) requires `networkx`; **single-layer queries (`layer="project"` or `layer="framework"`) do not**. When `networkx` is unavailable, `load_union()` returns `present=False` with `diagnostic="networkx_unavailable"`.

---

## Community Clustering (`graph_cluster.py`)

### Versioning

```
CLUSTER_SCHEMA_VERSION  = "1"
CLUSTER_BUILDER_VERSION = "8"
```

### Input Projection (`graph_cluster.py:319-348`)

`_project_undirected_projection()` converts the directed graph to a weighted undirected adjacency dict. External nodes (id starts with `external::`) are excluded. Edge weights are accumulated per undirected pair:

| Relation | Weight |
|---|---|
| `calls` | 3 |
| `imports` | 2 |
| `defines` | 1 |
| `doc_references_code` | 1 |

### Fixed Communities (`graph_cluster.py:228-293`)

Before the clustering algorithm runs, nodes are pre-assigned to fixed communities based on `node["kind"]` (for docs) and source file path patterns:

- **Documentation** — doc and seed kind nodes
- **Tests** — files matching test path patterns
- **Benchmarks** — benchmark path patterns
- **CI/CD** — CI/CD path patterns
- **Generated** — generated file path patterns
- **Scripts** — script path patterns
- **Configuration** — config file path patterns

Fixed community nodes are removed from the adjacency dict before the algorithm runs, then appended to the result with `kind: "fixed"` (`graph_cluster.py:799-800`).

### Clustering Algorithm (`graph_cluster.py:296-305, 351-427`)

**Primary**: Leiden algorithm via `leidenalg.find_partition` with `RBConfigurationVertexPartition`, `seed=0`. Requires both `igraph` and `leidenalg` Python packages.

**Fallback**: Label propagation (`_label_propagation()`, `graph_cluster.py:430-485`). Runs 24 fixed iterations, processing nodes in descending degree order and picking the highest-weight neighbor label. Used when the Leiden backend is unavailable.

The `cluster_algorithm` field in the output artifact records which algorithm ran (`graph_cluster.py:806`).

### Post-Processing

Four passes run after the algorithm (`graph_cluster.py:504-758`):

1. **Remap** (`_remap_clusters()`): Assigns stable `community_id` strings (e.g. `"project:c0"`) by matching new clusters to previous by node-set overlap. Preserves user-edited labels when a match is found.
2. **Merge same-stem** (`_merge_same_stem_communities()`): Merges communities whose seed nodes share the same directory and filename stem.
3. **Merge small** (`_merge_small_communities()`): Iteratively absorbs non-fixed communities below `MIN_COMMUNITY_SIZE = 12` into their most-connected neighbor.
4. **Disambiguate** (`_disambiguate_labels()`): Qualifies duplicate labels with parent directory, then adds numeric suffixes.

### Cluster Artifacts

| Artifact | Path |
|---|---|
| Project clusters | `.wavefoundry/index/graph/project-graph-clusters.json` |
| Framework clusters | `.wavefoundry/framework/index/graph/framework-graph-clusters.json` |

Each community record contains: `community_id`, `label`, `seed_node_id`, `node_ids`, `node_count`, `edge_count`, `boundary_node_count`, and optionally `kind: "fixed"`.

---

## MCP Integration (`server_impl.py`)

### Graph-Assisted `code_references`

`_graph_references_candidate_files()` at `server_impl.py:9326-9352` is called unconditionally from `code_references_response()` at line 8588. It loads the project graph, resolves the queried symbol to a `node_id`, reads `index._in[node_id]` (incoming edges), and extracts `source_file` from each edge's source node. Returns a `frozenset[str]` of repo-relative paths, or `None` when the graph is absent, the symbol is unresolvable, or there are no incoming edges.

When `restrict_files` is non-`None`, all three reference searchers (`_python_references`, `_treesitter_references`, `_non_python_references`) receive a pre-built `_files` list of `Path` objects, bypassing `_walk_repo_for_navigation()` entirely. The response includes `"graph_assisted": True/False` at `server_impl.py:8667, 8700`.

### `code_callhierarchy_response()` (`server_impl.py:8896-9047`)

1. Loads `GraphQueryIndex.from_root(root, layer="project")`.
2. Resolves the symbol, optionally qualifying with the `file` param by trying `file::symbol` first (`server_impl.py:8938-8943`).
3. **Outgoing** (callees): `index.traverse(node_id, relations=["calls"], max_hops=1, direction="callees")`. Collects all non-external callee names, calls `_scan_all_call_sites_in_file()` once on `definition_file`, uses `_first_call_site_at_or_after()` to pick the first call site at or after the caller's `source_location` line.
4. **Incoming** (callers): `index.traverse(node_id, relations=["calls"], max_hops=1, direction="callers")`. Groups callers by source file. Calls `_scan_call_sites_in_file()` once per unique source file for the target symbol. Attributes call sites to callers in ascending-definition-line order using a `used_lines` set to prevent double-attribution.
5. Each node entry carries a `community` field populated from `_load_cluster_lookup(root)`.
6. When `context_depth > 0`, all immediate caller/callee node ids are gathered into a set, then a single combined `traverse(max_hops=1, direction="both")` is called per immediate neighbor; expanded neighbors (not already known) are appended as a `context` list.
7. When the symbol is unresolvable, `_suggest_near_symbols(index, symbol)` populates a `suggestions` list in the response.

### `code_callgraph_response()` (`server_impl.py:9610-9716`)

Calls `index.callgraph(symbol, depth=max(1,depth), direction=direction_value)`. When `include_tests=False` (default), nodes whose `source_file` matches `_is_test_path()` patterns are dropped, and edges referencing those filtered nodes are also dropped — keeping the subgraph internally consistent. Symmetric with `code_impact`'s filter. Enriches each remaining `"calls"` edge with a `"line"` field: groups all edges by source file, calls `_scan_all_call_sites_in_file()` once per unique source file, then calls `_first_call_site_at_or_after()` per edge using the source node's `source_location` as the start line.

### `code_definition_response()` — graph-narrowed lookup

Calls `_graph_definition_candidate_files(root, symbol)` first. The helper iterates the project graph's `_node_by_id` and collects `source_file` paths from nodes whose `label == symbol`, whose id ends with `::<symbol>`, or whose label contains the symbol as a substring — mirroring the scanner predicate `name == symbol or symbol in name`. Returns `None` when the graph is absent or fails to load; returns an empty frozenset when graph is present but no candidates match.

The response carries a `lookup_method` field with one of five values:

- `graph_narrowed` — graph candidate set was non-empty on the first query; the four scanners (`_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions`) skipped the full repo walk entirely and constructed file paths directly from the restriction set. Typical latency: <300ms on this repo (down from 38–43s pre-change).
- `graph_narrowed_after_refresh` — first query returned an empty candidate set, so an incremental graph refresh (`wave_index_build_response(content="graph", mode="update")`) ran (~4ms when nothing has changed); after refresh the candidate set was non-empty and scanners ran on the restricted set. This handles the recently-added-code case.
- `graph_definitive_not_found` — refresh ran and the candidate set was still empty; since the structural scanners share the same file scope the graph extractor uses, walking the tree again would burn 40+s for nothing. The graph is treated as the source of truth and a fast not-found response is returned with a diagnostic suggesting `code_keyword` for symbols in file types the graph does not index. Typical latency: <300ms.
- `graph_index_missing_degraded` — graph never built; the structural scanners run their existing four-pass repo walk (pre-1301h behavior, 40+s cold). The response carries a `graph_index_missing_degraded` advisory diagnostic telling the operator to run `wave_index_build(content="graph")` once to switch all subsequent calls to the sub-300ms `graph_narrowed` path. The walk still runs so callers that depend on `name`-bearing structural definitions (the existing test suite, for example) keep working through initial setup.
- `keyword_fallback` — structural scanners produced no result and the broad `_keyword_fallback_definitions` walker ran as a last resort. Reachable when the graph is absent and the symbol has no structural definition anywhere, or when the graph is present and refers to a stale candidate file that no longer contains the symbol.

Substring-match semantics are preserved across all paths because the candidate helper uses the same `name == symbol or symbol in name` predicate the scanners use. The graph-narrowed path is guaranteed (by `TestCodeDefinitionGraphNarrowed.test_graph_narrowed_path_finds_correct_definition` and `test_missing_symbol_with_graph_returns_definitive_not_found`) to return the same definition set as the structural walk for symbols the graph knows about. (Wave `12xr3`, change `1301h`.)

### Graph-Tool Miss Behavior — Refresh-and-Instruct Contract (wave `1304x`, change `1304r`)

The pattern established by `1301h` for `code_definition` is now applied uniformly across the seven other graph-using MCP tools: `code_references`, `code_callhierarchy`, `code_callgraph`, `_code_impact_graph_response` (graph mode of `code_impact`), `code_graph_path`, `code_graph_community`, and `wave_graph_report`. Every miss path attempts an incremental graph refresh before emitting suggestions or not-found.

**Shared helpers in `server_impl.py`:**

- `_graph_refresh_then_recheck(root, recheck_fn)` — generic primitive that calls `wave_index_build_response(root, content='graph', mode='update')` then invokes the supplied `recheck_fn()`. Returns `recheck_fn`'s result on success, or `None` on any exception. The refresh side-effect is centralized here; the six call sites only own the recheck closure.
- `_graph_refresh_and_resolve(root, symbol, layer)` — convenience for the common symbol-resolution case. Refreshes, reloads `GraphQueryIndex`, calls `resolve_symbol(symbol)`, and returns `(fresh_index, node_id)` on hit or `(None, None)` on miss / refresh failure. `code_callhierarchy_response`, `code_callgraph_response`, and `_code_impact_graph_response` consume this helper.

**Per-tool miss behavior:**

- `code_references_response()` — when `_graph_references_candidate_files()` returns `None` on first query, retries via `_graph_refresh_then_recheck`. Preserves the existing 176ms-range fast path; the refresh only fires when the symbol isn't in the graph.
- `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()` — when `index.resolve_symbol(symbol)` returns `None`, calls `_graph_refresh_and_resolve()`. On hit, swaps in the fresh index and proceeds normally; on miss, emits a `graph_symbol_not_found` diagnostic with `recovery_tools=["code_definition", "code_keyword"]` and the existing suggestions list.
- `code_graph_path_response()` — when either `from_id` or `to_id` is `None`, runs an inline refresh-then-recheck that resolves BOTH symbols against the freshly loaded index (the generic helper rather than `_graph_refresh_and_resolve` is used here, because the helper's return contract discards the fresh index when its single target symbol still misses post-refresh). When at least one symbol remains unresolved, emits `graph_symbol_not_found` with a message that names the missing symbol(s).
- `code_graph_community_response()` — when the requested `community_id` is absent from the cluster artifact, `_graph_refresh_then_recheck` re-reads the (possibly re-clustered) artifact. On hit, proceeds normally; on miss, emits `not_found` with the existing community-suggestions list.
- `wave_graph_report_response()` — when `index.present` is `False` on first load, refresh-then-recheck reloads the index. On hit, the report proceeds normally; on miss, emits the existing `graph_not_ready` diagnostic.

**Diagnostic vocabulary** — three codes carry consistent recovery hints across all seven tools:

- `graph_index_missing_degraded` — graph index never built; advisory in `code_definition` `1301h` path; recovery: `wave_index_build(content='graph')`.
- `graph_not_ready` — graph layer absent and no fallback exists; emitted by `code_callhierarchy`, `code_callgraph`, `code_impact` (graph mode), `code_graph_path`, `wave_graph_report` via `gq.graph_not_ready_diagnostic(layer)`; recovery: `wave_index_build(content='graph')`.
- `graph_symbol_not_found` — incremental refresh ran and the symbol still doesn't resolve; emitted by the four symbol-resolution tools; recovery: `code_definition` (try a broader symbol lookup) or `code_keyword` (try literal-text search for symbols in file types the graph extractor doesn't cover).

**Latency budget** — incremental graph refresh is ~4ms when nothing has changed (measured during wave `12xr3` close-review). The fast path (symbol-in-graph on first query) pays zero overhead because the refresh branch is gated behind the miss. The miss-plus-refresh path stays well under 1s on this repo (live smoke at wave close: 304ms for `code_callhierarchy` triggering a real refresh; 753ms for a never-resolves bogus symbol including the suggestions scan).

Test coverage: `TestGraphRefreshThenRecheck`, `TestGraphRefreshAndResolve`, and `TestGraphToolRefreshOnMiss` in `tests/test_server_tools.py` cover the helpers' unit behavior and verify each of the seven tools triggers exactly one refresh call on its miss path. The 1301h regression suite continues to pass, confirming `code_definition` was not affected by the helper extraction.

### `code_impact_response()` (`server_impl.py:9579-9604`)

Two modes:

- **Graph mode** (`symbol=` param): `_code_impact_graph_response()` calls `index.graph_impact(symbol, max_hops=max(1,max_hops), relations=relations)`. Default relations: `("imports","calls")`, `max_hops=3`. Supports `layer` param (project/framework/union). Truncates `affected` at `max_results=50`. Each affected node carries a `community` field from `_load_cluster_lookup(root)`. When `include_tests=False` (default), nodes whose `source_file` matches `_is_test_path()` patterns are excluded from `affected`.
- **Heuristic mode** (`path=` param): File-based reverse-import search. Does not use `graph_query.py`.

### `code_graph_path_response()`

Resolves both `from_symbol` and `to_symbol` via `index.resolve_symbol()`. When either is unresolvable, returns `found=False` with `suggestions` from `_suggest_near_symbols()`. Otherwise calls `index.shortest_path(from_id, to_id, relations=relations, max_hops=max_hops, direction=direction)`. Always returns the consistent shape `{found, path_nodes, path_edges, hop_count, direction, suggestions}`.

The `direction` parameter (added in wave `12xr3`) controls which adjacency lists BFS may walk: `forward` (default — outgoing edges only, byte-identical to pre-13006 behavior), `backward` (incoming edges only, answering "who reaches me?"), or `either` (both — for general coupling questions). In `either` mode, every entry in `path_edges` carries an extra `traversal_direction` field (`"forward"` or `"backward"`) so the chain is unambiguous. Candidate edges at each BFS step are sorted by neighbor-id length so output is deterministic when multiple equal-length paths exist. Invalid direction values return `invalid_arguments` with the consistent shape preserved.

### `code_graph_community_response()`

Loads the cluster artifact via `_load_cluster_lookup()` / `graph_cluster.read_cluster_payload()`. Validates `community_id` is non-empty (returns `invalid_arguments` otherwise — closes the empty-string-matches-null-id edge case). Looks up the requested `community_id`; returns `{community_id, label, node_count, nodes}` where `nodes` are sorted by degree descending. On not-found, returns `suggestions: [{community_id, label, node_count}, …]` ranked by id/label substring match then node count — up to 5 entries — via `_suggest_near_communities()`. For ambient catalog discovery without a tool call, prefer the `wavefoundry://graph/communities` resource.

### `wave_graph_report_response()`

Loads `GraphQueryIndex.from_root(root, layer=layer_value)`, calls `index.report(limit=max(1, min(limit, 100)), sections=sections)`. Limit is clamped to `[1, 100]`. Defaults to all five standard sections when `sections=None`. The `betweenness` section (opt-in via `sections=["betweenness"]`) computes igraph betweenness centrality over the calls-only subgraph; returns `diagnostic: "graph_too_large_for_betweenness"` when node count exceeds `_BETWEENNESS_NODE_LIMIT` (10,000) or `diagnostic: "igraph_unavailable"` when igraph is not installed.

### `_scan_all_call_sites_in_file()` (`server_impl.py:9373-9426`)

Scans a single file exactly once for a list of callee labels:

- **Python**: Parses with `ast`, walks all `ast.Call` nodes, matches against the full `label_set` in one pass. Returns `{label: [sorted call-site dicts]}`.
- **Non-Python**: Iterates `callee_labels` and calls `_treesitter_references()` then `_non_python_references()` per label against the single restricted file.

Called from `code_callhierarchy_response()` (outgoing direction, `server_impl.py:8993`) and `code_callgraph_response()` (per source file, `server_impl.py:9677`).

---

## Build Pipeline

### Wiring

`wave_index_build(content='graph')` invokes `setup_index.py --graph-only --root <root>` (`server_impl.py:2479-2480`). The `--graph-only` flag (`setup_index.py:757, 787-792`) routes to `run_index_rebuild(content="graph")` inside `setup_index.py`, which calls `_build_graph_artifacts()` in `indexer.py:1582-1642`:

```
wave_index_build(content='graph')
  → setup_index.py --graph-only
    → indexer._build_graph_artifacts()
      → graph_indexer.update_graph_index()   → project-graph.json + state
      → graph_cluster.update_graph_clusters() → project-graph-clusters.json
```

Semantic embedding (LanceDB) is skipped entirely in graph mode (`indexer.py:1938-1939`).

### Incremental vs. Full Rebuild

The graph build is **incremental by default**. `update_graph_index()` receives `changed` and `removed` file sets and only calls `session.record_file()` for files in `changed`. Unchanged files reuse their cached artifact from the state file. Files in the `removed` set have their cached artifacts excluded from the merged output during `session.finalize()` — removed-file nodes and edges do not persist into the next build's payload.

A full re-extraction is forced when:
1. The state file is absent or empty (first build).
2. Any version constant changes (`schema_version`, `builder_version`, `walker_version`, `chunker_version`) — detected by `_load_state()` at `graph_indexer.py:1044-1061`.
3. The state's `"files"` dict is empty after loading — `update_graph_index()` expands `changed_set` to all files (`graph_indexer.py:2191-2202`).

Additionally, when code files change, doc artifacts that referenced changed symbols are automatically re-scanned via the `impacted_docs` pass at `graph_indexer.py:1886-1931`.

### Staleness Check

`_index_is_up_to_date()` always returns `False` for `content="graph"` (`server_impl.py:2194-2196`). The staleness gate is bypassed so the build always enters the incremental extraction logic — but this does not mean every file is re-extracted. Within that logic, only files in the `changed_set` are re-extracted; unchanged files reuse their cached state artifacts. Bypassing the gate means the caller never short-circuits before entering the logic, not that the logic discards incremental state.

### Separation from Semantic Index

`content="graph"` and `content="docs"` / `content="code"` are completely independent pipelines. The graph pipeline writes JSON artifacts only. The semantic pipeline runs LanceDB embedding and does not call `_build_graph_artifacts()`. `content="all"` (via `setup_index.py --include-code`) runs both.

---

## Implementation Paths

| Concern | Entry point | Key file |
|---|---|---|
| Build the graph | `update_graph_index()` | `graph_indexer.py:2163` |
| Read the graph from disk | `read_graph_payload()` | `graph_indexer.py:2229` |
| Load into memory | `GraphQueryIndex.__init__()` | `graph_query.py:123` |
| Resolve a symbol | `GraphQueryIndex.resolve_symbol()` | `graph_query.py:152` |
| BFS traversal | `GraphQueryIndex.traverse()` | `graph_query.py:178` |
| Cluster communities | `update_graph_clusters()` | `graph_cluster.py` |
| Extract DI edges | `resolve_di_edges()` | `graph_di_signals.py:245` |
| MCP: callers/callees | `code_callhierarchy_response()` | `server_impl.py:8896` |
| MCP: call tree | `code_callgraph_response()` | `server_impl.py:9610` |
| MCP: blast radius | `code_impact_response()` | `server_impl.py:9579` |
| MCP: shortest path | `code_graph_path_response()` | `server_impl.py:9864` |
| MCP: community members | `code_graph_community_response()` | `server_impl.py:9951` |
| MCP: structural report | `wave_graph_report_response()` | `server_impl.py:9719` |
| MCP: reference restriction | `_graph_references_candidate_files()` | `server_impl.py:9326` |
| MCP: definition narrowing | `_graph_definition_candidate_files()` | `server_impl.py` |
| MCP resource: graph status | `wavefoundry://graph/status` | `server_impl.py` |
| MCP resource: community catalog | `wavefoundry://graph/communities` | `server_impl.py` |

## Related Docs

- `docs/architecture/search-architecture.md` — semantic index layers; how graph and semantic search are separate pipelines
- `docs/architecture/chunking-and-indexing-pipeline.md` — semantic embedding pipeline that runs alongside graph extraction in `content="all"` mode
- `docs/specs/mcp-tool-surface.md` — MCP tool surface specification; see "Navigation Tools" section for graph-backed tool descriptions and "Which Code Tool To Use" table for selection guidance
