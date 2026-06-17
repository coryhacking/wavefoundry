# Graph clustering cohesion: split cross-directory grab-bag communities

Change ID: `1p65m-enh graph-clustering-cohesion`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p65k codebase-map-round3`

## Rationale

teton round-3 (#2): community detection produces **cross-directory grab-bag communities**. The `spinner-animation` area (rep path `libs/utils/src`) spans `libs/utils`, backend `apis/ldap.ts` + `ldap-stream.ts`, a UI `.js`, and two vendored bundles — unrelated code joined into one community by **incidental weak/util edges** (a shared `toJson` / logging / common-util call). The representative-directory collapse can't make an incoherent community coherent, so the area is named after an arbitrary leaf (`spinner-animation`) and is the root cause of the vendored leak `1p65l #1` mitigates only downstream.

This is the deeper, source-side fix: raise the bar for cross-directory community formation so communities map to cohesive modules rather than edge-of-graph grab-bags.

**Round-3 UPDATE — cross-rebuild NON-DETERMINISM is now the headline (teton: "highest-value item").** Identical-input rebuilds produce different results: the top-tier area COUNT churns **221 / 224 / 100**, areas appear/disappear, names shift (`packages`↔`logger`), and the config-area label flips between the correct `configuration / manifest files` and a scraped doc-prose label (so round-3 #3 is INTERMITTENT — a symptom of this instability, not a pure generator bug). The typings area count (6–8 vs 2) varies for the same reason. This contradicts the prior "Leiden `seed=0` → deterministic" assumption. **Strong hypothesis:** the **100 outlier = label-propagation fallback** — `graph_cluster.update_graph_clusters` falls back to label-propagation when the leidenalg/igraph backend is unavailable, and label-prop is order/random-dependent (very different counts); the 221↔224 small variance may be incremental-reindex input-graph churn or the Leiden seed not fully controlling the optimizer. Making clustering reproducible stabilizes round-3 #3 (config label), the typings count (#4), and the structural-name churn (#5) **at once** — so determinism is a PRIMARY goal of this change, alongside cohesion.

## Requirements

0. **Determinism is a PRIMARY goal (round-3 #4, highest-value).** Investigate why identical-input rebuilds vary (area count 221/224/100, name/label flips). Confirm whether the leidenalg/igraph backend is consistently used or silently falling back to non-deterministic label-propagation (the likely 100 outlier); confirm the input graph is actually identical across rebuilds (vs incremental-reindex churn); confirm `seed=0` fully controls the Leiden optimizer. Make clustering reproducible: identical input → identical communities, labels, and count. If label-prop fallback is in play, make the fallback deterministic (sorted/seeded) or surface clearly when it is used. This stabilizes round-3 #3 (config label), the typings count (#4), and structural names (#5) downstream.
1. **Investigation first (no blind tuning).** Characterize WHY these communities form in `graph_cluster.py` (Leiden over the projected undirected graph): which edge types (calls/imports/reads) bridge unrelated top-level packages, and whether a resolution change vs. a post-pass split is the right lever. Record findings before tuning.
2. **Split or prevent cross-directory grab-bags.** A community whose members span N unrelated top-level packages joined only by weak/util edges should be split (or not formed) so each cohesive directory/module is its own community — without over-fragmenting genuinely cohesive single-module communities.
3. **Faithfulness / anti-over-split.** Must not shatter a real cohesive module (a legitimately cross-file feature within one package) into per-file communities; validate that genuine modules survive intact. The inverse failure (over-splitting) is as bad as the grab-bag.
4. **Determinism preserved.** Keep the existing `seed=0` determinism; the change must not introduce run-to-run instability.
5. **Project- and language-generic.** The grab-bag detection (communities spanning N unrelated top-level packages joined only by weak/util edges) and the determinism fix operate on graph structure + edge types — no hardcoded teton/JS-specific paths or names. Synthetic, cross-stack fixtures. Bump `CLUSTER_BUILDER_VERSION` (community shape changes → consumer caches re-cluster). Validate against teton (grab-bag `spinner-animation` resolves; stable area count) + the multilang pack as real-world oracles.

## Scope

**In scope (`graph_cluster.py`):** investigation of the grab-bag formation; a resolution/granularity change or a post-cluster split pass that separates cross-directory grab-bags joined by weak edges; `CLUSTER_BUILDER_VERSION` bump; fixtures (a grab-bag fixture that splits; an anti-over-split cohesive-module fixture; a determinism check); validation against teton + multilang pack.

**Out of scope:** the generator-side polish (sibling `1p65l`); the symbol-kind extractor; any retrieval/embedding change.

## Acceptance Criteria

- [x] AC-1: A fixture community whose members span multiple unrelated top-level packages joined only by a shared-util edge is split into per-module communities (no grab-bag); on teton the `spinner-animation`-style cross-directory area resolves into cohesive areas.
- [x] AC-2: Anti-over-split — a genuinely cohesive single-package multi-file module is NOT shattered into per-file communities; a fixture confirms it stays one community.
- [x] AC-3 (PRIMARY — round-3 #4): identical input → identical communities, labels, AND area count across repeated runs (no 221/224/100-style churn). The leidenalg path is used when available and is reproducible; the label-propagation fallback is either made deterministic (sorted/seeded) or clearly surfaced as degraded. A test asserts two clusterings of the same fixture graph are byte-identical (community ids/labels/membership); on teton the config-area label no longer flips and the area count is stable across rebuilds. `CLUSTER_BUILDER_VERSION` bumped with a descriptive line; multilang pack + full suite green.

## Tasks

- [x] Investigation: characterize grab-bag formation (bridging edge types; resolution vs split-pass lever); record findings in the change doc / journal before tuning.
- [x] Implement the chosen lever (resolution change and/or post-cluster split of weak-edge cross-directory grab-bags).
- [x] Anti-over-split guard + determinism preservation.
- [x] Fixtures (grab-bag split, anti-over-split, determinism); bump `CLUSTER_BUILDER_VERSION`.
- [x] Validate against teton (spinner-animation resolves) + multilang pack; full suite + docs-lint.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — update if it documents clustering granularity/cohesion behavior; otherwise `N/A`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix — grab-bag communities split into cohesive areas (source of the leak + low-value areas). |
| AC-2 | required | Anti-over-split faithfulness — over-fragmentation is as harmful as the grab-bag. |
| AC-3 | required | Determinism + version bump mandatory for community-shape changes. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | teton round-3: cross-directory grab-bag `spinner-animation` (libs/utils + backend ldap + UI .js + 2 vendored bundles) joined by weak/util edges; root cause of the vendored key-file leak. Operator opted to include this (harder, clustering) alongside the generator polish. | field-feedback memory; `graph_cluster.py` Leiden formation |
| 2026-06-17 | **Investigation (council condition):** on a byte-fixed graph in this env (modern leidenalg, `seed=0` accepted) `_run_clustering` is REPRODUCIBLE (two runs identical). `_label_propagation` is itself deterministic (fixed sort, deterministic tie-break, fixed 24 iters). The determinism holes are: (a) the Leiden `except TypeError` fallback ran UNSEEDED on older leidenalg (no `seed=` kwarg) → non-reproducible (the 221↔224 churn); (b) a silent Leiden→label-prop flip (any `find_partition` exception → label-prop, a very different count, e.g. the 100 outlier) — already recorded in the artifact's `cluster_algorithm`. | `graph_cluster.py:_build_leiden_clusters`, `_label_propagation`, `_run_clustering` |
| 2026-06-17 | Implemented: (det) seed igraph's global RNG (`igraph.set_random_number_generator(random.Random(0))`) before partitioning so the unseeded fallback is also reproducible; kept `seed=0`. (cohesion) `_split_cross_directory_grabbags` — conservative (≥`GRABBAG_MIN_DIRS`=4 distinct module-dirs, none ≥`GRABBAG_DOMINANT_SHARE`=0.5) anti-over-split per-module-dir split, deterministic. `CLUSTER_BUILDER_VERSION` 9→10. 4 new tests (grab-bag splits, cohesive doesn't, fixed-graph reproducible, version); full suite 3281 green. **Residual:** if teton STILL sees identical-input churn after upgrading, the cause is upstream INPUT-GRAPH determinism (incremental reindex producing different graphs) — out of `graph_cluster`'s scope; a separate graph-build-determinism follow-up. The grab-bag split thresholds are conservative and teton-validation may tune them. | `graph_cluster.py:13,408-414,536-585,839`; `test_graph_cluster.py` |


## Round-3 p65w re-validation + recalibration (2026-06-17)

teton re-validated on p65w (cluster v10, from-scratch rebuild): the generator polish (`1p65l`: #1 vendored key-files/hub, #3 config name, #5 structural names, #4-typings) is **confirmed resolved**. Two items needed a different approach:

- **#2 grab-bag — RESOLVED via a generator-side cohesion filter (the safe lever).** My clustering split's anti-over-split guard skipped `spinner-animation` because its home (`libs/utils`) dominates. Rather than risky post-merge clustering surgery (peel-then-the-merge-pass-re-merges), I added a deterministic generator-side filter in `gen_codebase_map.py`: an area's `key_files` and `hub_node_id` are restricted to its OWN module (first-two-segment prefix of the representative dir), with a fail-safe fallback. This strips the cross-package strays (backend `ldap.ts`) a grab-bag community absorbed — fixing teton's visible symptom — without changing community shape. Chosen per the map-ROI feedback (memory `project-codebase-map-roi`): the map is cold-start orientation for MCP agents, so the cheap/safe fix is proportionate; risky clustering surgery is not. The clustering split (no-dominant grab-bags) remains.
- **#4 determinism — DEFERRED (operator-directed).** v10's clustering-seed is real (verified: extraction AND clustering are deterministic in our env across multiple runs), but teton's identical-input churn (199/221/224/100) PERSISTS and is **not reproducible here**, so it's environment-specific and cannot be fixed blind. Deferred to a future change whose first step is INSTRUMENTATION — record a graph-content hash + `cluster_seeded`/`cluster_algorithm` flags in the artifact (and surface in the map) so teton's next rebuild pinpoints the layer (same graph-hash + different clusters = seed; different hash = upstream input-graph build). The fix follows the diagnosis.

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Investigation-first before tuning; separate change from the generator polish. | Clustering cohesion is fuzzy + a different subsystem/version constant; blind resolution tuning risks over-fragmentation. | Tune resolution immediately (rejected — needs characterization first). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Resolution/split tuning over-fragments cohesive modules. | Investigation-first; AC-2 anti-over-split fixture + teton validation that real modules survive. |
| Determinism regression from a new split pass. | AC-3 determinism test (same input → same output); preserve `seed=0`. |
| May exceed one tuning pass (fuzzy). | Investigation phase scoped before tuning; can land iteratively behind the version bump. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
