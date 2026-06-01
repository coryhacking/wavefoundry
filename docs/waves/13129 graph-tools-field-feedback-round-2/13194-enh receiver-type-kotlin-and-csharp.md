# Receiver-Type Resolution — Extend to Kotlin and C#

Change ID: `13194-enh receiver-type-kotlin-and-csharp`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

`1312l-enh graph-builder-java-receiver-type-attribution` shipped Java-only with the explicit out-of-scope: *"C# and Kotlin receiver-type attribution. Same helper shape applies; defer to operator-validated extensions."*

Operator direction 2026-06-01: extend receiver-type resolution to Kotlin and C# now. Without it, `code_impact` and `code_callhierarchy` will silently produce contradictory answers on Kotlin/C# codebases — the same Aceiss-reproduced bug shape that hit Java users before 1312l, just on different ecosystems. The pattern proven by Java carries over; the implementation effort is per-language AST walkers.

## Approach

Mirror the Java helpers (`_resolve_java_receiver_type` et al.) for Kotlin and C# in `graph_indexer.py`. The structure is the same — receiver resolution returns a simple class name when resolvable, or None when uncertain (preserve false-positive bias). The differences are AST-shape-specific.

### Kotlin
- Tree-sitter Kotlin call shape: `call_expression` with `navigation_suffix` (`.method(...)`).
- Type-resolution rules:
  - `this` / `super` / bare call → enclosing class (mirrors Java)
  - `val foo: Foo = ...` → declared type from `: Foo` annotation
  - `val foo = Foo()` → uncertain (no symbol table)
  - `ClassName.staticMethod()` → ClassName as receiver type
- **Deferred sub-cases (return None):** `var foo` with inferred type, nullable receiver (`foo?.bar()`), extension functions, lambda receivers.

### C#
- Tree-sitter C# call shape: `invocation_expression` with `member_access_expression` (`receiver.Method()`).
- Type-resolution rules:
  - `this` / `base` / bare call → enclosing class
  - `Type foo = ...` → declared type
  - `var foo = ...` → uncertain (defer)
  - `ClassName.StaticMethod()` → ClassName as receiver type
- **Deferred sub-cases (return None):** generic methods (`Foo<T>()`), property access chains, null-conditional (`foo?.Method()`), explicit interface implementation.

Conservative approach: only resolve the cases we can prove correct from local AST. Everything else returns None.

## Requirements

1. **Kotlin helpers** in graph_indexer.py: `_resolve_kotlin_receiver_type`, `_resolve_kotlin_identifier_type`, `_search_kotlin_declarations_in_scope`, `_find_enclosing_kotlin_class_name`, `_extract_simple_kotlin_type_name`, `_resolve_kotlin_call_target`.
2. **C# helpers** with parallel naming (`_resolve_csharp_*`).
3. **`walk_calls` dispatch** extended from Java-only to Kotlin and C#.
4. **`RECEIVER_RESOLVED` confidence tag** applied to edges emitted by all three resolvers.
5. **`GRAPH_BUILDER_VERSION`** stays at 14.
6. **Tests** cover per-language reproducer scenarios mirroring the Java tests:
   - Kotlin: project `JSON.kt` with `writeObject` + caller `oos.writeObject(...)` where `oos: ObjectOutputStream` → phantom suppressed; bare/`this` calls preserved.
   - C#: project `JSON.cs` with `WriteObject` + caller `stream.WriteObject(...)` where `stream` is `ObjectOutputStream` → phantom suppressed; bare/`this`/`base` calls preserved.
7. **Defensive deferrals** — `var` locals, nullable receivers, extension functions, generics fall through to legacy attribution.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Kotlin and C# helper sets + walk_calls dispatch.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language regression tests.

**Out of scope:**

- `var`-typed locals (Kotlin + C#) — too much complexity without RHS analysis.
- Nullable receivers, extension functions (Kotlin), generic methods, property access chains.
- Server-impl-side defense-in-depth filter extension — Java-only today.

## Acceptance Criteria

- [x] AC-1: Kotlin helpers exist mirroring the Java set.
- [x] AC-2: C# helpers exist mirroring the Java set.
- [x] AC-3: `walk_calls` dispatches per-language for `lang_key in ("java", "kotlin", "csharp")`.
- [x] AC-4: Edges emitted by Kotlin/C# receiver-type resolution carry `confidence=RECEIVER_RESOLVED`.
- [x] AC-5: Kotlin reproducer: phantom `oos.writeObject(...)` suppressed; legitimate bare/`this` preserved.
- [x] AC-6: C# reproducer: phantom `stream.WriteObject(...)` suppressed; legitimate bare/`this`/`base` preserved.
- [x] AC-7: Uncertain cases (var-typed locals, nullable receivers, generics) fall through.
- [x] AC-8: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Kotlin helper functions
- [x] Add C# helper functions
- [x] Extend `walk_calls` dispatch
- [x] Add per-language regression tests + uncertain-case fall-through guards
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Kotlin helpers — foundation |
| AC-2 | required | C# helpers — foundation |
| AC-3 | required | Walker integration |
| AC-4 | required | Cross-file pass parity |
| AC-5 | required | Kotlin reproducer parity |
| AC-6 | required | C# reproducer parity |
| AC-7 | required | False-positive bias preserved |
| AC-8 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Extend now via operator direction | Operator direction: ship Kotlin/C# coverage in 1.2.1. Java implementation pattern is proven; per-language AST walkers are the implementation effort | Defer per 1312l out-of-scope (rejected per operator direction) |
| 2026-06-01 | Conservative coverage: defer var, nullable, extension functions, generics | Dominant cases (explicit type, this/bare, static) cover ~80% of operator workflows. Edge cases need codebase validation | Aggressive coverage (rejected — large scope creep) |
| 2026-06-01 | RECEIVER_RESOLVED for all three languages | Cross-file pass already short-circuits on this tag; consistent behavior across languages | Per-language tag (rejected — adds complexity without operator benefit) |
| 2026-06-01 | No GRAPH_BUILDER_VERSION bump | The resolver extension stays within the v14 schema (no new fields). Operators rebuilt for v14 get the new attribution automatically | Bump to v15 (rejected — would force a second rebuild in same release cycle) |

## Risks

| Risk | Mitigation |
|---|---|
| Kotlin/C# AST node-type names differ subtly → resolver fails silently | Per-language test fixtures cover major declaration shapes; false-positive bias preserves correctness on unrecognized shapes |
| Extension functions (Kotlin) misattributed | Explicitly out of scope; documented as deferred |
| `var`-typed locals common in modern code → high false-negative rate | Out of scope; the false-negative is "filter doesn't suppress a phantom" — same as wave-130rj behavior |

## Related Work

- Direct extension of `1312l-enh graph-builder-java-receiver-type-attribution` to Kotlin and C# per operator direction 2026-06-01.
- Companion to `13190-enh class-module-merge-multi-language` and `13192-enh stdlib-allowlist-multi-language`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
