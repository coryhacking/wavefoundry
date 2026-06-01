# Java Receiver-Type Resolution — Filter False Cross-Class Callers on Method Name Matches

Change ID: `130tw-enh java-receiver-type-resolution`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field report on `1.1.0+30tt`: `code_callhierarchy(JSON.writeObject)` returned 11 Java callers, but 2 cross-community entries (`JdbcConnectionRegistry.cloneConnectionMap`, `LdapContextRegistry.cloneLdapEnv`) were false positives — they call `oos.writeObject(object)` where `oos` is a `java.io.ObjectOutputStream`, NOT the `JSON` class. The call-site scanner matched the method name `writeObject` without resolving the receiver type, producing phantom cross-community signal that could trigger an incorrect architecture-review escalation per seed-214.

The earlier scope for this change was a *diagnostic warning* on high-collision method names. Per operator direction 2026-05-31, replaced with actual receiver-type resolution: parse each candidate call site's AST, resolve the receiver to its declared type, and exclude the entry when the type definitively doesn't match the queried symbol's owning class.

## Approach

For Java `method_invocation` nodes (`receiver.method(...)`), tree-sitter exposes:
- `object` field → the receiver expression
- `name` field → the method identifier

Resolution algorithm (per candidate call site):

1. Walk up from the identifier match to the enclosing `method_invocation`. If not inside one (e.g. `method_reference`, bare statement), apply the fallback rules below.
2. Get the `object` field. If absent, the call is bare (e.g. `process()`) → resolve to enclosing class.
3. Resolve the receiver expression to a declared type:
   - **`this`** → enclosing `class_declaration` simple name
   - **`super`** → preserve (we don't yet resolve up the inheritance chain; uncertain → preserve)
   - **simple identifier `x`** (a local variable, parameter, or field):
     - Walk up to the enclosing method scope, then to the class scope
     - Look for a `local_variable_declaration`, `formal_parameter`, or `field_declaration` named `x` in scope
     - Return the declared type's simple name from that node
   - **`ClassName.staticMethod()`** style — receiver is a bare identifier referencing a class — match by simple class name
   - **`field_access` `obj.field.method()`** → uncertain (defer)
   - **Anything else** (cast, generic, lambda, complex chain, `var`-typed local) → uncertain
4. Compare the resolved type to the queried symbol's owning class:
   - **Match (simple-name equality)** → include the entry
   - **Definitive mismatch** → exclude
   - **Uncertain** → include (false-positive is better than false-negative for operator verification)

## Requirements

1. New `_resolve_java_receiver_type(method_invocation_node, source_bytes) -> str | None` helper that walks the AST around a method invocation node, resolves the receiver, and returns the declared simple type name (or `None` for uncertain).
2. Java reference scanner filters refs whose receiver-type resolution returns a definitively non-matching class. The queried symbol's owning class is parsed from the resolved `node_id` portion before `::<method>`.
3. The MATCH is the simple class name (last `.`-segment). Fully qualified name resolution via imports is NOT performed (deferred — proper symbol table work).
4. C# / Kotlin receiver-type resolution is OUT OF SCOPE for this change. Java-specific per Aceiss report.
5. Tests cover the Aceiss reproducer pattern: a Java fixture with two classes where `JSON.writeObject(...)` and `oos.writeObject(...)` (with `ObjectOutputStream oos = new ObjectOutputStream(...)`) both appear. Querying `JSON.writeObject` returns the JSON-class caller and excludes the `JdbcRegistry` caller. Plus tests for `this.writeObject()`, bare `writeObject()`, `Class.method()` static-style, and uncertain receivers (preserve the candidate).
6. No regression to existing call-site attribution for non-Java languages or for bare-name (no class context) Java queries.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: `_resolve_java_receiver_type` helper + Java filter in the reference/call-site path used by `code_callhierarchy_response`.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 5+ regression tests covering the matrix.

**Out of scope:**

- C# / Kotlin / other-language receiver-type resolution.
- Inheritance chain resolution (queried `JSON.writeObject`; caller via subtype reference).
- Fully-qualified-name matching via import resolution.
- Generic type parameter resolution.
- `var`-typed local variables (Java 10+) — return `None` (uncertain → preserve).
- Method-reference receiver-type resolution (`Foo::process` already handled by 130r7 at AST classification).

## Acceptance Criteria

- [x] AC-1: `_resolve_java_receiver_type(node, source_bytes)` returns a simple class name when the receiver is resolvable, or `None` when uncertain.
- [x] AC-2: Resolution covers `this`, simple-identifier local variables, simple-identifier parameters, simple-identifier fields, and `ClassName.staticMethod()` static-style.
- [x] AC-3: Java reference scanner extracts the queried symbol's owning class from `node_id` (when present in `<file>::<Class>.<method>` form) and filters refs whose resolved receiver type definitively doesn't match.
- [x] AC-4: When the queried symbol is bare (no class context), no filtering is applied — backward compatible.
- [x] AC-5: When receiver-type resolution returns `None` (uncertain), the ref is preserved (false-positive bias).
- [x] AC-6: The Aceiss reproducer pattern resolves correctly: synthetic two-class Java fixture where `JSON.writeObject` is queried returns the JSON-class caller and excludes the `JdbcRegistry`-class caller whose receiver is an `ObjectOutputStream` local.
- [x] AC-7: `this.method()`, bare `method()`, and `Class.method()` static-style all resolve to the enclosing or named class.
- [x] AC-8: Non-Java languages and bare-name Java queries continue to work without filtering.
- [x] AC-9: 5+ new regression tests covering the trigger matrix; all existing tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Implement `_resolve_java_receiver_type` helper (and supporting `_extract_java_owner_class_from_node_id`, `_search_java_declarations_in_scope`, `_find_enclosing_java_class_name`, `_extract_simple_java_type_name` helpers)
- [x] Wire the filter into the Java call-site path in `code_callhierarchy_response`. Also fixed a pre-existing bug where the incoming-path call-site scan used the qualified `symbol` (e.g. `JSON.writeObject`) instead of the bare label — now uses `node.get("label")`.
- [x] Add regression tests (5 end-to-end tests + 4 helper-unit tests = 9 total)
- [x] Run framework tests (2007 tests pass)
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline helper |
| AC-2 | required | Receiver-resolution coverage matrix |
| AC-3 | required | The integration that wires the filter into the scanner |
| AC-4 | required | Backward compat for bare-name queries |
| AC-5 | required | False-positive bias on uncertainty |
| AC-6 | required | The Aceiss-reported scenario end-to-end |
| AC-7 | required | Edge cases (this/bare/static) |
| AC-8 | required | No collateral damage |
| AC-9 | required | Regression coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Resolution instead of diagnostic warning | Per operator direction 2026-05-31. Actual filtering removes phantom callers; a diagnostic-only approach still surfaces the phantoms with a warning | Diagnostic only (original scope, rejected per operator direction) |
| 2026-05-31 | Bias toward including uncertain matches | False-positive is better than false-negative for the operator's manual verification | Bias toward excluding (rejected — loses real callers in complex cases) |
| 2026-05-31 | Simple-name type matching, no import resolution | 85% solution covering the dominant Java idiom (`Type x = new Type()` then `x.method()`) | Full import-table resolution (deferred — major scope expansion) |
| 2026-05-31 | Java-only scope | Aceiss reported Java specifically; C# extension is operator-validation-driven | Pre-emptive C# extension (rejected — no operator-validated need yet) |
| 2026-05-31 | Defer inheritance chain | Rarely the cause of cross-community phantoms in the reported case | Walk supertype chain (deferred — requires class hierarchy tracking) |
| 2026-05-31 | Defer `var`-typed locals | Less common in mature codebases; safe fallback to `None` | RHS expression resolution (deferred) |

## Risks

| Risk | Mitigation |
|---|---|
| Receiver resolution wrong → exclude real callers (false negatives) | AC-5 bias toward inclusion on uncertain; tests cover the common patterns explicitly |
| Performance impact on Java files with many common-name calls | One AST walk per candidate; ~10s of microseconds per call site. Aceiss reported 11 candidates / 130ms total — well within budget |
| Complex receiver expressions (chained calls, casts, generics) silently treated as uncertain | Acceptable per AC-5 |
| Edge case: queried symbol is qualified but caller uses bare `method()` intra-class | Bare call resolves to `this` → enclosing class → matches if caller is in same class as queried. Correct |

## Related Work

- Aceiss field report on `1.1.0+30tt`: detailed reproducer of `JSON.writeObject` false-positive cross-community callers.
- Companion changes in this wave's round-trip extension batch: `130tw-enh exclude-external-from-graph-report`, `130tw-enh betweenness-computed-field`, `130tw-enh large-community-pagination`, `130tw-enh fan-in-name-collision-hint-and-seed-note`.
- Builds on 130r7's call-site classification.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
