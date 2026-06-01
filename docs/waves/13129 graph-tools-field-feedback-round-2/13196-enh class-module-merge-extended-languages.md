# Class/Module Merge — Extend to JS, TS, Scala, PHP

Change ID: `13196-enh class-module-merge-extended-languages`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Operator direction 2026-06-01: extend class/module merge coverage to remaining supported languages where the file-named-after-type convention is dominant. `1316l`/`13190` shipped Swift/Java/Kotlin/C#. This change covers TypeScript, JavaScript, Scala, and PHP — all four follow the same name-match convention.

Go, Rust, and Ruby are intentionally excluded: their file-name convention is snake_case while the type name is PascalCase. The exact-basename-match invariant doesn't naturally apply without case translation, which would break the clean rule.

## Approach

Extend the per-language dispatch tables in `graph_indexer.py` (`_CLASS_MODULE_MERGE_KINDS_BY_LANG`, `_CLASS_MODULE_MERGE_EXT_BY_LANG`) with the four new languages and their type-declaration kinds.

The detection logic remains the same: file basename (sans extension) equals top-level type qname.

## Requirements

1. **Dispatch tables extended:**
   - JavaScript (`javascript` lang_key): extensions `.js`, `.jsx`, `.mjs`, `.cjs`; merge kinds `{class}` (JS function components default-exported by name also merge if the indexer classifies them as `class`).
   - TypeScript (`typescript` lang_key): extensions `.ts`, `.tsx`; merge kinds `{class, interface, type, enum}`.
   - Scala (`scala` lang_key): extension `.scala`; merge kinds `{class, object, trait, enum}`.
   - PHP (`php` lang_key): extension `.php`; merge kinds `{class, interface, trait}`.
2. **For multi-extension languages** (JS has 4, TS has 2): the dispatch checks if the file ends with ANY of the language's extensions and computes the basename accordingly.
3. **Existing Swift/Java/Kotlin/C# behavior preserved.**
4. **Tests** cover one merge fixture per new language + one regression that an unmatched-basename file does not merge.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — dispatch table extensions.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language regression tests.

**Out of scope:**

- Go, Rust, Ruby (file-name case convention mismatch).
- C++ (header/impl split — different concern).
- React component merging based on default export name (not basename) — defer.

## Acceptance Criteria

- [x] AC-1: Dispatch tables cover JS, TS, Scala, PHP with their respective extensions and kind sets.
- [x] AC-2: Multi-extension language detection (JS: .js/.jsx/.mjs/.cjs; TS: .ts/.tsx) works.
- [x] AC-3: Per-language fixtures show merged node at file id with `collapsed_pair: true`.
- [x] AC-4: Existing Swift/Java/Kotlin/C# tests pass without modification.
- [x] AC-5: 4+ new regression tests (one per language).

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extend dispatch tables
- [x] Update multi-extension basename computation
- [x] Add 4 regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Foundation |
| AC-2 | required | Multi-extension handling |
| AC-3 | required | Per-language coverage |
| AC-4 | required | No regression |
| AC-5 | required | Test coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Skip Go/Rust/Ruby | Their snake_case file names don't match PascalCase type names; would require case translation, breaking the clean exact-match invariant | Case-insensitive comparison (rejected — surprises operators in mixed-case cases); separate per-language naming rules (rejected — adds complexity for marginal benefit) |
| 2026-06-01 | TypeScript includes `type` and `enum` | TS type aliases and enums are commonly the dominant export when the file is named after them | Class/interface only (rejected — TS idiom uses `type Foo = {...}` patterns extensively) |
| 2026-06-01 | PHP follows PSR-4 strongly | PSR-4 mandates one class per file basename matching. Merge is almost always operator-correct | Per-namespace handling (rejected — PSR-4 already handles this) |

## Risks

| Risk | Mitigation |
|---|---|
| Multi-class TS files (rare) get partial merge | Same as Java/C#: basename-matching type merges; others remain separate. Operator-friendly |
| React component class kind classification varies by JSX heuristic | Tests cover the common `class Foo extends React.Component` shape; default exports of arrow functions don't have kind=class so don't merge |
| Scala companion objects (`class Foo` + `object Foo`) | Both register; basename match applies to the class (or whichever the extractor classifies first). Multi-symbol coexistence is fine |

## Related Work

- Direct extension of `1316l`/`13190` to remaining supported languages with strong file-named-after-type convention.
- Companion: `13198-enh stdlib-allowlist-extended-languages`, `1319a-enh receiver-type-go-rust-scala`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
