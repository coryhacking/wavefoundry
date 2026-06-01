# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-06-01

## Active Wave

**Wave:** `12xr2 graph-query-surface`  
**Status:** active — all five admitted changes implemented (uncommitted)

**Complete (uncommitted):**
- `12z48-bug stale-index-build-lock-cleanup` — liveness-aware lock, hook debounce, meta-only staleness
- `12z4a-bug test-file-detection-case-conventions` — multi-language fixed-community classifiers (`CLUSTER_BUILDER_VERSION=8`)
- `12xs4-feat graph-query-surface` — `graph_query.py`, `code_callgraph`, `wave_graph_report`, graph `code_impact`, `graph=true` augmentation on four MCP tools
- `12ynp-enh graph-dependency-injection-wiring` — `graph_di_signals.py`, `binds`/`injects` edges, `GRAPH_BUILDER_VERSION=4`
- `12yro-enh graph-visualization-navigation-overhaul` — WebGL `GraphWebGLView` (`force-graph` + `elkjs`), per-view layouts (force / ELK / radial), `GraphTreeNav` peer, server `degree`/`community_id` enrichment, SVG/`_layoutGraph` removed

**Tests:** 1797 framework tests passing (2026-05-29).

**Next:** Operator review diff; run **Review wave** lanes; commit when ready; close wave on operator instruction.

**Graph rebuild (2026-05-29):** Project graph ~4558 nodes / ~29479 edges. Framework graph ~125 nodes. Union layer works after `networkx` in tool venv.

**Bugfix (2026-05-29):** `graph_indexer.update_graph_index` re-extracts full corpus when graph state is empty.

## AC-1 Graph Size Measurement (12yro)

Recorded 2026-05-29 after full project graph rebuild:

| Layer | Nodes | Edges | Notes |
|-------|-------|-------|-------|
| project | 4557 | 29479 | includes scripts + dashboard + tests in project layer |
| framework | 125 | 1311 | pack-filtered docs/config only |
| union | compose | — | `wave_graph_report(layer=union)` OK after rebuild + networkx |

**Tier decision:** Lighter `force-graph` + ELK; rendered views capped (≤24 communities overview, ≤120 detail, 1-hop focus via neighbors API).

## Last Closed Wave

**Wave:** `12xr1 graph-index-extraction` — shipped 2026-05-29 (commit `60cc21a`)

## Open Questions / Deferred Decisions

- `12z4a` AC-18: operator graph rebuild + spot-check on external Swift repo.
- Commit when ready — all wave code is local/uncommitted.
- FA2 worker / sigma stack only if dashboard view caps are raised beyond measured budget.

## Current Session

**Active wave:** *(none)*
