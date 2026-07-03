# Graph index: build-time betweenness centrality with size-tiered strategy; retire the per-query 10k-node cap

Change ID: `1p9q1-enh graph-buildtime-betweenness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

`wave_graph_report` computes betweenness centrality **per query** via `igraph.Graph(...).betweenness(directed=True)` (`graph_query.py:1663-1697`), guarded by `_BETWEENNESS_NODE_LIMIT = 10_000` (`graph_query.py:22`): above the cap it returns a `graph_too_large_for_betweenness` diagnostic instead of a ranking. **The self-hosted repo, at 10,776 nodes, already exceeds the cap** — our own medium-sized project gets no betweenness section from its own analysis tool, and every larger target repo is worse off.

The cap exists only because the computation runs inline with a query: exact betweenness is O(V·E)-ish, too slow to pay per tool call. But it is precompute-shaped — the graph changes only at build time, and the sibling analyses already precompute: Leiden communities are computed at build and persisted (`graph_cluster.py:859,936`), and igraph articulation-point chokepoint flags are computed at build (`graph_indexer.py:8144-8162`). Betweenness is the odd one out. Moving it to build time (with a size-tiered exact/approximate strategy so large graphs still get a useful ranking) removes the cap, restores `wave_graph_report` on medium repos, and makes report queries O(read) instead of O(V·E).

## Requirements

1. **Build-time computation.** Betweenness is computed during the graph build/cluster pass (natural home: alongside the Leiden pass in `graph_cluster.py`, which already loads igraph and the merged payload) and persisted — top-N node ranking with scores (N generous, e.g. 200) plus computation metadata (`method`, `node_count`, elapsed), not a per-node score for every node.
2. **Size-tiered strategy.** Exact `betweenness(directed=True)` below an exact-tier node threshold; above it, a bounded approximation via igraph's `cutoff` parameter (bounded-length shortest paths) with the cutoff and tier thresholds as named, env-overridable constants. Above a hard upper tier (very large graphs), degrade to persisting the cheap fan-out ranking with `method: "degree_fallback"` — never an unbounded computation in any build path. Thresholds calibrated by measurement during implementation (exact tier must comfortably cover ~10-15k nodes given the current cap was purely query-latency-motivated).
3. **igraph-optional fallback.** When igraph is unavailable (it is an optional dep with an existing fallback pattern — label propagation for clusters, silent skip for chokepoints), persist the degree/fan-out ranking with honest `method` metadata rather than nothing, mirroring `wave_graph_report`'s existing cheap chokepoint section (`graph_query.py:1612-1635`).
4. **Query reads, never computes.** `wave_graph_report` serves the persisted ranking (with its `method` metadata surfaced in the response so consumers can see exact vs approximate vs fallback) and drops the inline igraph computation and the `graph_too_large_for_betweenness` diagnostic path. `_BETWEENNESS_NODE_LIMIT` is retired.
5. **Determinism.** The persisted ranking is deterministic for a given graph (igraph exact betweenness is deterministic; `cutoff` approximation is too — no sampling RNG; the degree fallback is a deterministic sort with a stable tiebreak on node id). Consistent with the graph build's `input_fingerprint` determinism stance.
6. **Version bump.** The persisted artifact gains a section → bump the owning artifact version (`cluster_builder_version` if it lands in the clusters artifact, plus `GRAPH_BUILDER_VERSION` if the payload/counts shape changes) per the standing rule, coordinated with `1p9py`/`1p9q2` bumps at wave integration.
7. **Build-cost guard.** The betweenness pass is timed and logged with the existing build timing instrumentation (`indexer.py:2815-2819` pattern); if the exact tier exceeds a wall-time budget on a given repo, the tier thresholds are the tuning knob (documented), not an unbounded wait.

## Scope

**Problem statement:** Betweenness centrality is computed per query with a 10k-node cap that the self-hosted repo already exceeds, so `wave_graph_report` returns a diagnostic instead of a ranking on exactly the repos where centrality analysis is most useful.

**In scope:**

- Build-time betweenness in the cluster/analysis pass with exact/cutoff/degree-fallback tiers and persisted top-N + method metadata.
- `wave_graph_report` reads the persisted section; inline computation, cap constant, and `graph_too_large_for_betweenness` diagnostic removed.
- igraph-absent fallback with honest metadata.
- Timing instrumentation for the new pass; threshold constants env-overridable.
- Tests: tier selection, determinism, fallback, report serving, cap-retirement behavior on a >10k-node fixture.
- Version bump coordination.

**Out of scope:**

- Other centrality measures (PageRank, closeness) — nothing consumes them today.
- Changing the separate build-time articulation-point chokepoint flag or the report's cheap fan-out chokepoint section (they remain as-is; the fan-out ranking is additionally reused as the fallback method).
- Incremental betweenness maintenance (recompute-on-build is correct; incremental centrality is research-grade complexity for no current need).
- Dashboard visualization of the ranking (consumer-side, separate concern).

## Acceptance Criteria

- [ ] AC-1: On the self-hosted repo (>10k nodes, over the old cap), a graph build persists a betweenness ranking and `wave_graph_report` returns it — real scores, `method` metadata, no `graph_too_large_for_betweenness` diagnostic. Integration-tested against the built artifact; observed result recorded in the Progress Log.
- [ ] AC-2: Tier selection is correct and tested — fixtures below the exact threshold get `method: "exact"`; between exact and hard tiers get `method: "cutoff"` with the configured cutoff recorded; above the hard tier (or with igraph absent) get `method: "degree_fallback"`. Unit-tested with threshold overrides pinning each tier.
- [ ] AC-3: Determinism — two builds of the same fixture graph produce identical rankings (order and scores) in each tier, including the fallback's stable tiebreak. Unit-tested.
- [ ] AC-4: With igraph unavailable (import blocked in test), the build persists the degree fallback with honest metadata and the report serves it — no crash, no silent absence. Unit-tested (respecting the known constraint that spawned test agents must use the `~/.wavefoundry/venv` interpreter so igraph-present tests don't silently skip).
- [ ] AC-5: Query-time cost — `wave_graph_report` performs no igraph betweenness call at query time (verified by test instrumentation/monkeypatch showing zero inline computation) and `_BETWEENNESS_NODE_LIMIT` no longer exists in the codebase (grep gate).
- [ ] AC-6: The betweenness pass is timed in build output; measured build-time delta on the self-hosted repo recorded in the Progress Log and within a sane budget for its tier (measurement, not a hard assert).
- [ ] AC-7: Version bump(s) applied per the standing artifact-shape rule; pre-change artifacts (no betweenness section) are handled gracefully by the report (absent-section message, not a crash) until the first rebuild.
- [ ] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Implement the tiered betweenness pass in `graph_cluster.py` (or an adjacent analysis module if cleaner): tier constants + env overrides, exact/cutoff/degree paths, top-N truncation, method metadata, timing.
- [ ] Persist the section in the clusters artifact (or payload — settle placement first; see Serialization Points) with its version bump.
- [ ] Rework `wave_graph_report`'s betweenness section to read the persisted ranking, surface `method`, and handle absent-section legacy artifacts; remove the inline computation, the cap constant, and the diagnostic path.
- [ ] Tests: tier matrix, determinism, igraph-absent fallback, report serving + legacy-artifact grace, no-inline-computation instrumentation, grep gate for the retired constant.
- [ ] Measure build-time delta and record the self-hosted repo's actual top-of-ranking in the Progress Log (sanity: hub modules like `server_impl`/`indexer` should rank high).
- [ ] Run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-buildtime-pass | implementer | — | Tiered computation + persistence + timing in the build/cluster pass; version bump. |
| ws2-report-rework | implementer | ws1-buildtime-pass | `wave_graph_report` reads persisted section; retire cap/diagnostic/inline path. |
| ws3-tests-and-measurement | implementer | ws1-buildtime-pass, ws2-report-rework | Tier/determinism/fallback/serving tests; grep gate; build-delta measurement. |


## Serialization Points

- **Artifact placement decision** (clusters artifact vs graph payload) must be settled before ws1 persists and ws2 reads — default: clusters artifact (it already owns build-time igraph analysis and has its own version field); confirm at implementation start.
- Version bumps coordinate with `1p9py`/`1p9q2` at wave integration (one final bump per artifact is the clean outcome).
- If `1p9py` lands first, the persistence goes through its gzip-aware writer — no format decisions here.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — `wave_graph_report` entry: remove/replace any mention of the 10k-node betweenness cap or per-query computation; document the `method` metadata. No boundary or layering impact otherwise (build-pass internal + one tool response shape refinement).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Restoring betweenness on >10k-node repos is the point; the self-hosted repo is the live proof. |
| AC-2 | required | The tier strategy is the design core; wrong tiering silently degrades ranking quality or build time. |
| AC-3 | required | Nondeterministic rankings would break the build's determinism stance and produce noisy artifact diffs. |
| AC-4 | required | igraph is optional; a crash or silent absence without it regresses existing graceful-degradation behavior. |
| AC-5 | required | Leaving an inline computation path would silently reintroduce the latency the change removes. |
| AC-6 | important | Build-cost visibility is the guard against paying too much at build time; measurement, not a hard gate. |
| AC-7 | required | Standing artifact-shape/version rule; legacy-artifact grace prevents a crash window between upgrade and first rebuild. |
| AC-8 | required | Suite + docs-lint green is the standing merge gate for framework code. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Confirmed: per-query `igraph.betweenness` at `graph_query.py:1663-1697` behind `_BETWEENNESS_NODE_LIMIT = 10_000` (`graph_query.py:22`); self-hosted graph is 10,776 nodes → the live repo already gets the `graph_too_large_for_betweenness` diagnostic. Precompute precedent: Leiden clusters (build-time, persisted, `graph_cluster.py:859,936`) and igraph articulation chokepoint flags (build-time, `graph_indexer.py:8144-8162`). Distinct cheap fan-out chokepoint ranking in the report (`graph_query.py:1612-1635`) is the natural fallback method. | `graph_query.py:22,1612-1635,1663-1697`; `graph_cluster.py:335-343,388-475,859,936`; `graph_indexer.py:8144-8162`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Build-time tiered computation (exact / igraph `cutoff` / degree fallback), persisted top-N (approach A). | Matches the established precompute pattern (Leiden, articulation points); removes the cap by moving cost to where the graph actually changes; tiers keep every repo size served with honest metadata; deterministic throughout. | (B) Keep per-query but raise the cap + add approximation — weakness: still pays O(V·E)-ish per report call and the cap merely moves; latency cliff remains. (C) Exact-only at build with no tiers — weakness: unbounded build cost on very large repos (100k+ nodes), exactly the scale this wave targets. (D) Drop betweenness, keep only fan-out chokepoints — weakness: fan-out is local degree, not path centrality; loses the analysis the report exists to give. |
| 2026-07-03 | Deterministic `cutoff` approximation rather than sampling for the middle tier. | igraph's bounded-path-length betweenness is deterministic (no RNG seed management, honors the no-`random()` convention and artifact determinism) and captures the "local bridge" structure that matters for chokepoint-style analysis. | Vertex-sampling approximation — better global fidelity on some topologies but nondeterministic without seeding and igraph's Python API support for it is weaker; rejected for determinism and dependency-surface reasons. |
| 2026-07-03 | Persist top-N + metadata, not per-node scores for all nodes. | The report consumes a ranking; full per-node scores would bloat the artifact (counter to `1p9py`) for no consumer. N=200 leaves generous headroom over the report's display needs. | Full score vector — rejected as artifact bloat; N can be raised by constant if a future consumer appears. |
| 2026-07-03 | Default artifact placement: clusters artifact. | `graph_cluster.py` already owns build-time igraph analysis, has its own version field, and keeps the payload (read by every query tool) lean — report-only data belongs with report-shaped analysis. | Graph payload `counts`/analysis section — single-file simplicity but taxes every payload parse with report-only data; final call confirmed at implementation start (serialization point). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Build-time regression on large repos from the exact tier. | Tiers with env-overridable thresholds; timing instrumentation (AC-6) makes cost visible per repo; the hard tier guarantees bounded cost everywhere. |
| `cutoff` approximation ranks differently enough from exact to confuse consumers. | `method` metadata is surfaced in the report response so approximate rankings are labeled, never silently presented as exact; cutoff value recorded in metadata. |
| Legacy artifacts without the section crash the report between upgrade and first rebuild. | AC-7 absent-section grace path, tested; the builder-version bump makes the first query trigger a rebuild anyway via the existing staleness path. |
| The betweenness pass runs on every incremental build, re-paying full cost for one changed file. | Acceptable now (same is true of Leiden today); `1p9q2`'s incremental merge is the systemic fix for re-analysis cost — noted there as a shared analysis-pass concern. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
