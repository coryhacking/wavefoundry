# Graph Community Clustering

Change ID: `12xwy-enh graph-community-clustering`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The current graph UI is readable only by approximation: top hubs, file neighborhoods, and one-hop focus. That is useful, but it still leaves the operator doing the clustering in their head. A community pass gives the graph actual structural grouping so the dashboard can answer “what subsystem is this?” instead of only “what is highly connected?”

Graphify is the right implementation shape reference here. Its clustering is a separate post-processing step over persisted graph data, with `--cluster-only` / `cluster-only` reruns that do not re-extract the corpus. It also keeps community labels stable across re-clusterings by remapping them to prior labels when possible. Wavefoundry should borrow that separation: clustering should run after graph extraction, from persisted graph files, with no second repository walk and no change to the canonical graph format.

Graphify’s docs describe clustering as topology-based and driven by edge density. For Wavefoundry, the canonical graph stays directed, but the clustering pass should consume a derived undirected projection built from the persisted graph: each canonical edge contributes weight to an undirected pair `(min(source,target), max(source,target))`, reciprocal edges accumulate weight, and relation labels stay on the canonical graph rather than the cluster graph. That keeps the source of truth directional while giving the clustering algorithm the topology it needs.

The preferred backend for that pass is Leiden via `igraph` + `leidenalg`. The graph artifact stays the same regardless of backend, but the implementation should use Leiden when the dependency is present and fall back to the local deterministic pass only in minimal environments where the dependency is missing.

## Requirements

1. Add a topology-based clustering pass over persisted `project-graph.json` and `framework-graph.json`.
2. Keep the canonical graph unchanged and directed; compute community membership from a derived clustering view if the algorithm needs one.
3. Persist cluster metadata in a derived artifact per layer, versioned alongside the graph schema and graph builder state.
4. Make clustering rerunnable independently from extraction, so a graph refresh does not require re-parsing the repository.
5. Surface cluster-aware summaries in the dashboard so the first view can pivot from “hubs” to “communities” without exposing the full graph hairball.
6. Preserve stable community labels across reruns when the graph changes incrementally.
7. Keep the baseline local and deterministic: no embeddings, no LLMs, no media ingestion, and no vector database.
8. Add tests for cluster derivation, rerun stability, empty/small graph handling, and dashboard integration.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_server.py` if the cluster artifact needs a dedicated read path
- `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- graph extraction semantics
- graph file layout for the canonical graph
- query-tool augmentation
- LLM-derived edges or semantic clustering
- media/document ingestion changes

## Graphify Reference Implementation

Graphify keeps clustering separate from extraction. That is the useful bit to copy.

| Graphify module / feature | What it does | Wavefoundry takeaway |
| --- | --- | --- |
| [`graphify/cluster.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/cluster.py) | Community detection / grouping | Keep clustering as a separate post-processing pass over persisted graphs |
| [`graphify/analyze.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/analyze.py) | Centrality and cross-community analysis | Use the same style of summary to power cluster cards and bridge-node views |
| [`graphify/README.md`](https://github.com/safishamsi/graphify/blob/v4/README.md) | Documents `--cluster-only` / `cluster-only` reruns | Make clustering rerunnable without re-extraction |
| [`graphify` releases](https://github.com/safishamsi/graphify/releases) | Notes stable community-label remapping across re-clusterings | Preserve community identity across incremental rebuilds when possible |

Graphify’s key design point is that topology is the signal. No embeddings are required for the clustering itself. Wavefoundry should use the same rule: cluster from graph structure, not from a separate semantic vector layer.

## Cluster Artifact Contract

The derived cluster artifact should be a per-layer JSON file, separate from the canonical graph payload. The minimum fields are:

```json
{
  "cluster_schema_version": "1",
  "cluster_builder_version": "1",
  "layer": "project",
  "graph_schema_version": "1",
  "graph_builder_version": "1",
  "graph_graph_path": ".wavefoundry/index/project-graph.json",
  "community_count": 4,
  "communities": [
    {
      "community_id": "project:c0",
      "label": "core-indexing",
      "node_ids": ["..."],
      "seed_node_id": "...",
      "node_count": 42,
      "edge_count": 188,
      "boundary_node_count": 11
    }
  ]
}
```

`community_id` is the stable identity. `label` is the human-readable display label. `seed_node_id` is the representative anchor used for remapping. On reruns, Wavefoundry should remap communities to previous IDs by maximizing overlap of `node_ids` with the prior artifact; if overlap is too weak, allocate a new `community_id` and record the remap in the derived artifact or state file.

## Acceptance Criteria

- [x] AC-1: A clustering pass consumes existing graph files and produces per-layer community metadata without re-walking the repository.
- [x] AC-2: The canonical graph remains directed and unchanged; clustering operates on a derived undirected projection built from the persisted graph.
- [x] AC-3: Cluster metadata is versioned with `cluster_schema_version` / `cluster_builder_version` and records the source graph schema/version so incompatible changes force a clean recompute.
- [x] AC-4: Community labels remain stable across reruns by remapping new communities to prior `community_id` values using node-set overlap, or the artifact records when a new community was minted.
- [x] AC-5: The dashboard can surface cluster summaries and use them as a readable overview path into smaller neighborhoods.
- [x] AC-6: Tests cover cluster derivation, rerun stability, empty/small graph behavior, and dashboard wiring.

## Tasks

- [x] Add a graph clustering helper that reads the persisted graph payload and emits per-layer cluster metadata.
- [x] Define the derived cluster artifact shape and its versioning contract.
- [x] Wire the dashboard to consume cluster summaries for overview mode.
- [x] Add stable remapping for community labels across reruns.
- [x] Add tests for clustering and dashboard cluster summaries.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| cluster extraction | implementer | graph files | Build topology-only communities from the persisted graph |
| cluster persistence | implementer | cluster extraction | Write per-layer cluster metadata and preserve versioning |
| dashboard summary | implementer | cluster persistence | Render cluster-aware overview and drill-down affordances |
| tests | qa-reviewer | all implementation | Verify cluster derivation, reruns, and dashboard wiring |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` should describe clustering as a derived post-processing step over the persisted graph, not part of extraction.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Clustering must stay separate from extraction to keep rebuilds cheap and predictable |
| AC-2 | required | The canonical graph is the source of truth and should not be mutated for clustering |
| AC-3 | required | Versioning prevents stale community artifacts from surviving algorithm changes |
| AC-4 | important | Stable labels keep the dashboard readable across incremental updates |
| AC-5 | required | The point of clustering is to make the graph approachable by default |
| AC-6 | required | Cluster behavior needs coverage before it can influence the dashboard |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted from the Graphify clustering model and Wavefoundry’s current degree-based overview. | `graphify/cluster.py`, `graphify/analyze.py`, `graphify/README.md`, `graphify/releases` |
| 2026-05-27 | Implemented derived graph clustering with stable community remapping and dashboard cluster summaries. | `.wavefoundry/framework/scripts/graph_cluster.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/dashboard/dashboard.js`, `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Keep clustering as a derived pass over persisted graph files. | This mirrors Graphify’s `cluster-only` path and keeps the extraction pipeline stable. | Re-run extraction to regenerate communities — rejected because it duplicates work |
| 2026-05-27 | Preserve the canonical graph as directed while clustering on a projected undirected view. | `calls`, `imports`, and references are directional; clustering needs topology, not a mutation of the source of truth. | Store an undirected canonical graph — rejected because it weakens relation semantics |
| 2026-05-27 | Prefer stable community labels across reruns. | Dashboard summaries should not churn on every incremental rebuild. | Recompute cluster IDs freely on every run — rejected because it creates UI noise |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Community detection adds a new failure mode to graph refreshes | Keep clustering separate from extraction so the graph files remain available even if clustering needs a retry |
| Cluster labels may churn on incremental updates | Add remapping to previous community IDs where possible |
| The dashboard could become more complex instead of simpler | Use cluster summaries as the overview and keep the detailed node view one hop at a time |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
