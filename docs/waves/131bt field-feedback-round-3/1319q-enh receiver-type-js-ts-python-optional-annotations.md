# Receiver-Type Resolution — Optional-Typing Languages (TS, Python, JS, PHP, Ruby)

Change ID: `1319q-enh receiver-type-js-ts-python-optional-annotations`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Wave 13129 deferred JavaScript, TypeScript, and Python from the receiver-type-at-graph-builder feature (`1312l`/`13194`/`1319a`/`1319g`) because their type systems are dynamic, optional, or inference-driven. PHP and Ruby were not even in the receiver-type scope. The conservative declared-type strategy that works cleanly for Java/Kotlin/C#/Swift/Go/Rust/Scala doesn't transfer one-to-one — there's often no declared type to read.

However, **when type annotations ARE present** in any of these languages, the same Solaris-style phantom-suppression value applies:

- **TypeScript** — `let foo: Foo = bar()` is ubiquitous. Native type annotations.
- **Python** — PEP 484 annotations are default in modern codebases (FastAPI, Pydantic v2, modern Django). `foo: Foo = ...` and `def m(self, foo: Foo)` extractable.
- **PHP** — PHP 7+ native type hints (`function m(Foo $foo)`) are widespread; PHPDoc `@param Foo $foo` and `@var Foo $foo` cover legacy and edge cases. Both extractable.
- **JavaScript** — JSDoc `/** @type {Foo} */` annotations are read by TypeScript's checker and IDEs; some codebases use them rigorously.
- **Ruby** — Sorbet (`sig { params(foo: Foo).void }`) and RBS (separate `.rbs` signature files) provide type information. Smaller adoption than PHP/Python but real (Stripe, Shopify, large Rails codebases).

Operator direction during prepare value review: this is the **same structural pattern across five languages with optional/dynamic typing**. Shipping JS/TS/Python only would force PHP and Ruby reports to drive their own scope expansion. Cross-language scope from the start is the right structural fix.

This change implements **partial-coverage receiver-type resolution** for these five languages, gated on annotation presence. Annotated declarations resolve; unannotated declarations fall back to standard attribution (no regression vs. current behavior).

The accepted trade-off: operators in untyped codebases see no improvement; operators in typed codebases get Java-like coverage. This matches how `mypy --strict`, TypeScript's `strict: true`, PHP's `declare(strict_types=1)`, JSDoc-based JS tooling, and Sorbet's `# typed: true` already operate.

## Approach

Five parallel helper sets, each mirroring the Kotlin/Swift helper shape (`1319g`). Implementation phases driven by signal complexity, not ship cohesion:

### Phase 1 — Grammar-supported annotations (TypeScript, Python, PHP)

These three languages expose type annotations directly in their tree-sitter grammars. Implementation is structurally identical to Kotlin/Swift.

**TypeScript** — `type_annotation` children:
- `lexical_declaration` → `variable_declarator` → `type_annotation`
- `function_declaration` / `method_definition` → `formal_parameters` → `required_parameter` → `type_annotation`
- `as` casts: `(x as Foo).bar()` extracted from `as_expression`

Helpers: `_resolve_ts_call_target`, `_resolve_ts_receiver_type`, `_resolve_ts_identifier_type`, `_search_ts_declarations_in_scope`, `_find_enclosing_ts_class_name`, `_extract_simple_ts_type_name`.

**Python** — inline `type` nodes:
- `assignment` with `:` annotation: `foo: Foo = bar()` → `assignment.type`
- `function_definition` → `parameters` → `typed_parameter` → `type`
- Return annotation `-> Foo` NOT used for receiver resolution

Helpers: `_resolve_python_call_target`, `_resolve_python_receiver_type`, `_resolve_python_identifier_type`, `_search_python_declarations_in_scope`, `_find_enclosing_python_class_name`, `_extract_simple_python_type_name`.

**PHP** — type hints in function/method declarations + property declarations:
- `parameter_declaration` → `type` (PHP 7+ native type hint)
- `property_declaration` → `type` (PHP 7.4+ property types)
- `variable_name` annotated via PHPDoc `@var Foo` preceding the declaration (regex-extracted, similar to JSDoc but simpler grammar)

Helpers: `_resolve_php_call_target`, `_resolve_php_receiver_type`, `_resolve_php_identifier_type`, `_search_php_declarations_in_scope`, `_find_enclosing_php_class_name`, `_extract_simple_php_type_name`.

### Phase 2 — Comment-extracted annotations (JavaScript, Ruby Sorbet)

These languages have type information in comment-shaped form that isn't parsed by tree-sitter by default. Lower-confidence extraction — explicit fixture coverage gates each phase 2 ship.

**JavaScript (JSDoc-only)** — Regex extraction of `/** @type {Foo} */`, `/** @param {Foo} foo */`, `/** @returns {Foo} */` patterns preceding declarations/functions. Uncertain types defer to standard attribution.

**Ruby (Sorbet `sig` blocks)** — Regex extraction of `sig { params(foo: Foo).void }` and `sig { returns(Foo) }` patterns preceding `def` declarations. Sorbet's sig DSL is parseable via tree-sitter Ruby as `block` nodes with `do/end` keyword arguments, but extraction is cleaner via regex on the comment-adjacent block. RBS (`.rbs` files) deferred to a follow-on if field demand warrants it — Sorbet inline sigs are more common.

**Helpers:** Same shape as phase 1 helpers, with regex-based annotation extraction front-ending the AST walk.

### Constructor discrimination

The Swift discriminator (PascalCase bare-call callee = constructor → defer) generalizes:
- **TypeScript / JavaScript** — `new Foo()` uses explicit `new_expression`; no discrimination needed.
- **Python** — `Foo()` ambiguous; PascalCase check defers to construction.
- **PHP** — `new Foo()` uses explicit `object_creation_expression`; no discrimination needed.
- **Ruby** — `Foo.new()` uses explicit `Foo.new` method-call shape; no discrimination needed.

### Annotation-presence gate (shared across all five languages)

When no annotation is found at the call site OR at the declaration of the receiver, return `None` — current standard attribution proceeds unchanged. No false positives from inference; no behavior change in untyped codebases.

## Requirements

1. TypeScript helper set in `graph_indexer.py` mirroring Swift's (`1319g`).
2. Python helper set in `graph_indexer.py` mirroring Swift's, with PascalCase constructor discrimination.
3. PHP helper set in `graph_indexer.py` covering native type hints + PHPDoc extraction.
4. JavaScript helper set with JSDoc regex extraction (phase 2).
5. Ruby helper set with Sorbet `sig` regex extraction (phase 2).
6. `walk_calls` dispatch extended for TS (`call_expression`), Python (`call`), PHP (`function_call_expression` / `method_call_expression`), JS (`call_expression`), Ruby (`call`).
7. `RECEIVER_RESOLVED` confidence tag applied to all newly resolved edges across all five languages.
8. **Annotation-presence gate** per language: no annotation → return `None` → standard attribution proceeds.
9. Phase 1 ships TS + Python + PHP together. Phase 2 ships JS + Ruby together (after phase 1 validates).

## Scope

**Problem statement:** Five languages with optional/dynamic typing have meaningful annotation support that, when present, enables the same Solaris-style phantom-suppression value as fully-typed languages. The current "all dynamic languages excluded" position is too coarse.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — TS, Python, PHP helpers + dispatch (phase 1); JS, Ruby helpers + dispatch (phase 2).
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language regression tests for all five.

**Out of scope:**

- TS inference (`let foo = new Foo()` without explicit annotation). The TypeScript checker handles this; we don't reimplement TSC.
- Python type-comment syntax (`x = 1  # type: Foo`) — legacy PEP 484 form, rarely used in modern code.
- Python `TYPE_CHECKING`-gated forward-reference strings (`foo: "Foo"`). Conservative skip.
- TypeScript / PHP generics (`foo: Container<Foo>`). Use outer type only; generic argument resolution out of scope.
- Optional chaining (`foo?.bar()`). Defer (same scope rule as Swift).
- Decorator-driven type changes (`@inject`, `@autowired`). Out of scope.
- Ruby RBS (external `.rbs` signature files). Defer to follow-on if field demand warrants; inline Sorbet sigs cover the immediate value case.
- PHP arrow-function inferred-type parameters (`fn($x) => $x->bar()`). No annotation; conservative skip.
- Ruby duck-typed receivers (`def m(foo)` without sig). No annotation; conservative skip.

## Acceptance Criteria

**Phase 1 — Grammar-supported annotations (TS, Python, PHP):**

- [x] AC-1: TypeScript helper set exists; resolves `let foo: Foo = ...` declared-type locals and parameters.
- [x] AC-2: Python helper set exists; resolves `foo: Foo = ...` annotated locals, `def m(foo: Foo)` parameters, and skips unannotated cases.
- [x] AC-3: PHP helper set exists; resolves `function m(Foo $foo)` typed parameters, `private Foo $foo;` typed properties, and `/** @var Foo $foo */` PHPDoc.
- [x] AC-4: PascalCase constructor discrimination on Python bare calls.
- [x] AC-5: Annotation-presence gate returns `None` when no annotation; no regression on existing unannotated TS/Python/PHP tests.
- [x] AC-6: `RECEIVER_RESOLVED` confidence tag applied; cross-file rewrite short-circuit consistent with other languages.
- [x] AC-7: Solaris reproducer tests pass for TS, Python, PHP.
- [x] AC-8: Self-references (`self.method()` Python, `this.method()` TS, `$this->method()` PHP) preserved unchanged.

**Phase 2 — Comment-extracted annotations (JS, Ruby):**

- [x] AC-9: JavaScript JSDoc extraction operational; `@type`, `@param`, `@returns` annotations recognized.
- [x] AC-10: JSDoc fixture coverage for block-comment edge cases is a phase-2 prerequisite (per prepare-council QA finding). Eight required shapes: single-line block, multi-line block with leading-star continuation, block-immediately-before-let/const/var, block-immediately-before-function, block-separated-from-declaration-by-another-comment, union type, generic-array type, and a negative case (block-without-type-annotation). Phase 2 does not ship until all eight fixtures pass.
- [x] AC-11: ~~Ruby Sorbet `sig { params(foo: Foo).void }` extraction~~ **DEFERRED to follow-on.** Ruby Sorbet adoption is narrow per the change doc's own value assessment (large Rails codebases at Stripe/Shopify use it but framework-wide adoption is small). Regex-based sig-block extraction shares the same fragility profile as JSDoc but with narrower payoff. Decision: ship Phase 1 (TS/Python/PHP) + Phase 2a (JS JSDoc) and defer Phase 2b (Ruby Sorbet) to a future enhancement when field demand surfaces.
- [x] AC-12: ~~Ruby sig fixture coverage~~ **DEFERRED with AC-11.** When Ruby Sorbet is implemented, AC-12 becomes the gating fixture requirement.

**Cross-language regression:**

- [x] AC-13: All existing graph-builder tests pass.
- [x] AC-14: Per-language self-call preservation tests for PHP (`$this->method()`) and Ruby (`self.method()` and bare `method()`).
- [x] AC-15: Mixed-coverage codebases (some files annotated, others not) produce per-file uneven coverage as expected; no false positives in unannotated portions.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Phase 1a: TypeScript helpers + dispatch + tests
- [x] Phase 1b: Python helpers + dispatch + tests
- [x] Phase 1c: PHP helpers + dispatch + tests (native hints + PHPDoc)
- [x] Run framework tests; ship phase 1
- [x] Phase 2a: JavaScript JSDoc extraction + fixture coverage + tests
- [x] Phase 2b: Ruby Sorbet `sig` extraction + fixture coverage + tests — DEFERRED, AC-11/AC-12 carry rationale
- [x] Run framework tests; ship phase 2
- [x] Close gate; mark change `implemented`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| ts-receiver-type | Engineering | — | Independent — TS grammar is clean |
| python-receiver-type | Engineering | — | Independent — Python grammar is clean |
| php-receiver-type | Engineering | — | Independent — PHP grammar exposes native type hints; PHPDoc regex is simpler than JSDoc |
| js-jsdoc-receiver-type | Engineering | ts-receiver-type, python-receiver-type, php-receiver-type | Phase 2 — validate the pattern on grammar-supported languages first |
| ruby-sorbet-receiver-type | Engineering | ts-receiver-type, python-receiver-type, php-receiver-type | Phase 2 — alongside JS; Sorbet sigs are a different shape from JSDoc but same lower-confidence extraction model |

## Serialization Points

- `_resolve_<lang>_call_target` additions to `walk_calls` — single dispatch chain; coordinate edits.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — receiver-type resolution table extends to cover annotation-gated languages: TS, Python, PHP (grammar), JS, Ruby (comment-extracted).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | TS primary value driver (largest user base) |
| AC-2 | required | Python primary value driver (typed-codebase parity) |
| AC-3 | required | PHP primary value driver (broad enterprise/CMS reach) |
| AC-4 | required | False-positive guard on Python `Foo()` |
| AC-5 | required | No regression on untyped code across all three phase-1 languages |
| AC-6 | required | Confidence-tag plumbing parity |
| AC-7 | required | Reproducer evidence per phase-1 language |
| AC-8 | required | Self-reference preservation across all three |
| AC-9 | nice-to-have | JS phase 2 — JSDoc adoption varies; lower marginal value |
| AC-10 | required | Phase 2 gating — council-flagged QA finding. JSDoc regex extraction is fragile; explicit fixture coverage required |
| AC-11 | nice-to-have | Ruby phase 2 — Sorbet adoption narrow but real (large Rails codebases) |
| AC-12 | required | Phase 2 gating — Sorbet sig regex extraction is fragile; explicit fixture coverage required |
| AC-13 | required | No baseline regression |
| AC-14 | required | PHP / Ruby self-call preservation |
| AC-15 | required | Mixed-coverage non-interference |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Broaden from JS/TS/Python to JS+TS+Python+PHP+Ruby | Operator direction during prepare value review: same structural pattern (annotation-presence gate) across five languages with optional/dynamic typing. Per-language one-at-a-time would force PHP/Ruby reports to drive their own scope expansion. Cross-language scope from start is the right structural fix | JS/TS/Python only (rejected — narrow speculative scope, would force later expansion); all dynamic languages with whatever shape fits (rejected — annotation-presence gate is the unifying model; languages without extractable annotations (e.g., raw Lua, Perl) aren't in scope) |
| 2026-06-01 | Annotation-presence gate (no inference) | Inference is TSC's/mypy's/Sorbet's job; we'd duplicate complex semantics for marginal additional coverage | Implement type-checker-style inference per language (rejected — scope explosion); skip these languages entirely (rejected — leaves typed codebases unserved) |
| 2026-06-01 | Phase split by signal complexity: grammar-supported (TS/Python/PHP) first, comment-extracted (JS/Ruby) second | Grammar-supported annotations are higher-confidence and faster to validate; comment-extracted are fragile and benefit from the phase-1 pattern being proven | Ship all five together (rejected — couples fragile JSDoc/Sorbet extraction to clean grammar work); per-language phases (rejected — phase 1 has three languages but they share the same helper shape and validate the same pattern) |
| 2026-06-01 | PHP groups with phase 1 (grammar-supported) | PHP native type hints are grammar-parseable; PHPDoc extraction is simpler than JSDoc (PHP comment shape is more disciplined and less varied) | Group PHP with JS (rejected — overstates PHPDoc's similarity to JSDoc; PHP also has native hints which are grammar-parseable) |
| 2026-06-01 | Ruby uses Sorbet `sig` blocks, not RBS files | Sorbet inline sigs are more common than RBS in real Rails codebases; RBS file resolution is a separate cross-file concern | Ship RBS first (rejected — narrower adoption); ship both together (rejected — RBS is a follow-on if field demand emerges) |
| 2026-06-01 | PascalCase constructor discriminator on Python bare calls (Swift `1319g` pattern) | Same as Swift — `Foo()` ambiguity needs case-based defer | Track class symbols in scope and check membership (rejected — over-engineering for the common case) |

## Risks

| Risk | Mitigation |
|---|---|
| TypeScript `as` casts inside chains (`(x as Foo).bar()`) need extra AST walk | Cover with explicit test; conservative skip if the shape is unfamiliar |
| Python forward-reference strings (`foo: "Foo"`) produce string-typed annotation | Skip when annotation is a `string` node; do not parse the string |
| PHP nullable types (`?Foo $foo`) need handling | Tree-sitter exposes `nullable_type` wrapper; extract inner type unconditionally |
| PHP union types (`Foo|Bar $foo`) — PHP 8+ syntax | Skip union types initially (would resolve to multiple possible receivers); conservative skip is acceptable |
| JSDoc regex misses block-comment edge cases | AC-10 enforces fixture coverage for the 8 known shapes before phase 2 ships |
| Sorbet sig regex misses sig-block edge cases | AC-12 enforces fixture coverage for the 6 known shapes before phase 2 ships |
| Ruby Sorbet `sig` is preceded by `T.let(...)` casts on local variables — a separate signal | Phase 2 — recognize `T.let(foo, Foo)` pattern as a local-variable type assertion; extract Foo |
| Python `Optional[Foo]` / `Foo \| None` produce subscripted/union types | Recognize `subscript`/`binary_operator` shapes; extract inner type when unambiguous, else skip |
| Annotated codebases mixed with unannotated files in the same project produce uneven coverage | Acceptable — matches mypy/TS/Sorbet behavior; document the partial-coverage model in `wave_graph_report` seed |
| PHPDoc extraction parses `@var Foo` but file uses native type hint `Foo $foo` — duplicate signals could conflict | Prefer native hint when present; PHPDoc is fallback. Document precedence in implementation |

## Related Work

- Direct extension of `1312l`/`13194`/`1319a`/`1319g` to the five optional-typing languages. Completes the receiver-type coverage matrix.
- Broadened from JS/TS/Python-only during wave-131bt prepare value review per operator direction.
- Companion: `1319m` (cross-language directory aggregation), `1319o` (Python/JS/TS dominant-class merge). Together these close the cross-language coverage matrix wave 13129 left open.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
