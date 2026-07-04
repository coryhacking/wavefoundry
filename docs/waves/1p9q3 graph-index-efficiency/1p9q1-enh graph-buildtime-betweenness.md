# Graph index: build-time betweenness centrality with size-tiered strategy; retire the per-query 10k-node cap

Change ID: `1p9q1-enh graph-buildtime-betweenness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9q3 graph-index-efficiency`

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

- [x] AC-1: On the self-hosted repo (>10k nodes, over the old cap), a graph build persists a betweenness ranking and `wave_graph_report` returns it — real scores, `method` metadata, no `graph_too_large_for_betweenness` diagnostic. Integration-tested against the built artifact; observed result recorded in the Progress Log. *(Live rebuild + `wave_graph_report_response` probe on this repo: 11,023 nodes → `method: "exact"`, real scores, no cap diagnostic; Progress Log 2026-07-03. Integration-shaped test `test_large_graph_served_without_cap_diagnostic` covers the >10k serve path.)*
- [x] AC-2: Tier selection is correct and tested — fixtures below the exact threshold get `method: "exact"`; between exact and hard tiers get `method: "cutoff"` with the configured cutoff recorded; above the hard tier (or with igraph absent) get `method: "degree_fallback"`. Unit-tested with threshold overrides pinning each tier. *(`BuildTimeBetweennessTests` tier matrix: `test_tier_exact_below_exact_threshold`, `test_tier_cutoff_between_exact_and_hard_thresholds`, `test_tier_degree_fallback_above_hard_threshold`, `test_igraph_absent_falls_back_to_degree_with_honest_method`.)*
- [x] AC-3: Determinism — two builds of the same fixture graph produce identical rankings (order and scores) in each tier, including the fallback's stable tiebreak. Unit-tested. *(`test_determinism_exact_tier`, `test_determinism_cutoff_tier`, `test_determinism_degree_fallback_stable_node_id_tiebreak` — the latter pins the node-id tiebreak on equal scores.)*
- [x] AC-4: With igraph unavailable (import blocked in test), the build persists the degree fallback with honest metadata and the report serves it — no crash, no silent absence. Unit-tested (respecting the known constraint that spawned test agents must use the `~/.wavefoundry/venv` interpreter so igraph-present tests don't silently skip). *(Import blocked via `patch.dict(sys.modules, {"igraph": None})` → `method: "degree_fallback"`, ranking persisted; all tests run with the venv python, igraph 1.0.0 present so exact/cutoff tests did not skip.)*
- [x] AC-5: Query-time cost — `wave_graph_report` performs no igraph betweenness call at query time (verified by test instrumentation/monkeypatch showing zero inline computation) and `_BETWEENNESS_NODE_LIMIT` no longer exists in the codebase (grep gate). *(Exploding-`igraph.Graph` monkeypatch tests at both layers: `test_report_performs_no_igraph_betweenness_at_query_time` (server) + `test_report_never_calls_igraph_betweenness` (GraphQueryIndex). Grep gate: exhaustive `code_keyword` limit=0 — only assertion-of-absence mentions in tests remain — plus the standing test `test_cap_constant_retired_grep_gate`.)*
- [x] AC-6: The betweenness pass is timed in build output; measured build-time delta on the self-hosted repo recorded in the Progress Log and within a sane budget for its tier (measurement, not a hard assert). *(stderr instrumentation line per the indexer pattern + `elapsed_ms` in the persisted metadata; self-hosted delta 14ms (exact tier) — noise against the 14.1s graph build.)*
- [x] AC-7: Version bump(s) applied per the standing artifact-shape rule; pre-change artifacts (no betweenness section) are handled gracefully by the report (absent-section message, not a crash) until the first rebuild. *(`CLUSTER_BUILDER_VERSION` 10→11; `GRAPH_BUILDER_VERSION` untouched at 36 — already covers this wave per the coordinated single-bump serialization point. Legacy grace: `betweenness_skipped_reason: "betweenness_not_in_artifact"` + `betweenness_note` rebuild hint; `test_legacy_clusters_artifact_without_section_is_graceful`, `test_missing_clusters_artifact_is_graceful`.)*
- [x] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. *(Full suite 4314 tests OK with the venv python; `wave_validate` passed; `__pycache__` count 0.)*

## Tasks

- [x] Implement the tiered betweenness pass in `graph_cluster.py` (or an adjacent analysis module if cleaner): tier constants + env overrides, exact/cutoff/degree paths, top-N truncation, method metadata, timing. *(`compute_betweenness_ranking` + `_betweenness_projection`; `BETWEENNESS_TOP_N`/`BETWEENNESS_EXACT_MAX_NODES`/`BETWEENNESS_CUTOFF_MAX_NODES`/`BETWEENNESS_CUTOFF` env-overridable via `WAVEFOUNDRY_GRAPH_BETWEENNESS_*`.)*
- [x] Persist the section in the clusters artifact (or payload — settle placement first; see Serialization Points) with its version bump. *(Clusters artifact confirmed — Decision/Progress Log; `cluster_builder_version` 10→11; persisted through 1p9py's gzip-aware `_write_json`.)*
- [x] Rework `wave_graph_report`'s betweenness section to read the persisted ranking, surface `method`, and handle absent-section legacy artifacts; remove the inline computation, the cap constant, and the diagnostic path. *(`server_impl.wave_graph_report_response` serves from `read_cluster_payload`; `graph_query.py` inline block, `_BETWEENNESS_NODE_LIMIT`, and the `graph_too_large_for_betweenness` path deleted; `ReportSection` Literal updated.)*
- [x] Tests: tier matrix, determinism, igraph-absent fallback, report serving + legacy-artifact grace, no-inline-computation instrumentation, grep gate for the retired constant. *(+10 `BuildTimeBetweennessTests` in `test_graph_cluster.py`, +4 `GraphQueryBetweennessRetirementTests` in `test_graph_query.py` (replacing the 3 old inline-computation tests), +7 `TestBetweennessServedFromArtifact` in `test_server_tools.py` (replacing 130tw's 2-test `TestBetweennessComputedField`).)*
- [x] Measure build-time delta and record the self-hosted repo's actual top-of-ranking in the Progress Log (sanity: hub modules like `server_impl`/`indexer` should rank high). *(14ms exact tier at 11,023 nodes; top-of-ranking recorded 2026-07-03 — `server_impl.py` functions in the top 10.)*
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`. *(4314 tests OK; docs-lint ok; 0 `__pycache__` dirs.)*

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
| 2026-07-03 | **IMPLEMENTED — all 8 ACs met; full suite 4314 green with the venv python.** Build pass: `graph_cluster.compute_betweenness_ranking` (directed `calls` projection over ALL payload nodes, mirroring the retired query-time graph so rankings stay comparable) wired into `update_graph_clusters` alongside the Leiden pass — `finalize()`'s merge structure untouched; the pass is a pure function of the merged payload per the pre-settled 1p9q2 seam. Persisted section: `{method, node_count, edge_count, top_n, elapsed_ms, ranking[<=200 rows: node_id/score/label/kind], cutoff?}`. Report rework: `wave_graph_report` serves the persisted ranking (limit-truncated) + `betweenness_method`/`betweenness_metadata`; the 1p9pz query cache is untouched (artifact read per call, like communities). Retired: `_BETWEENNESS_NODE_LIMIT`, the inline igraph block, `graph_too_large_for_betweenness` — exhaustive `code_keyword` (limit=0, `**/*.py`) shows only assertion-of-absence test mentions. Docs: `mcp-tool-surface.md` wave_graph_report entry + `graph-index-system.md` `wave_graph_report_response()` section updated. Tests: +21 new/reworked across the three test files (tier matrix, per-tier determinism, blocked-import fallback, serving + legacy grace, exploding-igraph instrumentation at both layers, grep gate, env-override reload, top-N truncation, persistence round-trip). | `graph_cluster.py`, `graph_query.py`, `server_impl.py`, `tests/test_graph_cluster.py`, `tests/test_graph_query.py`, `tests/test_server_tools.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/graph-index-system.md`; suite log 2026-07-03. |
| 2026-07-03 | **Tier calibration + self-hosted measurement (AC-1/AC-6).** Fresh-venv-subprocess full graph rebuild (`indexer.py --content graph --full` — deliberately NOT `wave_index_build`, whose server process runs pre-edit code in the known old-code window): **11,023 nodes / 10,033 calls edges → tier `exact`, betweenness pass 14ms** inside a 14.1s graph build (delta = noise). Calibration: igraph's C-core exact betweenness is effectively free on sparse call graphs at this scale, so `BETWEENNESS_EXACT_MAX_NODES=25000` covers the 10-15k target band with order-of-magnitude headroom; `BETWEENNESS_CUTOFF_MAX_NODES=100000` + `BETWEENNESS_CUTOFF=6` bound denser mid-tier graphs; above 100k igraph is never consulted (degree fallback). Live `wave_graph_report_response(sections=['betweenness'])` probe against the built artifact: `betweenness_computed: true`, `method: "exact"`, metadata `{node_count: 11023, edge_count: 10033, top_n: 200, elapsed_ms: 14}`, **no cap diagnostic** (query served in 259ms incl. index load). Top-of-ranking sanity: `secrets_validators.check_hardcoded_secrets` (5132), `test_secrets_validators._run_check` (3555), `secrets_validators._match_hits_for_file` (1933), `secrets_validators.scan_file_raw` (1760), `server_impl.run_index_rebuild` (1592), `gen_codebase_map.generate_codebase_map` (1526), `server_impl.wave_index_build_response` (1468) — hub-module functions (`server_impl`, `gen_codebase_map`, the lint/secrets pipeline) rank high as expected; the secrets-validator cluster tops the list because it sits on the longest call chains (lint dispatch → scan → per-file → per-hit). | Build/probe transcripts 2026-07-03; persisted artifact `.wavefoundry/index/graph/project-graph-clusters.json` (`cluster_builder_version: 11`). |
| 2026-07-03 | **Implementation start — artifact placement CONFIRMED: clusters artifact** (serialization point settled). Reasoning: (1) `graph_cluster.update_graph_clusters` already loads igraph and receives the full merged graph payload per build, so the pass adds no new module/payload plumbing; (2) the clusters artifact carries its own `cluster_builder_version` field for the shape bump, leaving `GRAPH_BUILDER_VERSION` (already at 36, covering this wave's coordinated bump) untouched; (3) the graph payload is parsed by every query tool via the 1p9pz stat-validated cache — keeping report-only data out of it keeps that hot path lean and leaves the immutable `GraphQueryIndex` cache design unaffected (the report reads the clusters artifact per call, exactly like the existing communities section). Persistence goes through 1p9py's gzip-aware `_write_json`/`read_json_artifact`. | `graph_cluster.py:894-978` (pass call site), `server_impl.py:15036-15083` (communities-read precedent), sibling notes 1p9py/1p9pz. |
| 2026-07-04 | Delivery-review cross-pointer: the serving-path questions raised at review (the report's pre-existing `[1,100]` limit clamp vs the artifact's top-200 headroom — accepted, pre-existing contract; the corrupt-artifact response-consistency hardening in the serving block) are recorded in the sibling `1p9pz` 2026-07-04 Progress Log row and in `server_impl.py` (method/metadata assigned only after all casts succeed; cleared on exception). No 1p9q1-owned code changed in the fix round. | Rotating-seat docs-contract note 2026-07-04. |
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
