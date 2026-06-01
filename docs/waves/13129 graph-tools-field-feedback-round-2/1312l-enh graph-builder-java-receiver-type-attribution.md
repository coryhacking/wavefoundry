# Graph-Builder Java Receiver-Type Attribution — Eliminate Phantom Edges at Index Time

Change ID: `1312l-enh graph-builder-java-receiver-type-attribution`
Change Status: `implemented`
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

The receiver-type resolution helpers (`_resolve_java_receiver_type` at server_impl.py:8225, `_resolve_java_identifier_type` at server_impl.py:8204, `_search_java_declarations_in_scope` at server_impl.py:8233, `_extract_simple_java_type_name` at server_impl.py:8161, `_find_enclosing_java_class_name` at server_impl.py:8194, plus `_extract_java_owner_class_from_node_id` at server_impl.py:8138 and `_annotate_java_call_sites_with_receiver_type` at server_impl.py:9981) are general-purpose and already proven by wave 130rj's 9 unit tests (`TestJavaReceiverTypeResolution` + `TestExtractJavaOwnerClassFromNodeId` in test_server_tools.py). The refactor:

1. **Move the helpers into `graph_indexer.py`** (not a new top-level module). server_impl.py already loads graph_indexer.py lazily via `_load_script("graph_indexer")`; reusing the existing dependency direction avoids a new top-level file. The helpers gain module-level visibility via `_load_script` import path. (Council action item: architecture-reviewer.)
2. **In `graph_indexer.py` Java edge construction**: when emitting a `calls` edge for a `method_invocation` node, dispatch by receiver-type resolution **deterministically per call site** (no double-emission):
   - Resolved type matches a project class's simple name → emit edge to that class's method node (project-qualified attribution).
   - Resolved type is a non-project type (e.g. `ObjectOutputStream`) → emit edge to `external::<ResolvedType>.<method>` (external-qualified attribution).
   - Resolution returns None (uncertain — e.g. `var` local, complex expression) → fall through to existing simple-name attribution. For unresolved cross-file calls this remains `external::<method>` (the simple-name external node). False-positive bias preserved. (Council action item: red-team — single dispatch decision per call site; the qualified and simple-name external nodes coexist in the graph only for distinct call sites with different receiver-resolution outcomes.)
3. **The resolver must short-circuit on first uncertain branch** — return None as soon as receiver expression can't be classified into one of the three handled cases (this/super, simple identifier, ClassName.staticMethod). No exhaustive scope walks past the first identifiable ambiguity. (Council action item: performance-reviewer.)
4. **The query-time filter in `code_callhierarchy_response` stays as defense-in-depth** for codebases on cached pre-version-bump graphs. Becomes a no-op for cleanly-rebuilt graphs.
5. **`GRAPH_BUILDER_VERSION` bump** so on upgrade the graph is rebuilt with correct attribution.

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

- [x] AC-1: Receiver-type helpers exist in `graph_indexer.py` (extending the existing module, not a new top-level file) and are importable from `server_impl.py` via the existing `_load_script("graph_indexer")` path. After the refactor, the existing wave-130rj unit tests (`TestJavaReceiverTypeResolution` and `TestExtractJavaOwnerClassFromNodeId`, 9 tests total) continue to pass without modification beyond import-path adjustment. The five receiver-type cases proven by wave-130rj are explicitly preserved: (a) bare call `process()` → enclosing class; (b) `this.process()` → enclosing class; (c) `Type x = new Type(); x.process()` → declared local type; (d) `void foo(Type x) { x.process() }` → parameter declared type; (e) `Foo.staticProcess()` → class name (static-style). (Council action items: architecture-reviewer + qa-reviewer.)
- [x] AC-2: `graph_indexer.py` Java edge construction dispatches deterministically per call site: resolved-to-project-type → project node; resolved-to-non-project-type → `external::<Type>.<method>`; uncertain → fall through to simple-name attribution (preserves existing `external::<method>` for unresolved cross-file calls). No double-emission for the same call site. (Council action item: red-team.)
- [x] AC-3: `GRAPH_BUILDER_VERSION` is bumped; cached pre-bump graphs are re-extracted on next `wave_index_build`.
- [x] AC-4: On the Aceiss fixture (`oos.writeObject` in JdbcRegistry + bare `writeObject` calls in JSON class), `code_impact("writeObject")` returns 2 callers in 1 community — parity with `code_callhierarchy("writeObject")`.
- [x] AC-5: `wave_graph_report.fan_in` for project `JSON.writeObject` no longer counts the phantom JdbcRegistry edges. The `oos.writeObject` edge instead appears under `external::ObjectOutputStream.writeObject`, filterable via `exclude_external=true`.
- [x] AC-6: Bare and `this`-call within the same project class still attribute correctly (regression guard).
- [x] AC-7: Existing `code_callhierarchy_response` filter is preserved (defense-in-depth; no-op on clean graphs).
- [x] AC-8: 5+ regression tests covering the Aceiss reproducer + `code_impact` parity + fan_in counts + bare/`this` preservation + version-bump re-extraction trigger.
- [x] AC-9: All existing tests continue to pass (2007+ pre-bump baseline).

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extract receiver-type helpers to a shared module (new file or existing graph_indexer.py)
- [x] Refactor `server_impl.py` to import from shared module
- [x] Wire receiver-type resolution into `graph_indexer.py` Java edge construction
- [x] Bump `GRAPH_BUILDER_VERSION`
- [x] Verify existing receiver-type unit tests still pass (location may need adjustment after refactor)
- [x] Add 5+ regression tests for the indexer-level attribution
- [x] Add `code_impact` parity test on the Aceiss reproducer
- [x] Add `wave_graph_report.fan_in` count test
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

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
| 2026-06-01 | Pin shared helpers to `graph_indexer.py` rather than a new top-level module | server_impl.py already loads graph_indexer.py lazily via `_load_script("graph_indexer")`. Reusing the existing dependency avoids a new top-level file and a new import direction. Per council architecture-reviewer | New `java_receiver_resolution.py` module (rejected — adds a new file and import direction without semantic benefit) |
| 2026-06-01 | Resolver must short-circuit on first uncertain branch | Avoids worst-case scope walks that could cost milliseconds per call site on pathological inputs. Preserves the wave-130rj implementation's actual behavior (fail fast on unrecognized receiver shape). Per council performance-reviewer | Exhaustive multi-pass resolution (rejected — performance footgun with no upside on uncertain cases) |
| 2026-06-01 | Deterministic per-call-site dispatch — no double-emission of edges | Avoids the failure mode where a call site emits both an `external::ObjectOutputStream.writeObject` AND an `external::writeObject` edge during dispatch. Each call site produces exactly one attribution decision: project | external-qualified | external-simple-name. Per council red-team | Dual emission with deduplication downstream (rejected — adds graph-build complexity for a hypothetical use case) |
| 2026-06-01 | Java-only scope in this change | Aceiss reported Java specifically. C# / Kotlin extend the helper but warrant their own operator validation cycle. Avoids over-scoping a builder bump | Pre-emptive C#/Kotlin extension (rejected — no operator validation; bump risk if the C# / Kotlin AST pattern surfaces edge cases) |
| 2026-06-01 | Builder version bump (cache invalidation) | Existing graphs carry phantom edges; without invalidation, operators upgrade and still see wrong data | No bump (rejected — silent staleness; the change has no observable benefit on cached graphs) |
| 2026-06-01 (delivery review) | Initial implementation deviated from AC-1 — duplicated helpers into graph_indexer.py rather than importing from server_impl via `_load_script`. Corrected in delivery review to thin wrappers in server_impl.py that delegate to `graph_indexer.py` (the AC's intended shape) | The duplication shipped intact through implementation review because the duplicate text was treated as the source-of-truth comment. Delivery-review red-team caught the drift trap; council action item #2 was about source-of-truth, not just helper presence. Refactor verified by all 9 wave-130rj unit tests passing without modification via `srv._resolve_java_receiver_type(...)` attribute access through the thin wrappers | Leave duplicated (rejected — perpetuates the drift trap the council action item warned about) |
| 2026-06-01 (delivery review) | `_load_script` extended to register loaded modules in `sys.modules` under the namespaced cache key | Required for graph_indexer's `@dataclass(frozen=True)` to resolve types at module-construction time when loaded dynamically. The original "does not pollute public sys.modules" intent is preserved (namespaced key keeps public `graph_indexer` namespace free); only the cached private key gets registered. Wider than just unblocking 1312l but fixes a latent issue any future dataclass-using sibling module would hit | Inline the helpers in server_impl.py (rejected — reverts to duplication trap); use a separate loader (rejected — adds parallel infrastructure for one consumer) |
| 2026-06-01 (delivery review) | `code_callhierarchy_response` short-circuits the receiver-type filter on graphs with `builder_version >= 13` | The filter is provably redundant on v13+ graphs (the indexer eliminated phantoms at construction). Skipping the per-call AST walks is a real per-query latency win for steady-state operators. The defense-in-depth path stays active for cached pre-bump graphs (`builder_version < 13` or absent) until operators rebuild. Documents `index.builder_version` as the authoritative signal of whether the graph is self-cleaning | Always run the filter (rejected — wastes AST-walk work on freshly-built graphs); never run the filter (rejected — pre-bump graphs would surface phantoms until rebuild) |

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
