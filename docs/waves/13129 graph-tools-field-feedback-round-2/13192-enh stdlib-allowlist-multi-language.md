# Stdlib Allowlist — Extend to C#, Kotlin, Swift, Python

Change ID: `13192-enh stdlib-allowlist-multi-language`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

`1316p-enh external-name-collision-stdlib-allowlist` shipped Java-only with the explicit out-of-scope: *"Per-language allowlists for C# / Kotlin / Swift / Python. Java is the dominant operator-reported case; add others on operator validation."*

Operator direction 2026-06-01: extend the allowlist coverage now. The verification trigger documented in seed-211 (`external_name_collision_count > 0`) is otherwise a Java-only signal; operators on C# / Kotlin / Swift / Python codebases see the same diagnostic dead weight Aceiss reported for the Java common case before 1316p.

## Approach

Replace the single `_JAVA_STDLIB_COMMON_NAMES` frozenset with a per-language dispatch table keyed by source-file extension. `_collision_fields` extracts the language from the node's `source_file` and consults the language-specific allowlist (or returns 0 when the language has no allowlist).

Per-language allowlists (curated; ~25-35 names each):

**C# (`.cs`)** — `Equals`, `GetHashCode`, `ToString`, `GetType`, `Dispose`, `MoveNext`, `Current`, `Compare`, `CompareTo`, `Clone`, `Read`, `Write`, `Close`, `Flush`, `Start`, `Stop`, `Reset`, `Cancel`, `Invoke`, `Add`, `Remove`, `Contains`, `Clear`, `ToArray`, `ToList`, `Format`, `Parse`, `TryParse`, `Visit`, `Execute`, `Process`, `Handle`.

**Kotlin (`.kt`)** — runs on JVM so inherits Java common names. Plus Kotlin-specific stdlib extension methods: `equals`, `hashCode`, `toString`, `compareTo`, `iterator`, `next`, `hasNext`, `close`, `run`, `accept`, `apply`, `let`, `also`, `with`, `invoke`, `getValue`, `setValue`, `plus`, `minus`, `times`, `div`, `rangeTo`.

**Swift (`.swift`)** — `init`, `deinit`, `description`, `debugDescription`, `hash`, `encode`, `decode`, `compare`, `index`, `count`, `append`, `remove`, `insert`, `contains`, `forEach`, `map`, `filter`, `reduce`, `compactMap`, `flatMap`, `sorted`, `prefix`, `suffix`, `first`, `last`, `min`, `max`, `allSatisfy`.

**Python (`.py`)** — dunder methods + common stdlib: `__init__`, `__str__`, `__repr__`, `__eq__`, `__hash__`, `__len__`, `__iter__`, `__next__`, `__enter__`, `__exit__`, `__call__`, `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`, `__bool__`, `__add__`, `__sub__`, `__mul__`, `__lt__`, `close`, `read`, `write`, `flush`, `run`, `start`, `join`.

Other languages (Go, Rust, JS/TS) deliberately omitted in this change — no operator-validated demand. Add via follow-on waves when surfaced.

## Requirements

1. **Replace `_JAVA_STDLIB_COMMON_NAMES`** with `_STDLIB_COMMON_NAMES_BY_LANG: dict[str, frozenset[str]]` keyed by language extension (lower-case, with leading dot for clarity).
2. **`_collision_fields` derives language from `source_file`** of the node (extension lookup) and consults the corresponding allowlist. Returns 0 for languages without an allowlist.
3. **The deprecated alias `name_collision_count`** is unaffected (maps to `same_name_node_count`, not the external field).
4. **Seed-211 update:** the verification trigger note documents that allowlists are now multi-language and operators on C# / Kotlin / Swift / Python codebases benefit too.
5. **Tests** cover (a) Java entry still fires for `run` (regression); (b) C# `Equals` fires; (c) Kotlin `let` fires; (d) Swift `init` fires; (e) Python `__str__` fires; (f) Go/Rust file (no allowlist) returns 0.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — per-language allowlist table + `_collision_fields` rewrite.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — multi-language note.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 5+ regression tests covering each new language.

**Out of scope:**

- Go / Rust / JS / TS allowlists. Add via follow-on waves when operator-validated.
- Per-name framework attribution (JDK vs Spring vs Hibernate; .NET BCL vs ASP.NET; etc.). Defer.
- Allowlist-as-config (operator-tunable). Defer; the curated lists cover the dominant cases.

## Acceptance Criteria

- [x] AC-1: `_STDLIB_COMMON_NAMES_BY_LANG` exists with `.java`, `.cs`, `.kt`, `.swift`, `.py` entries with appropriately curated lists.
- [x] AC-2: `_collision_fields` extracts the language from the project node's `source_file` and consults the matching allowlist; returns 0 for languages without an allowlist (`.go`, `.rs`, `.js`, `.ts`, etc.).
- [x] AC-3: Existing Java tests (1316p) continue to pass — `run`, `close`, `equals`, `writeObject`, `getMethod` all fire.
- [x] AC-4: New language coverage tests fire for canonical names: C# `Equals`, Kotlin `let` (or `apply`/`also`), Swift `init`, Python `__str__`.
- [x] AC-5: Non-allowlist language files (e.g., Go `.go`) return 0 even when the simple name matches a Java allowlist entry like `run`.
- [x] AC-6: Seed-211 verification trigger note updated for multi-language.
- [x] AC-7: 5+ new regression tests; all existing tests pass.
- [x] AC-8: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Replace `_JAVA_STDLIB_COMMON_NAMES` with `_STDLIB_COMMON_NAMES_BY_LANG` dispatch table
- [x] Rewrite `_collision_fields` to derive language + lookup
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-211 verification trigger note (multi-language)
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 5+ regression tests covering each new language
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Per-language dispatch table |
| AC-2 | required | Language detection from source_file extension |
| AC-3 | required | Java regression — 1316p tests must continue passing |
| AC-4 | required | New language coverage |
| AC-5 | required | Languages without allowlist don't false-fire |
| AC-6 | required | Operator interpretation guidance |
| AC-7 | required | Regression coverage |
| AC-8 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Per-language dispatch by source_file extension | Each language has different stdlib patterns; one global allowlist would either over-flag (Java `run` triggers on a Python file) or be ambiguous. Extension-based dispatch is mechanically clean | Single global allowlist (rejected — `run` is Java but also Python Thread.run); explicit language tag on each node (rejected — adds field for marginal benefit; extension is already derivable) |
| 2026-06-01 | Kotlin inherits Java common names + adds Kotlin-specific extensions | Kotlin compiles to JVM; project Kotlin code routinely overrides JDK methods (`equals`, `hashCode`, etc.). Also has Kotlin-specific extension functions (`let`, `apply`, `also`) that are commonly used as method names in Kotlin DSL code | Kotlin-only list (rejected — misses the JDK collision dimension) |
| 2026-06-01 | Defer Go / Rust / JS / TS / others | Operator demand is the right validation cycle. Adding all languages preemptively adds maintenance for cases no operator has reported | Cover all major languages (rejected — over-scoped without operator validation) |

## Risks

| Risk | Mitigation |
|---|---|
| Allowlist misses a common name an operator reports | Operator reports are the right validation cycle; the lists are easy to extend |
| Per-language list over-flags a name that's project-specific (e.g. a project genuinely defines a method `process` that doesn't collide with Spring) | The flag is "verify with code_callhierarchy" trigger, not a verdict. False-positive cost is one extra verification call |
| File extension detection fails for files without standard extensions | Falls through to 0 (no allowlist hit); same as the "no allowlist for this language" branch. Operator can verify manually |

## Related Work

- Direct extension of `1316p-enh external-name-collision-stdlib-allowlist` to multi-language scope per operator direction 2026-06-01.
- Companion to `13190-enh class-module-merge-multi-language` and `13194-enh receiver-type-kotlin-and-csharp` — all three multi-language extensions land together in 1.2.1.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
