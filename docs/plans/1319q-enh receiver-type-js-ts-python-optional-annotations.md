# Receiver-Type Resolution — JS / TS / Python via Optional Type Annotations

Change ID: `1319q-enh receiver-type-js-ts-python-optional-annotations`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

Wave 13129 deferred JavaScript, TypeScript, and Python from the receiver-type-at-graph-builder feature (`1312l`/`13194`/`1319a`/`1319g`) because their type systems are dynamic, optional, or inference-driven. The conservative declared-type strategy that works cleanly for Java/Kotlin/C#/Swift/Go/Rust/Scala doesn't transfer one-to-one — there's often no declared type to read.

However, **when type annotations ARE present** in these languages, the same Solaris-style phantom-suppression value applies:

- **TypeScript** — `let foo: Foo = bar()` is ubiquitous. The declared type is right there.
- **Python** — PEP 484 annotations are now default in modern codebases (FastAPI, Pydantic v2, modern Django). `foo: Foo = ...` and `def m(self, foo: Foo)` are extractable.
- **JavaScript** — JSDoc `/** @type {Foo} */` annotations are read by TypeScript's checker and IDEs; some codebases use them rigorously.

This change implements **partial-coverage receiver-type resolution** for these languages, gated on annotation presence. Annotated declarations resolve; unannotated declarations fall back to standard attribution (no regression vs. current behavior).

The accepted trade-off: operators in untyped codebases see no improvement; operators in typed codebases get Java-like coverage. This matches how `mypy --strict`, TypeScript's `strict: true`, and JSDoc-based JS tooling already operate.

## Approach

Three parallel helper sets, each mirroring the Kotlin/Swift helper shape (`1319g`).

### TypeScript

Tree-sitter TypeScript exposes type annotations as `type_annotation` children:
- `lexical_declaration` (let/const) → `variable_declarator` → `type_annotation`
- `function_declaration` / `method_definition` → `formal_parameters` → `required_parameter` → `type_annotation`
- `as` casts: `(x as Foo).bar()` — extract from `as_expression`

Helpers: `_resolve_ts_call_target`, `_resolve_ts_receiver_type`, `_resolve_ts_identifier_type`, `_search_ts_declarations_in_scope`, `_find_enclosing_ts_class_name`, `_extract_simple_ts_type_name`.

### Python

Tree-sitter Python exposes annotations as inline `type` nodes:
- `assignment` with `:` annotation: `foo: Foo = bar()` → `assignment.type`
- `function_definition` → `parameters` → `typed_parameter` → `type`
- `function_definition` return annotation: `-> Foo` (return type) is NOT used for receiver resolution — only parameter/local types.

Helpers: `_resolve_python_call_target`, `_resolve_python_receiver_type`, `_resolve_python_identifier_type`, `_search_python_declarations_in_scope`, `_find_enclosing_python_class_name`, `_extract_simple_python_type_name`.

### JavaScript (JSDoc-only)

Tree-sitter JavaScript does not parse JSDoc by default. Reading JSDoc requires either:
- A separate tree-sitter-jsdoc pass over comment text, OR
- Regex extraction of `/** @type {Foo} */` and `/** @param {Foo} foo */` patterns.

Given the complexity and lower confidence of JSDoc extraction, **JavaScript ships in a second phase** of this change, gated on TS/Python landing successfully. The JS implementation will likely use a regex pass for JSDoc immediately preceding `let`/`const`/`var` declarations and function parameters; uncertain types defer to standard attribution.

### Constructor discrimination

The Swift discriminator (PascalCase callee on bare call = constructor → defer) generalizes:
- TypeScript / JavaScript: `new Foo()` already uses an explicit `new_expression` node — no discrimination needed.
- Python: `Foo()` is ambiguous (could be constructor or callable). Apply the PascalCase check: if the callee is a bare identifier starting with uppercase and a class of that name is in scope, treat as constructor.

## Requirements

1. TypeScript helper set in `graph_indexer.py` mirroring Swift's (`1319g`).
2. Python helper set in `graph_indexer.py` mirroring Swift's, with PascalCase constructor discrimination.
3. JavaScript helper set deferred to phase 2 (after TS/Python validate).
4. `walk_calls` dispatch extended for TS (`call_expression`), Python (`call`), and eventually JS.
5. `RECEIVER_RESOLVED` confidence tag applied to all newly resolved edges.
6. **Annotation-presence gate**: when no annotation is found, return `None` — current standard attribution proceeds unchanged. No false positives from inference.
7. Tests per language (Solaris reproducer style):
   - TS: `let oos: ObjectOutputStream = ...; oos.writeObject(...)` → routes to `external::ObjectOutputStream.writeObject`.
   - TS: `let foo = bar()` (inferred) → unresolved, falls through.
   - Python: `oos: ObjectOutputStream = ...; oos.writeObject(...)` → routes externally.
   - Python: `def m(self, foo: Foo)` parameter type used.
   - Python: `foo = bar()` (no annotation) → unresolved.
   - Python: `Foo()` PascalCase bare call → defers (constructor).
   - JS (phase 2): JSDoc `/** @type {Foo} */ const foo = ...` → resolves.

## Scope

**Problem statement:** Typed JS / TS / Python codebases get no Solaris-style phantom suppression despite having declared types in the AST. The current "all dynamic languages excluded" position is too coarse.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — TS + Python helpers, `walk_calls` dispatch.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language regression tests.
- Phase 2 (separate ship): JS JSDoc extraction.

**Out of scope:**

- TS inference (`let foo = new Foo()` without explicit annotation). The TypeScript checker handles this; we don't reimplement TSC.
- Python type-comment syntax (`x = 1  # type: Foo`) — legacy PEP 484 form, rarely used in modern code.
- Python `TYPE_CHECKING`-gated imports producing forward-reference strings (`foo: "Foo"`). Defer; conservative skip is acceptable.
- TypeScript generics (`foo: Container<Foo>`). Use the outer type (`Container`); generic argument resolution out of scope.
- Optional chaining (`foo?.bar()`). Defer (same scope rule as Swift).
- Decorator-driven type changes (`@inject`, `@autowired`). Out of scope — they don't modify the AST type annotation.

## Acceptance Criteria

- [ ] AC-1: TypeScript helper set exists; resolves `let foo: Foo = ...` declared-type locals and parameters.
- [ ] AC-2: Python helper set exists; resolves `foo: Foo = ...` annotated locals, `def m(foo: Foo)` parameters, and skips unannotated cases.
- [ ] AC-3: PascalCase constructor discrimination on Python bare calls.
- [ ] AC-4: Annotation-presence gate returns `None` when no annotation; no regression on existing unannotated TS/Python tests.
- [ ] AC-5: `RECEIVER_RESOLVED` confidence tag applied; cross-file rewrite short-circuit consistent with other languages.
- [ ] AC-6: Solaris reproducer tests pass for TS and Python.
- [ ] AC-7: Self-references (`self.method()` Python, `this.method()` TS) preserved unchanged.
- [ ] AC-8: All existing graph-builder tests pass.
- [ ] AC-9 (phase 2): JS JSDoc extraction operational; `@type` and `@param` annotations recognized.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Phase 1a: TypeScript helpers + dispatch + tests
- [ ] Phase 1b: Python helpers + dispatch + tests
- [ ] Run framework tests; ship phase 1
- [ ] Phase 2: JS JSDoc extraction + tests
- [ ] Run framework tests; ship phase 2
- [ ] Close gate; mark change `implemented`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| ts-receiver-type | Engineering | — | Independent — TS grammar is clean |
| python-receiver-type | Engineering | — | Independent — Python grammar is clean |
| js-jsdoc-receiver-type | Engineering | ts-receiver-type, python-receiver-type | Phase 2 — validate the pattern works on typed languages first |

## Serialization Points

- `_resolve_<lang>_call_target` additions to `walk_calls` — single dispatch chain; coordinate to avoid merge conflicts.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — receiver-type resolution table extends to cover annotation-gated languages.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | TS primary value driver (largest user base) |
| AC-2 | required | Python primary value driver (typed-codebase parity) |
| AC-3 | required | False-positive guard on Python `Foo()` |
| AC-4 | required | No regression on untyped code |
| AC-5 | required | Confidence-tag plumbing parity |
| AC-6 | required | Reproducer evidence |
| AC-7 | required | Self-reference preservation |
| AC-8 | required | No baseline regression |
| AC-9 | nice-to-have | JS phase 2 — JSDoc adoption varies; lower marginal value |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Annotation-presence gate (no inference) | Inference is TSC's/mypy's job; we'd duplicate complex semantics for marginal additional coverage | Implement TSC-style inference (rejected — scope explosion); skip these languages entirely (rejected — leaves typed codebases unserved) |
| 2026-06-01 | Ship JS in phase 2, after TS/Python | JSDoc extraction is harder and lower-confidence; prove the pattern on grammar-supported annotations first | Ship all three together (rejected — couples a hard problem to two easy ones) |
| 2026-06-01 | PascalCase constructor discriminator on Python | Same as Swift `1319g` — `Foo()` ambiguity needs case-based defer | Track class symbols in scope and check membership (rejected — over-engineering for the common case) |

## Risks

| Risk | Mitigation |
|---|---|
| TypeScript `as` casts inside chains (`(x as Foo).bar()`) need extra AST walk | Cover with explicit test; conservative skip if the shape is unfamiliar |
| Python forward-reference strings (`foo: "Foo"`) produce string-typed annotation | Skip when annotation is a `string` node; do not parse the string |
| JSDoc regex misses block-comment edge cases | Phase 2 — start with the strict `/** @type {Foo} */` form; iterate |
| Python `Optional[Foo]` / `Foo \| None` produce subscripted/union types | Recognize `subscript`/`binary_operator` shapes; extract inner type when unambiguous, else skip |
| Annotated codebases mixed with unannotated files in the same project produce uneven coverage | Acceptable — matches mypy/TS behavior; document the partial-coverage model in `wave_graph_report` seed |

## Related Work

- Direct extension of `1312l`/`13194`/`1319a`/`1319g` to the optional-typing language family. Completes the receiver-type coverage matrix.
- Companion: `1319m` (Go directory), `1319o` (Python merge). Together, these three changes close every deliberate exclusion left by wave 13129.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
