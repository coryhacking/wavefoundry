# Construction Call Edges Not Attributed to Class Node

Change ID: `1319s-bug construction-call-edges-to-class-node`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

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

6. **Scope-aware symbol lookup (per prepare-council red-team finding).** "Class symbol in scope" means **lexically reachable** at the call site, with normal name-resolution precedence: parameters and locals shadow methods, methods on the enclosing class shadow same-named sibling classes elsewhere in the project. The precondition is NOT a project-wide name lookup. Specifically: if `class Outer { fun Foo() { ... Foo() ... } }` AND a sibling `class Foo` exists, the bare-call `Foo()` inside `Outer.Foo()` routes to the method `Outer.Foo` (closest lexical binding), not to the sibling class `Foo`. The helper consults the symbol table with scope-precedence semantics; a class symbol only wins when no closer-scope binding shadows it.

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
| **Rust** | `Foo { x: 1, y: 2 }` (struct literal) | `Foo::new(args)` (convention; not enforced) | `struct_expression` with `type_identifier` `Foo` (struct literal — primary Rust construction shape). PLUS `call_expression` with `scoped_identifier` ending in `new`, AND `struct_item`/`enum_item` `Foo` in scope (associated-function `::new` convention; lower confidence). |
| **Go** | `&Foo{...}` (composite literal with address-of), `Foo{...}` (value composite literal) | `new(Foo)` (builtin), `NewFoo(args)` (factory function convention) | `composite_literal` with `type_identifier` `Foo` — primary Go construction shape (`Foo{x: 1}` or `&Foo{x: 1}`). PLUS `call_expression` with `identifier` callee `new` and `type_identifier` argument (`new(Foo)` builtin). PLUS `call_expression` with `identifier` callee matching `^New[A-Z]` convention AND struct named after the trailing-portion in scope (`NewFoo` constructs `Foo`; lower-confidence convention match). |

### Construction AST shape inventory (per language)

The previous draft of this change treated Go as "no class constructors — skip" and Rust as `Foo::new()` only. Both were incorrect:

- **Go does have construction shapes** — it's just structural (composite literals), not class-method-based. Primary form is `&Foo{x: 1, y: 2}` for pointer construction and `Foo{x: 1, y: 2}` for value construction. Less common: `new(Foo)` builtin (returns `*Foo` zeroed) and the `NewFoo(args)` factory-function convention.
- **Rust's primary construction shape is the struct literal `Foo { x: 1, y: 2 }`** — not `Foo::new()`. The associated-function `::new` convention is widespread but not language-required; some structs expose `Foo::with_capacity(n)`, `Foo::builder().build()`, etc.

Including both struct-literal and convention-based forms gives the right structural coverage. Convention-based shapes (Rust `::new`, Go `NewFoo`) are marked lower-confidence and operators see them tagged accordingly.

### Phase 0a audit — explicit-`new` and composite-literal baseline (precondition to gate-open)

Before opening `framework_edit_allowed`, baseline the current behavior of `walk_calls` on:
- `new_expression` / `object_creation_expression` for Java/C#/TS/JS/PHP
- `struct_expression` for Rust
- `composite_literal` and `call_expression(new(...))` for Go
- `scoped_identifier ::new` for Rust convention form
- `call_expression` with `New<TypeName>` callee for Go factory-function convention form

Two possible findings per language/shape:

- **Already routes to class node** → AC closes as a confirmation; doc updated, no code change for that language.
- **Does not route** → extend the helper; AC becomes a required code change.

**Deliverable** (recorded in the Phase 0a row of Decision Log, replacing the TBD placeholder):

A multi-row table covering every (language, AST shape) pair in scope. Format:

| Language | AST shape | Current behavior | Action | Reproducer fixture | Inspected commit |
|---|---|---|---|---|---|
| Java | `object_creation_expression` (type_identifier) | routes to class node ✓ / produces no edge ✗ / routes to wrong target ✗ | close-out / extend helper / extend helper + retarget | `class Foo {}; class Bar { Foo make() { return new Foo(); } }` | `<git sha>` |
| C# | `object_creation_expression` (identifier) | … | … | … | … |
| TypeScript | `new_expression` (identifier) | … | … | … | … |
| JavaScript | `new_expression` (identifier) | … | … | … | … |
| PHP | `object_creation_expression` (name) | … | … | … | … |
| Rust | `struct_expression` (type_identifier) — primary | … | … | `struct Foo { x: i32 } fn make() -> Foo { Foo { x: 1 } }` | … |
| Rust | `call_expression` (scoped_identifier ending `::new`) — convention | … | … | … | … |
| Go | `composite_literal` (type_identifier) — primary | … | … | `type Foo struct{ X int }; func make() *Foo { return &Foo{X: 1} }` | … |
| Go | `call_expression` (`new` builtin) | … | … | `type Foo struct{}; func make() *Foo { return new(Foo) }` | … |
| Go | `call_expression` (`New<TypeName>` factory convention) | … | … | `type Foo struct{}; func NewFoo() *Foo { return &Foo{} }` (the call site `NewFoo()` is the construction; routing to `Foo`) | … |

Audit method per (language, shape) pair: write the reproducer fixture, run `wave_index_build(content="graph", mode="rebuild")`, then `code_callhierarchy(symbol="Foo", direction="incoming")`. Inspect for the expected edge. Record the exact commit SHA inspected so the Phase 0a result is reproducible.

ACs covering each language/shape are rewritten after Phase 0a as either `close-out` (verified routing already correct; doc-only update) or `extend` (code change required).

### Phase 0b audit — `server_impl.py` integration check (precondition to gate-open)

Audit `code_callhierarchy` server-side behavior for class-node queries. Two possible findings to resolve before edge emission:

- **Walker currently transitively expands class → methods via `defines` → method callers** — construction edges directly to the class node may double-count callers (once for construction, once per method they happen to call). Decide: separate result section (`construction_callers`) vs deduplication pass vs merged `incoming` with a `kind: "construction"` discriminator.
- **Walker reads class-node inbound edges directly** — no integration change needed.

**Deliverable** (recorded in the Phase 0b row of Decision Log, replacing the TBD placeholder):

A three-paragraph note:

1. **Current behavior summary**: a 3–5 sentence description of how `code_callhierarchy(symbol=<ClassName>, direction="incoming")` is implemented in `server_impl.py` today — which graph edges it reads, whether it follows `defines` transitively, what node kinds it includes. Cite the function name and line range of the relevant code.
2. **Double-counting risk verdict**: one of three explicit positions:
   - **(a) No risk** — walker reads class-node inbound edges directly without `defines` expansion. No integration change needed.
   - **(b) Risk — deduplicate** — walker transitively expands; the fix is a deduplication pass that collapses (caller, class) pairs from both construction edges and method edges into one result entry.
   - **(c) Risk — separate result section** — walker transitively expands; the fix is exposing `construction_callers` as a separate list alongside `incoming` (operators get explicit signal that the relationship is construction, not method-call).
3. **Implementation impact**: one sentence per verdict path — for (a), no code change. For (b), file/function to edit and approximate LOC. For (c), the schema addition to `code_callhierarchy` response shape and which seed needs the doc update.

Audit method: read `server_impl.py` `code_callhierarchy` implementation; write a minimal Swift fixture (`class Foo` with one method `bar` called from another file's `Caller` function — no construction); run `code_callhierarchy(symbol="Foo", direction="incoming")` on the current 1.2.1+319y graph; observe whether `Caller` appears as an incoming caller via the `defines` expansion path. If yes → verdict (b) or (c). If no → verdict (a).

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

- [x] AC-1: Reproducer fixture per language produces a `calls` edge from caller function to class node after rebuild.
- [x] AC-2: `code_callhierarchy(symbol=<ClassName>, direction="incoming")` returns construction call sites with `name`, `file`, `line`, `snippet`.
- [x] AC-3: `CONSTRUCTION_RESOLVED` confidence tag appears in `code_impact.edges[].confidence` for construction edges.

**Per-language coverage:**

- [x] AC-4: Swift — bare-call (`Foo(args)`), explicit-init (`Foo.init(args)`), failable (`Foo?(args)`) all produce construction edges.
- [~] AC-5: Python — `Foo(args)` with `class Foo` in scope produces a construction call edge (routes correctly to class node via cross-file simple-name resolution). **Confidence tag remains `EXTRACTED` rather than `CONSTRUCTION_RESOLVED`** because Python uses `ast`-based extraction in `_extract_python_artifact`, not the tree-sitter `walk_calls` path where the construction-resolution dispatch lives. Routing is correct; tag upgrade deferred to a Python-specific follow-up that adds construction-detection to `CallCollector`. Documented in Decision Log.
- [x] AC-6: Kotlin — `Foo(args)` produces construction edge.
- [x] AC-7: Scala — `Foo(args)` for case class + `new Foo(args)` for non-case class produce construction edges.
- [x] AC-8: Ruby — `Foo.new(args)` produces construction edge to class `Foo`.
- [x] AC-9: Java — `new Foo(args)` produces construction edge (close-out if already routing, extend otherwise — depends on Phase 0 audit).
- [x] AC-10: C# — `new Foo(args)` produces construction edge (close-out or extend).
- [x] AC-11: TypeScript — `new Foo(args)` produces construction edge (close-out or extend).
- [x] AC-12: JavaScript — `new Foo(args)` produces construction edge (close-out or extend).
- [x] AC-13: PHP — `new Foo(args)` produces construction edge (close-out or extend).
- [x] AC-14: Rust — `Foo::new(args)` produces construction edge (lower-confidence — convention-based; mark behind a per-language flag if needed).
- [x] AC-14b: Rust — `Foo { x: 1, y: 2 }` struct-literal produces construction edge (PRIMARY Rust construction shape; high confidence via `struct_expression` + type_identifier match).
- [x] AC-14c: Go — `&Foo{x: 1}` and `Foo{x: 1}` composite-literal produce construction edge (primary Go construction shape).
- [x] AC-14d: Go — `new(Foo)` builtin produces construction edge.
- [~] AC-14e: ~~Go `NewFoo(args)` factory-function convention produces construction edge~~ **Out of scope per Phase 0a empirical finding.** The factory function call already produces a correct function-call edge to `NewFoo` (verified). Adding an additional construction edge to `Foo` would double-emit for the same call site. Operators wanting "what constructs Foo via factory?" can chain `code_callhierarchy(NewFoo).incoming` from the existing edge. Scope changed per Phase 0a Decision Log row.

**Negative / safety cases (required):**

- [x] AC-15: Method named identically to enclosing class (`class Foo { func Foo() {...} }`) — method call does NOT produce a construction edge. Validates symbol-lookup precondition.
- [x] AC-15b: **Scope-aware lookup — sibling class shadowed by enclosing method.** `class Outer { fun Foo() { Foo() } }` with a sibling `class Foo` existing in another file → the bare-call `Foo()` inside `Outer.Foo` routes to method `Outer.Foo` (closest lexical binding wins), NOT to construction of the sibling class `Foo`. Validates scope-aware lookup precedence. Required test per the prepare-council red-team finding.
- [x] AC-16: Type-name-as-value reference (`let factory = Foo` Swift; `cls = Foo` Python) — no construction edge produced. Validates bare-call invariant.
- [x] AC-17: `self.method()` / `this.method()` / `self.foo()` inside `Foo` — does NOT produce a self-construction edge.
- [x] AC-18: Navigation-expression PascalCase method call (`obj.Foo()` where `Foo` is a method on `obj`'s type) — does NOT trigger construction-resolution; remains receiver-type-resolution territory.

**Plumbing / integration:**

- [x] AC-19: External construction (external code constructs an in-project class) — **documented deferral**: the indexer only walks files inside the project root; external code (third-party packages, system libraries) is not parsed, so external callers of in-project classes never produce edges in the graph by design. The query-time `external_incoming_count` field surfaces external-to-project edges in the *other* direction (in-project code calling external symbols). External-to-in-project construction is not in scope for this change and would require indexing dependency sources, which is out of scope for the wavefoundry indexer's project-bounded walk.
- [x] AC-20: No regression on existing receiver-type-resolution tests (`RECEIVER_RESOLVED` confidence still applied where it was before).
- [x] AC-21: `code_graph_path` between caller and class node reflects the construction edge as an expected hop.
- [x] AC-22: `GRAPH_BUILDER_VERSION` bumped 14 → 15.
- [x] AC-23: Seed docs updated for `code_callhierarchy`, `code_impact`, `code_graph_path` describing construction edges and `CONSTRUCTION_RESOLVED` confidence tag.

## Tasks

- [x] **Phase 0a** — audit `walk_calls` baseline behavior on `new_expression`/`object_creation_expression` for Java/C#/TS/JS/PHP and `::new` for Rust; record findings in Decision Log
- [x] **Phase 0b** — audit `server_impl.py` `code_callhierarchy` behavior on class-node queries; resolve double-counting question in Decision Log
- [x] Open `framework_edit_allowed` gate
- [x] Implement `_resolve_construction_target` helper covering all in-scope languages
- [x] Add `CONSTRUCTION_RESOLVED` confidence tag plumbing
- [x] Wire `walk_calls` discriminator chain per language
- [x] Implement `server_impl.py` integration per Phase 0b outcome — **no integration change required** per Phase 0b verdict (a): `code_callhierarchy_response` walker reads class-node inbound edges via `index.traverse(..., relations=["calls"], max_hops=1, direction="callers")` at `server_impl.py:9332`. Construction edges surface as direct `incoming` entries with no double-counting and no schema additions.
- [x] Add per-language regression tests (positive + negative)
- [x] Bump `GRAPH_BUILDER_VERSION` 14 → 15
- [x] Open `seed_edit_allowed` gate; update `code_callhierarchy`, `code_impact`, `code_graph_path` seeds; close gate
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [x] Repackage; field-verify against Solaris reproducer + cross-language fixtures — shipped in 1.3.0+31f7. Solaris field-verified `SolarisCommand.run → AutomationController` (canonical bare-call construction; `EXTRACTED → CONSTRUCTION_RESOLVED` confidence promotion). One Swift parse-failure edge case (`StatusBarManager` construction missing when the class body trips tree-sitter into ERROR-wrapping the declaration) is tracked separately as `1319v` — tree-sitter grammar issue, not a defect in this change's construction-detector logic.

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
| AC-5 | not-this-scope | Python construction routing already worked via EXTRACTED (cross-file simple-name resolution); CONSTRUCTION_RESOLVED tag upgrade deferred — Python uses ast-based extraction, separate code path |
| AC-6 | required | Kotlin — Android / server-side parity |
| AC-7 | required | Scala — case-class idiom + new-keyword variant |
| AC-8 | required | Ruby — `Foo.new` is the universal Ruby form |
| AC-9 | required | Java — most-used explicit-`new` language |
| AC-10 | required | C# parity |
| AC-11 | required | TypeScript parity |
| AC-12 | required | JavaScript parity |
| AC-13 | required | PHP parity |
| AC-14 | important | Rust `::new` — convention not language semantics |
| AC-14b | required | Rust struct-literal — primary Rust construction shape |
| AC-14c | required | Go composite-literal — primary Go construction shape (previously incorrectly dismissed) |
| AC-14d | required | Go `new(Foo)` builtin — secondary but real Go construction shape |
| AC-14e | not-this-scope | Go factory convention removed from scope per Phase 0a empirical finding — existing function-call edge to factory is correct; additional construction edge would double-emit |
| AC-15 | required | False-positive guard (method-named-as-class) |
| AC-15b | required | Scope-aware lookup — sibling-class-shadowed-by-method case (council red-team finding) |
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
| 2026-06-01 | Scope-aware symbol lookup (lexical reachability with shadowing precedence) | Prepare-phase Wave Council red-team finding: project-wide name lookup would false-trigger construction when an enclosing-class method shares a name with a sibling class. The fix is normal name-resolution semantics — parameters/locals shadow methods, methods shadow sibling classes, then class symbol wins | Project-wide name lookup (rejected — false-positive on `class Outer { fun Foo() {} }` + sibling `class Foo`) |
| 2026-06-01 | Ship all 11 languages in one change; do NOT split into bare-call (Swift/Python/Kotlin/Scala/Ruby) + explicit-`new` (Java/C#/TS/JS/PHP/Rust) phases | Operator direction during prepare. Single change preserves the unified discriminator-chain implementation; phased ship would split the same `_resolve_construction_target` helper across two release cycles | Phased ship A+B (rejected by operator — implementation cohesion outweighs incremental delivery for this change) |
| 2026-06-01 | Add Rust struct-literal `Foo { x: 1 }` as primary Rust construction shape | Operator direction during prepare value review: `Foo::new()` is convention; `struct_expression` is the language-native construction form. Covering only `::new` would miss the dominant Rust idiom | Convention-only coverage (rejected — would miss the primary shape) |
| 2026-06-01 | Add Go construction shapes: composite-literal `&Foo{}` / `Foo{}`, `new(Foo)` builtin, `NewFoo()` factory convention | Operator direction during prepare value review: "Go has no class constructors" was incorrect framing. Go has the patterns; they're structural not class-method-based. Composite literal is the dominant shape; `new()` and `NewFoo` are real secondary shapes | Skip Go entirely (rejected — matches the incorrect original framing); cover only composite literals (rejected — would miss real but secondary shapes); cover all shapes (chosen) |
| 2026-06-01 | Fold all construction-edge variants under one `CONSTRUCTION_RESOLVED` confidence tag (no `STRUCT_LITERAL_RESOLVED` or per-shape tags) | Operator question is "how is this type instantiated?" not "what AST shape was used?" — finer-grained tags would add diagnostic noise without operator value. The `confidence` field tells operators the edge is type-resolved construction; specific call-site shape is in the source file at the edge endpoint | Per-shape tags (rejected — diagnostic noise without operator-actionable distinction); per-confidence-level tags (rejected — Rust convention vs Go factory convention are both "lower confidence" but in different ways; per-shape granularity belongs in `source_file` analysis, not the confidence tag) |
| 2026-06-01 (Phase 0a) | Empirical baseline complete — per-shape findings in the table below this row | Audit run via `/tmp/phase0a_audit.py` against `update_graph_index` with synthetic fixtures; results inspected against the produced edges/nodes. Reproducible on the wavefoundry commit at the head of branch `main` at audit time | (no alternative — direct audit result) |

### Phase 0a — per-shape baseline behavior

| Language | AST shape | Current behavior | Action | Reproducer fixture |
|---|---|---|---|---|
| Java | `object_creation_expression` (type_identifier) | **Routes to class node ✓** with `confidence=EXTRACTED`. Edge: `src/Bar.java::Bar.make` → `src/Foo.java` | **Close-out + retag confidence** — routing is correct; upgrade `EXTRACTED` → `CONSTRUCTION_RESOLVED` so operators can filter on it | `public class Foo { public Foo() {} }` / `public class Bar { public Foo make() { return new Foo(); } }` |
| C# | `object_creation_expression` (identifier) | **Routes to class node ✓** with `confidence=EXTRACTED`. Edge: `src/Bar.cs::Bar.Make` → `src/Foo.cs` | **Close-out + retag confidence** — same as Java | `public class Foo { public Foo() {} }` / `public class Bar { public Foo Make() { return new Foo(); } }` |
| TypeScript | `new_expression` (identifier) | **Routes to class node ✓** with `confidence=EXTRACTED`. Edge: `src/bar.ts::make` → `src/foo.ts::Foo` | **Close-out + retag confidence** — same as Java | `export class Foo { constructor() {} }` / `import { Foo } from './foo'; export function make() { return new Foo(); }` |
| JavaScript | `new_expression` (identifier) | **Routes to class node ✓** with `confidence=EXTRACTED`. Same shape as TypeScript | **Close-out + retag confidence** — same as TS | (mirror of TS fixture with `.js`) |
| PHP | `object_creation_expression` (name) | **Produces NO calls edge ✗** — `_TS_CALL_NODES_PHP` does not include `object_creation_expression` (only `function_call_expression` / `member_call_expression` / `scoped_call_expression`). The constructor call is invisible | **Extend** — add `object_creation_expression` to `_TS_CALL_NODES_PHP` and route to class node with `CONSTRUCTION_RESOLVED` | `<?php class Foo {}` / `<?php class Bar { public function make() { return new Foo(); } }` |
| Rust | `struct_expression` (type_identifier) — PRIMARY | **Produces NO calls edge ✗** — `_TS_CALL_NODES_RUST` includes only `call_expression` + `macro_invocation`. Struct literal `Foo { x: 1 }` is invisible | **Extend** — add `struct_expression` to `_TS_CALL_NODES_RUST` (or handle in a Rust-specific construction-resolution path) and route to struct node with `CONSTRUCTION_RESOLVED` | `pub struct Foo { pub x: i32 }` / `pub fn make() -> Foo { Foo { x: 1 } }` |
| Rust | `call_expression` (scoped_identifier ending `::new`) — convention | **Wrong target ✗** — call IS captured but resolves to `external::Foo::new` (associated-function key, not the project class node). Edge: `src/bar.rs::make` → `external::Foo::new` | **Extend + retarget** — detect `<TypeName>::new()` and retarget edge to the struct node when `TypeName` matches a `struct_item`/`enum_item` in scope; lower-confidence (convention) | `pub struct Foo {} impl Foo { pub fn new() -> Foo { Foo {} } }` / `pub fn make() -> Foo { Foo::new() }` |
| Go | `composite_literal` (type_identifier) — PRIMARY | **Produces NO calls edge ✗** — `_TS_CALL_NODES_GO` includes only `call_expression`. Composite literal `&Foo{}` / `Foo{}` is invisible | **Extend** — add `composite_literal` to `_TS_CALL_NODES_GO` (filter on `type_identifier` to exclude map/slice/array composite literals) and route to struct node with `CONSTRUCTION_RESOLVED` | `type Foo struct{ X int }` / `func makeLit() *Foo { return &Foo{X: 1} }` |
| Go | `call_expression` (`new` builtin) | **Wrong target ✗** — call IS captured but resolves to `external::new` (the builtin). Edge: `src/bar.go::makeNew` → `external::new` | **Extend + retarget** — special-case `new(<TypeName>)`: extract the type-identifier argument as the target; retarget to the struct node when present | `type Foo struct{}` / `func makeNew() *Foo { return new(Foo) }` |
| Go | `call_expression` (`New<TypeName>` factory convention) | **Routes to factory function ✓** — call IS captured and resolves to the factory function. Edge: `src/bar.go::useFactory` → `src/bar.go::NewFoo`. The factory function `NewFoo` is what's called; that edge is correct as a function call | **Skip / no additive edge** — the function-call edge to `NewFoo` already exists with correct semantics. Adding an additional construction edge to `Foo` would double-emit (one to `NewFoo`, one to `Foo`) for the same call site. **Decision: Go factory convention out of scope.** Operators wanting "what constructs Foo via factory?" can chain `code_callhierarchy(NewFoo).incoming` from the existing edge | `type Foo struct{}` / `func NewFoo() *Foo { return &Foo{} }` / `func useFactory() *Foo { return NewFoo() }` |

**Implication for ACs:**

- **AC-9 / AC-10 (Java, C#)** — `close-out + retag confidence`. Verify routing already correct (covered); add test that confirms `CONSTRUCTION_RESOLVED` tag is applied.
- **AC-11 / AC-12 (TS, JS)** — same as Java/C#: close-out + retag.
- **AC-13 (PHP)** — `extend`. Add `object_creation_expression` to PHP call-node set; route to class node with `CONSTRUCTION_RESOLVED`.
- **AC-14 (Rust `::new`)** — `extend + retarget`. Add convention-based detection in `_resolve_rust_call_target` (or a new construction-target helper) that retargets `Foo::new()` to the struct node when `Foo` is a `struct_item`/`enum_item` in scope.
- **AC-14b (Rust struct-literal)** — `extend`. Add `struct_expression` to Rust call-node set; route to struct node with `CONSTRUCTION_RESOLVED`.
- **AC-14c (Go composite-literal)** — `extend`. Add `composite_literal` to Go call-node set with `type_identifier` filter (exclude map/slice/array composite literals); route to struct node with `CONSTRUCTION_RESOLVED`.
- **AC-14d (Go `new(Foo)`)** — `extend + retarget`. Special-case `new(<TypeName>)` in Go call attribution: extract the `type_identifier` argument as the construction target.
- **AC-14e (Go factory convention)** — **scope change.** Out of scope; existing function-call edge to the factory function (`NewFoo`) is correct and additive construction-to-`Foo` edge would double-emit. Operators can chain `code_callhierarchy(NewFoo).incoming` from the existing edge. Update the Decision Log entry below.


| 2026-06-01 (Implementation) | Python `Foo(...)` construction edges work via the existing EXTRACTED path (route correctly to class node post-cross-file resolution), but the `CONSTRUCTION_RESOLVED` confidence tag is NOT applied because Python uses `ast`-based extraction in `_extract_python_artifact` rather than the tree-sitter `walk_calls` path. The new `_resolve_construction_target` helper only fires on tree-sitter call nodes. Operators relying on `confidence` for filtering Python construction edges will not see them via that signal in this release | **Decision: defer Python `CONSTRUCTION_RESOLVED` tagging to a follow-up.** Routing is correct; tagging is the only gap. A Python-specific addition to `CallCollector.visit_Call` (detect PascalCase `Name` callees resolving to a class in scope; emit with `CONSTRUCTION_RESOLVED` instead of `EXTRACTED`) is straightforward but architecturally separate. Document in seed-211 client-side filtering recommendation (`RECEIVER_RESOLVED` OR `CONSTRUCTION_RESOLVED` keeps the tag-based filter forward-compat without needing the Python-side change) | Implement Python tag in this change (rejected — separate ast-based code path; out-of-scope for this delivery); ship without Python coverage (rejected — Python construction routing already works at the EXTRACTED level, tag upgrade is the only gap) |
| 2026-06-01 (Phase 0b) | **Verdict (a) — no risk, no integration change needed.** Walker reads class-node inbound `calls` edges directly via `index.traverse(node_id, relations=["calls"], max_hops=1, direction="callers")` at `server_impl.py:9332`. No `defines`-transitive expansion through methods. Construction edges added by this change will surface as direct `incoming` entries on `code_callhierarchy(symbol=<ClassName>)` queries with no double-counting risk and no schema additions to the response shape | Audit: read `code_callhierarchy_response` walker call at server_impl.py:9332 and the surrounding incoming-edge construction. Confirmed: relations filter is `["calls"]` only (no `defines`), `max_hops=1` (no transitive), `direction="callers"` (edges pointing AT the node). Empirical confirmation: Phase 0a fixtures showed Java/C#/TS/JS construction edges already exist (`Bar.make → src/Foo.java`) and the file-level class merge unifies the file and class node, so `code_callhierarchy(symbol="Foo").incoming` already returns these on builder-version-14 graphs. The Solaris field report on Swift was specific to Swift's deferred-PascalCase-bare-call path (per `1319g`), not a walker limitation. No `code_callhierarchy_response` change needed | Verdict (b) deduplication pass (not needed — no double-counting); verdict (c) separate `construction_callers` result section (not needed — walker semantics already correct; separate section would be redundant and confusing) |

## Risks

| Risk | Mitigation |
|---|---|
| Double-counting in `code_callhierarchy(<ClassName>).incoming` if walker also transitively expands class → methods → callers | Phase 0b audit + explicit resolution before edge emission |
| Construction-edge bypass of method-resolution chain creates phantom edges where a same-name function shadows a class (e.g., Python `def Foo(): ...` next to `class Foo`) | Symbol-lookup precondition: only route to class node if a class/struct/enum/actor entity exists for the name. If both function and class exist, prefer the class; document |
| Scala companion `apply` returning a different type from the companion class | Detection rule restricts to case classes + companion `apply` returning `Foo` itself; non-matching `apply` falls through to receiver-type resolution |
| Kotlin object-invocation overload (`object Foo; Foo()` resolves to `invoke()` operator) confused with construction | Out of scope per Decision Log; symbol-lookup distinguishes `object` declarations from `class` declarations |
| Operators relying on the absence of construction edges in pre-bump graphs (e.g., custom downstream metrics counting only method-call edges) see counts shift | `GRAPH_BUILDER_VERSION` bump signals the change; `CONSTRUCTION_RESOLVED` confidence-tag filter lets downstream consumers exclude these edges if needed |
| Rust convention-based detection (`::new`) produces false positives for non-construction associated functions named `new` | Lower-confidence label on `::new` matches; struct-literal `Foo {}` (AC-14b) is high-confidence and primary — convention match is a secondary signal |
| Rust struct-literal `Foo { x: 1 }` matches a `struct_expression` but Rust also allows struct updates `Foo { ..base }` and shorthand `Foo { x }` — variant shapes | Tree-sitter `struct_expression` covers all these variants; detection works on the `type_identifier` regardless of body shape |
| Go composite-literal `&Foo{...}` and `Foo{...}` differ only in pointer-vs-value semantics — operators may want to distinguish | Both route to the same class node (the type `Foo`). The pointer-vs-value distinction is at the call site, not the construction target; operators inspecting the call-site source see the distinction |
| Go `NewFoo` convention false-positives on factory functions returning `Bar` or `interface{}` — function name matches convention but doesn't construct `Foo` | Lower-confidence label; could be tightened by checking return type but only when annotated. Phase 0 audit explicitly tests `NewFoo() (*Foo, error)` return-type pattern |
| Go composite-literal in unrelated contexts (e.g., `map[string]int{"a": 1}` is also a composite_literal) | Type-identifier check filters: map/slice/array composite literals have map/slice/array `type` nodes, not `type_identifier`. Filter on `type_identifier` only |
| Cross-module construction (caller in `mod_a`, class in `mod_b`) requires import resolution to populate `symbol_lookup` | Existing cross-file resolution already handles imports for receiver-type — reuse |
| External libraries constructing in-project classes (Swift SwiftUI runtime, Python FastAPI DI, Spring `@Component`) — should bump `external_incoming_count` symmetrically | AC-19 — confirm direction during implementation; document if deferred |

## Related Work

- Direct response to Solaris 1.2.1+319y field report (this conversation) and its predecessor pattern (seed-211 fallback rule).
- Builds on `1312l` receiver-type resolution (Java) and the multi-language extensions in `13194` (Kotlin/C#), `1319a` (Go/Rust/Scala), `1319g` (Swift). The discriminator added in `1319g` was correct but incomplete — this change wires the deferred path.
- Closes the last per-language attribution gap for the most common refactor-impact question on a class. After this lands, `code_callhierarchy(<ClassName>).incoming` becomes the canonical operator answer across all 11 class-supporting languages.
- Complements `1319q` (receiver-type for JS/TS/Python via annotations) — that change does not produce construction edges by itself; this one does. Together they make `code_callhierarchy` fully populated for typed dynamic-language codebases.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
