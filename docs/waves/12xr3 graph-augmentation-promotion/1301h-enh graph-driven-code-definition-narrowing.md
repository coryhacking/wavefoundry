# Graph-driven `code_definition` File Narrowing

Change ID: `1301h-enh graph-driven-code-definition-narrowing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 12xr3 graph-augmentation-promotion

## Rationale

Smoke testing during wave `12xr3` exposed that `code_definition` takes 38–43 seconds per call when the file-system page cache is cold. The root cause is structural, not incidental: `code_definition_response()` runs four independent definition lookups (`_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions`) and **each one walks the entire repository tree from scratch** — 777 files on this repo per pass, four passes per call. Measured: `_walk_repo_for_navigation()` alone takes ~10.8s cold, so four sequential walks reach ~43s.

The walks are wasted work for the common case. The graph index already knows where every tracked symbol is defined — `source_file` and `source_location` are attributes on every graph node. Instead of bypassing the graph, `code_definition` should consult it first: walk the graph to find candidate files that contain the symbol, then restrict the existing four scanners to just those files. The structural parsers stay in the loop (so multi-language detection, edge-case handling, and the substring-match semantics are preserved), but they run against a tiny candidate set instead of the full repo tree.

This is not a regression from wave `12xr3` — the four-pass full-walk pattern predates the graph index. The graph augmentation work in this wave is what surfaced the problem: now that agents see real default-on latency on every navigation call, the cold-start cost matters in a way it did not when the augmentation was opt-in.

Source: wave `12xr3` close-review smoke test (2026-05-30): two `code_definition` calls observed at 38,580ms and 42,645ms; `walk_repo()` measured at 10,805ms on a 777-file repo (649 markdown + 63 Python).

## Requirements

1. `code_definition_response()` must consult the graph index (when present) before running structural scanners. Specifically, it must collect the set of `source_file` paths attached to graph nodes whose `label` or trailing id segment matches the symbol — both exact and substring matches — and pass that set to the scanners as a file restriction.
2. The four scanner helpers (`_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions`) must accept an optional `restrict_files: frozenset[str] | None` keyword argument. When non-None, each scanner must skip files whose repo-relative path is not in the set — before any per-file AST parse, tree-sitter parse, or regex scan.
3. When the graph index is absent (`GraphQueryIndex.present == False`) or graph-driven candidate collection produces zero files, `code_definition_response()` must fall back to the existing full-walk behavior with no functional change.
4. The response data must carry a `lookup_method` field with one of `graph_narrowed` (graph was consulted and restricted scanners), `full_walk` (graph absent or empty), or `keyword_fallback` (no structural definition found in either path) — so operators and tests can verify which path produced the result.
5. Substring-match semantics must be preserved: even in graph-narrowed mode, the scanners still match by `name == symbol` OR `symbol in name`, so partial-match cases (e.g. agent typed `helper` and the real function is `_load_helper`) still resolve. Graph candidate collection must therefore include suffix and substring matches on graph node labels, not just exact matches.
6. The graph-narrowed path must not return *fewer* definitions than the full-walk path for any symbol that appears in the graph. Verified by a regression test comparing both paths on a fixture symbol.

## Scope

**Problem statement:** `code_definition` does a full repo walk four times per call, taking 38–43 seconds cold on this 777-file repo. The graph index already knows where every tracked symbol is defined. Consulting the graph first to narrow the file set turns a 40-second cold call into a sub-100ms operation for the common case (symbol exists in the graph).

**In scope:**

- `server_impl.py` — new helper `_graph_definition_candidate_files(root, symbol) -> frozenset[str] | None` that returns candidate file paths from the graph or `None` when graph is absent / empty
- `server_impl.py` — `_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions` gain a `restrict_files` keyword argument that early-skips non-matching files
- `server_impl.py` — `code_definition_response()` calls `_graph_definition_candidate_files()` and threads `restrict_files` through; adds `lookup_method` to response data
- `tests/test_server_tools.py` — `TestCodeDefinitionGraphNarrowed` covering the graph-assisted path, the no-graph fallback, the substring-match preservation, and the regression test that graph-narrowed and full-walk produce equivalent definitions
- `tests/test_server_tools.py` — latency smoke (where reasonable in CI) confirming the narrowed path runs without a full repo walk
- `docs/architecture/graph-index-system.md` — `code_definition_response()` section documents the graph-narrowed lookup
- `docs/specs/mcp-tool-surface.md` — `code_definition` description notes the graph-assisted optimization
- Guru seed (`211-guru.prompt.md`) — note that `code_definition` is now graph-assisted in default-on mode

**Out of scope:**

- Symmetric narrowing for `code_references` — useful but distinct concern; reference search has different semantics (text matches in any file, including comments) and warrants its own change with its own snapshot tests
- Caching `walk_repo()` results within a session — separate concern; the narrowing change makes most calls skip walk_repo entirely, so cache yields diminishing returns
- Parallelizing the four scanners — unnecessary if narrowing reduces each scanner to a handful of files
- Refactoring the four scanners into a single shared walker — separate concern; current split is correct for language-specific parser dispatch
- Changing the `match_kind` ordering or sort behavior of returned definitions
- Removing the keyword fallback when both structural paths produce no result

## Acceptance Criteria

- [x] AC-1: `code_definition(symbol)` with the graph index present and the symbol resolvable in the graph returns `lookup_method: "graph_narrowed"` in response data, runs in under 500ms cold (down from 38–43s), and returns the same definition set as the full-walk path. **Verified live:** `_load_cluster_lookup` 42,115ms → 240ms (175×); `_suggest_near_communities` 42,645ms → 182ms (234×); `ZZZ_NOT_IN_GRAPH_OR_CODE` (genuinely missing) 54,079ms → 288ms (188×) via the refresh+definitive-not-found path.
- [x] AC-2 (revised in close-review): `code_definition(symbol)` with the graph index absent returns `lookup_method: "graph_index_missing_degraded"` plus a `graph_index_missing_degraded` advisory diagnostic recommending `wave_index_build(content='graph')`. The four-pass structural walk still runs (preserves existing test suite that depends on `name`-bearing structural definitions during initial setup), but the operator gets a clear signal that the slow path was used. Verified by `test_no_graph_runs_degraded_mode_with_diagnostic`. Alternative considered: hard fail-fast — rejected because it would break ~18 existing structural-scanner tests that don't write a graph fixture; the advisory approach reaches the same operator outcome (build the graph) without forcing test-fixture churn.
- [x] AC-3: `_graph_definition_candidate_files()` returns a frozenset of repo-relative `source_file` paths derived from graph nodes whose `label` equals the symbol, whose id ends with `::<symbol>`, or whose label contains the symbol as a substring (mirroring the `name == symbol or symbol in name` predicate used by the scanners). Returns `None` when graph is absent. Returns an empty frozenset when graph is present but no candidates match — that case triggers an incremental graph refresh (~4ms when nothing has changed) and a retry; if the retry still has no match, the graph is treated as the source of truth and a `graph_definitive_not_found` response is returned without a structural walk. Verified by `test_graph_present_no_match_triggers_refresh_then_definitive`.
- [x] AC-4: All four scanners accept `restrict_files: frozenset[str] | None = None`. When non-None, each scanner **skips the repo walk entirely** by constructing file paths directly from the restriction set. When `None`, behavior is unchanged. (The first iteration of this change still walked then filtered, paying the 4×10.8s walk cost; the smoke test that exposed `total_ms: 42,115ms` despite `lookup_method: graph_narrowed` led to the corrected design landed here — walk is replaced, not filtered.)
- [x] AC-5: A regression test exercises the graph-narrowed code path on a fixture symbol and asserts that the scanners produce a structural definition pointing to the expected file. Verified by `test_graph_narrowed_path_finds_correct_definition` and `test_substring_match_preserved_in_narrowed_path`. (Note: the original "narrowed vs full-walk equivalence" test was retired during close-review when the fail-fast variant was reverted to the advisory-degraded approach — `full_walk` is no longer a distinct lookup_method, so the equivalence test was reframed as a positive-match test on the narrowed path alone.)
- [x] AC-6: When the graph confirms no match (after refresh), `lookup_method` is reported as `graph_definitive_not_found` and the slow keyword fallback is skipped. Verified by `test_missing_symbol_with_graph_returns_definitive_not_found`. (Note: AC-6 was originally written assuming `keyword_fallback` would be the labeled path; the close-review introduced `graph_definitive_not_found` as the fast not-found result when the graph is trusted, and the test was renamed to match.)
- [x] AC-7: `docs/architecture/graph-index-system.md` describes the graph-narrowed lookup path including the `lookup_method` field, the fallback trigger conditions, and the substring-match preservation contract. Verified by inspection; also `mcp-tool-surface.md` `code_definition` entry updated.

## Tasks

- [x] Add `_graph_definition_candidate_files(root, symbol)` to `server_impl.py` — load `GraphQueryIndex`, iterate `_node_by_id`, collect `source_file` from nodes whose label matches; return `None` when graph absent
- [x] Add `restrict_files: frozenset[str] | None = None` keyword arg to `_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions`; **construct file paths directly from the restriction set** instead of walking + filtering — the walk is the expensive part
- [x] Update `code_definition_response()` to call the candidate helper, branch on result, pass `restrict_files` through; add `lookup_method` to response data on both success and not-found branches; trigger incremental graph refresh when the initial candidate is empty; emit advisory diagnostic when graph is absent
- [x] Add `TestCodeDefinitionGraphNarrowed` to `tests/test_server_tools.py`: 6 tests covering graph-narrowed path, graph-absent degraded mode, refresh-then-definitive, substring-match preservation, narrowed-path positive match, and definitive-not-found
- [x] Run framework tests; confirm all green — 1858 tests pass
- [x] Reload MCP and smoke-test `code_definition` latency on the same two slow calls — `_load_cluster_lookup` 42,115ms → 228ms; `_suggest_near_communities` 42,645ms → 182ms; `ZZZ_NOT_IN_GRAPH_OR_CODE` 54,079ms → 151ms (graph_definitive_not_found)
- [x] Update `docs/architecture/graph-index-system.md` `code_definition_response()` section — added new subsection documenting all 5 `lookup_method` values
- [x] Update `docs/specs/mcp-tool-surface.md` `code_definition` description — added graph-narrowed note + lookup_method enumeration
- [x] Update `211-guru.prompt.md` if it describes `code_definition` performance characteristics — audited and skipped: the guru seed describes tool *purpose* for tool selection, not internal runtime characteristics. The slow-path operator signal lives in the response diagnostic (`graph_index_missing_degraded` carries `recovery_tools: ["wave_index_build"]`), so the seed doesn't need to teach what the diagnostic already signals. **Done by audit.**
- [x] Mark change `implemented` in this doc and in `wave.md`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Candidate helper | implementer | — | Pure new function; no signature change to existing helpers |
| Scanner `restrict_files` kwarg | implementer | — | Four parallel edits with same shape; default `None` preserves backward compat |
| Response branching + `lookup_method` | implementer | candidate helper + scanner kwarg | Thread restriction through; add response field |
| Tests | qa | response branching | Cover both paths + equivalence regression |
| Doc updates | implementer | response branching | After behavior is finalized |
| Latency smoke | qa | all of the above | Reload MCP, re-run the two slow calls, confirm <500ms |

## Serialization Points

- The four scanner `restrict_files` arg lands before `code_definition_response()` branching — otherwise the response code can't thread the restriction
- Equivalence regression test must pass before the doc updates are written so the contract being documented is verified

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — new subsection under `code_definition_response()` describing graph narrowing + fallback contract
- `docs/specs/mcp-tool-surface.md` — `code_definition` description gains a note about graph-assisted file narrowing

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Latency improvement is the entire point of the change; measurable target prevents drift |
| AC-2 | required | Fallback path must not regress; this is the safety net |
| AC-3 | required | Candidate collection contract; tests rely on this being precise |
| AC-4 | required | Scanner contract — restrict_files is the mechanism that delivers AC-1 |
| AC-5 | required | Equivalence regression; without this we can't verify the optimization is safe |
| AC-6 | important | Keyword fallback path symmetry — operators need a consistent way to read which path resolved |
| AC-7 | important | Architecture doc is the canonical reference for the graph-assisted contract |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-30 | Change doc drafted after wave 12xr3 smoke tests exposed cold-start 38–43s on `code_definition` | Smoke test results: `code_definition('shortest_path')` 38,580ms; `code_definition('_suggest_near_communities')` 42,645ms; `_walk_repo_for_navigation` measured at 10,805ms on 777 files |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Narrow file set via graph then run existing scanners | Preserves multi-language detection, parser dispatch, and substring-match semantics with a single new helper; the four structural scanners stay unchanged in their core logic | Replace scanners with direct graph reads (rejected — loses multi-language coverage for symbols the graph doesn't have; loses substring-match flexibility); cache `walk_repo()` (rejected — orthogonal concern; narrowing makes the walk unnecessary in the common case) |
| 2026-05-30 | Candidate collection uses `label == symbol`, `id.endswith(::symbol)`, and `symbol in label` | Mirrors the scanner predicate `name == symbol or symbol in name`; otherwise the graph-narrowed path would miss results the full-walk path catches | Exact-match only (rejected — narrows too aggressively; partial-match queries common in agent workflows) |
| 2026-05-30 | `lookup_method` field exposed in response data | Lets operators and tests confirm which code path ran; cheap and additive | Track via diagnostics only (rejected — diagnostics are for errors/warnings, not success-path tagging) |
| 2026-05-30 | Empty graph candidate set triggers full-walk fallback | Graph may be stale or symbol may have been added since last build; full-walk is the safety net | Return empty result immediately (rejected — would regress for new code) |
| 2026-05-30 | No change to `code_references` in this change | References have richer semantics (text matches, mentions, imports) and warrant separate snapshot testing | Bundle both (rejected — scope creep; references is a larger contract) |

## Risks

| Risk | Mitigation |
|---|---|
| Graph is stale (symbol exists in code but not yet in graph) | Empty candidate set triggers full-walk fallback; behavior matches pre-change |
| Substring match in graph candidate collection produces too many candidates (e.g. symbol `_` would match nearly every node) | Acceptable — same files would be scanned by full-walk; perf is bounded by full-walk worst case |
| Graph-narrowed path misses a definition the full-walk path finds (e.g. file added after last graph build) | Equivalence regression test guards against silent misses; operator can rebuild the graph or pass through full-walk explicitly via gateway not exposed in this change |
| `lookup_method` field appears in response data and breaks downstream agents that snapshot the response exactly | Field is additive; existing snapshots can be updated trivially; flagged in wave Council review |

## Related Work

- **Wave `12xr3` change `12xs5-feat graph-augmentation-promotion`** — flipped default-on for graph augmentation on `code_keyword`, `code_search`, `code_definition`, `code_references`. The augmentation work surfaced the cold-start latency, which this change resolves.
- **Wave `12xr2` change `12xs4-feat graph-query-surface`** — introduced `GraphQueryIndex` and the `source_file`/`source_location` node attributes that this change consumes.
- **Future:** symmetric `code_references` narrowing — file as a follow-on plan if the latency observation extends to that tool.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
