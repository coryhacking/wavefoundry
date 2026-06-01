# Graph-Builder Java Receiver-Type Attribution — Eliminate Phantom Edges at Index Time

Change ID: `1312l-enh graph-builder-java-receiver-type-attribution`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Aceiss field report (2026-06-01) on `1.2.0+312f`: `code_impact("writeObject")` returns 19 affected callers across 3 communities (JSON, JdbcUserListJob, LdapUserListJob), while `code_callhierarchy("writeObject")` correctly returns 2 callers in 1 community (JSON). Same symbol, same graph, contradictory answers.

**Root cause:** wave 130rj's receiver-type fix (`130tw-enh java-receiver-type-resolution`) was implemented as a per-tool filter inside `code_callhierarchy_response`. The underlying graph still carries phantom `calls` edges from simple-name attribution at index time. `code_impact` (which traverses the graph directly), `wave_graph_report.fan_in` (which counts incoming edges), and any future consumer that touches edges all see the phantoms. The seed-180/211 architecture-review guidance ("check community: field on affected nodes — escalate when cross-cutting") fires false positives because the graph itself lies.

The per-tool filter is whack-a-mole. The correct fix is to resolve receiver types **once, at graph-build time**, and attribute `calls` edges to the actual target class's node instead of the simple-name match. This eliminates phantoms for all consumers — `code_callhierarchy`, `code_impact`, `code_callgraph`, `code_graph_path`, `wave_graph_report.fan_in` / `fan_out` / `chokepoints` / `betweenness`, and `code_graph_community.generated_node_fraction` (which uses edge counts internally) — without per-tool duplication.

This change moves the receiver-type resolution logic from `server_impl.py` into `graph_indexer.py`, applies it during Java edge construction, and bumps `GRAPH_BUILDER_VERSION` so existing graph caches re-extract on upgrade.

## Approach

The receiver-type resolution helpers (`_resolve_java_receiver_type`, `_resolve_java_identifier_type`, `_search_java_declarations_in_scope`, `_extract_simple_java_type_name`, `_find_enclosing_java_class_name`) are general-purpose and already proven by wave 130rj's 9 unit tests. The refactor:

1. **Move the helpers to a shared module** (`.wavefoundry/framework/scripts/java_receiver_resolution.py` or extend `graph_indexer.py`). Both `server_impl.py` and `graph_indexer.py` import.
2. **In `graph_indexer.py` Java edge construction**: when emitting a `calls` edge for a `method_invocation` node:
   - Resolve the receiver type using the existing helper.
   - If the resolved type matches a project class's simple name → emit edge to that class's method node.
   - If the resolved type is uncertain (None) → emit edge using current simple-name attribution (false-positive bias preserved — same rule as the query-time filter).
   - If the resolved type is a known external class (no project node) → emit edge to `external::<ResolvedType>.<method>`.
3. **The query-time filter in `code_callhierarchy_response` stays as defense-in-depth** for codebases on cached pre-version-bump graphs. Becomes a no-op for cleanly-rebuilt graphs.
4. **`GRAPH_BUILDER_VERSION` bump** so on upgrade the graph is rebuilt with correct attribution.

Java is in scope per Aceiss. C# / Kotlin can extend the same pattern but operator-validation-driven.

## Requirements

1. **Refactor**: extract receiver-type helpers from `server_impl.py` into a shared module accessible to both `graph_indexer.py` and `server_impl.py`. No behavior change at the server layer.
2. **`graph_indexer.py` Java edge construction**: when scanning `method_invocation` nodes for `calls` edges, resolve the receiver type before edge emission. Attribute to project nodes when receiver type matches; preserve simple-name attribution when uncertain.
3. **External attribution**: when receiver type resolves to a non-project type (e.g., `ObjectOutputStream`), edges go to `external::<Type>.<method>` instead of a project node.
4. **`GRAPH_BUILDER_VERSION` bump**: existing cached graphs invalidate; first wave_index_build after upgrade re-extracts.
5. **Query-time filter in `code_callhierarchy_response` preserved as no-op defense**: when the index is rebuilt correctly, no edges to filter. For cached pre-bump graphs, the existing filter still works.
6. **`code_impact` no longer needs a parallel filter**: its underlying graph is clean.
7. **`wave_graph_report.fan_in/fan_out/chokepoints/betweenness` counts reflect cleaned-up edges**: the Aceiss case (`JSON.writeObject` fan_in counting `oos.writeObject` callers) goes away at index time.
8. **Tests** cover (a) two-class Java fixture indexes correctly attributing `oos.writeObject` to `external::ObjectOutputStream.writeObject` and NOT to project `JSON.writeObject`; (b) `code_impact` on the rebuilt graph returns only 2 callers (parity with code_callhierarchy); (c) `wave_graph_report.fan_in` count for project `JSON.writeObject` excludes phantom edges; (d) bare and `this`-call within the same project class still attributes to the project node; (e) `GRAPH_BUILDER_VERSION` bump triggers re-extraction on upgrade.

## Scope

**In scope:**

- New shared module for Java receiver-type resolution helpers, or extension of `graph_indexer.py` to host them.
- `graph_indexer.py` — Java edge-construction path consumes the resolver.
- `server_impl.py` — refactor existing receiver-type code to import from shared module; preserve `code_callhierarchy_response` filter as no-op for clean graphs / defense-in-depth for cached.
- `GRAPH_BUILDER_VERSION` bump (13 → 14, or whatever the current value is).
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — fixtures verifying clean attribution.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — fixtures verifying `code_impact` and `wave_graph_report` parity with `code_callhierarchy`.

**Out of scope:**

- C# and Kotlin receiver-type attribution. Same helper shape applies; defer to operator-validated extensions.
- Inheritance-chain resolution (queried `JSON.writeObject`; caller via subtype). Preserve the wave 130rj scope boundary.
- Full symbol-table-with-imports resolution. The 85% Java-idiom solution from wave 130rj stays.
- Removing the `code_callhierarchy_response` query-time filter. Kept for cached-graph defense; becomes a no-op for rebuilt graphs.

## Acceptance Criteria

- [ ] AC-1: Receiver-type helpers exist in a shared module imported by both `graph_indexer.py` and `server_impl.py`.
- [ ] AC-2: `graph_indexer.py` Java edge construction resolves receiver type before edge emission; attributes to project nodes on match, to `external::*` on definitive non-project type, falls through to simple-name on uncertain.
- [ ] AC-3: `GRAPH_BUILDER_VERSION` is bumped; cached pre-bump graphs are re-extracted on next `wave_index_build`.
- [ ] AC-4: On the Aceiss fixture (`oos.writeObject` in JdbcRegistry + bare `writeObject` calls in JSON class), `code_impact("writeObject")` returns 2 callers in 1 community — parity with `code_callhierarchy("writeObject")`.
- [ ] AC-5: `wave_graph_report.fan_in` for project `JSON.writeObject` no longer counts the phantom JdbcRegistry edges.
- [ ] AC-6: Bare and `this`-call within the same project class still attribute correctly (regression guard).
- [ ] AC-7: Existing `code_callhierarchy_response` filter is preserved (defense-in-depth; no-op on clean graphs).
- [ ] AC-8: 5+ regression tests covering the Aceiss reproducer + `code_impact` parity + fan_in counts + bare/`this` preservation + version-bump re-extraction trigger.
- [ ] AC-9: All existing tests continue to pass (2007+ pre-bump baseline).

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Extract receiver-type helpers to a shared module (new file or existing graph_indexer.py)
- [ ] Refactor `server_impl.py` to import from shared module
- [ ] Wire receiver-type resolution into `graph_indexer.py` Java edge construction
- [ ] Bump `GRAPH_BUILDER_VERSION`
- [ ] Verify existing receiver-type unit tests still pass (location may need adjustment after refactor)
- [ ] Add 5+ regression tests for the indexer-level attribution
- [ ] Add `code_impact` parity test on the Aceiss reproducer
- [ ] Add `wave_graph_report.fan_in` count test
- [ ] Run framework tests
- [ ] Close gate
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Refactor foundation — eliminates duplication risk going forward |
| AC-2 | required | The headline graph-builder fix |
| AC-3 | required | Cache invalidation triggers the cleanup on upgrade |
| AC-4 | required | Aceiss reproducer — `code_impact` parity with `code_callhierarchy` |
| AC-5 | required | `wave_graph_report.fan_in` cleanup — Aceiss's secondary ask |
| AC-6 | required | No regression on legitimate same-class callers |
| AC-7 | required | Defense-in-depth for cached graphs |
| AC-8 | required | Regression coverage |
| AC-9 | required | No collateral breakage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Move resolution to graph builder, not per-tool filter | Whack-a-mole tax on every new graph-consuming tool; phantom edges are wrong at the source. One fix solves N consumers | Per-tool filter for `code_impact` only (rejected — same trap for wave_graph_report, code_callgraph, etc.); per-section filter for wave_graph_report only (rejected — same trap repeated) |
| 2026-06-01 | Preserve `code_callhierarchy_response` query-time filter as no-op | Cached pre-bump graphs benefit; defense-in-depth is cheap; removal is a follow-on cleanup once all known consumers have rebuilt | Remove (deferred — clean-up follow-on after operator confirmation) |
| 2026-06-01 | Attribute `oos.writeObject` to `external::ObjectOutputStream.writeObject` when receiver type resolves to a non-project type | The edge is to the external symbol, not to the project's simple-name match. This is the semantically correct attribution and `exclude_external=true` will continue to filter it from "show me MY code" views | Drop the edge entirely (rejected — operators occasionally want to see stdlib touch points); leave as `external::writeObject` bare (rejected — under-attributed; the class context is the signal) |
| 2026-06-01 | Java-only scope in this change | Aceiss reported Java specifically. C# / Kotlin extend the helper but warrant their own operator validation cycle. Avoids over-scoping a builder bump | Pre-emptive C#/Kotlin extension (rejected — no operator validation; bump risk if the C# / Kotlin AST pattern surfaces edge cases) |
| 2026-06-01 | Builder version bump (cache invalidation) | Existing graphs carry phantom edges; without invalidation, operators upgrade and still see wrong data | No bump (rejected — silent staleness; the change has no observable benefit on cached graphs) |

## Risks

| Risk | Mitigation |
|---|---|
| Builder-level resolution wrong → legitimate edges lost (false negatives at graph build) | False-positive bias preserved: uncertain → fall through to simple-name attribution. AC-6 ensures bare/`this` calls still attribute correctly. Test fixtures cover the trigger matrix |
| Index-build slowdown from per-edge AST walk | Receiver-type resolution is single-pass per method_invocation; ~10s of microseconds per call. Bounded by edge count. Measure during implementation; profile if needed |
| Cached graphs without re-build silently keep phantoms | `GRAPH_BUILDER_VERSION` bump forces re-extraction; documented in release notes |
| Aceiss expectations on `wave_graph_report` may include edge cases not in the test matrix (e.g. methods called via reflection, dynamic proxies) | Out of scope per design; document the AC-5 boundary as "static call graph correctness; reflective/dynamic invocation remains unattributed" |
| Future C# / Kotlin extension may surface AST differences that complicate the shared resolver | Helper signatures stay Java-specific in initial scope; language-specific resolvers can co-exist when added |

## Related Work

- Direct response to Aceiss field feedback on `1.2.0+312f` — `code_impact` / `code_callhierarchy` divergence + wave_graph_report fan_in inflation.
- Promotes wave 130rj's `130tw-enh java-receiver-type-resolution` from a per-tool filter to the source-of-truth fix at the graph layer.
- Companion to `01-decompose-name-collision-count` — that change is the *diagnostic* layer (operators see the collision risk); this change is the *fix* layer (graph attributes correctly).
- Eliminates the contradiction Aceiss called out: `code_impact` vs `code_callhierarchy` returning different communities for the same symbol.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
