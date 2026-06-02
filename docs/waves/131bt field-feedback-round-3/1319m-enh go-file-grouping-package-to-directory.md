# Directory Aggregation — Cross-Language Package/Namespace Collapse

Change ID: `1319m-enh go-file-grouping-package-to-directory`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Wave 13129 deferred Go from the class/module merge family because Go's grouping model fundamentally differs — Go uses a directory-as-package-boundary model, while the merge family uses a file-as-type-boundary model. Operator direction during prepare: rather than treating this as a Go-only gap, recognize that the **directory-as-grouping-unit pattern is broadly applicable across the languages wavefoundry supports** and ship the cross-language version.

The pattern exists, in varying strengths, across eight of the supported languages:

**Strict (language-enforced):**
- **Go** — `package` declaration must match directory; compiler-enforced
- **Python** — package = directory containing `__init__.py`; enforced by the import system

**Strong by convention (widespread tooling/build-system enforcement):**
- **Java** — `package` declaration; Maven/Gradle expect directory match
- **Kotlin** — `package` declaration; Gradle expects directory match
- **C#** — `namespace` declaration + project-file convention
- **Scala** — `package` declaration + sbt convention
- **PHP** — `namespace` declaration + PSR-4 autoloading
- **Swift** — module = build target; Xcode/SPM build-system convention

**Excluded:**
- **Rust** — `mod` tree (inline or `foo.rs` / `foo/mod.rs`); module-tree-shaped, not strictly directory-based. Skip.
- **Ruby** — `module` is a namespace declaration, not directory-bound. Skip.
- **JavaScript / TypeScript** — no package concept beyond ES modules. Skip.

Operator-value case: in any project using one of the eight covered languages, a deep directory hierarchy fragments graphs into per-file nodes when operators conceptually think in packages/namespaces. The directory-aggregation flag collapses files into one node per directory-grouping unit, complementing the existing `collapse_class_module_pairs` (intra-file class+file merge) — they stack: classes → files → packages.

## Approach

A new graph-level transformation, applied as a sibling to `collapse_class_module_pairs`:

1. **Per-language detection of the grouping unit** — for each candidate language, parse the relevant declaration node and group files by the detected unit:

| Language | Grouping signal | Detection rule |
|---|---|---|
| **Go** | `package <name>` declaration (`package_clause`) | All `.go` files in a directory sharing the same package name → one candidate group |
| **Python** | `__init__.py` presence | Every directory containing `__init__.py` (or its subdirectories without their own `__init__.py`) → one candidate group |
| **Java** | `package <fqn>;` declaration (`package_declaration`) | All `.java` files in a directory sharing the same FQN → one candidate group |
| **Kotlin** | `package <fqn>` declaration (`package_header`) | All `.kt` files in a directory sharing the same FQN → one candidate group |
| **C#** | `namespace <fqn> { ... }` declaration (`namespace_declaration`) | All `.cs` files in a directory sharing the same namespace → one candidate group |
| **Scala** | `package <fqn>` declaration (`package_clause`) | All `.scala` files in a directory sharing the same package → one candidate group |
| **PHP** | `namespace <fqn>;` declaration (`namespace_definition`) | All `.php` files in a directory sharing the same namespace → one candidate group |
| **Swift** | Build-target convention (no in-source declaration) | All `.swift` files in a directory → one candidate group (build-system info not parsed; convention-based) |

2. **Eligibility gate per group** — collapse only when:
   - At least 2 files in the group (single-file directories skipped)
   - All files in the directory agree on the grouping unit (mixed-package/mixed-namespace directories skip with a diagnostic — rare but legal in some languages)
   - For Swift: at least 2 `.swift` files; convention only (no declaration parsing required)

3. **Merge** — produce a single `kind: "package"` (or `kind: "namespace"` for C#/PHP — preserves language idiom) node per directory grouping. Absorb constituent file nodes; re-attribute their declarations and edges to the package/namespace node. Preserve `path` as the directory path; preserve `name` as the detected grouping unit (e.g., `com.example.foo` for Java, `Example\Foo` for PHP, or the directory basename for Swift).

4. **Edge rewrite** — incoming edges from outside the package retarget to the package node; intra-package edges between merged files collapse. Mirrors `_collapse_class_module_pairs` pattern.

5. **Opt-in flag** — new `wave_graph_report` parameter `collapse_package_to_directory: bool = False` (default off, matching the cautious rollout of `collapse_class_module_pairs`). Single flag covers all eight languages — per-language behavior driven by automatic detection, not separate flags per language.

6. **Diagnostic fields on collapsed nodes:**
   - `collapse_origin_files: list[str]` — absorbed file paths
   - `collapse_unit: str` — detected grouping unit (e.g., `"com.example.foo"`, `"Example\\Foo"`, directory basename for Swift)
   - `collapse_lang: str` — source language for the group

## Requirements

1. New collapse helper in `graph_indexer.py` (or a new `graph_collapse.py` module) implementing cross-language directory-aggregation per the detection table.
2. Per-language declaration extractors using tree-sitter AST queries — one helper per supported language for `package`/`namespace` detection; Python uses filesystem detection (`__init__.py`); Swift uses directory-presence detection only.
3. New `wave_graph_report` parameter `collapse_package_to_directory: bool = False`. Full MCP server restart required to expose at protocol layer (FastMCP wrapper-signature-cache limitation).
4. Diagnostic fields on collapsed nodes (`collapse_origin_files`, `collapse_unit`, `collapse_lang`).
5. Per-language regression tests: multi-file matching-unit → collapse; single-file → no collapse; mixed-unit → skip with diagnostic; cross-package edges retarget correctly.
6. seed-211 / `wave_graph_report` doc updates describing the parameter and per-language coverage.

## Scope

**Problem statement:** Eight of the supported languages have meaningful directory-as-grouping-unit semantics. Operators reading their graphs see per-file fragmentation when they conceptually think in packages/namespaces. No flag currently exposes the aggregated view.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` (or new `graph_collapse.py`) — cross-language collapse implementation with per-language detection.
- `.wavefoundry/framework/scripts/server_impl.py` — `wave_graph_report` parameter wiring.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language collapse regression tests (8 languages × {multi-file, single-file, mixed-unit, cross-package} = ~32 test cases minimum).
- `.wavefoundry/framework/seeds/` — `wave_graph_report` parameter doc update covering all eight languages.

**Out of scope:**

- Rust `mod` tree aggregation. Rust module trees are not strictly directory-bound (inline `mod foo { }` is common); a Rust-shaped feature is a separate change.
- Ruby module aggregation. Ruby modules are namespace declarations, not directory-bound; a Ruby-shaped feature is a separate change.
- JS / TS module aggregation. No package concept beyond ES modules; a feature for these would be ES-module-shape-specific.
- Cross-package symbol resolution improvements. This change is graph-structure-only.
- Build-system parsing for Swift (reading `Package.swift` or `.xcodeproj`). Swift uses directory-presence detection only; explicit build-target boundaries are deferred.
- Auto-detection of the right collapse level (i.e., decide for the operator whether to collapse). Operator opts in via the flag.

## Acceptance Criteria

**Core:**

- [x] AC-1: New collapse helper produces one package/namespace node per detected directory grouping for the eight in-scope languages.
- [x] AC-2: `wave_graph_report(collapse_package_to_directory=True)` returns a graph with directory-aggregated nodes; default off behavior unchanged.
- [x] AC-3: Collapsed nodes carry `collapse_origin_files`, `collapse_unit`, `collapse_lang` diagnostic fields.
- [x] AC-4: Intra-package edges between merged files are absorbed; cross-package edges retarget to the package node.

**Per-language coverage:**

- [x] AC-5: Go — multi-file directory with matching `package <name>` declarations collapses; mixed-package directories skip with diagnostic.
- [x] AC-6: Python — directory with `__init__.py` collapses; subdirectories without their own `__init__.py` join the parent; single-file packages skipped.
- [x] AC-7: Java — multi-file directory with matching `package <fqn>;` declarations collapses.
- [x] AC-8: Kotlin — multi-file directory with matching `package <fqn>` declarations collapses.
- [x] AC-9: C# — multi-file directory with matching `namespace <fqn>` declarations collapses. Nested namespace block (`namespace A.B { namespace C { ... } }`) uses the innermost declaration.
- [x] AC-10: Scala — multi-file directory with matching `package <fqn>` declarations collapses.
- [x] AC-11: PHP — multi-file directory with matching `namespace <fqn>;` declarations collapses.
- [x] AC-12: Swift — multi-file directory collapses on convention (no declaration parsing); single-file directories skipped.

**Safety / edge cases:**

- [x] AC-13: Single-file directories are never collapsed (no value, would create noise).
- [x] AC-14: Mixed-package/mixed-namespace directories skip collapse and surface a diagnostic.
- [x] AC-15: Excluded languages (Rust, Ruby, JS, TS) are unchanged by the flag — graph output identical with flag on/off when only excluded-language files exist.
- [x] AC-16: Flag default `False` — no behavior change for operators not opting in.
- [x] AC-17: All existing graph-builder tests continue to pass (no default-behavior regression).
- [x] AC-18: Stacks cleanly with `collapse_class_module_pairs` — both flags on produces classes → files → packages collapse chain.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Phase 0a — per-language AST audit: for each of the seven declaration-parsing languages, identify the tree-sitter node and field paths for extracting the grouping unit. Record in Decision Log. *(Recorded inline in the per-language extractor implementations rather than as a separate audit artifact; per-language regression tests covering Go/Python/Java/Kotlin/C#/Scala/PHP/Swift pin the contract.)*
- [x] Phase 0b — Python `__init__.py` detection: implement filesystem walker; verify behavior on PEP 420 namespace packages (directories without `__init__.py` but containing Python files — out of scope, but verify they're correctly skipped). *(Implemented; PEP 420 namespace packages skip collapse silently per AC-6 — design accepted.)*
- [x] Implement per-language declaration extractors
- [x] Implement directory grouping + collapse transformation
- [x] Wire `wave_graph_report` parameter
- [x] Add per-language regression tests (multi-file, single-file, mixed-unit fixtures per language)
- [x] Update `wave_graph_report` seed doc with parameter and per-language coverage
- [x] Run framework tests
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — graph collapse pipeline now has two flag-gated transformations (class-module-pairs + package-to-directory) that stack.
- `docs/architecture/decisions/` — consider an ADR for "directory-as-grouping-unit" as a separate primitive from basename-match merge, plus the cross-language coverage decision (eight languages now, Rust/Ruby/JS/TS deliberately excluded with reasoning).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core collapse foundation |
| AC-2 | required | Operator surface |
| AC-3 | required | Observability parity with `collapse_class_module_pairs` |
| AC-4 | required | Edge correctness |
| AC-5 | required | Go — original scope |
| AC-6 | required | Python — strict directory-grouping language |
| AC-7 | required | Java — broadest enterprise reach |
| AC-8 | required | Kotlin — Android / server-side parity |
| AC-9 | required | C# — namespace-declaration variant |
| AC-10 | required | Scala — package-clause parity |
| AC-11 | required | PHP — namespace + PSR-4 parity |
| AC-12 | required | Swift — convention-only parity |
| AC-13 | required | Single-file safety |
| AC-14 | required | Mixed-package safety |
| AC-15 | required | Excluded-language non-interference |
| AC-16 | required | Default-off non-regression |
| AC-17 | required | No baseline regression |
| AC-18 | required | Stackable collapse — operator-facing composition |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Broaden from Go-only to eight-language directory aggregation | Operator direction during prepare value review: directory-as-grouping-unit pattern is broadly applicable across supported languages; shipping Go-only would force per-language reports to each drive their own scope expansion later. Single cross-language implementation is the right structural fix | Go-only (rejected — narrow speculative scope makes the same case for every future report); per-language separate changes (rejected — same helper, fragmented implementation) |
| 2026-06-01 | Exclude Rust, Ruby, JS, TS | Rust uses module-tree (not strictly directory-bound); Ruby modules are namespace declarations not directory-bound; JS/TS have no package concept beyond ES modules. Each would need a meaningfully different feature shape | Cover all 12 languages with whatever shape fits (rejected — dilutes the directory-aggregation concept; mixed semantics across languages is worse than honest exclusion) |
| 2026-06-01 | Single `collapse_package_to_directory: bool` flag covers all eight languages | Operator-facing simplicity; per-language detection happens automatically | Per-language flag (`collapse_go_packages`, etc.) (rejected — eight flags is operator-noise; single flag with automatic per-language detection is the right abstraction) |
| 2026-06-01 | Swift uses convention-only detection (no build-target parsing) | Build-system parsing (`Package.swift` / `.xcodeproj`) is meaningful additional implementation cost; directory-presence as proxy for module is the 90% correct case | Parse build-system files (rejected — adds platform-specific tooling dependencies); skip Swift (rejected — Swift's module-as-directory convention is strong enough to support convention-only) |
| 2026-06-01 | Kind preserves language idiom (`"package"` for Go/Python/Java/Kotlin/Scala/Swift; `"namespace"` for C#/PHP) | Operators reading graph queries see the language-native term; avoids forcing a foreign vocabulary | Unified `kind: "package"` across all eight (rejected — C#/PHP operators expect "namespace" terminology) |
| 2026-06-01 | Per-language AST node paths recorded inline in the extractor implementations | Per-language regression tests pin the AST contract per language; a separate audit artifact would have decayed faster than the tests; the implementations themselves are the durable record | Standalone audit doc (rejected — duplicates the impl as a reference, drifts) |
| 2026-06-01 | PEP 420 namespace packages skip collapse silently | Detection key (`__init__.py` presence) intentionally excludes PEP 420; silent skip preserves the explicit-package convention without surfacing a noisy diagnostic for the common case of test fixture/script directories | Surface a `pep420_namespace_skipped` diagnostic (rejected — would fire on most fixture/script directories and pollute the response) |

## Risks

| Risk | Mitigation |
|---|---|
| Large monorepos in any of the eight languages produce few but very-large package nodes; readability could regress | Default off; document trade-off in `wave_graph_report` seed; operators can experiment on smaller subgraphs first |
| Mixed-package directories (rare but legal in some languages — e.g., Java with `package-info.java` annotations) trigger the skip path more often than expected | Diagnostic surfaces the skip reason; operators see "mixed-unit detected" and understand why their directory didn't collapse |
| C# `namespace A.B { namespace C { ... } }` nested-namespace files within one source file | Use innermost namespace declaration; document in AC-9 |
| Swift convention-based detection (no declaration parsing) over-aggregates when one directory has multiple unrelated targets (rare but possible in deeply customized Xcode setups) | Convention is the 90% case; operators with build-system-shaped grouping use a future build-system-parsing change |
| Python PEP 420 namespace packages (no `__init__.py` but containing Python files) skip collapse silently | Phase 0b decides: graceful skip (current design) or surface a diagnostic. Documented in Decision Log when resolved |
| `_collapse_class_module_pairs` + `collapse_package_to_directory` interaction produces unexpected stacked output | AC-18 explicit test for the stacking; documented in seed |
| FastMCP wrapper-signature cache prevents the new parameter from appearing until full MCP restart | Document restart requirement in changelog entry's required-action callout (same limitation as `collapse_class_module_pairs`) |
| Per-language detection logic spreads across eight implementations and drifts over time | Single shared collapse helper with language-specific extractors; per-language tests catch drift |

## Related Work

- Sibling to `1312h-enh collapse-class-module-pairs` (shipped in 13129) — same flag-gated, query-time-view shape. Stacks: class → file (via 1312h) → package/namespace (via this change).
- Broadened from the Go-only proposal during wave-131bt prepare value review per operator direction.
- Related to `1319o` (Python single-dominant-class merge) — for Python projects, `1319o` collapses class-into-module within a file, and this change collapses module-into-package within a directory. Both opt-in.
- No direct dependency on `1319s` (construction edges) or `131ar` (description sync).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
