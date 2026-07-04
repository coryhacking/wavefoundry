# Graph index: server-process payload and adjacency cache for graph query tools

Change ID: `1p9pz-enh graph-query-payload-cache`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9q3 graph-index-efficiency`

## Rationale

Every graph tool call — `code_graph_path`, `code_graph_community`, `code_callgraph`, `code_callhierarchy`, `code_dependencies`, `code_impact`, `code_references`, `wave_graph_report` — constructs a fresh `GraphQueryIndex.from_root()` (`graph_query.py:937-940`), which does a full `json.loads` of the entire graph payload (`load_graph`, `graph_query.py:278-294`) and then rebuilds three in-memory structures from scratch: `_node_by_id`, `_out`, and `_in` adjacency maps (`GraphQueryIndex.__init__`, `graph_query.py:896-935`). This happens on **every single MCP tool invocation** — ~15 construction sites across `server_impl.py` — inside a long-lived server process. The only existing cache is `_VERSION_CHECK_CACHE` (`graph_query.py:69-74`), an mtime-based staleness check for the *state file*, not the payload.

On the self-hosted repo this costs ~30 ms parse + adjacency build and ~47 MB transient allocation per call — tolerable. It scales linearly with graph size: a 5k-file target repo pays an estimated 300 ms–1 s and several hundred MB of allocation churn *per tool call*, for a graph that changed at most once since the last call. The MCP server is exactly the long-lived process where a mtime-validated cache is safe and high-value: agents typically issue graph-tool bursts (path → impact → community) against an unchanged graph.

This is the single biggest query-latency lever identified in the graph-index efficiency evaluation, and it composes with `1p9py` (compressed artifacts make the cold load cheaper; the cache makes warm calls near-free).

## Requirements

1. **Process-level cache.** A module-level cache in `graph_query.py` holds the constructed `GraphQueryIndex` (parsed payload + `_node_by_id`/`_out`/`_in`), keyed by resolved artifact path and validated by `(mtime_ns, size)` of the graph payload file on every access. Hit → reuse the constructed index; miss/stale → reload, rebuild, replace.
2. **Correct invalidation.** Any rewrite of the payload by a build (post-edit hook refresh, `wave_index_build`, the in-query `_ensure_graph_builder_current` rebuild at `graph_query.py:122-275`) is observed on the next access via the stat check. The version-staleness path continues to run before cache consultation, and a rebuild it triggers invalidates the cached entry in-process (not only via stat, to be robust to same-mtime-resolution rewrites — compare `generated_at`/`input_fingerprint` from the loaded payload when stats are equal but a rebuild is known to have run). **Precondition (council finding, prepare review 2026-07-03):** stat-keyed caching is only safe over atomic artifact writes — `1p9py` AC-8 (temp + `os.replace`) must land before or with this change; a cache over in-place writes could pin a torn read whose stats look final.
3. **Bounded footprint.** The cache holds at most one entry per `(root, layer)` — in practice one graph (only the `project` layer exists; `graph_query.py:18`). No unbounded growth; replacing an entry releases the prior reference.
4. **Concurrency safety.** Construction and replacement are guarded (same discipline as the existing `_VERSION_REBUILD_INFLIGHT` lock, `graph_query.py:87-89`) so concurrent tool calls neither double-build nor observe a half-constructed index. `GraphQueryIndex` is treated as immutable after construction — verify no query method mutates shared structures (audit; fix or copy-on-read if any does).
5. **Kill switch.** An env var (`WAVEFOUNDRY_GRAPH_QUERY_CACHE=0` or similar, following existing env-override naming) disables the cache for diagnosis, restoring today's load-per-call behavior.
6. **All consumers routed.** Every `GraphQueryIndex` construction site in `server_impl.py` goes through the cached accessor; no site keeps a private fresh-parse path (except under the kill switch).
7. **Docs-accuracy rider.** Correct the stale graph-layer documentation encountered during the evaluation: `AGENTS.md` (and the owning seed, if the text is seed-rendered) still describes `layer='framework'` / `layer='union'` and a networkx requirement for graph query tools, but only the `project` layer exists (removed in wave 1p4ww; `Layer = Literal["project"]`, `graph_query.py:18`) and the actual optional dependency is igraph+leidenalg — networkx is never imported by any graph module. Fix the wording where it describes graph tools; respect the seed-edit gate if the surface is seed-owned.

## Scope

**Problem statement:** The MCP server re-parses the full graph payload and rebuilds all adjacency structures on every graph tool call, paying O(nodes+edges) per invocation for a graph that rarely changed between calls; cost grows linearly with repo size.

**In scope:**

- Cached accessor in `graph_query.py` with stat-validated invalidation, single-entry bound, concurrency guard, and env kill switch.
- Immutability audit of `GraphQueryIndex` query methods.
- Migration of all `server_impl.py` construction sites to the accessor.
- The AGENTS.md/seed graph-layer + networkx docs correction (Requirement 7).
- Tests: hit/miss/invalidation (including rebuild-triggered), concurrency (two threads, one build), kill switch, staleness-after-external-rewrite.

**Out of scope:**

- Caching across processes (CLI invocations remain load-per-run; only the long-lived server benefits).
- Any change to query algorithms or results — identical outputs cached vs uncached is the invariant.
- Persistent/precomputed adjacency on disk (revisit with `1p9q2` measurements if warranted).
- Semantic-index (lance) caching — separate machinery, already columnar.

## Acceptance Criteria

- [x] AC-1: Two consecutive graph tool calls against an unchanged graph parse the payload exactly once; the second call reuses the cached `GraphQueryIndex`. Verified by a unit test instrumenting the loader (call count) and, in the Progress Log, by a measured warm-call latency reduction on the self-hosted repo. *(`test_cache_hit_parses_payload_once_and_reuses_index`; measured 42.8 ms → 0.04 ms warm, see Progress Log.)*
- [x] AC-2: After the payload file is rewritten (simulated build: new mtime/size or same-stat with changed `generated_at`), the next access reloads and returns results reflecting the new graph. Unit-tested for the stat-change path, the rebuild-triggered in-process invalidation, and the same-stat pathological case. *(`test_stat_change_reloads_and_reflects_new_graph`, `test_rebuild_triggered_invalidation_reloads_despite_equal_stats`, `test_same_stat_rewrite_requires_explicit_invalidation`.)*
- [x] AC-3: Cached and uncached (kill-switch) results are identical for a representative query of each tool family — path, impact, callgraph/hierarchy, dependencies, references, community, report. Unit-tested by running both modes against a fixture graph and comparing outputs. *(`test_cached_and_uncached_results_identical_per_tool_family` — also re-runs all families against the same cached instance.)*
- [x] AC-4: Concurrent access is safe — two threads issuing queries during a cache rebuild both receive a fully-constructed index; no double-build beyond at most one redundant construction, no partially-initialized reads. Unit-tested with a barrier/latch harness consistent with existing `_VERSION_REBUILD_INFLIGHT` tests. *(`test_concurrent_access_during_construction_is_safe` — construction under the cache lock: zero redundant builds, second thread reuses the fresh entry.)*
- [x] AC-5: Immutability audit recorded — every public `GraphQueryIndex` query method verified non-mutating of `_node_by_id`/`_out`/`_in`/payload (or fixed); audit list in the Progress Log. *(All 10 methods read-only; no fixes required; `test_queries_do_not_mutate_cached_structures` locks it.)*
- [x] AC-6: All `GraphQueryIndex.from_root` construction sites in `server_impl.py` route through the cached accessor; a grep gate shows zero remaining direct fresh-parse sites outside the accessor and kill-switch path. *(17 sites migrated, exhaustive `code_keyword` enumeration in Progress Log; grep gate = `ServerImplGraphAccessorGateTests`.)*
- [x] AC-7: The AGENTS.md (and owning seed, if rendered) graph-tool paragraph no longer claims framework/union layers or a networkx dependency; wording matches ground truth (project layer only; igraph+leidenalg optional with label-propagation fallback). Seed-edit gate honored if applicable. *(AGENTS.md paragraph not seed-rendered → direct edit; seed-211's own stale `cross_layer`/`union` claims fixed under `seed_edit_allowed`, plus identical stale recipes in seeds 214/180; rendered `docs/agents/guru.md` synced manually; `docs/specs/mcp-tool-surface.md` audited — no stale wording found, skip.)*
- [x] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. *(4298 tests / 41 files OK with the wavefoundry venv python; docs-lint ok; pycache count 0.)*

## Tasks

- [x] Add the cached accessor to `graph_query.py`: module cache keyed by `(root, layer)`, stat validation `(mtime_ns, size)`, `generated_at`/fingerprint tiebreak for same-stat rewrites, construction lock, kill-switch env, explicit invalidate hook called by the in-query rebuild path. *(`get_query_index` + `invalidate_query_index_cache` + `_invalidate_query_index_cache_key`; kill switch `WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE` follows the `WAVEFOUNDRY_DISABLE_RERANKER` naming/truthy convention.)*
- [x] Audit `GraphQueryIndex` methods for mutation of shared state; fix or document immutability. *(All read-only — see Progress Log audit row.)*
- [x] Migrate all `server_impl.py` construction sites to the accessor; add the grep gate to tests or the audit record. *(17 sites; `ServerImplGraphAccessorGateTests` grep gate; `_graph_refresh_then_recheck` also invalidates explicitly after its inline graph update.)*
- [x] Correct the AGENTS.md graph-layer/networkx paragraph (and the owning seed via `seed_edit_allowed` gate if the surface is seed-rendered; check `render_platform_surfaces` ownership first). *(Paragraph is not seed-rendered — direct edit; seed-211/214/180 stale `cross_layer`/`union` wording fixed under the gate; rendered `docs/agents/guru.md` synced.)*
- [x] Tests for AC-1..AC-4 (loader-count, invalidation matrix, output-equivalence, concurrency). *(9 new `GraphQueryIndexCacheTests` + 2 gate tests; 2 existing wrapper tests re-seamed to patch `get_query_index`.)*
- [x] Measure warm-call latency before/after on the self-hosted repo; record in Progress Log.
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`. *(4298 OK; docs-lint ok; no pycache.)*

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-cache-core | implementer | — | Cached accessor + invalidation + lock + kill switch in `graph_query.py`; immutability audit. |
| ws2-consumer-migration | implementer | ws1-cache-core | Route all `server_impl.py` construction sites through the accessor; grep gate. |
| ws3-docs-rider | implementer | — | AGENTS.md / seed graph-layer + networkx wording fix (independent of code lanes; seed gate if owned). |
| ws4-tests-and-measurement | implementer | ws1-cache-core, ws2-consumer-migration | Invalidation/equivalence/concurrency tests; warm-latency measurement. |


## Serialization Points

- The accessor signature (ws1) gates ws2's mechanical migration.
- If `1p9py` lands in the same wave, the loader the cache wraps becomes gzip-aware — land `1p9py`'s reader first or coordinate the loader seam so the cache is format-agnostic (it should key on file stats, not content format).
- ws3 touches `AGENTS.md`, a shared surface also edited by other waves — small, isolated paragraph; coordinate at integration.

## Affected Architecture Docs

`AGENTS.md` graph-tool paragraph (Requirement 7 — stale layer/networkx claims) and, if the text is seed-rendered, the owning seed under `.wavefoundry/framework/seeds/`. Audit `docs/specs/mcp-tool-surface.md` for the same stale layer/union wording in graph tool entries. No layering or data-flow doc impact — the cache is process-internal to the server.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The cache actually caching is the point. |
| AC-2 | required | A stale cache silently serving an outdated graph is worse than no cache — invalidation is the correctness core. |
| AC-3 | required | Guarantees the change is transparent to every tool's results. |
| AC-4 | required | The MCP server serves concurrent calls; a half-built index would produce wrong answers, not errors. |
| AC-5 | required | Cache safety depends on immutability; one mutating method poisons every subsequent call. |
| AC-6 | required | A missed construction site keeps paying full parse and dilutes the win; the grep gate makes it checkable. |
| AC-7 | important | Docs-accuracy rider; wrong layer docs mislead agents but break nothing at runtime. |
| AC-8 | required | Suite + docs-lint green is the standing merge gate for framework code. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Delivery-review fixes (Level-2, in-session): (1) two graph-refresh initiators (`code_definition`'s refresh-then-recheck and `_graph_refresh_and_resolve`) triggered a known payload rewrite without the explicit cache invalidation Requirement 2 mandates for known rewrites — both now call `invalidate_query_index_cache` before the re-read (mirroring `_graph_refresh_then_recheck`; the same-stat coarse-mtime hazard on the repo's own Windows list). (2) Old-code-window hardening (architecture seat): the cache accessor now refuses to PIN a payload whose own `builder_version` differs from the runtime constant — a stale pre-upgrade process rewriting an old-format payload while the store meta reads current is served uncached until the next build heals it. (3) Requirement 2 mechanism note: the same-stat tiebreak shipped as the `rebuild_ran` bypass + explicit invalidation hooks; the `generated_at`/`input_fingerprint` markers are recorded per cache entry and test-asserted but not compared in production (comparing them would require the read the cache avoids) — external same-stat writers remain covered by stat granularity (`mtime_ns`) + the invalidation hooks; accepted with this rationale. (4) Serving-limit note: the report's `[1,100]` limit clamp predates this wave and is unchanged; the betweenness artifact's top-200 leaves headroom, not a served contract. | Code-reviewer lane findings 2026-07-04; architecture seat F3; red-team F4. |
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Confirmed: fresh `GraphQueryIndex.from_root()` per call at ~15 `server_impl.py` sites; full `json.loads` + three-structure rebuild per call (`graph_query.py:896-940, 278-294`); only cache today is the version-check mtime cache (`graph_query.py:69-74`); measured ~30 ms / ~47 MB per cold construction on the self-hosted repo (10,776 nodes / 30,899 edges). Also confirmed the AGENTS.md layer/networkx drift (layers removed in 1p4ww; networkx never imported by graph modules — igraph+leidenalg is the real optional dep). | `graph_query.py:18,69-74,87-89,122-275,278-294,896-940`; `server_impl.py:14369-14374`; measurements 2026-07-03. |
| 2026-07-03 | Implemented cached accessor `get_query_index` in `graph_query.py`: single-entry cache per `(resolved root, layer)`, validated by `(st_mtime_ns, st_size)` each access; version-staleness check runs before cache consultation; successful in-query rebuild explicitly invalidates via `_invalidate_query_index_cache_key` AND the observing call bypasses the stat hit (belt-and-suspenders for same-stat rewrites); `generated_at`/`input_fingerprint` recorded per entry as the same-stat content markers; construction/replacement under `_QUERY_INDEX_CACHE_LOCK` (same discipline as `_VERSION_REBUILD_INFLIGHT`); per-call `auto_rebuild_diagnostic` carried on an O(1) slot-copy view so the shared cached index is never mutated and diagnostic semantics match load-per-call exactly; kill switch `WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE` (truthy: 1/true/yes/on, per `WAVEFOUNDRY_DISABLE_RERANKER` convention). Stat is taken before the read so an atomic replace mid-sequence self-heals on the next access rather than pinning stale content. | `graph_query.py` (`get_query_index`, `invalidate_query_index_cache`, `_index_with_diagnostic`, `_QUERY_INDEX_CACHE*`); explicit invalidation in `_ensure_graph_builder_current` success path. |
| 2026-07-03 | AC-5 immutability audit — all `GraphQueryIndex` query methods verified non-mutating of `nodes`/`edges`/`_node_by_id`/`_out`/`_in`: `get_node`, `resolve_symbol`, `_prefer_callable_ids`, `traverse`, `one_hop_neighbors`, `shortest_path` (already copies each edge via `dict(edge)` before annotating `traversal_direction`), `graph_impact`, `risk_score`, `callgraph`, `report` (betweenness builds separate igraph structures). No fixes required. Methods return references to shared node/edge dicts — unchanged from per-call behavior; the repeated-query test locks non-mutation across calls. | Read of `graph_query.py:897-1701`; `test_queries_do_not_mutate_cached_structures`; AC-3 equivalence test re-runs all families on one cached instance. |
| 2026-07-03 | AC-6 migration — exhaustive `code_keyword` enumeration (limit=0, queries=[`GraphQueryIndex`, `from_root`]) found 21 hits in `server_impl.py`: 17 `from_root` construction sites (pre-edit lines 1242, 12548, 12617, 12757, 13179, 14171, 14408, 14544, 14612, 14759, 14829, 14962, 14966, 15543, 15561, 15779, 18963), 3 direct `GraphQueryIndex(payload)` constructions over locally-transformed collapse payloads (`collapsed_payload`/`merged_payload`/`directory_payload` — not fresh parses, retained), 1 docstring mention. All 17 migrated to `gq.get_query_index(...)`; `_graph_refresh_then_recheck` additionally calls `invalidate_query_index_cache` after its inline graph update. `dashboard_server.py:97` keeps `from_root` (separate process, out of scope per change doc). Grep gate: `ServerImplGraphAccessorGateTests` (no `.from_root` in server_impl; direct constructions limited to the three transform payloads). | `code_keyword` enumeration 2026-07-03; `server_impl.py`; `tests/test_graph_query.py`. |
| 2026-07-03 | Measurement (self-hosted repo, 10,955 nodes / 31,437 edges): uncached `from_root` per call 155.2 / 42.8 / 42.7 ms (first call includes cold FS cache); cached accessor cold 39.3 ms, warm hits 0.035–0.088 ms (mean 0.047 ms). Warm-call reduction ≈ 42.8 ms → 0.04 ms (~900×; ~1700× vs the uncached mean including the cold call). Tests: 11 new (9 `GraphQueryIndexCacheTests` + 2 `ServerImplGraphAccessorGateTests`), `test_graph_query.py` 61→72; 2 existing `test_server_tools.py` wrapper tests re-seamed from patching `from_root` to patching `get_query_index` (the new accessor seam). Full suite 4298 tests / 41 files OK (wavefoundry venv python); `wave_validate` docs-lint ok; no `__pycache__`. | Bench run 2026-07-03; `run_tests.py` output; `wave_validate`. |
| 2026-07-03 | AC-7 docs rider — AGENTS.md "Graph index:" paragraph verified NOT seed-rendered (no seed contains it) → direct edit to ground truth (single `project` layer; igraph+leidenalg optional with label-propagation fallback; networkx claim removed). Seed-211's own stale claims fixed under `seed_edit_allowed` (opened/closed around the seed edits): removed the nonexistent `cross_layer` report section + `cross_layer_candidates_total` bullets and replaced the `wave_graph_report(sections=["cross_layer"], layer="union")` recipe with a `code_dependencies` corroboration. Identical stale `cross_layer`/`union` recipes found and fixed in seeds 214 (architecture-reviewer) and 180 (implement-feature) under the same gate — same defect class, in-scope per Requirement 7 "fix the wording where it describes graph tools". Rendered `docs/agents/guru.md` synced manually with the seed-211 fix (renderer run out of lane scope; drift avoided by mirroring). `docs/specs/mcp-tool-surface.md` audited for stale layer/union wording — none found (audit-and-skip). Remaining repo `cross_layer` mention is an accurate historical note in `docs/architecture/graph-index-system.md:263`. | `AGENTS.md:265`; seeds 211/214/180; `docs/agents/guru.md`; grep audit 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | In-process stat-validated cache of the constructed `GraphQueryIndex` (approach A). | Highest-value lever with the smallest surface: the server is long-lived, the graph changes rarely between tool calls, stat validation is O(1), and caching the *constructed* index (not just parsed JSON) also eliminates the adjacency rebuild. Extends the codebase's existing mtime-cache pattern. | (B) Cache parsed JSON only, rebuild adjacency per call — weakness: keeps the O(nodes+edges) rebuild, which approaches parse cost; halves the win for the same invalidation complexity. (C) Persistent on-disk adjacency (precomputed indexes in the artifact) — weakness: helps cold starts only, grows the artifact, and doesn't help the dominant warm-burst pattern; deferred to `1p9q2` evidence. (D) Watchdog/inotify invalidation — weakness: platform-divergent (Windows scar tissue) for no gain over per-access stat. |
| 2026-07-03 | Validate by `(mtime_ns, size)` with `generated_at`/fingerprint tiebreak, not content hashing. | Stat is O(1) per access; hashing an 11 MB+ file per call would re-spend a large fraction of the parse cost the cache exists to save. The tiebreak covers same-stat rewrites (coarse mtime filesystems). | Hash-validate every access — rejected on cost; rely on mtime alone — rejected: known coarse-mtime hazard, and the in-query rebuild path gives a free explicit invalidation hook. |
| 2026-07-03 | Fold the AGENTS.md layer/networkx docs fix into this change rather than a separate doc change. | The stale text documents exactly the query surface this change touches; a one-paragraph rider avoids a fourth micro-change in the wave. Flagged distinctly as AC-7 so it is not silent scope. | Separate `doc` change — cleaner taxonomy, rejected as overhead for one paragraph; leave the drift — rejected: it actively misleads agents about graph tool capabilities. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stale cache after a build the stat check misses (same mtime resolution, same size). | `generated_at`/`input_fingerprint` tiebreak on equal stats; the in-query rebuild path explicitly invalidates; AC-2 tests the pathological case directly. |
| A query method mutates the cached index, corrupting subsequent calls. | AC-5 immutability audit before enabling; equivalence tests (AC-3) run repeated queries against one cached instance. |
| Memory: the cache pins one full graph in the server long-term. | Same order as one in-flight query today (~47 MB here), single-entry bound, released on invalidation; kill switch for constrained hosts; large-repo memory profile re-checked in the `1p9q2` measurement pass. |
| Cache interacts badly with the inline version-rebuild path (rebuild inside a query while another query holds the old index). | Old index stays valid for reads (immutable); replacement is atomic under the construction lock; AC-4 concurrency test covers query-during-rebuild. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
