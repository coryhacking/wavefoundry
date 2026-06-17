# Codebase map: generator area-selection & labeling (generated/vendored noise, per-module floor, labels)

Change ID: `1p61w-enh graph-clustering-granularity-stability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

> **Re-scoped 2026-06-17 (operator-directed).** Originally framed as a `graph_cluster.py` (Leiden) clustering change. Investigation + a third consumer (javaagent) showed the real work is in the **generator's area selection + labeling** (`gen_codebase_map.py`), not the clusterer: clustering determinism is already handled (`seed=0`), and the granularity/noise problems are area-selection decisions the generator makes over an otherwise-faithful graph. The change ID slug ("graph-clustering-…") is retained for stability but the content is now generator area-selection. No `CLUSTER_BUILDER_VERSION` bump — the signals this consumes are already persisted.

## Rationale

Three downstream field tests converge on one conclusion: the codebase map's faithful-projection layer is solid (paths, hubs, entry points verified across Solaris/teton/javaagent), but its **area SELECTION and LABELING invert the signal/noise ratio** on real repos — especially any repo that bundles a large vendored or generated dependency.

javaagent (Java OTel/ByteBuddy agent, 233 files) is the sharpest case: ~51% of files are a vendored/generated Expression-Language implementation, and raw-community-size area selection gives it ~13 of 24 areas — a 99%-generated JavaCC parser renders as **area #3** — while real instrumentation modules (hibernate, spring, sailpoint, neo4j, ofbiz, shopizer) get no dedicated area (shopizer is absent entirely). An agent told "consult the map first" is routed into parser internals and away from the product.

Crucially, the graph **already emits the signals** to fix the worst of this: every community carries `generated_node_fraction` (persisted in the cluster artifact, Aceiss §6.5), and nodes carry a `generated` tag. The generator simply doesn't consume them.

## Requirements

1. **Consume the generated signal (1a — cheapest, highest-leverage).** Exclude communities whose `generated_node_fraction` exceeds a threshold (0.4, matching `wave_graph_report`) from the primary area tier — they are not orientation targets. Do not silently drop: surface the omitted count (and a sample) in the map so coverage stays honest.
2. **Per-module area floor (2).** Bias the top tier toward top-level module/package boundaries over raw community size: each distinct top-level module/source-root gets at least one slot before remaining slots fill by size, so a large vendored subtree cannot crowd out small product modules.
3. **Non-code / data / minified hubs excluded from rep+hub selection (teton Issue 3).** A representative path or `hub_node_id` must never be a `.json`/data node (`…json::map`) or a minified/vendored bundle (`otel.cjs`, `prism.js`); drill-in handles must be actionable first-party source.
4. **Label disambiguation (3).** Colliding area titles (5×`parser`, 4×`javax`) are disambiguated by representative path segment (`el/apache/parser` vs `el/javax`); titles derive from the representative path, not a single top-fan-in symbol; trailing ordinal noise (`… 1`) is dropped.
5. **Generator-only + deterministic + faithful.** No `CLUSTER_BUILDER_VERSION` bump (consumes already-persisted signals). Must not exclude genuine first-party product (the generated signal is path/marker-based and reliable; the vendored axis — which carries the lookalike risk — is explicitly deferred). Generic across all projects.

## Scope

**Problem statement:** The generator's area selection ranks by raw community size and ignores the generated signal, so vendored/generated subtrees dominate the map and crowd out product; hubs can land on non-code nodes; area titles collide.

**In scope (`gen_codebase_map.py`):**

- Read per-community `generated_node_fraction`; exclude generated-dominated communities from the primary tier with an honest omitted-count footer.
- Per-module/top-level-source-root area floor in the top-tier selection.
- Exclude non-code/data/minified sources from representative + `hub_node_id` selection.
- Label-collision disambiguation by path segment; drop ordinal suffixes.
- Fixtures for each; regenerate `docs/references/codebase-map.md`.

**Out of scope:**

- **Vendored-but-not-generated axis (javaagent 1b)** — needs a new explicit signal (`docs/repo-profile.json` `vendored_paths` glob or `.gitattributes linguist-vendored`) and carries a first-party-lookalike risk (a vendored-looking `JSON.java` is product code). Deferred to its own follow-up change.
- Any `graph_cluster.py` / Leiden change or `CLUSTER_BUILDER_VERSION` bump (determinism already handled; granularity root is generator-side).
- The TS extractor (sibling `1p61v`, shipped).

## Acceptance Criteria

- [x] AC-1: Communities with `generated_node_fraction > 0.4` are excluded from the primary area tier; a fixture with a generated-dominated community confirms it no longer appears as a ranked area, and the omitted count is surfaced (not silent). A real product community at the same size IS still selected.
- [x] AC-2: Per-module floor — a fixture where one oversized (e.g. vendored) subtree would otherwise consume the cap confirms each distinct top-level module still gets at least one area (no product module dropped to incidental key-file only).
- [x] AC-3: No representative path or `hub_node_id` is a non-code/data (`.json`) or minified/vendored-bundle node; a fixture with a `.json` data node and a minified file confirms neither is chosen as rep/hub.
- [x] AC-4: Area titles are disambiguated (no two areas share an identical bare title where representative paths differ); titles derive from the representative path; trailing ordinal suffixes are removed. Regenerated map + full suite + docs-lint clean; no `CLUSTER_BUILDER_VERSION` bump.

## Tasks

- [x] Read `generated_node_fraction` per community in `compute_areas`; exclude generated-dominated from the primary tier + honest omitted-count footer (AC-1).
- [x] Add the per-module / top-level-source-root area floor to top-tier selection (AC-2).
- [x] Exclude non-code/data/minified sources from representative + hub selection (AC-3).
- [x] Disambiguate colliding titles by path segment; title from representative path; drop ordinal noise (AC-4).
- [x] Fixtures for each; regenerate the map; full suite + docs-lint.
- [x] Anti-over-exclusion check: a first-party product community is never dropped by the generated filter or the per-module floor.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — note that the map consumes `generated_node_fraction` for area selection if it documents the map/cluster contract; otherwise `N/A`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The cheapest, highest-leverage fix — removes the worst vendored/generated areas using a signal that already exists. |
| AC-2 | required | Without a module floor, the product is still buried under a large dependency subtree. |
| AC-3 | important | Non-code/minified hubs make drill-in non-actionable; rep/hub must be real source. |
| AC-4 | important | Label collisions make the area list read as near-duplicates; navigability. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | teton p60n re-test: `libs/typings` split into 8 areas; grab-bag UI area with backend key files / `.json::map` hub; names shift `logger`→`packages` across rebuilds. | field-feedback memory |
| 2026-06-17 | Investigation: determinism already handled (Leiden `seed=0`); `logger`→`packages` was the Bucket-A naming change (fixed `1p60q`); granularity root is generator subdivision, not Leiden. | `graph_cluster.py:390,414`; `gen_codebase_map.py` |
| 2026-06-17 | javaagent field test: vendored/generated EL dominates area selection (~13/24 areas; 99%-generated parser as area #3); product modules crowded out (shopizer absent); label collisions (5×parser/4×javax). Re-scoped this change to generator area-selection. Confirmed `generated_node_fraction` is persisted per community (27/27 in the project artifact) — 1a is generator-only, no cluster bump. | field-feedback memory; `project-graph-clusters.json`; `graph_cluster.py:830` |
| 2026-06-17 | Implemented in `gen_codebase_map.py` (generator-only, no `CLUSTER_BUILDER_VERSION` bump): (1a) exclude communities with `generated_node_fraction>0.4` from the area tier + honest omitted-count footer; (2) `_select_with_module_floor` guarantees each top-level module a slot under the cap; (3) hub selection skips non-code/`.json`/data nodes; (4) `_disambiguate_area_names` strips ordinal noise + re-titles colliding names by path segment. 4 new tests; full suite 3258 OK; map regenerated; docs-lint clean. Faithfulness: generated filter is path/marker-based (not name heuristics) and a same-size product community is still selected; no merging, so no over-merge risk. | `gen_codebase_map.py:74,491,807,855`; `test_gen_codebase_map.py::GeneratorAreaSelectionTests` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Bundle granularity + contamination + stability into one change. | Originally believed clustering-parameter-coupled. | (Superseded by the 2026-06-17 re-scope.) |
| 2026-06-17 | Re-scope to generator area-selection + labeling (operator-directed); drop the Leiden tuning. | Investigation + javaagent showed the open work is generator area selection over an already-faithful, already-deterministic graph; the signals (`generated_node_fraction`) are already persisted. | Keep as a clustering change (rejected — wrong layer; determinism already handled). |
| 2026-06-17 | Defer the vendored-but-not-generated axis (javaagent 1b) to a follow-up. | Needs a new explicit signal (`repo-profile.json`/`.gitattributes`) and carries a first-party-lookalike risk; the generated axis (1a) delivers most of the value now with no lookalike risk. | Bundle 1b here (rejected — adds config surface + risk beyond the high-leverage fix). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The generated filter drops genuine first-party code. | The `generated` tag is path/marker-based (dir segments, `.gitattributes linguist-generated`, header signatures), not name heuristics; AC-1 includes an anti-over-exclusion check that a real product community at the same size is still selected. |
| Per-module floor over-fragments (one area per tiny dir). | Floor guarantees at least one slot per top-level module, not per leaf dir; remaining slots still fill by size within the cap. |
| Vendored EL still dominates after the generated filter (1b deferred). | Acknowledged: 1b is the structurally-complete fix and is deferred; 1a + the per-module floor materially improve the javaagent case now, and the follow-up closes the rest. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
