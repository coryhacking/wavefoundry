# Construction Call Edges Not Attributed to Class Node

Change ID: `1319s-bug construction-call-edges-to-class-node`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

Across every supported language with a class-like construct, `code_callhierarchy(symbol="<ClassName>", direction="incoming")` returns an empty `incoming` list even when the class is demonstrably constructed elsewhere in the codebase. The graph genuinely does not represent the construction relationship — `code_graph_path` between caller and class confirms no `calls` edge exists between them.

Two construction syntaxes are affected:

| Syntax | Languages | AST shape |
|---|---|---|
| Bare-call construction (no `new` keyword) | Swift, Python, Kotlin, Scala, Ruby (`Foo.new` is also bare-call form) | `call_expression` with bare-identifier callee |
| Explicit `new` keyword | Java, C#, TypeScript, JavaScript, PHP, Rust (`Foo::new()`), Go (no constructors — N/A) | `object_creation_expression` / `new_expression` / scoped `::new` call |

The root cause: receiver-type resolution introduced in `1312l` and extended to Kotlin/C# (`13194`), Go/Rust/Scala (`1319a`), and Swift (`1319g`) handles **instance-method dispatches** (`obj.method()`) but does not handle **type-name invocations** (`Foo(args)` / `new Foo()`). For Swift specifically, the `1319g` PascalCase discriminator correctly stopped treating `Foo()` as a self-method call but never wired the deferred path to anywhere — so no edge is produced.

For explicit-`new` languages, current behavior is unverified at start; the same audit applies (could be already routing correctly, could have the identical gap). The fix must treat all languages uniformly.

Operator impact: every "what calls / instantiates this class?" investigation — the most common refactor-impact question on a class-init signature change — currently requires a `code_references` fallback per the seed-211 fallback rule. For a codebase with N classes, every such investigation costs an extra round-trip and per-call-site rather than per-caller-function semantics.

## Field Reproducer (Solaris, Swift)

```swift
// SolarisMonitor/Sources/AppDelegate.swift:19
let manager = StatusBarManager(dataModel: dataModel)
```

`code_callhierarchy(symbol="StatusBarManager", direction="incoming")` on 1.2.1+319y returns `incoming: []`. `code_graph_path(from_symbol="AppDelegate", to_symbol="StatusBarManager")` confirms no `calls` edge — files are connected only by both importing a shared trivial external token.

The same gap reproduces in synthetic fixtures across Python, Kotlin, and Scala (see Acceptance Criteria).

## Approach

**Reporter-recommended Option B (route construction edges to the class node):**

The class node already serves as a hub via `defines` edges to its methods. Routing construction edges to the same node makes `code_callhierarchy(<ClassName>).incoming` the canonical answer to "where is this class instantiated?" — operator-facing semantics. Option A (route to a synthesized `T.init` node) is semantically purer but forces operators to query init separately, defeating the natural-question affordance.

### Implementation outline (language-agnostic core)

1. **New helper** `_resolve_construction_target(callee_node, source_bytes, symbol_lookup, lang_key)` in `graph_indexer.py`:
   - Detects construction call shapes per language.
   - Returns the class-node target node ID when the callee resolves to a known class/struct/enum/actor/object symbol.
   - Returns `None` for non-construction shapes (defers to existing resolution chain).

2. **Invariant: bare-call shape only.** The helper fires ONLY on bare-identifier call shapes (no-`new` languages) or explicit `new_expression`/`object_creation_expression` shapes (explicit-`new` languages). It **never** fires on `navigation_expression`/`field_expression`/`member_expression` callees — those remain receiver-type-resolution territory. Prevents accidental hijack of `obj.Foo()` method calls where `Foo` happens to be PascalCase.

3. **Discriminator chain in `walk_calls`** per language:
   1. Try `_resolve_construction_target` first.
   2. If `None`, fall through to existing receiver-type resolution.
   3. If still `None`, fall through to standard attribution.

4. **New `CONSTRUCTION_RESOLVED` confidence tag** alongside `RECEIVER_RESOLVED` / `EXTRACTED`. Surfaces in `code_impact.edges[].confidence` — preserves the diagnostic clarity the reporter explicitly valued in the field report.

5. **Class/module merge interaction:** when merge is active (default for languages in the merge family, opt-in via `collapse_class_module_pairs`), the class node IS the unified file+class node — edges route there naturally. When merge is inactive or N/A, edges route to the bare class node.

### Per-language detection rules

| Language | Bare-call form | Explicit-`new` form | Detection rule |
|---|---|---|---|
| **Swift** | `Foo(args)`, `Foo.init(args)`, `Foo?(args)` (failable) | — | `call_expression` with `simple_identifier` callee starting with uppercase, AND class/struct/enum/actor `Foo` in scope. Plus `navigation_expression` with `.init` selector on type name. |
| **Python** | `Foo(args)` | — | `call` with `identifier` callee starting with uppercase, AND `class_definition` `Foo` in scope. |
| **Kotlin** | `Foo(args)` | — | `call_expression` with `simple_identifier` callee starting with uppercase, AND class of that name in scope. Object-invocation overload (`object Foo; Foo()`) explicitly out of scope. |
| **Scala** | `Foo(args)` (case classes; companion `apply` returning Foo) | `new Foo(args)` | Case classes: route bare-call to class node. Non-case classes with companion `apply`: route ONLY when `apply` returns `Foo` (auto-synthesized) or is a single primary-constructor wrapper. `apply` returning a different type → not construction. |
| **Ruby** | `Foo.new(args)` | — | `call` with `method` `new` on receiver `Foo` where `Foo` is a class/module in scope. Bare `Foo()` is not Ruby construction syntax. |
| **Java** | — | `new Foo(args)` | `object_creation_expression` with `type_identifier` `Foo`. |
| **C#** | — | `new Foo(args)` | `object_creation_expression` with `identifier` `Foo`. |
| **TypeScript** | — | `new Foo(args)` | `new_expression` with `identifier` `Foo`. |
| **JavaScript** | — | `new Foo(args)` | `new_expression` with `identifier` `Foo`. |
| **PHP** | — | `new Foo(args)` | `object_creation_expression` with `name` `Foo`. |
| **Rust** | — | `Foo::new(args)` (convention; not enforced) | `call_expression` with `scoped_identifier` ending in `new`, AND `struct_item`/`enum_item` `Foo` in scope. Marked **lower confidence** — Rust convention, not language semantics. |
| **Go** | — | — | N/A — Go has no class constructors. Skip. |

### Phase 0 audit (precondition to gate-open)

Before opening `framework_edit_allowed`, baseline the current behavior of `walk_calls` on `new_expression`/`object_creation_expression` for Java/C#/TS/JS/PHP and on `scoped_identifier` `::new` for Rust. Two possible findings:

- **Already routes to class node** → AC-7 closes as a confirmation; doc updated, no code change for that language.
- **Does not route** → extend the helper; AC-7 becomes a required code change.

Document the audit results in the Decision Log before implementation starts.

### `server_impl.py` integration check (precondition to gate-open)

Audit `code_callhierarchy` server-side behavior for class-node queries. Two possible findings to resolve before edge emission:

- **Walker currently transitively expands class → methods via `defines` → method callers** — construction edges directly to the class node may double-count callers (once for construction, once per method they happen to call). Decide: separate result section (`construction_callers`) vs deduplication pass vs merged `incoming` with a `kind: "construction"` discriminator.
- **Walker reads class-node inbound edges directly** — no integration change needed.

Document resolution in Decision Log.

## Requirements

1. New `_resolve_construction_target` helper in `graph_indexer.py` covering Swift, Python, Kotlin, Scala, Ruby, Java, C#, TypeScript, JavaScript, PHP, Rust per the per-language detection table.
2. New `CONSTRUCTION_RESOLVED` confidence tag applied to construction-call edges; surfaced in `code_impact.edges[].confidence`.
3. `walk_calls` dispatch updated per language: construction-resolution attempt precedes existing receiver-type resolution.
4. `code_callhierarchy(symbol=<ClassName>, direction="incoming")` returns construction call sites as `incoming` entries with calling function's `name`, `file`, `line`, `snippet`.
5. `code_graph_path` between caller and class reflects the construction edge.
6. `external_incoming_count` on a class node accounts for construction calls originating in external code (or explicitly defers with rationale in Decision Log).
7. Per-language regression tests (reproducer fixture) for every in-scope language.
8. No regression on existing receiver-type-resolution tests — the discriminator chain must preserve their behavior.
9. `GRAPH_BUILDER_VERSION` 14 → 15 — operators with pre-bump caches see a rebuild prompt via `wave_index_health`.

## Scope

**Problem statement:** Constructor calls — across every language with class semantics — are not routed as incoming edges to the class node. `code_callhierarchy(<ClassName>).incoming` returns empty for classes that are demonstrably constructed elsewhere. Operators must fall back to `code_references` for the most common refactor-impact question.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — construction-target helper for all 11 languages with class semantics, discriminator chain, confidence tag.
- `.wavefoundry/framework/scripts/server_impl.py` — `code_callhierarchy` integration (depends on the integration check outcome).
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language construction-edge tests, negative-case tests.
- `.wavefoundry/framework/seeds/` — `code_callhierarchy`, `code_impact`, `code_graph_path` seed docs: describe construction edges + `CONSTRUCTION_RESOLVED` confidence label.
- `GRAPH_BUILDER_VERSION` bump.

**Out of scope:**

- Routing to a synthesized `T.init` node (Option A). Hedge: if init-level granularity becomes a demand signal, a follow-up change could synthesize `T.init` nodes as `defines` children of T, with construction edges retargeted to the specific init based on argument-label match — additive, not breaking.
- Generic / parameterized construction (`Container<Foo>()` TS/Scala, `Foo<T>()` C#/Java) — use outer type name only.
- Construction via reflection / dynamic dispatch (Java `Class.forName(...).newInstance()`, Swift `objc_getClass`, Python `__import__`, PHP `ReflectionClass::newInstance`) — would never resolve statically.
- Builder patterns (`Foo.builder().build()`) — these are method dispatches, already covered by receiver-type resolution.
- Factory functions whose return type implies construction — too inference-driven; defer.
- Kotlin object-invocation overload (`object Foo; Foo()` resolves to `invoke()` operator) — different semantics from class construction; defer.
- Scala companion `apply` factories returning a different type than the companion — not semantically construction.
- Type-name-as-value reference (`let factory = Foo` Swift; `cls = Foo` Python) — not a call expression; no edge produced. Covered by the bare-call invariant.

## Acceptance Criteria

**Core (required for every in-scope language):**

- [ ] AC-1: Reproducer fixture per language produces a `calls` edge from caller function to class node after rebuild.
- [ ] AC-2: `code_callhierarchy(symbol=<ClassName>, direction="incoming")` returns construction call sites with `name`, `file`, `line`, `snippet`.
- [ ] AC-3: `CONSTRUCTION_RESOLVED` confidence tag appears in `code_impact.edges[].confidence` for construction edges.

**Per-language coverage:**

- [ ] AC-4: Swift — bare-call (`Foo(args)`), explicit-init (`Foo.init(args)`), failable (`Foo?(args)`) all produce construction edges.
- [ ] AC-5: Python — `Foo(args)` with `class Foo` in scope produces construction edge.
- [ ] AC-6: Kotlin — `Foo(args)` produces construction edge.
- [ ] AC-7: Scala — `Foo(args)` for case class + `new Foo(args)` for non-case class produce construction edges.
- [ ] AC-8: Ruby — `Foo.new(args)` produces construction edge to class `Foo`.
- [ ] AC-9: Java — `new Foo(args)` produces construction edge (close-out if already routing, extend otherwise — depends on Phase 0 audit).
- [ ] AC-10: C# — `new Foo(args)` produces construction edge (close-out or extend).
- [ ] AC-11: TypeScript — `new Foo(args)` produces construction edge (close-out or extend).
- [ ] AC-12: JavaScript — `new Foo(args)` produces construction edge (close-out or extend).
- [ ] AC-13: PHP — `new Foo(args)` produces construction edge (close-out or extend).
- [ ] AC-14: Rust — `Foo::new(args)` produces construction edge (lower-confidence — convention-based; mark behind a per-language flag if needed).

**Negative / safety cases (required):**

- [ ] AC-15: Method named identically to enclosing class (`class Foo { func Foo() {...} }`) — method call does NOT produce a construction edge. Validates symbol-lookup precondition.
- [ ] AC-16: Type-name-as-value reference (`let factory = Foo` Swift; `cls = Foo` Python) — no construction edge produced. Validates bare-call invariant.
- [ ] AC-17: `self.method()` / `this.method()` / `self.foo()` inside `Foo` — does NOT produce a self-construction edge.
- [ ] AC-18: Navigation-expression PascalCase method call (`obj.Foo()` where `Foo` is a method on `obj`'s type) — does NOT trigger construction-resolution; remains receiver-type-resolution territory.

**Plumbing / integration:**

- [ ] AC-19: External construction (external code constructs an in-project class) routes to `external_incoming_count` or has documented deferral with rationale.
- [ ] AC-20: No regression on existing receiver-type-resolution tests (`RECEIVER_RESOLVED` confidence still applied where it was before).
- [ ] AC-21: `code_graph_path` between caller and class node reflects the construction edge as an expected hop.
- [ ] AC-22: `GRAPH_BUILDER_VERSION` bumped 14 → 15.
- [ ] AC-23: Seed docs updated for `code_callhierarchy`, `code_impact`, `code_graph_path` describing construction edges and `CONSTRUCTION_RESOLVED` confidence tag.

## Tasks

- [ ] **Phase 0a** — audit `walk_calls` baseline behavior on `new_expression`/`object_creation_expression` for Java/C#/TS/JS/PHP and `::new` for Rust; record findings in Decision Log
- [ ] **Phase 0b** — audit `server_impl.py` `code_callhierarchy` behavior on class-node queries; resolve double-counting question in Decision Log
- [ ] Open `framework_edit_allowed` gate
- [ ] Implement `_resolve_construction_target` helper covering all in-scope languages
- [ ] Add `CONSTRUCTION_RESOLVED` confidence tag plumbing
- [ ] Wire `walk_calls` discriminator chain per language
- [ ] Implement `server_impl.py` integration per Phase 0b outcome
- [ ] Add per-language regression tests (positive + negative)
- [ ] Bump `GRAPH_BUILDER_VERSION` 14 → 15
- [ ] Open `seed_edit_allowed` gate; update `code_callhierarchy`, `code_impact`, `code_graph_path` seeds; close gate
- [ ] Run framework tests
- [ ] Close framework gate; mark change `implemented`
- [ ] Repackage; field-verify against Solaris reproducer + cross-language fixtures

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| phase-0-audit | Engineering | — | Sequential precondition; outputs feed every other workstream |
| helper-bare-call-langs | Engineering | phase-0-audit | Swift + Python + Kotlin + Scala + Ruby |
| helper-explicit-new-langs | Engineering | phase-0-audit | Java + C# + TS + JS + PHP + Rust (audit-or-extend) |
| confidence-tag-plumbing | Engineering | helper-bare-call-langs OR helper-explicit-new-langs | First-merge; second adds usage |
| server-impl-integration | Engineering | phase-0-audit | May be no-op depending on audit |
| seed-updates | Engineering | helper-* + confidence-tag-plumbing | Last — describes what shipped |

## Serialization Points

- `_resolve_construction_target` is a single helper — all per-language additions land in the same function. Coordinate to avoid merge conflicts.
- `walk_calls` per-language dispatch chains — coordinate when multiple languages land simultaneously.
- `GRAPH_BUILDER_VERSION` bump — single line; do once as part of confidence-tag-plumbing workstream.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — graph-builder pipeline gains a construction-resolution step before receiver-type resolution. Document the discriminator chain order.
- `docs/architecture/decisions/` — ADR for the Option-B (route-to-class-node) decision and the Option-A hedge (future init-level granularity is additive, not breaking).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core edge emission |
| AC-2 | required | Operator-facing surface |
| AC-3 | required | Confidence-tag observability |
| AC-4 | required | Swift — Solaris field-validation case |
| AC-5 | required | Python — broad operator base |
| AC-6 | required | Kotlin — Android / server-side parity |
| AC-7 | required | Scala — case-class idiom + new-keyword variant |
| AC-8 | required | Ruby — `Foo.new` is the universal Ruby form |
| AC-9 | required | Java — most-used explicit-`new` language |
| AC-10 | required | C# parity |
| AC-11 | required | TypeScript parity |
| AC-12 | required | JavaScript parity |
| AC-13 | required | PHP parity |
| AC-14 | important | Rust — convention not language semantics |
| AC-15 | required | False-positive guard (method-named-as-class) |
| AC-16 | required | Bare-call invariant validation |
| AC-17 | required | Self-reference preservation |
| AC-18 | required | Navigation-expression boundary |
| AC-19 | important | External-incoming semantics |
| AC-20 | required | No baseline regression |
| AC-21 | required | `code_graph_path` parity |
| AC-22 | required | Cache-invalidation correctness |
| AC-23 | required | Seed-first doc workflow |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Option B (route construction to class node) | Operator-facing — "what calls this class?" is the natural question; class node already serves as `defines` hub | Option A (synthesized `T.init` node) — semantically purer but worse operator UX. Hedge: future additive change could add init-level granularity without breaking |
| 2026-06-01 | New `CONSTRUCTION_RESOLVED` confidence tag | Distinguishes construction-routed edges from instance-receiver-routed edges in `code_impact` diagnostics | Reuse `RECEIVER_RESOLVED` (rejected — collapses two meaningfully different resolution paths) |
| 2026-06-01 | Cover all class-language languages in one change | Same root cause across the matrix; one fix prevents drift | Per-language changes (rejected — over-fragmented for a uniform gap) |
| 2026-06-01 | Bare-call invariant: helper fires only on bare-identifier / `new_expression` / `::new` shapes | Prevents accidental hijack of `obj.Foo()` method calls where `Foo` happens to be PascalCase | Symbol-lookup precondition alone (insufficient — would still walk the wrong AST shape) |
| 2026-06-01 | Phase 0 audit gates code edits | Java/C#/TS/JS/PHP behavior is unknown at start; helper scope depends on findings | Assume-broken-and-extend (rejected — could duplicate already-working logic); assume-working-and-skip (rejected — could leave gap) |
| 2026-06-01 | `GRAPH_BUILDER_VERSION` 14 → 15 | Edge wiring changes; cached graphs would otherwise show no `incoming` until manual rebuild | Skip bump (rejected — silent stale graphs) |
| 2026-06-01 | Rust marked lower-confidence | `Foo::new()` is convention, not language semantics; other associated functions can be construction-shaped without semantic construction intent | Skip Rust (rejected — covers ~90% of real Rust construction); equal-priority (rejected — overstates confidence) |
| TBD (Phase 0a) | Java/C#/TS/JS/PHP/Rust baseline behavior | (to be filled at Phase 0a) | |
| TBD (Phase 0b) | `code_callhierarchy` server-side integration approach | (to be filled at Phase 0b) | |

## Risks

| Risk | Mitigation |
|---|---|
| Double-counting in `code_callhierarchy(<ClassName>).incoming` if walker also transitively expands class → methods → callers | Phase 0b audit + explicit resolution before edge emission |
| Construction-edge bypass of method-resolution chain creates phantom edges where a same-name function shadows a class (e.g., Python `def Foo(): ...` next to `class Foo`) | Symbol-lookup precondition: only route to class node if a class/struct/enum/actor entity exists for the name. If both function and class exist, prefer the class; document |
| Scala companion `apply` returning a different type from the companion class | Detection rule restricts to case classes + companion `apply` returning `Foo` itself; non-matching `apply` falls through to receiver-type resolution |
| Kotlin object-invocation overload (`object Foo; Foo()` resolves to `invoke()` operator) confused with construction | Out of scope per Decision Log; symbol-lookup distinguishes `object` declarations from `class` declarations |
| Operators relying on the absence of construction edges in pre-bump graphs (e.g., custom downstream metrics counting only method-call edges) see counts shift | `GRAPH_BUILDER_VERSION` bump signals the change; `CONSTRUCTION_RESOLVED` confidence-tag filter lets downstream consumers exclude these edges if needed |
| Rust convention-based detection produces false positives for non-construction associated functions named `new` | Lower-confidence label; consider a per-language flag if field feedback shows pattern degrades |
| Cross-module construction (caller in `mod_a`, class in `mod_b`) requires import resolution to populate `symbol_lookup` | Existing cross-file resolution already handles imports for receiver-type — reuse |
| External libraries constructing in-project classes (Swift SwiftUI runtime, Python FastAPI DI, Spring `@Component`) — should bump `external_incoming_count` symmetrically | AC-19 — confirm direction during implementation; document if deferred |

## Related Work

- Direct response to Solaris 1.2.1+319y field report (this conversation) and its predecessor pattern (seed-211 fallback rule).
- Builds on `1312l` receiver-type resolution (Java) and the multi-language extensions in `13194` (Kotlin/C#), `1319a` (Go/Rust/Scala), `1319g` (Swift). The discriminator added in `1319g` was correct but incomplete — this change wires the deferred path.
- Closes the last per-language attribution gap for the most common refactor-impact question on a class. After this lands, `code_callhierarchy(<ClassName>).incoming` becomes the canonical operator answer across all 11 class-supporting languages.
- Complements `1319q` (receiver-type for JS/TS/Python via annotations) — that change does not produce construction edges by itself; this one does. Together they make `code_callhierarchy` fully populated for typed dynamic-language codebases.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
