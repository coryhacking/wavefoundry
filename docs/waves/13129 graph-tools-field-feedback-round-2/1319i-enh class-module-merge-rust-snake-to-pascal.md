# Class/Module Merge — Extend to Rust (Snake-to-Pascal Convention)

Change ID: `1319i-enh class-module-merge-rust-snake-to-pascal`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Class/module merge was deferred for Rust because the file convention is snake_case (`foo.rs`) while type names are PascalCase (`struct Foo`). Adding case-aware conversion lets the merge apply to Rust's dominant idiom without breaking the exact-basename invariant for other languages.

## Approach

Extend the per-language merge detection with a snake_case → PascalCase conversion for Rust. For a file `foo_bar.rs` (basename `foo_bar`), the detection looks for a top-level type declaration whose name matches `FooBar`. Detection tries BOTH the snake-derived PascalCase AND the literal basename (some Rust crates use PascalCase file names directly).

Rust merge-eligible kinds: `struct`, `enum`, `trait`.

## Requirements

1. Rust added to `_CLASS_MODULE_MERGE_KINDS_BY_LANG` and `_CLASS_MODULE_MERGE_EXTS_BY_LANG`.
2. Per-language basename transformation — Rust uses snake-to-PascalCase. Detection tries both forms.
3. Tests: `foo_bar.rs` containing `struct FooBar` → merged. Plus literal `Foo.rs` containing `struct Foo` → merged. Plus mismatch (`foo.rs` containing `struct Bar`) → no merge.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Rust dispatch entry + basename-transformation logic.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — 3 regression tests.

**Out of scope:**

- Go merge (different feature — package=directory).
- Ruby merge (separate change `1319k`).

## Acceptance Criteria

- [x] AC-1: Rust entries added to dispatch tables.
- [x] AC-2: Snake-to-PascalCase derivation in the merge gate.
- [x] AC-3: Detection tries BOTH snake-derived AND literal basename.
- [x] AC-4: Fixture `foo_bar.rs` containing `struct FooBar` → merged.
- [x] AC-5: Fixture `Foo.rs` containing `struct Foo` → merged.
- [x] AC-6: Mismatch fixture → no merge.
- [x] AC-7: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add Rust dispatch entries + snake-to-Pascal transformation
- [x] Add 3 regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Dispatch foundation |
| AC-2 | required | Snake convention support |
| AC-3 | required | PascalCase fallback |
| AC-4 | required | Snake-case reproducer |
| AC-5 | required | PascalCase fixture |
| AC-6 | required | Negative case |
| AC-7 | required | No regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Try both snake-derived PascalCase AND literal basename | Some Rust projects use `Foo.rs` directly | Single-rule (rejected — excludes legitimate cases) |

## Risks

| Risk | Mitigation |
|---|---|
| File with multiple top-level types matching different forms | First match wins; tested |
| Rust grammar edge cases (`pub struct Foo<T>`, derives) | Tree-sitter handles via modifiers; detection works on the type_identifier child |

## Related Work

- Direct extension of `1316l`/`13190`/`13196` to Rust via convention-aware basename matching.
- Companion: `1319g`, `1319k`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
