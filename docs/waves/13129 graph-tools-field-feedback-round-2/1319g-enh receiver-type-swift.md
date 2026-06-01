# Receiver-Type Resolution — Extend to Swift

Change ID: `1319g-enh receiver-type-swift`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Receiver-type resolution at the graph builder layer was previously implemented for Java (`1312l`), Kotlin/C# (`13194`), Go/Rust/Scala (`1319a`). Swift was deferred without a strong justification — Swift has strong typing with `let foo: Foo = ...` patterns identical to Kotlin's. The same conservative coverage applies cleanly. Operator value: Swift codebases get phantom-suppression parity with the other typed languages.

## Approach

Mirror the Kotlin helper structure for Swift. Tree-sitter Swift call shape:
- `call_expression` with `navigation_expression` (`foo.bar()`) — receiver + method
- Bare call: `call_expression` with `simple_identifier`

Type-resolution rules (conservative):
- `this` (Swift `self`) → enclosing class/struct/actor/enum/protocol
- `super` → uncertain (defer inheritance walk)
- `let foo: Foo = ...` → declared type from `type_annotation`
- `let foo = Foo()` → uncertain (defer inference)
- `func bar(foo: Foo)` → parameter declared type
- `Foo.staticMethod()` → Foo as receiver

Deferred: `var`-typed locals with inference, optional chaining (`foo?.bar()`), closure receivers, generic methods.

## Requirements

1. Swift helpers in `graph_indexer.py`: `_resolve_swift_receiver_type`, `_resolve_swift_identifier_type`, `_search_swift_declarations_in_scope`, `_find_enclosing_swift_class_name`, `_extract_simple_swift_type_name`, `_resolve_swift_call_target`.
2. `walk_calls` dispatch extended to `lang_key == "swift"` and `node_type == "call_expression"`.
3. `RECEIVER_RESOLVED` confidence tag applied to Swift-resolved edges.
4. Tests: Solaris-style reproducer (typed local + phantom callee on simple name) for Swift; bare call + `self.method()` preserved.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Swift helpers + dispatch.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — Swift regression tests.

**Out of scope:**

- `var`-typed inferred locals.
- Optional chaining (`foo?.bar()`).
- Generic methods.
- Closures as receivers.

## Acceptance Criteria

- [x] AC-1: Swift helper set exists mirroring Kotlin's shape.
- [x] AC-2: `walk_calls` dispatches for Swift `call_expression`.
- [x] AC-3: Swift `RECEIVER_RESOLVED` edges pass the cross-file rewrite short-circuit (consistent with other languages).
- [x] AC-4: Reproducer test: `oos.writeObject(obj)` in Swift with `let oos: ObjectOutputStream = ...` routes to `external::ObjectOutputStream.writeObject`, NOT phantom project method.
- [x] AC-5: `self.method()` and bare `method()` from same class preserved.
- [x] AC-6: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Swift helper functions
- [x] Extend `walk_calls` dispatch
- [x] Add Swift regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Helper foundation |
| AC-2 | required | Walker integration |
| AC-3 | required | Cross-file pass consistency |
| AC-4 | required | Reproducer parity with Java/Kotlin/C# |
| AC-5 | required | False-positive bias preserved |
| AC-6 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Add Swift now — earlier deferral wasn't justified | Swift's type system matches Kotlin's; same conservative coverage applies cleanly. Operator value is parity with the other typed-language coverage | Continue deferring (rejected — no design reason) |
| 2026-06-01 | Conservative coverage (no inference) | Matches the established pattern from Kotlin/C#/Go/Rust/Scala — false-positive bias preserved on uncertain cases | Aggressive coverage including type inference (rejected — scope creep) |

## Risks

| Risk | Mitigation |
|---|---|
| Swift grammar AST shapes differ subtly from Kotlin | Test fixtures cover the major declaration shapes |
| `var foo = Foo()` inferred-type idiom common in Swift → high false-negative rate | Out of scope per design |

## Related Work

- Extension of `1312l`/`13194`/`1319a` to Swift. Closes the last typed-language gap in receiver-type coverage.
- Companion: `1319i`, `1319k`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
