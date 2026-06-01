# Class/Module Merge — Extend to Java, Kotlin, C#

Change ID: `13190-enh class-module-merge-multi-language`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

`1316l-enh graph-builder-swift-class-module-merge` shipped Swift-only with the explicit out-of-scope: *"Java / Kotlin / C# class/module merges. Same pattern applies but each language has its own edge cases."*

Operator direction 2026-06-01: extend the merge to Java, Kotlin, and C# now rather than deferring to a future wave. The 1316l detection (file basename == top-level type name) is language-agnostic; the edge cases cited in the original deferral (Java inner classes, Kotlin companion objects, C# multi-class files) **don't actually break the merge** — the basename-matching type merges; other top-level types in the same file remain as separate `<file>::<typename>` nodes.

Operator value: any consumer of `code_callhierarchy` / `code_impact` / `code_callgraph` / `code_graph_path` on a Java/Kotlin/C# codebase following the basename-per-file convention sees the unified node automatically. Constructor calls (`new Foo()` in Java/C#, `Foo()` in Kotlin) resolve correctly to incoming.

## Approach

Extend `_CLASS_MODULE_COLLAPSE_LANGUAGES` (graph_query.py) and the per-file extractor merge gate (graph_indexer.py) from Swift-only to a per-language table:

| Language | File extension | Merge kinds |
|---|---|---|
| Swift | `.swift` | `class`, `struct`, `actor`, `enum`, `protocol` |
| Java | `.java` | `class`, `interface`, `enum`, `record`, `annotation_type` |
| Kotlin | `.kt` | `class`, `interface`, `object`, `enum_class` |
| C# | `.cs` | `class`, `interface`, `struct`, `record`, `enum` |

Detection remains name-based: file basename (sans extension) == top-level type qname. No AST analysis beyond the existing kind classification.

The "exactly one top-level type" question handles itself naturally:
- File with one basename-matching type → merge.
- File with multiple top-level types where one matches basename → matching one merges; others remain separate.
- File with no basename-matching top-level type → no merge.

This matches Swift behavior and is operator-friendly for the multi-class Java/C# case.

## Requirements

1. **Per-language merge table** in graph_indexer.py extending `_CLASS_MODULE_COLLAPSE_LANGUAGES` with Java / Kotlin / C# entries and their respective kind sets.
2. **The `register_symbol` gate** uses the table to detect merge candidates per language (replacing the Swift-only inline check).
3. **`GRAPH_BUILDER_VERSION`** stays at 14 (no schema change beyond what 1316l already shipped).
4. **Existing 1316l tests** (`Java/C#/Kotlin files with basename-class patterns are NOT merged`) **flip to assert merge IS performed**. The original tests' assertions are inverted to lock in the multi-language behavior.
5. **New per-language end-to-end tests:** for each of Java, Kotlin, C#, write a basename-matching class file plus a caller file constructing it; assert the call resolves to the merged file id (mirrors the Swift Solaris reproducer).
6. **Forward-pointer note on 1316l** indicating multi-language extension shipped via this change.
7. **Files with multiple top-level types** where only one matches the basename: assert the basename-matching one merges and the others remain as `<file>::<typename>` nodes.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — replace Swift-only merge detection with the per-language table.
- `.wavefoundry/framework/scripts/graph_query.py` — extend `_CLASS_MODULE_COLLAPSE_LANGUAGES` for the (pre-v14) query-time view path.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — flip existing non-merge guards to merge assertions; add per-language end-to-end tests.

**Out of scope:**

- Multi-class-per-file aggregation (selecting "primary" type from multiple). Only basename-matching type merges; others remain separate.
- `extension`-only files (Swift extension declarations; no class-equivalent in other languages here).
- Nested types (inner classes). Top-level only.

## Acceptance Criteria

- [x] AC-1: `_CLASS_MODULE_COLLAPSE_LANGUAGES` covers `.swift`, `.java`, `.kt`, `.cs` with appropriate kind sets.
- [x] AC-2: Per-file extractor uses the table for merge detection (no Swift-only inline check).
- [x] AC-3: Java fixture: `Foo.java` containing `class Foo` → single merged node at `Foo.java` with `kind: "class"`, label `"Foo"`, `collapsed_pair: true`.
- [x] AC-4: Kotlin fixture: `Foo.kt` containing `class Foo` → merged.
- [x] AC-5: C# fixture: `Foo.cs` containing `class Foo` → merged.
- [x] AC-6: Per-language Solaris-reproducer test: a caller in another file constructing `new Foo()` (Java/C#) or `Foo()` (Kotlin) resolves to the merged file id.
- [x] AC-7: Multi-top-level-types file where only one matches basename: matching one merges; others remain as `<file>::<typename>` nodes.
- [x] AC-8: Existing 1316l per-language non-merge guards are flipped to assert merge IS performed.
- [x] AC-9: All wave 13129 baseline tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Replace Swift-only merge detection with per-language table
- [x] Extend `_CLASS_MODULE_COLLAPSE_LANGUAGES` for the query-time view path
- [x] Flip existing 1316l per-language non-merge tests
- [x] Add per-language end-to-end tests (Java + Kotlin + C# + multi-top-level guard)
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Detection table is the foundation |
| AC-2 | required | The extraction integration |
| AC-3 | required | Java coverage |
| AC-4 | required | Kotlin coverage |
| AC-5 | required | C# coverage |
| AC-6 | required | End-to-end reproducer parity with Swift |
| AC-7 | required | Multi-top-level guard |
| AC-8 | required | Regression flip — locks in the new behavior |
| AC-9 | required | No collateral breakage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Extend now via operator direction rather than deferring per the 1316l out-of-scope | The "edge cases" cited in the 1316l deferral (Java inner classes, Kotlin companion objects, C# multi-class files) don't actually break the merge — the basename-matching type merges; others remain as separate `<file>::<typename>` nodes. The detection is name-based and language-agnostic | Defer per 1316l out-of-scope (rejected per operator direction — same operator round-trip cycle; bundling avoids second rebuild) |
| 2026-06-01 | Multi-top-level file: matching type merges, others remain separate | Operator-friendly default. Java/C# multi-class files don't lose nodes; the basename-matching type still gets the unified-identity benefit | Skip merge when file has multiple top-level types (rejected — denies the benefit to operators following basename convention in mixed files) |

## Risks

| Risk | Mitigation |
|---|---|
| Java/Kotlin/C# fixtures hit a grammar edge case the Swift logic didn't (e.g. Kotlin `companion object` AST shape) | Per-language test fixtures explicitly cover the major declaration shapes. False-positive bias preserved — uncertain cases fall through to current behavior |
| `record` in Java/C# isn't in tree-sitter as expected | Verify during implementation; adjust the kind set if grammar differs |
| Kotlin `object Foo` declarations might warrant the merge but currently in a different code path | Include in the kind set; verify via test |

## Related Work

- Direct extension of `1316l-enh graph-builder-swift-class-module-merge` to multi-language scope per operator direction 2026-06-01.
- Companion to `13192-enh stdlib-allowlist-multi-language` and `13194-enh receiver-type-kotlin-and-csharp` — all three multi-language extensions land together in 1.2.1.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
