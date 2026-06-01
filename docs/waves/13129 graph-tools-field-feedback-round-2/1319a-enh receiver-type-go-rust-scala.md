# Receiver-Type Resolution — Extend to Go, Rust, Scala

Change ID: `1319a-enh receiver-type-go-rust-scala`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Operator direction 2026-06-01: extend `1312l`/`13194`-style receiver-type resolution to remaining supported languages with **explicit type annotations**. Java/Kotlin/C# already covered. Go, Rust, and Scala have explicit-typed bindings that allow clean per-call-site resolution. JavaScript, TypeScript, Ruby, and PHP are deferred — their type systems are dynamic, optional, or inference-driven, making the pattern unreliable.

## Approach

Add per-language helpers mirroring the Java implementation:

### Go
- Tree-sitter Go call shape: `call_expression` with `selector_expression` (`receiver.Method()`).
- Type-resolution rules:
  - `var foo Type` → declared type from `type` field
  - `foo := Type{...}` → uncertain (composite literal; defer composite-literal type inference)
  - `func (r *Receiver) Method()` → receiver from method's declared receiver
  - Bare call → enclosing function/file scope
- **Deferred:** short variable declarations with type inference, type assertions, interface conversions.

### Rust
- Tree-sitter Rust call shape: `call_expression` with `field_expression` (`receiver.method()`).
- Type-resolution rules:
  - `let foo: Type = ...` → declared type
  - `let foo = Type::new(...)` → uncertain (defer turbofish + paths)
  - `fn method(self, ...)` / `fn method(&self, ...)` → enclosing impl block's type
  - `Type::associated_fn()` → Type as receiver (`<Type as Trait>::method` etc. → defer)
- **Deferred:** trait method calls, generic method calls, smart-pointer auto-deref, lifetime elision edge cases.

### Scala
- Tree-sitter Scala call shape: `call_expression` with member-access shape.
- Type-resolution rules:
  - `val foo: Type = ...` → declared type
  - `def method(): ReturnType` → uncertain unless local type annotation present
  - `this` / `super` / bare call → enclosing class/object
- **Deferred:** type-class instances, implicit conversions, path-dependent types, structural types.

Conservative coverage across all three: only resolve cases provable from local AST. Uncertain returns None, preserving false-positive bias.

## Requirements

1. **Per-language helpers** in graph_indexer.py: `_resolve_go_*`, `_resolve_rust_*`, `_resolve_scala_*` mirroring the Java/Kotlin/C# helper sets.
2. **`walk_calls` dispatch** extended to `lang_key in ("go", "rust", "scala")` for the appropriate call-node types.
3. **`RECEIVER_RESOLVED` confidence tag** applied to edges emitted by all three new resolvers.
4. **Tests** cover per-language reproducer scenarios:
   - Go: `oos OutputStream; oos.WriteObject(obj)` where `oos OutputStream` resolves to phantom-suppress; bare/`this`-style preserved.
   - Rust: `let oos: ObjectOutputStream = ...; oos.write_object(obj)` phantom-suppress; bare/`self.method()` preserved.
   - Scala: `val oos: ObjectOutputStream = ...; oos.writeObject(obj)` phantom-suppress; bare/`this` preserved.
5. **Defensive deferrals documented** — short variable declarations, inferred types, generic methods fall through.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Go, Rust, Scala helper sets + dispatch.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language reproducer tests.

**Out of scope:**

- C++ (different AST + header/impl split).
- JavaScript (no type system).
- TypeScript (optional + inference-driven).
- Ruby (dynamic).
- PHP (optional type hints; revisit when type-hint coverage justifies).

## Acceptance Criteria

- [x] AC-1: Go helpers exist + dispatch wired.
- [x] AC-2: Rust helpers exist + dispatch wired.
- [x] AC-3: Scala helpers exist + dispatch wired.
- [x] AC-4: Per-language phantom-suppression reproducer passes for Go, Rust, Scala.
- [x] AC-5: Per-language bare/`this`/`self` calls preserved.
- [x] AC-6: Uncertain cases (short var decls, inferred types, generics) fall through.
- [x] AC-7: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Go helper functions
- [x] Add Rust helper functions
- [x] Add Scala helper functions
- [x] Extend `walk_calls` dispatch
- [x] Add per-language regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Go helpers foundation |
| AC-2 | required | Rust helpers foundation |
| AC-3 | required | Scala helpers foundation |
| AC-4 | required | Reproducer parity |
| AC-5 | required | No regression on legitimate same-class callers |
| AC-6 | required | False-positive bias preserved |
| AC-7 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Extend via operator direction | Operator chose maximum language coverage | Defer (rejected per operator direction) |
| 2026-06-01 | Skip JS, TS, Ruby, PHP for receiver-type | Dynamic / optional / inference-driven type systems; partial coverage creates uneven UX | Attempt partial coverage (rejected — partial UX worse than none) |
| 2026-06-01 | Conservative coverage in Go/Rust/Scala | Edge cases (composite literals, trait dispatch, implicits) need symbol-table work | Aggressive coverage (rejected — large scope creep) |

## Risks

| Risk | Mitigation |
|---|---|
| Go method receivers (`func (r *T) M()`) require AST walk through impl block | Implementation handles the receiver via the same enclosing-class pattern Java uses |
| Rust short variable declarations (`let foo = ...`) are dominant idiom → high false-negative rate | Out of scope per design; documented |
| Scala implicit conversions / type classes → resolver misses real calls | Out of scope; false-negative = phantom not suppressed = same as wave-130rj behavior |

## Related Work

- Extension of `1312l`/`13194` to languages with explicit type systems.
- Companion: `13196`, `13198`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
