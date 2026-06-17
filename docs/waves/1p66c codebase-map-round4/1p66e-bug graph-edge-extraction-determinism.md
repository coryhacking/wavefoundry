# Code-graph edge extraction is nondeterministic on identical input

Change ID: `1p66e-bug graph-edge-extraction-determinism`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66c codebase-map-round4`

## Rationale

Field validation (teton, TS/Nx monorepo) ran two back-to-back `wave_index_build(content='graph', mode='rebuild')` passes on **identical source** and got **different graphs**: edge count `75068` vs `74890`, and a different top-24 area set downstream (`data-grid` in one run, `tokens` in the other). Across history the area denominator churned `221 / 224 / 199 / 100`. `hub_node_id` is stable by design, but the human-facing structure (areas, names) is not reproducible, which is the root of round-3 `#3` (config label scraped intermittently) and the typings-count variance.

The decisive signal is that **edge count varies on identical input** — not just ordering. That means cross-file resolution *outcomes* differ run-to-run: the same call binds to a real edge in one run and stays `external::` in another. Clustering was only ever downstream of this — round-4 confirms the instability originates in the **input graph** (edge extraction), so seeding the clusterer (`1p65m`, `CLUSTER_BUILDER_VERSION=10`) could not stabilize it.

Investigation of `graph_indexer.py` locates the order-sensitive machinery in the cross-file resolution stage (the disambiguation passes added in 1.6):

- The input file list passed to `update_graph_index` is **not confirmed sorted** before extraction; processing order can vary between runs.
- `node_map.items()` (`~7169`) builds `per_file_simple` with a last-wins rule (`len(node_id) < len(existing)`) — a tie keeps whichever was seen first.
- `per_file_simple.items()` (`~7199`) appends into `simple_name_index` / `qualified_index` candidate lists in iteration order; resolution then turns on `len(candidates) == 1` and `candidates[0]`, so candidate **order and membership** decide whether an edge resolves or stays external.
- `imports_by_file` (`~7263`) keeps a **last-wins** FQN per final segment, feeding ambiguous-receiver disambiguation.
- The cross-file rewrite loop over `edge_map.items()` (`~7279`) and the post-rewrite `edge_map.setdefault(new_key, …)` (`~7489`) collapse colliding rewrites first-wins by iteration order.

No input-graph fingerprint is emitted today, so the instability could not be confirmed at the source. This change makes the input graph **reproducible** (deterministic resolution outcomes) and emits a fingerprint so reproducibility is verifiable on every build.

## Requirements

1. **Instrument first.** Emit a stable input-graph fingerprint into the graph build output/metadata: a content hash over the **sorted** node-set and the **sorted** edge-set (after resolution), plus the clustering seed/algorithm flags already used. Two identical-input rebuilds must report the same fingerprint when the build is deterministic; a differing fingerprint localizes any residual nondeterminism to extraction vs. clustering for downstream debugging.
2. **Deterministic file processing order.** Sort the file list deterministically before extraction so worker/result order cannot vary between runs (independent of any concurrency).
3. **Order-independent cross-file resolution.** Every resolution decision (candidate-set construction, last-wins maps, `len==1`/`candidates[0]` selection, `setdefault` collisions) is made independent of dict/set iteration order: sort candidate iterations and apply an explicit, stable tie-break (e.g. shortest-then-lexicographic node id) wherever a "pick one" or "first/last wins" currently depends on order.
4. **Faithfulness preserved (binding correctness gate).** The determinism hardening must change only *which-comes-first* among equally-valid outcomes — it must **not** newly bind a wrong same-named twin, drop a previously-correct edge, or change the unambiguous (`len==1`) resolutions. The chosen edge for a genuinely ambiguous case must be picked by an explicit, documented, faithful tie-break, never by accident of iteration. (Per security-control/binding-faithfulness review policy for graph symbol-resolution changes.)
5. **Version bump.** Bump `GRAPH_BUILDER_VERSION` (currently `"31"`, `graph_indexer.py:28`) because the emitted edge set changes shape (stabilizes), so consumer caches rebuild on upgrade.
6. **Reproducibility test.** A test extracts a fixed multi-file fixture twice (and/or with shuffled input file order) and asserts an **identical** resolved edge set and identical fingerprint — the regression lock for `#4`.

## Scope

**Problem statement:** Identical source produces different code graphs (edge count `75068` vs `74890`) across rebuilds because cross-file resolution outcomes depend on file-processing and dict/set iteration order, making the codebase map non-reproducible.

**In scope:**

- `graph_indexer.py`: deterministic file ordering before extraction; order-independent + explicitly tie-broken resolution at the sites above (`~7169`, `~7199`, `~7263`, `~7279`, `~7489`); input-graph fingerprint emission into graph metadata; `GRAPH_BUILDER_VERSION` bump.
- Tests in `test_graph_indexer.py` (reproducibility/shuffle-invariance, fingerprint stability, faithfulness no-regression on the existing cross-file resolution fixtures).
- Surfacing the fingerprint where graph status is reported if cheap (`wavefoundry://graph/status` / `wave_graph_report`) — audit; include only if it is a small, natural addition.

**Out of scope:**

- Clustering determinism (`1p65m` already seeds the clusterer; this change removes the *upstream* cause it could not reach). Re-validate clustering stability only as a downstream effect.
- The per-area `AGENTS.md` resolver (`1p66d`).
- Finer symbol-kind taxonomy (round-4 `#4` cosmetic sub-item: `interface`/`type`/`property`/`enum`) — not required for determinism; deferred.
- Any change to *what* a faithful resolution should be — only *stability* of the outcome.

## Acceptance Criteria

- [x] AC-1: Extracting a fixed multi-file fixture twice produces an **identical resolved edge set** (same edges, same count); a test that **shuffles the input file order** produces the identical edge set. This is the `#4` regression lock. (`EdgeExtractionDeterminismTests.test_double_build_identical_edge_set_and_fingerprint`, `test_shuffled_input_order_identical_edge_set_and_fingerprint`.)
- [x] AC-2: A stable input-graph fingerprint (sha256 over sorted node-set + sorted resolved edge-set) is emitted into the graph payload + state (`input_fingerprint`) and is identical across the two AC-1 runs. (Excludes the volatile `generated_at`; same tests assert equality.)
- [x] AC-3: Faithfulness no-regression — existing cross-file resolution tests (same-name-twin disambiguation, sibling-loader, namespace/receiver resolution, constant `reads`) still pass unchanged (`CrossFileResolutionTests`, 38 green incl. determinism); no unambiguous (`len==1`) resolution changed — every branch still requires a unique match; ambiguous picks use the documented stable tie-break (`_pick_shorter_node_id` commutativity test), not iteration order.
- [x] AC-4: `GRAPH_BUILDER_VERSION` bumped `31`→`32` in the same change; consumers re-extract on upgrade. (Version-pin test updated.)
- [x] AC-5: Full suite (3297) + docs-lint clean. Perf: no new per-edge sort — the only added sorts are once over `edge_replacements` (bounded by rewrite count) and once over node/edge keys for the fingerprint at finalize (a single O(n log n) pass already mirrored by the existing payload node/edge sort); negligible at graph scale. The note re-bind/twin faithfulness gate is preserved by the unique-match invariant.

## Tasks

- [x] Input ordering: confirmed the final node/edge assembly already iterates `sorted(artifacts.keys())` (`graph_indexer.py:7060`), so node/edge *content* is order-independent; the remaining holes were the resolution tie sites below (no redundant file-list sort added). Council condition 1 (complete-table post-join resolution) confirmed: resolution runs as a second pass over the fully-assembled, sorted `edge_map`/`node_map`.
- [x] Made candidate selection order-independent with explicit stable tie-breaks: `per_file_simple` via module-level `_pick_shorter_node_id` (shortest-then-lexicographic), `imports_by_file` collision keeps the lexicographically smallest FQN, rewrite-apply sorted by `(new_key, old_key)`.
- [x] Compute + emit the input-graph fingerprint (sha256 over sorted node-set + sorted resolved edge-set) into the graph payload + state.
- [x] Bump `GRAPH_BUILDER_VERSION` `31`→`32`.
- [x] Tests: double-build + shuffled-input edge-set identity, fingerprint stability, `_pick_shorter_node_id` order-independence (non-vacuous unit lock), cross-file faithfulness no-regression.
- [x] docs-lint + full suite (3297 green); extraction-time impact noted in AC-5; arch doc `graph-index-system.md` updated.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — note the determinism guarantee and the input-graph fingerprint in the graph build description. No layering/boundary change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix — identical input → identical edge set. |
| AC-2 | required | Verifiable reproducibility signal (instrument-first ask). |
| AC-3 | required | Faithfulness: stability must not change correct bindings. |
| AC-4 | required | Shape change requires the version bump (consumer rebuild). |
| AC-5 | important | No regression / perf sanity. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Planned from teton round-4 `#4`: edge count `75068` vs `74890` on identical input pins nondeterminism to the input graph (resolution outcomes), not clustering. | round-4 feedback; resolution sites `graph_indexer.py:~7169/7199/7263/7279/7489`; `GRAPH_BUILDER_VERSION` line 28 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Fix the input-graph (extraction) determinism, not the clusterer. | Edge-count variance on identical input proves the instability is upstream of clustering; `1p65m` already seeds the clusterer and could not stabilize it. | Re-seed/replace clustering only (rejected — does not address edge-set variance). |
| 2026-06-17 | Stabilize via deterministic ordering + explicit tie-breaks, preserving existing faithful bindings. | Round-4 ask + binding-faithfulness policy: stability must not silently re-bind twins or drop edges. | Lock outcomes by caching first-run results (rejected — masks the bug, not reproducible from scratch). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A "stabilizing" tie-break silently changes a previously-correct ambiguous binding (wrong-twin). | AC-3 faithfulness no-regression on existing resolution fixtures; explicit documented tie-break; adversarial faithfulness review before close (graph symbol-resolution policy). |
| Not reproducible locally (teton's environment reproduces; ours did not in round 3). | Instrument-first (fingerprint) makes reproducibility verifiable downstream; shuffle-invariance test exercises the order-dependence deterministically in-suite. |
| New sorting regresses extraction time on a large repo. | Sort once at the file-list and index-construction level (not per-edge hot loop); record a spot-check (AC-5). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
