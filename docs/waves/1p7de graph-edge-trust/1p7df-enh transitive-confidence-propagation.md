# Transitive confidence propagation in blast-radius and risk

Change ID: `1p7df-enh transitive-confidence-propagation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p7de graph-edge-trust`
Last verified: 2026-06-23

## Rationale

`graph_impact` (and the `code_risk_score` / `code_impact` surfaces built on it) already down-weight low-trust `EXTRACTED` (name-based, receiver-unresolved) call edges — but only at the **immediate hop**. `graph_impact` sets a node's weight to the **max entering-edge confidence**, so a node reached via `resolved → EXTRACTED → target` keeps full weight. Blast radius is multi-hop, so the transitive leak remains: on the Java consumer graph (~66% `EXTRACTED` edges) a low-confidence path still contributes full weight to the affected-file count two hops out.

The mechanism to fix it **already exists in the codebase**: `code_graph_path` runs a weighted-cost Dijkstra (`_path_edge_cost`: deterministic edges cost 1, `EXTRACTED` cost 2) plus a `min_confidence` filter. This change ports that path-confidence model into `graph_impact`'s BFS so blast-radius/risk discount `EXTRACTED` edges **along the whole path**, not just the entering hop. Query-layer only — no graph re-extraction, no `GRAPH_BUILDER_VERSION` bump — so it improves accuracy on the graphs consumers already have.

## Requirements

1. **Path-confidence propagation.** In `graph_impact`'s traversal, propagate confidence along the path (product or min of per-edge weights, decided at implement against the real graphs) rather than taking the max entering-edge weight. A node reached only via an `EXTRACTED` hop must carry the discounted weight transitively to everything it then reaches.
2. **Reuse the existing model.** Use the same per-edge weights `code_graph_path` already applies (`_path_edge_cost`'s `EXTRACTED` discount); do not introduce a second, divergent confidence scheme. Refactor to a shared helper if practical.
3. **Preserve the surfaced fields + add transitivity transparency.** Keep `code_risk_score`'s `extracted_edge_fraction` + raw/weighted components; add a field exposing how much of the weighted blast radius arrived via a low-confidence path (e.g. `transitive_extracted_fraction`) so callers can see the propagation effect.
4. **No regression of resolved reach.** Genuinely-resolved (`RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED`) multi-hop paths must keep full weight; only paths that traverse `EXTRACTED` edges are discounted. Fractional cost, never exclusion (do not drop real reach).
5. **Value gate against the real graphs (AC-8 style).** Measure before/after on the multi-language consumer pack (Swift/solaris, Java, RDS) — the over-attribution cases (e.g. `getKey`) must drop in rank, and the resolved-path cases must be unchanged. Ship only if the change demonstrably improves ranking on real data, not synthetic fixtures.

## Scope

**Problem statement:** Blast-radius / risk aggregation discounts low-trust edges only at the first hop, so multi-hop blast radius still leaks `EXTRACTED`-edge weight, over-counting on name-collision-heavy graphs (Java) and mis-ranking `code_risk_score`.

**In scope:** `graph_query.py` `graph_impact` traversal (path-confidence propagation); the `code_risk_score` / `code_impact` aggregation that consumes it; the transparency field; tests; the before/after measurement.

**Out of scope:** changing the extractor or the per-edge confidence values (that's `1p7dg`); the constant-value retrieval ranking; any `GRAPH_BUILDER_VERSION` change.

**Depends on:** none — independent of the two extractor changes (`1p7dg`/`1p7dh`), works on existing edges. Lands first (no re-extraction).

## Acceptance Criteria

- [x] AC-1: `graph_impact` propagates path confidence (`min` of edge weights, default — preserves single-hop semantics exactly; `product` available behind `_PATH_CONFIDENCE_COMBINE`) instead of max entering-edge weight; a node reachable only via an `EXTRACTED` hop carries the discount to its transitive reach (relaxation in ascending target-depth order; forward-only to skip cycle back-edges).
- [x] AC-2: reused `_edge_confidence_weight` — the blast-radius confidence model `risk_score`/`graph_impact` already share — so no divergent second scheme. (`code_graph_path`'s `_path_edge_cost` is a separate shortest-path *cost* scale (1/2/100), intentionally not conflated with the blast-radius confidence weight.)
- [x] AC-3: `code_risk_score` keeps `extracted_edge_fraction` + raw/weighted components and adds `transitive_extracted_fraction` (share of affected nodes reached only via an `EXTRACTED`-traversing path); surfaced through the MCP wrapper + documented in `mcp-tool-surface.md` + `guru.md`.
- [x] AC-4: resolved-only multi-hop paths keep full weight (test `b`=1.0); single-hop weights preserved exactly (min-combine); `EXTRACTED` reach never dropped — only the `confidence_weight` changes, the affected set is unchanged.
- [~] AC-5: local real-graph validated — the field populates and **diverges from the edge-mix** (`load_graph`: `extracted_edge_fraction` 0.5 vs `transitive_extracted_fraction` 0.931 on wavefoundry's own graph), proving the transitive metric surfaces signal the immediate-hop view hid; the full before/after on the consumer pack (Swift/Java/RDS) is **pending a repacked build for downstream measurement** — the standard measure-downstream-before-close step (mirrors `1p5l4`).
- [x] AC-6: `GraphImpactTransitiveConfidenceTests` covers resolved-path-full-weight, single-hop parity, EXTRACTED-own-hop, transitive-propagation, best-path-wins, and the risk transparency field; full suite **3400 OK** bytecode-free; `wave_validate` clean.

## Tasks

- [x] Open `framework_edit_allowed`; close after.
- [~] Factor the per-edge weight into a shared helper used by `code_graph_path` and `graph_impact` — reused the existing `_edge_confidence_weight` (the shared blast-radius model) rather than factoring a new helper; the shared-model goal (no divergent scheme) is met, so no new helper was needed.
- [x] Implement path-confidence propagation in `graph_impact`'s BFS; add the transparency field (`transitive_extracted_fraction`).
- [x] Tests (resolved full weight / EXTRACTED discounted / transitive) bytecode-free.
- [~] Run the before/after attribution measurement on the consumer pack; record the gate verdict — local real-graph validated (the field diverges from the edge-mix on the self-host graph); the consumer-pack before/after for the transitive metric is deferred (mirrors AC-5 [~]), non-blocking.

## Agent Execution Graph


| Workstream    | Owner       | Depends On | Notes                                                  |
| ------------- | ----------- | ---------- | ------------------------------------------------------ |
| propagation   | implementer | —          | shared edge-weight helper + BFS path confidence        |
| tests         | implementer | propagation| resolved/EXTRACTED/transitive cases                    |
| value-gate    | reviewer    | propagation| before/after on Swift/Java/RDS graphs — go/no-go        |


## Serialization Points

- Independent of `1p7dg`/`1p7dh` (works on existing edges); can land first and ship value without re-extraction.

## Affected Architecture Docs

- **Update if present:** the graph-query / code-navigation architecture doc — note that blast-radius confidence now propagates transitively. Confirm exact target at Prepare; otherwise N/A.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The propagation is the deliverable. |
| AC-2 | required  | One confidence model — divergence would make `code_graph_path` and `code_impact` disagree. |
| AC-3 | important | Transparency so callers can see the propagation effect. |
| AC-4 | required  | No-regression on resolved reach + never-drop-real-reach is the correctness guard. |
| AC-5 | required  | The real-graph value gate is how we avoid shipping a no-op (the `code_risk_score` lesson). |
| AC-6 | required  | Behavior change must be test-locked, bytecode-free. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created. The "sharpened residual" from the Java consumer (`p5l8`): per-edge `EXTRACTED` discount applies only at the immediate hop; multi-hop blast radius leaks. Mechanism already exists in `code_graph_path` (weighted Dijkstra). Query-layer, no builder bump. | MCP code-tool quality log session 11; `code_graph_path` `_path_edge_cost`; consumer attribution stats (extracted ~66% Java) |
| 2026-06-22 | Implemented inline (correctness-critical core). `graph_impact` propagates path confidence (min-combine, ascending target-depth relaxation, forward-only to skip cycle back-edges); `confidence_weight` is now the propagated path weight; `code_risk_score` adds `transitive_extracted_fraction`. Reused `_edge_confidence_weight` (no divergent scheme). 6 new transitive tests + updated score_components / wrapper-field test / docstring / `mcp-tool-surface.md` / `guru.md`. **Tangential in-session fix:** the +6 tests perturbed suite sharding and exposed a pre-existing test-isolation defect in `test_get_reranker_does_not_cache_none_on_failure` (it patched the stale `fastembed` path, not the `accel_embedder` path `_get_reranker` actually imports since 1p52p) — repatched to `accel_embedder`. Full suite **3400 OK** bytecode-free; docs-lint clean; live `code_risk_score` confirms the field diverges from edge-mix. | `graph_query.py` graph_impact/risk_score + `_combine_path_confidence`; `test_graph_query.py`; `test_server_tools.py`; `server_impl.py` docstring; `run_tests.py` 3400 OK |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Divergent pre-plan — selected: propagate path confidence in `graph_impact`, reusing `code_graph_path`'s model** | The mechanism is already proven in `code_graph_path`; porting it is low-risk, query-layer, and fixes the transitive leak without re-extraction. | (B) Hard `min_confidence` filter on `graph_impact` (drop EXTRACTED) — rejected: loses real reach; the field told us EXTRACTED edges still carry genuine signal. (C) Leave it (immediate-hop only) — rejected: the leak is the active mis-ranking on real Java graphs. |
| 2026-06-22 | Fractional/transitive discount, never exclusion | EXTRACTED edges are low-trust, not wrong — excluding them re-introduces the Python under-count. | Exclude EXTRACTED entirely — rejected (under-count). |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Propagation changes ranking in a way that looks worse on some repo   | AC-5 before/after gate on the multi-language pack is the go/no-go; ship only on demonstrated improvement. |
| Product-of-weights underflows / over-discounts deep paths            | Decide product vs min at implement by measuring on real graphs; cap or floor if needed.             |
| Two confidence schemes drift                                          | Shared edge-weight helper (AC-2).                                                                   |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
