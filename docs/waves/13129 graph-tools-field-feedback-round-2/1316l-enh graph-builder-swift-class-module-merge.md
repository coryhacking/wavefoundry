# Graph-Builder Swift Class/Module Merge — Unify File+Top-Level-Class at Index Time

Change ID: `1316l-enh graph-builder-swift-class-module-merge`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris round-trip report on `1.2.1+315o` (2026-06-01): `code_callhierarchy(symbol="StatusBarManager", direction="incoming")` returns empty incoming despite known constructor calls in `AppDelegate.swift`:

```swift
// AppDelegate.swift:19
let manager = StatusBarManager(dataModel: dataModel)
```

The graph carries two distinct nodes for what is conceptually one entity:
- Module node `SolarisMonitor/Sources/StatusBarManager.swift` (kind: `module`)
- Class node `SolarisMonitor/Sources/StatusBarManager.swift::StatusBarManager` (kind: `class`)

The symbol resolver picks one when queried, leaving the other's incoming edges invisible. The constructor call's edge target is the class node; `code_callhierarchy` resolves to the module node; result: empty incoming.

Wave 13129's `1312h-enh collapse-class-module-pairs` shipped a **query-time view** on `wave_graph_report` that merges the pair for report rankings. But per-symbol tools (`code_callhierarchy`, `code_callgraph`, `code_impact`, `code_graph_path`) deliberately don't consume the view because they need the full per-symbol graph. So the structural issue persists for the most-used navigation path.

The 1312l council pattern was: don't whack-a-mole per-tool; fix at the source of truth. This change applies the same pattern — merge Swift class/module pairs at index time so every consumer sees the unified node automatically.

## Approach

For each Swift file `path/Foo.swift` that contains exactly one top-level type declaration named `Foo` (matching basename) with kind in `{class, struct, actor, enum, protocol}`, the indexer merges the file node and the type node into a single node:

- **Id wins**: the FILE id (`path/Foo.swift`) — preserves backward compat for any consumer querying by file path.
- **Label wins**: the type name (`Foo`) — the operator-visible identity.
- **Kind wins**: the type kind (`class`/`struct`/etc.) — semantically more useful than `module` for navigation.
- **Edges**: incoming + outgoing of both original nodes converge on the merged node. The class node's id becomes a forward-only alias to the file id during edge rewriting.
- **`collapsed_pair: true`** discriminator on the merged node so consumers can distinguish merged-by-builder from native single nodes.

Detection is purely name-based: file basename (sans `.swift`) == top-level type name. No AST analysis required beyond what the existing extractor already does.

Backward compat: when a file lacks a basename-matching top-level type, both nodes (if any) survive unmodified. This handles:
- Utility files with no top-level type (`Util.swift` with only functions).
- Multi-type files (no merge candidate).
- `extension`-only files (no class declaration).

The `1312h-enh collapse-class-module-pairs` query-time view becomes redundant on v14+ graphs (the merge has already happened) — leave the view as a no-op for v14+ to avoid breaking callers that explicitly pass `collapse_class_module_pairs=true`. The view stays useful for cached pre-v14 graphs.

## Requirements

1. **`graph_indexer.py` Swift extractor** identifies the basename-match case during per-file symbol registration. When detected, the indexer:
   - Registers ONE merged node at the file id with the type's label and kind, plus `collapsed_pair: true`.
   - Routes all `defines` / `calls` / `imports` edges that would target the class node to the file id instead.
2. **`GRAPH_BUILDER_VERSION` bump** 13 → 14. Cached v13 graphs re-extract on next `wave_index_build`.
3. **Query-time `collapse_class_module_view` becomes a no-op on v14+ graphs** — the merge is already in the graph. The view stays functional for v13- graphs.
4. **`code_callhierarchy(symbol="StatusBarManager")`** on the v14 graph returns the constructor call's caller in `incoming`. Verified with the Solaris reproducer.
5. **Tests** cover:
   - Swift file `Foo.swift` containing `class Foo` → single merged node at `Foo.swift` with `kind: "class"`, label `"Foo"`, `collapsed_pair: true`.
   - Swift file `Foo.swift` containing `struct Foo` → same merge (all 5 type kinds covered).
   - Swift file `Foo.swift` containing `class FooHelper` (basename mismatch) → no merge; both nodes survive.
   - Swift file `Util.swift` containing only functions → no merge.
   - Constructor call from another file (`let foo = Foo()`) attributes to the merged node; `code_callhierarchy("Foo", direction="incoming")` returns the caller.
   - Java / C# / Kotlin files with same basename-class pattern → NO merge (Swift-only per scope).
6. **Backward compat: pre-v14 graphs work unchanged** — the query-time `collapse_class_module_view` continues to function on cached v13 graphs.
7. **No regression on the wave 13129 baseline** — all existing 2032+ tests pass.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Swift class/module merge during per-file extraction.
- `.wavefoundry/framework/scripts/graph_query.py` — `collapse_class_module_view` becomes a no-op when input graph is already v14+.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — 7+ regression tests.
- `GRAPH_BUILDER_VERSION` bump 13 → 14.

**Out of scope:**

- Java / Kotlin / C# class/module merges. Same pattern applies but each language has its own edge cases (Java inner classes, Kotlin companion objects, C# multi-class files). Operator-validation-driven; defer to future waves with explicit operator reports.
- `extension`-only files. Swift extensions are intentionally separate nodes — they're not the "primary type" of the file. Multi-extension files with no class declaration stay as multi-node graphs.
- Tearing down `1312h-enh collapse-class-module-pairs`. The query-time view remains valid for cached pre-v14 graphs and operator-visible behavior continues. Becomes a no-op for v14+ where the merge is already baked in.

## Acceptance Criteria

- [x] AC-1: Swift extractor identifies basename-match class/module pairs during per-file registration. The five type kinds covered: `class`, `struct`, `actor`, `enum`, `protocol`.
- [x] AC-2: When a pair is detected, one merged node is registered at the file id with the class label, class kind, and `collapsed_pair: true`. The class node id (`<file>::<basename>`) is NOT registered; edges that would target it route to the file id instead.
- [x] AC-3: Files without a basename-matching top-level type are unaffected (both nodes — if any — survive unmodified).
- [x] AC-4: `GRAPH_BUILDER_VERSION` bumps 13 → 14; cached pre-v14 graphs re-extract on next `wave_index_build`.
- [x] AC-5: `code_callhierarchy(symbol="Foo", direction="incoming")` on a v14 graph with the Solaris reproducer (`Foo.swift` defining `class Foo`, `Bar.swift` constructing `let foo = Foo()`) returns at least one incoming entry referencing the constructor call.
- [x] AC-6: `collapse_class_module_view` (1312h) is a no-op on v14+ inputs (detected via `builder_version` on the payload) and continues to function on pre-v14 inputs.
- [x] AC-7: Java / C# / Kotlin files with basename-class patterns are NOT merged (Swift-only scope). **Explicit per-language test fixtures required:** at minimum `Foo.java` containing `class Foo`, plus one of `Foo.cs` containing `class Foo` or `Foo.kt` containing `class Foo`. Assert both the file node and the class node survive on each language fixture. (Council action item: qa-reviewer.)
- [x] AC-8: 7+ regression tests cover the matrix (5 type kinds × merge-or-not + Solaris reproducer + per-language non-merge guards from AC-7).
- [x] AC-9: All 2032+ existing tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Swift class/module-pair detection to the per-file extractor
- [x] Route class-node edges to the file id during edge construction
- [x] Bump `GRAPH_BUILDER_VERSION` to 14
- [x] Update `collapse_class_module_view` to no-op on v14+ inputs
- [x] Add 7+ regression tests including the Solaris reproducer
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Detection foundation |
| AC-2 | required | The headline graph-shape change |
| AC-3 | required | Backward compat for non-pair files |
| AC-4 | required | Cache invalidation triggers the cleanup on upgrade |
| AC-5 | required | The Solaris-reported symptom — empty incoming becomes populated |
| AC-6 | required | Pre-v14 graphs still work via the query-time view |
| AC-7 | required | Scope discipline (Swift-only) |
| AC-8 | required | Regression coverage |
| AC-9 | required | No collateral breakage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Merge at index time, not just at query time (mirrors 1312l pattern) | The 1312l council action item established the principle: don't whack-a-mole per-tool; fix at the source of truth. Per-symbol tools (`code_callhierarchy`, `code_impact`) need the merge for their primary use case. Query-time view (1312h) is necessarily blind to per-symbol consumers | Symbol-resolver-only fix (rejected — same whack-a-mole the council pattern warns against; per-symbol tools each need their own fix); keep query-time-only (rejected — per-symbol tools stay broken) |
| 2026-06-01 | File id wins the merge (not the class id) | Operators querying by file path (`code_callhierarchy(symbol="path/Foo.swift")`) should still resolve. The label and kind that win are the operator-visible identity, not the id | Class id wins (rejected — breaks file-path resolution) |
| 2026-06-01 | Swift-only scope | Solaris reported Swift specifically. Java inner classes, Kotlin companion objects, C# multi-class files have edge cases each warrants its own operator-validation cycle. Bumping v13→v14 for one language is acceptable; bumping for all four languages at once is operator-painful + over-scoped | Pre-emptive multi-language extension (rejected — Java/Kotlin/C# need their own validation) |
| 2026-06-01 | Second `GRAPH_BUILDER_VERSION` bump in the same release cycle (1312l: 12→13, this change: 13→14) | The structural fix is the right end-state. Bundling with the Finding 1 fix (`1316j-enh fix-module-simple-name-extraction`) so Solaris/Aceiss rebuild once for both fixes — better than splitting across releases. The cost is operator-visible (one more rebuild) but the alternative (defer to future wave) leaves the Solaris symptom unfixed | Defer the structural fix to a future wave; ship only the symptom-mitigation via symbol resolver in 1.2.2 (rejected — whack-a-mole; the structural fix is the right pattern) |
| 2026-06-01 | Keep `collapse_class_module_view` as a query-time view for pre-v14 graphs | Cached pre-v14 graphs benefit from the view until the operator rebuilds. The view's no-op-on-v14+ behavior is detected via the input payload's `builder_version` field | Remove the view entirely on v14+ (rejected — would break callers that pass the param explicitly on cached graphs) |
| 2026-06-01 | Land in wave 13129 (not a new wave) | Same operator (Solaris) reporting on the same release cycle. The structural fix is the natural completion of `1312h`'s deferral. Closing the loop in the same wave keeps audit trails coherent | New wave (rejected — operator round-trip is mid-cycle, not a separate iteration) |

## Risks

| Risk | Mitigation |
|---|---|
| Indexer-side merge wrong → legitimate non-pair files get incorrectly merged (false positives) | Detection is purely name-based with explicit basename + top-level-type-kind constraints. AC-3 and AC-7 are regression guards. Test fixtures cover the multi-class, extension-only, and cross-language cases |
| Second builder version bump in one release cycle causes operator fatigue | Document explicitly in release notes; bundle with 1316j so it's one rebuild not two. Future waves should batch bumps when possible |
| Files where the class name differs from the file basename (e.g. `Foo.swift` containing `class FooHelper`) won't merge — operators querying `FooHelper` see both nodes | Out of scope per AC-3. This is the existing graph behavior pre-fix; not a regression. Operator-validation-driven if the case is reported |
| Edge cases in Swift grammar (e.g. `@MainActor class Foo`, `final class Foo`, generic `class Foo<T>`) might not match the detection | Tests cover the major Swift declaration shapes; tree-sitter Swift grammar already classifies these as `class_declaration` (with modifiers). Verify during implementation |

## Related Work

- Direct response to Solaris field feedback on `1.2.1+315o` (Finding 2 — structural).
- Companion to `1316j-enh fix-module-simple-name-extraction` (Finding 1 — diagnostic fix). Both land together in 1.3.0 so Solaris/Aceiss rebuild once.
- Promotes wave 13129's `1312h-enh collapse-class-module-pairs` from a query-time view to the source of truth at the graph layer — mirrors 1312l's pattern (`130tw-enh java-receiver-type-resolution` → `1312l-enh graph-builder-java-receiver-type-attribution`).
- Eliminates the empty-incoming symptom Solaris reported on `code_callhierarchy` for Swift class symbols.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
