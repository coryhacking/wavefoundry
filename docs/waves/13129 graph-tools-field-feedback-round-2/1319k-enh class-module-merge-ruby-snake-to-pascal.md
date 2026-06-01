# Class/Module Merge — Extend to Ruby (Snake-to-Pascal Convention)

Change ID: `1319k-enh class-module-merge-ruby-snake-to-pascal`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Class/module merge was deferred for Ruby for the same reason as Rust — Ruby's file convention is snake_case (`foo.rb`) while class names are PascalCase (`class Foo`). The same snake-to-Pascal conversion (`1319i`) applies cleanly.

## Approach

Mirror the Rust extension (`1319i`) for Ruby. Ruby merge-eligible kinds: `class`, `module` (Ruby's module is a namespace primitive; when it's the dominant top-level construct in `foo.rb`, the merge applies). Detection tries both snake-derived PascalCase and literal basename.

## Requirements

1. Ruby added to `_CLASS_MODULE_MERGE_KINDS_BY_LANG` (`{class, module}`) and `_CLASS_MODULE_MERGE_EXTS_BY_LANG` (`.rb`).
2. Shared snake-to-PascalCase basename transformation (from `1319i`) covers Ruby identically.
3. Tests: `foo_bar.rb` containing `class FooBar` → merged. Plus `Foo.rb` containing `class Foo` → merged. Plus mismatch → no merge.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Ruby dispatch entries.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — 3 regression tests.

**Out of scope:**

- Ruby `module` namespace nesting (multiple modules per file).
- Mixin / inclusion patterns.

## Acceptance Criteria

- [x] AC-1: Ruby entries added to dispatch tables.
- [x] AC-2: Snake-to-PascalCase derivation works for Ruby (shared logic with `1319i`).
- [x] AC-3: Fixture `foo_bar.rb` containing `class FooBar` → merged.
- [x] AC-4: Fixture `Foo.rb` containing `class Foo` → merged.
- [x] AC-5: Mismatch fixture → no merge.
- [x] AC-6: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Ruby dispatch entries
- [x] Add 3 regression tests
- [x] Run framework tests
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Dispatch foundation |
| AC-2 | required | Snake convention support |
| AC-3 | required | Snake-case reproducer |
| AC-4 | required | PascalCase fixture |
| AC-5 | required | Negative case |
| AC-6 | required | No regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Include `module` kind | Ruby modules are commonly the top-level construct in a `module_name.rb` file | Class only (rejected — excludes namespace modules) |
| 2026-06-01 | Reuse the snake-to-Pascal transformation from `1319i` | Single implementation; consistent behavior | Per-language transformations (rejected — duplicates logic) |

## Risks

| Risk | Mitigation |
|---|---|
| Ruby files with multiple top-level classes | Same as Java/C# multi-top-level — basename-match wins |
| `class Foo < Bar` inheritance | Tree-sitter Ruby produces `class` node regardless |

## Related Work

- Direct extension of `1316l`/`13190`/`13196`/`1319i` to Ruby.
- Companion: `1319g`, `1319i`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
