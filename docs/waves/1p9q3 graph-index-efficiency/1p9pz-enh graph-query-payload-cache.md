# Graph index: server-process payload and adjacency cache for graph query tools

Change ID: `1p9pz-enh graph-query-payload-cache`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

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

- [ ] AC-1: Two consecutive graph tool calls against an unchanged graph parse the payload exactly once; the second call reuses the cached `GraphQueryIndex`. Verified by a unit test instrumenting the loader (call count) and, in the Progress Log, by a measured warm-call latency reduction on the self-hosted repo.
- [ ] AC-2: After the payload file is rewritten (simulated build: new mtime/size or same-stat with changed `generated_at`), the next access reloads and returns results reflecting the new graph. Unit-tested for the stat-change path, the rebuild-triggered in-process invalidation, and the same-stat pathological case.
- [ ] AC-3: Cached and uncached (kill-switch) results are identical for a representative query of each tool family — path, impact, callgraph/hierarchy, dependencies, references, community, report. Unit-tested by running both modes against a fixture graph and comparing outputs.
- [ ] AC-4: Concurrent access is safe — two threads issuing queries during a cache rebuild both receive a fully-constructed index; no double-build beyond at most one redundant construction, no partially-initialized reads. Unit-tested with a barrier/latch harness consistent with existing `_VERSION_REBUILD_INFLIGHT` tests.
- [ ] AC-5: Immutability audit recorded — every public `GraphQueryIndex` query method verified non-mutating of `_node_by_id`/`_out`/`_in`/payload (or fixed); audit list in the Progress Log.
- [ ] AC-6: All `GraphQueryIndex.from_root` construction sites in `server_impl.py` route through the cached accessor; a grep gate shows zero remaining direct fresh-parse sites outside the accessor and kill-switch path.
- [ ] AC-7: The AGENTS.md (and owning seed, if rendered) graph-tool paragraph no longer claims framework/union layers or a networkx dependency; wording matches ground truth (project layer only; igraph+leidenalg optional with label-propagation fallback). Seed-edit gate honored if applicable.
- [ ] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Add the cached accessor to `graph_query.py`: module cache keyed by `(root, layer)`, stat validation `(mtime_ns, size)`, `generated_at`/fingerprint tiebreak for same-stat rewrites, construction lock, kill-switch env, explicit invalidate hook called by the in-query rebuild path.
- [ ] Audit `GraphQueryIndex` methods for mutation of shared state; fix or document immutability.
- [ ] Migrate all `server_impl.py` construction sites to the accessor; add the grep gate to tests or the audit record.
- [ ] Correct the AGENTS.md graph-layer/networkx paragraph (and the owning seed via `seed_edit_allowed` gate if the surface is seed-rendered; check `render_platform_surfaces` ownership first).
- [ ] Tests for AC-1..AC-4 (loader-count, invalidation matrix, output-equivalence, concurrency).
- [ ] Measure warm-call latency before/after on the self-hosted repo; record in Progress Log.
- [ ] Run `run_tests.py` + `wave_validate`; clean `__pycache__`.

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
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Confirmed: fresh `GraphQueryIndex.from_root()` per call at ~15 `server_impl.py` sites; full `json.loads` + three-structure rebuild per call (`graph_query.py:896-940, 278-294`); only cache today is the version-check mtime cache (`graph_query.py:69-74`); measured ~30 ms / ~47 MB per cold construction on the self-hosted repo (10,776 nodes / 30,899 edges). Also confirmed the AGENTS.md layer/networkx drift (layers removed in 1p4ww; networkx never imported by graph modules — igraph+leidenalg is the real optional dep). | `graph_query.py:18,69-74,87-89,122-275,278-294,896-940`; `server_impl.py:14369-14374`; measurements 2026-07-03. |


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
