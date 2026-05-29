# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-05-29

wave-id: `12xr2 graph-query-surface`
Title: Graph Query Surface

## Objective

Ship MCP graph query tools and opt-in graph augmentation on existing navigation tools,
plus graph-quality fixes and follow-on extraction/visualization work admitted from plans.
Backed by the validated graph index from wave `12xr1`.

## Changes

Change ID: `12xs4-feat graph-query-surface`
Change Status: `planned`

Change ID: `12z48-bug stale-index-build-lock-cleanup`
Change Status: `planned`

Change ID: `12z4a-bug test-file-detection-case-conventions`
Change Status: `planned`

Change ID: `12ynp-enh graph-dependency-injection-wiring`
Change Status: `planned`

Change ID: `12yro-enh graph-visualization-navigation-overhaul`
Change Status: `planned`

## Wave Summary

**Core (`12xs4`):** Adds `graph_query.py`, extends `code_impact` with graph-backed `symbol=`
mode (preserving existing `path=` import heuristics), new `code_callgraph` and
`wave_graph_report` MCP tools, query-time project+framework union via `networkx.compose()`,
and `graph=true` opt-in augmentation on `code_keyword`, `code_search`, `code_definition`, and
`code_references`. Default tool output unchanged when `graph=false`.

**Infra (`12z48`):** Stale `index-build.lock` reclaim, live-vs-stale diagnostics, hook
reindex coalescing — unblocks reliable graph/index rebuilds.

**Clustering (`12z4a`):** Case-insensitive, multi-language fixed-community classifiers so
Tests/Benchmarks/Scripts/etc. buckets work for Swift, Go, Java, C#, JS/TS, not just Python.

**Extraction (`12ynp`):** DI framework wiring edges (`binds`/`injects`) for Spring, CDI,
Guice/Dagger, .NET — improves graph-backed impact/callgraph on enterprise stacks.

**Dashboard (`12yro`):** WebGL renderer, per-view layouts, search-to-focus +
expand-on-demand navigation; consumes the query surface for neighborhood expansion.

**Suggested implementation order:** `12z48` → `12z4a` → `12xs4` → `12ynp` (parallel with
late `12xs4` if graph API stable) → `12yro` last.

## Acceptance Criteria

- `code_impact(symbol)` returns files and symbols that would be affected by changing the given symbol, traversing the graph up to a configurable hop limit
- `code_callgraph(symbol)` returns direct callers and callees, with optional depth expansion
- `wave_graph_report` returns a structural summary: top callers by fan-in, orphan doc pages (no graph edges), high-fan-out nodes, and cross-layer references
- Union view: `load_union()` composes `project-graph.json` and `framework-graph.json` via `networkx.compose()`; nodes tagged by `layer` attribute; used at query time only, not persisted; safe below ~50k combined nodes
- `graph=true` parameter accepted by `code_keyword`, `code_search`, `code_definition`, `code_references`; when set, supplemental graph neighbor section appended after existing output; clearly labeled and non-breaking
- Default behavior (`graph=false`) of all existing tools is byte-for-byte identical to pre-wave behavior
- All new tools have unit tests; augmentation tests cover both `graph=true` and `graph=false` paths

## Journal Watchpoints

- `framework_edit_allowed` gate required before editing any MCP server tool or framework script
- The `graph=true` augmentation must never appear in default tool output — this is a hard constraint; the upgrade path to default requires a separate wave with explicit sign-off
- Verify union view memory footprint is acceptable before shipping; if `networkx.compose()` cost shows up in profiling, document and file a follow-up

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | planning | all admitted changes — scope, serialization, AC priority |
| wave-coordinator | coordination | readiness, implementation order, review routing |
| implementer | implement | framework scripts, MCP tools, dashboard, graph extractors |
| architecture-reviewer | review | all — MCP graph query contract, union compose, augmentation boundary, DI edge vocabulary |
| code-reviewer | review | all — `.wavefoundry/framework/scripts/*.py`, dashboard JS |
| qa-reviewer | review | all — required for bug fixes (`12z48`, `12z4a`); snapshot/regression for `graph=false` |
| security-reviewer | review | `12xs4`, `12z48` — MCP symbol/path inputs, read-only tool boundaries |
| performance-reviewer | review | `12xs4`, `12yro`, `12ynp`, `12z48` — union memory, WebGL budget, hook coalescing, DI extraction cost |
| docs-contract-reviewer | review | `12xs4` — AGENTS.md / MCP tool table, augmentation contract |
| council-moderator | council | Wave Council readiness synthesis |
| red-team | council | adversarial primer |
| reality-checker | council | wave size, delivery practicality |

## Review Evidence

- wave-council-readiness: approved-with-conditions — full-tier prepare council 2026-05-29; conditions: golden snapshots before `graph=true`, measure graph sizes before 12yro renderer pick, profile union memory, serialize 12yro after query API stable.
- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare wave — readiness verdict (2026-05-29):** All five change docs wave-owned and complete. AC priority recorded on each. Required lanes assigned. Wave Council readiness pass complete. Wave admissible for implementation after pre-implementation review gate (first phase of Implement wave).
- **Prepare-phase Wave Council [prepare-council] — 2026-05-29: PASS WITH NOTES** (moderator: council-moderator; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: five admitted changes span MCP trust boundaries query-time union memory and opt-in augmentation that must stay byte-identical by default plus a large WebGL dashboard overhaul; strongest-alternative: ship 12z48+12z4a+12xs4 first and defer 12ynp and 12yro to a follow-on wave)
- Council conditions: enforce implementation order 12z48 then 12z4a then 12xs4 then 12ynp then 12yro; golden snapshots before graph=true; 12yro AC-1 measurement before renderer pick; profile union compose on Wavefoundry graph.
- product-owner: N/A — framework harness wave.
- **Pre-implementation review (2026-05-29):** `passed` — pre-mortem completed; packet complete; highest risk is `graph=false` byte-identity regression on four existing MCP tools (12xs4); mitigated by capturing golden snapshots before any augmentation wiring and gating qa-reviewer on snapshot diff.

### Pre-mortem (failure modes)

| # | Likely cause | Mitigation |
| - | ------------ | ---------- |
| 1 | **`graph=false` output drift** — augmenting `code_keyword`, `code_search`, `code_definition`, `code_references` changes default serialization | Golden snapshots before implementation; augment only when `graph=true` explicit; separate code path; qa-reviewer on snapshot tests |
| 2 | **Wave scope creep** — five changes span lock infra, clustering, MCP query layer, DI extraction, and WebGL dashboard | Enforced serialization: `12z48` → `12z4a` → `12xs4` → `12ynp` → `12yro`; defer 12yro until 12xs4 neighbor API + AC-1 size measurement |
| 3 | **Union compose memory** — `networkx.compose()` on large project+framework graphs | Default `layer=project`; profile union on Wavefoundry graph; document ~50k combined-node budget |
| 4 | **DI edge noise** (12ynp) — false `binds`/`injects` edges poison impact/callgraph | Honest confidence; no guessed multi-impl bindings; per-framework fixtures + negative tests |
| 5 | **Stale lock reclaim race** (12z48) — reclaim path allows concurrent real builds | OS `flock`/`msvcrt` remains authority; pid liveness + `started_at` vs `LOCK_STALE_SECONDS`; extend `IndexBuildLockTests` |

**Accepted known risks:** 12yro renderer stack choice deferred to AC-1 measurement; `networkx` may require tool-venv dependency add; uncommitted local Documentation fixed-community work in `graph_cluster.py` is **not** admitted scope for 12z4a.

### Packet completeness

- [x] Five admitted change docs complete (Requirements + ACs + AC priority + tasks + risks)
- [x] Required review/builder lanes in Participants table
- [x] `wave-council-readiness` + valid `prepare-council` verdict present
- [x] Dependency wave `12xr1` closed; graph artifacts validated
- [x] Architecture docs named per change (`search-architecture.md`, `data-and-control-flow.md`, dashboard adapter model)
- [x] MCP grounding: `_index_build_lock` at `indexer.py:1258` (no liveness reclaim today); `code_impact` at `server_impl.py:9165` (`path`/`max_results` only); `_layoutGraph` at `dashboard.js:1101`; `graph_query.py` greenfield; hook reindex via bare `subprocess.Popen` in `after-file-edit.py:182` (no coalesce today)

### Ordered execution plan (operator-approved via Implement wave intent)

| Order | Change | Builder lane | Key touchpoints | Verification |
| ----- | ------ | ------------ | ----------------- | ------------ |
| 1 | `12z48` | implementer | `indexer.py` `_index_build_lock`, `after-file-edit.py` coalesce | `test_indexer.IndexBuildLockTests` |
| 2 | `12z4a` | implementer | `graph_cluster.py` shared dir helper + classifiers | Table-driven `test_graph_cluster.py`; graph rebuild spot-check |
| 3 | `12xs4` | implementer | **Snapshots first**, then `graph_query.py`, `server_impl.py` MCP wiring | `test_graph_query.py`, `test_server_tools.py` golden diffs |
| 4 | `12ynp` | implementer | `graph_indexer.py` collect-then-resolve DI signals | Per-framework fixtures; `GRAPH_BUILDER_VERSION` bump |
| 5 | `12yro` | ui-ux-engineer + implementer | AC-1 measurement → vendor UMD → `dashboard.js` WebGL + tree peer | `test_dashboard_server.py`; perf budget at p95 |

**Parallelism:** 12ynp may overlap late 12xs4 once graph query API is stable. 12yro is strictly last.

- pre-implementation-review: passed (2026-05-29) — pre-mortem completed, packet complete; highest risk is graph=false byte identity on four MCP tools; golden snapshots before augmentation wiring; serialization order enforced per council conditions.

## Dependencies

- Depends on wave `12xr1 graph-index-extraction-and-visualization` being closed and graph files validated via dashboard visualization before this wave opens.
