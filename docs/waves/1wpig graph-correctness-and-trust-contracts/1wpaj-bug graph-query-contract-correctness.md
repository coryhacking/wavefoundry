# Restore Graph Query Filtering and Edge-Trust Contracts

Change ID: `1wpaj-bug graph-query-contract-correctness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-30
Wave: 1wpig graph-correctness-and-trust-contracts

## Rationale

`wf_graph_report` truncates ranked sections before applying external/generated filters. A `limit=1` project-only fan-in request therefore returns an empty list even though project nodes exist below the external top result, regressing the completed public requirement that filtering precede truncation. `code_callhierarchy` also projects away edge relation and confidence plus node kind and ID, so consumers cannot apply the documented trust policy to individual hierarchy entries.

## Requirements

1. Graph-report eligibility filters SHALL run before top-N truncation for every affected ranking section and supported collapse view.
   The required matrix for `fan_in`, `fan_out`, `chokepoints`, and `file_hubs` is all eight boolean combinations of the public `collapse_generated_files`, `collapse_class_module_pairs`, and `collapse_package_to_directory` flags, crossed with filter modes none, external-only, generated-only, and combined. For every applicable cell, the metamorphic oracle is the first requested `N` eligible rows from that exact collapsed topology's complete deterministic unfiltered candidate order. `betweenness` is supported only when all three collapse flags are false: any collapsed request that includes it SHALL return no stale base-topology ranking, set `betweenness_computed=false`, and expose `betweenness_skipped_reason="unsupported_for_collapsed_view"`; the uncollapsed cell is crossed with all four filter modes. `communities` remains an artifact-defined base-topology section: collapse flags do not project or rerank it, its complete base order SHALL be invariant across all eight flag combinations, and supported generated eligibility SHALL run before top-N; external filtering is not applicable because community members are project nodes. `orphan_docs` is an unranked diagnostic set and is outside the refill matrix.
2. When eligible candidates are at least the requested limit, each ranking section SHALL return that many entries.
3. Each call-hierarchy entry SHALL expose stable node ID, node kind, edge relation, and edge confidence in addition to presentation fields.
4. Existing aggregate external counts, communities, snippets, and compatibility fields SHALL remain intact.
5. Tool descriptions and Guru guidance SHALL describe the fields actually returned.
6. Uncollapsed betweenness refill SHALL operate on a persisted complete deterministic ranking, not only the current `BETWEENNESS_TOP_N` presentation prefix. Its exact candidate universe is every base-graph node whose computed centrality score is finite and strictly greater than zero, sorted by `(-score, node_id)`; zero/non-finite nodes remain excluded as today. Refill is required only within that universe: when fewer than `N` eligible positive-score rows exist, return all of them and expose truthful eligible/candidate counts. The cluster artifact SHALL retain the existing compact top-N metadata for compatibility while adding the complete scored base order needed by filtered public queries; `CLUSTER_BUILDER_VERSION` SHALL bump and old artifacts SHALL rebuild. No query-time centrality is permitted, and collapsed views SHALL use the explicit unsupported contract in Requirement 1 rather than serving base-topology scores as if they described the collapsed graph.
7. **Precommitted performance oracle:** measure two controlled current-repository cluster/graph rebuilds plus one zero-change reuse, with identical graph fingerprint and environment recorded. Cluster-stage post-change time SHALL be at most baseline plus `max(25% of baseline, 1 second)`; graph-only rebuild above 30 seconds requires operator review. Compressed cluster artifact bytes SHALL be at most `max(2 * baseline, baseline + 2 MiB)` and the report SHALL include complete-order rows, uncompressed JSON bytes, compressed bytes, compression ratio, and peak RSS when available. For filtered betweenness at limit 1 and the public maximum 100, three warm repetitions use nearest-rank p95; p95 SHALL be at most 1 second and at most baseline plus `max(25% of baseline, 50 ms)`. A zero-change pass SHALL neither recompute nor rewrite the artifact, and the complete internal order SHALL never appear in the public response.

## Scope

**Problem statement:** Graph filters can manufacture empty/underfilled reports, and hierarchy projection hides the trust evidence needed to assess heuristic edges.

**In scope:** Report ranking/filter order, generated/external filters, complete persisted betweenness refill data, cluster artifact versioning, hierarchy response projection, MCP descriptions, and public-handler regression tests.

**Out of scope:** Graph extraction accuracy, relation weighting, deeper hierarchy traversal, and dashboard rendering.

## Acceptance Criteria

- [ ] AC-1: `fan_in(limit=1,exclude_external=true)` returns one project row on the current graph rather than `[]`.
- [ ] AC-2: Each applicable filtered report matrix cell fills its requested limit whenever enough eligible candidates exist; all eight public collapse-flag combinations are covered for topology-derived ranking sections, while collapsed betweenness returns the explicit unsupported contract instead of stale base-topology rows.
- [ ] AC-3: Incoming and outgoing hierarchy entries expose `node_id`, `kind`, `relation`, and `confidence` for resolved, construction-resolved, extracted, and external edges.
- [ ] AC-4: A client can deterministically retain only trusted confidence classes from a hierarchy response without calling a second graph tool.
- [ ] AC-5: Schema/tool descriptions, Guru guidance, focused tests, and the full framework suite agree with runtime behavior.
- [ ] AC-6: A builder-versioned cluster artifact persists the complete deterministic betweenness order required for filtering; filtered betweenness fills the requested public limit whenever enough eligible rows exist, old top-N consumers remain compatible, and rebuild time plus compressed artifact size stay within documented ceilings.
- [ ] AC-7: Every required section/collapse/filter matrix cell matches its specified metamorphic oracle; community order is collapse-invariant, collapsed betweenness is explicitly unsupported, positive-score exhaustion returns all eligible rows with truthful counts, and the precommitted rebuild, artifact-size/memory, zero-change reuse, and three-sample warm-query ceilings pass.

## Tasks

- [ ] Move eligibility filtering into report candidate ranking before slicing.
- [ ] Apply the ordering consistently across the exact eight-combination collapse matrix, preserve base-artifact community semantics, and reject collapsed betweenness with the documented structured reason.
- [ ] Propagate node and edge trust metadata through call-hierarchy projection.
- [ ] Add adversarial limit/refill and metadata-schema tests.
- [ ] Align tool descriptions and graph/Guru documentation.
- [ ] Extend and version the cluster artifact's betweenness payload, with compatibility, rebuild, determinism, size, and latency tests.
- [ ] Implement the complete section/collapse/filter matrix and the exact current-repository performance oracle before accepting delivery evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Report filtering | implementer | — | Eligibility before top-N |
| Hierarchy contract | implementer | — | Edge/node metadata |
| Public verification | qa-reviewer | Both | MCP responses and current-graph probes |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_query.py`, `.wavefoundry/framework/scripts/graph_cluster.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`, `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `docs/agents/guru.md`, `docs/architecture/graph-index-system.md`

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces and closes the public-contract regression. |
| AC-2 | required | Prevents the same ordering defect across sibling sections. |
| AC-3 | required | Trust filtering depends on per-edge metadata. |
| AC-4 | required | This is the consumer-visible purpose of the metadata. |
| AC-5 | important | Public schema and guidance must remain synchronized. |
| AC-6 | required | Betweenness cannot satisfy refill correctness from a truncated persisted universe. |
| AC-7 | required | The refill and performance contracts need complete, independently falsifiable oracles. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned from the graph audit lane. | Reproduced public report underfill and compared raw callgraph metadata with hierarchy output. |
| 2026-08-30 | Expanded filtered-refill scope to the persisted betweenness artifact after code review proved the current top-200 prefix cannot satisfy the unconditional public refill contract. | `compute_betweenness_ranking` slices to `BETWEENNESS_TOP_N`; code-review readiness finding. |
| 2026-08-30 | Replaced the nonexistent `collapse_to_files` test axis with the three real public collapse flags and bounded topology-sensitive artifact behavior. | All three collapse transforms run before `GraphQueryIndex.report`; persisted betweenness and communities describe the base topology, so collapsed betweenness is now explicitly unsupported and community ordering remains base-artifact invariant. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Filter the candidate universe before ranking truncation and preserve edge metadata in projection. | Directly restores both public contracts without heuristic overfetch. | **Overfetch by a fixed multiplier:** still underfills under larger skew. **Filter response after slicing:** current defect. **Require a second callgraph query:** keeps the preferred hierarchy tool unable to follow its own trust guidance. |
| 2026-08-30 | Persist the complete deterministic betweenness order beside the compatibility top-N view and bump the cluster builder version. | Public filtering cannot refill from the current bounded top-200 artifact even when eligible nodes exist below it. | **Narrow the public guarantee:** rejected because it would preserve a surprising underfill on a documented filter. **Fixed overfetch:** still fails under skew. **Recompute centrality per query:** violates the build-time centrality performance architecture. |
| 2026-08-30 | Support filtered betweenness only on the base topology and return a structured unsupported result for collapsed views. | Every collapse flag rewrites nodes or edges before report computation, while the persisted centrality artifact describes the base graph; serving that order under collapse is misleading, and persisting eight independent centrality universes is disproportionate to current user demand. | **Persist one order per collapse tuple:** substantially increases build/storage cost for an unvalidated use case. **Reuse base scores after collapse:** falsely labels base centrality as collapsed-graph centrality. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pre-filtering changes historical rank composition. | Preserve sort keys and compare unfiltered results byte-for-byte. |
| Added response fields increase payload size. | Fields are compact and limited to already-returned entries; measure representative response size. |
| Complete betweenness order enlarges the cluster artifact. | Keep the compatibility top-N view, gzip the existing artifact as today, and gate compressed-size plus rebuild-time deltas on the current repository. |
| A caller expects betweenness to compose with collapse flags. | Return a stable, documented `unsupported_for_collapsed_view` reason and preserve all non-betweenness collapsed report sections. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
