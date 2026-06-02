# Class/Module Merge — Single-Dominant-Class Convention (Python, JavaScript, TypeScript)

Change ID: `1319o-enh class-module-merge-python-dominant-class`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Wave 13129 deferred Python, JavaScript, and TypeScript from the class/module merge family because each permits **many top-level classes per file** — Python's `utils.py` containing `Foo`, `Bar`, `Baz`; a JS module exporting multiple classes; a TS module with several exports. Basename-match merge (the model used for Java/Kotlin/C#/Swift/Scala/PHP/Rust/Ruby) would over-trigger if applied naively.

However, a meaningful subset of each language's codebases follows a **single-dominant-class convention**: one top-level class whose name matches the file basename, with module-level helpers acting as adjuncts:

- **Python** — `foo_bar.py` containing exactly one `class FooBar`. Django models, dataclass modules, SQLAlchemy ORM files, Pydantic schema files all follow this.
- **JavaScript** — `FooBar.js` (or `foo-bar.js`) with one `export default class FooBar` plus helper functions. Common in React components, Node service modules, ES-module-organized libraries.
- **TypeScript** — same as JS but typed; even stronger convention because TS encourages explicit module-level structure. `FooBar.ts` with `export class FooBar`.

When the convention holds, merging behaves correctly. When it doesn't (a multi-class utility module), the merge must skip. **A conservative dominance gate** — merge only when the file has exactly one top-level class declaration AND the class name matches the basename (with per-language case-convention conversion) — covers all three languages with one mechanism.

Operator direction during prepare value review: this is the **same structural pattern across three languages** and shipping per-language one-at-a-time would force per-project reports to drive scope expansion. Cross-language scope from the start is the right structural fix.

## Approach

Mirror the Rust extension (`1319i`) for Python/JS/TS with one shared precondition (dominance gate) and per-language case-convention handling:

1. **Dominance check** — count top-level class declarations. If the count is not exactly 1, skip merge. Functions, constants, type aliases, and module-level statements are ignored — they're not class definitions and don't block the merge.

2. **Per-language detection of "top-level class":**

| Language | AST node | "Top-level" definition |
|---|---|---|
| **Python** | `class_definition` | Directly under `module` (not nested inside another class or function) |
| **JavaScript** | `class_declaration` AND `class` expression in `export default` | Directly under `program` or wrapped in `export_statement` / `export_default_declaration` |
| **TypeScript** | `class_declaration` AND `abstract_class_declaration` AND `class` in `export default` | Directly under `program` or wrapped in `export_statement` |

3. **Basename match with per-language case conventions:**

| Language | File-naming convention | Match strategy |
|---|---|---|
| **Python** | snake_case typical (`foo_bar.py`), PascalCase also legal (`Foo.py`) | Try both snake-derived PascalCase (`foo_bar` → `FooBar`) AND literal basename (`foo_bar` matches `class foo_bar`); class name match wins either form |
| **JavaScript** | PascalCase common (`FooBar.js`), kebab-case also common (`foo-bar.js`), camelCase rare | Try literal basename, PascalCase-from-kebab (`foo-bar` → `FooBar`), and PascalCase-from-snake (`foo_bar` → `FooBar`) |
| **TypeScript** | Same as JS — PascalCase typical, kebab-case common | Same matching strategy as JS |

4. **Extensions:** `.py` (Python), `.js`/`.mjs`/`.cjs` (JavaScript), `.ts`/`.tsx`/`.mts`/`.cts` (TypeScript). `.pyi` Python stubs out of scope.

5. **TSX/JSX special case** — React component files often have one default-export class component with the file matching basename. Same dominance gate applies. The component class is the dominant top-level class; helper functions/constants don't block.

## Requirements

1. Python, JavaScript, TypeScript added to `_CLASS_MODULE_MERGE_KINDS_BY_LANG` and `_CLASS_MODULE_MERGE_EXTS_BY_LANG`.
2. New `_CLASS_MODULE_MERGE_DOMINANCE_GATE_LANGS = frozenset({"python", "javascript", "typescript"})` controls the "exactly one top-level class" precondition. Other merge-family languages continue to merge on basename match alone (their language conventions enforce one-class-per-file).
3. Per-language top-level-class detection helpers (`_count_top_level_classes_<lang>`).
4. Per-language basename-match strategy (Python: snake-to-Pascal + literal; JS/TS: literal + snake-to-Pascal + kebab-to-Pascal).
5. Shared snake-to-PascalCase derivation (from `1319i`) reused; new kebab-to-PascalCase helper for JS/TS.
6. Per-language regression tests covering positive, negative, and edge cases per the AC table.

## Scope

**Problem statement:** Python, JavaScript, and TypeScript are the three popular languages still without merge coverage. Each has a meaningful single-dominant-class convention in real codebases. The current per-file fragmented view produces a two-node (file + class) representation when a unified node is more natural for operators thinking in component/model/schema-level terms.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Python/JS/TS dispatch entries + per-language top-level-class detection + per-language basename-match strategy + dominance-gate logic.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language regression tests.

**Out of scope:**

- Python `.pyi` stub files.
- Nested classes (outer class still wins basename match if it's the only top-level class).
- JavaScript prototype-style "classes" (`function Foo() { ... }; Foo.prototype.bar = ...`) — only `class` syntax recognized.
- TypeScript `namespace { class Foo { } }` patterns — namespaces are a different grouping primitive; merge applies to top-level (program-direct or export-wrapped) classes only.
- Semantic recognition of dataclass / `@Component` / `extends React.Component` — the dominance gate is structural, not semantic.
- Multi-class modules with one "primary" class plus helpers (would require heuristics — out of scope).
- ES module `export * from './foo'` re-export aggregation — files with no declarations only re-exports aren't class-merge-eligible regardless.
- JSX/TSX function components (`const Foo = () => ...`) — only class components in this scope; function components are a different idiom and warrant their own design pass.

## Acceptance Criteria

**Core (shared across all three languages):**

- [x] AC-1: Python, JavaScript, TypeScript entries added to dispatch tables.
- [x] AC-2: Dominance gate skips merge when top-level class count != 1 across all three languages.
- [x] AC-3: Per-language top-level-class detection respects language-specific definitions of "top-level" (program-direct or export-wrapped).
- [x] AC-4: Module-level non-class items (functions, constants, type aliases, statements) do not block merge.

**Python:**

- [x] AC-5: Python — `foo_bar.py` with one class `FooBar` → merged (snake-derived PascalCase branch).
- [x] AC-6: Python — `foo_bar.py` with one class `foo_bar` → merged (literal basename branch).
- [x] AC-7: Python — `Foo.py` with one class `Foo` → merged.
- [x] AC-8: Python — `utils.py` with classes `A`, `B`, `C` → NOT merged.
- [x] AC-9: Python — `foo_bar.py` with class `FooBar` plus module-level functions → merged.
- [x] AC-10: Python — `foo_bar.py` with class `Bar` (basename mismatch) → NOT merged.

**JavaScript:**

- [x] AC-11: JavaScript — `FooBar.js` with one `class FooBar` → merged (literal basename match).
- [x] AC-12: JavaScript — `foo-bar.js` with one `class FooBar` → merged (kebab-to-PascalCase branch).
- [x] AC-13: JavaScript — `foo_bar.js` with one `class FooBar` → merged (snake-to-PascalCase branch).
- [x] AC-14: JavaScript — `utils.js` with multiple top-level classes → NOT merged.
- [x] AC-15: JavaScript — `FooBar.js` with `class FooBar` plus helper functions → merged.
- [x] AC-16: JavaScript — `FooBar.js` with default export wrapping the class (`export default class FooBar { }`) → merged (export-wrapped top-level detection).
- [x] AC-17: JavaScript — `FooBar.js` with class `Baz` (basename mismatch) → NOT merged.

**TypeScript:**

- [x] AC-18: TypeScript — `FooBar.ts` with one `export class FooBar` → merged.
- [x] AC-19: TypeScript — `foo-bar.ts` with one `class FooBar` → merged (kebab branch).
- [x] AC-20: TypeScript — `FooBar.tsx` (React component class) with class component plus helper hooks → merged.
- [x] AC-21: TypeScript — abstract class `abstract class FooBar` (counts toward dominance) → merged when name matches.
- [x] AC-22: TypeScript — `utils.ts` with multiple top-level classes → NOT merged.
- [x] AC-23: TypeScript — `FooBar.ts` with `namespace Foo { class FooBar { } }` (namespace-nested) → NOT merged at top level (out-of-scope namespace pattern).

**Safety / regression:**

- [x] AC-24: All existing graph-builder tests pass.
- [x] AC-25: Existing per-language merge coverage (Java/Kotlin/C#/Swift/Scala/PHP/Rust/Ruby) unchanged by the new dominance-gate-language addition.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Python/JS/TS dispatch entries + dominance-gate language set
- [x] Implement per-language top-level-class detection helpers
- [x] Implement per-language basename-match strategy (including kebab-to-PascalCase helper)
- [x] Add per-language regression tests covering positive, negative, edge cases
- [x] Run framework tests
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

- N/A — extends an existing pattern at the same architectural layer as `1319i`/`1319k`. No boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Dispatch foundation |
| AC-2 | required | Idiom safety across all three |
| AC-3 | required | Per-language top-level definition |
| AC-4 | required | Functions-don't-block invariant |
| AC-5 | required | Python — common Django/Pydantic case |
| AC-6 | important | Python — snake-class-name edge |
| AC-7 | required | Python — PascalCase file branch |
| AC-8 | required | Python — negative case (multi-class) |
| AC-9 | required | Python — helper functions don't block |
| AC-10 | required | Python — basename mismatch negative |
| AC-11 | required | JS — PascalCase file convention |
| AC-12 | required | JS — kebab-case convention |
| AC-13 | important | JS — snake-case convention (less common) |
| AC-14 | required | JS — negative case |
| AC-15 | required | JS — helper functions don't block |
| AC-16 | required | JS — export-wrapped top-level detection |
| AC-17 | required | JS — basename mismatch negative |
| AC-18 | required | TS — primary TS case (export class with PascalCase file) |
| AC-19 | required | TS — kebab convention |
| AC-20 | required | TS — React component class case (TSX) |
| AC-21 | required | TS — abstract class support |
| AC-22 | required | TS — negative case |
| AC-23 | required | TS — namespace-nested out-of-scope guard |
| AC-24 | required | No baseline regression |
| AC-25 | required | Non-interference with existing merge-language coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Broaden from Python-only to Python + JavaScript + TypeScript | Operator direction during prepare value review: same structural pattern (single-dominant-class with multi-class-permitting language) across three languages. Per-language one-at-a-time would fragment implementation; cross-language scope from start is the right fix | Python-only (rejected — narrow speculative scope, would force per-language reports later); JS+TS only (rejected — Python has the strongest convention via Django/Pydantic adoption); all languages with dominance gate (rejected — Java/Kotlin/C#/Swift/Scala/PHP/Rust/Ruby don't need it because their conventions already enforce one-class-per-file) |
| 2026-06-01 | Dominance gate (exactly-one-class) is per-language opt-in via `_CLASS_MODULE_MERGE_DOMINANCE_GATE_LANGS` set | Some languages enforce one-class-per-file by convention/language rules and don't need the gate; Python/JS/TS permit multi-class files and need it | Apply gate to all merge languages (rejected — over-strict; would break existing Java/Kotlin/C# coverage where multi-class files are rare but legal); per-language separate flag (rejected — internal implementation detail, not operator-facing) |
| 2026-06-01 | Functions/constants/type-aliases don't count toward dominance | Module-level helpers are normal adjuncts to a class file; counting them would defeat the purpose | Count everything top-level (rejected — would block legitimate Django-model and React-component files) |
| 2026-06-01 | Multiple basename-match strategies per language (snake-to-Pascal + literal + kebab-to-Pascal for JS/TS) | Each language has multiple legitimate file-naming conventions; checking multiple strategies catches the dominant cases without expanding the merge to false positives | Single strategy per language (rejected — would miss `foo-bar.js` → `class FooBar` case, very common in modern JS) |
| 2026-06-01 | Function components (`const Foo = () => {}`) out of scope | Function components are a different idiom (not class declarations); the AST shape is `variable_declaration` with arrow function, not `class_declaration`. A function-component dominance gate is a separate design pass | Include function components (rejected — different AST shape, different idiom; conflating the two would muddy the merge semantics) |

## Risks

| Risk | Mitigation |
|---|---|
| Python files with one class + many top-level constants/dataclass instances merge anyway | Documented; dominance gate is structural by design — constants don't count |
| `pytest` fixture modules with `class TestFoo` patterns merge unexpectedly | Test files already excluded by framework conventions; if not, add filter |
| Python `__init__.py` files with re-exported class | basename is `__init__`; doesn't match any class name — naturally skipped |
| JS/TS files with default export as a class expression (`export default class extends Base { }` — anonymous class) | Anonymous classes have no name to match basename; naturally skipped |
| TypeScript declaration files (`.d.ts`) with multiple ambient declarations | `.d.ts` files are typically declaration-only and wouldn't carry merge value; consider explicit exclusion |
| Mixed-convention codebases (some files kebab-case, some PascalCase) trigger merge on some but not others | Documented; per-file detection is the right granularity — operators see consistent behavior for files matching either convention |
| React-component files mixing class and function components in the same file | Dominance gate counts only class declarations; function components don't block. If a file has one class component + multiple function components, the class merges with the file. Acceptable per AC-20 rationale |

## Related Work

- Closes the Python, JavaScript, TypeScript gap left by `13190`/`13196`. Final basename-match coverage for the popular merge-deferred languages.
- Broadened from the Python-only proposal during wave-131bt prepare value review per operator direction.
- Companion to `1319m` (cross-language directory aggregation) — for Python/JS/TS projects, `1319o` collapses class-into-module within a file, and `1319m` (when applicable per its scope) collapses module-into-package within a directory. Both opt-in.
- Reuses the snake-to-PascalCase helper from `1319i` (Rust merge); adds a new kebab-to-PascalCase helper.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
