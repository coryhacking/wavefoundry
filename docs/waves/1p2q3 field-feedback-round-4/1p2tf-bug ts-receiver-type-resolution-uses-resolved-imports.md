# TypeScript Receiver-Type Resolution Uses Resolved Imports

Change ID: `1p2tf-bug ts-receiver-type-resolution-uses-resolved-imports`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Teton field validation against 1.3.6+p2t6 surfaces the per-language attribution diagnostic shipped in [[1p2q9]] B and reveals that the TypeScript receiver-resolved share on their 12,301-node strict-TS Nx monorepo is **4.3%** — 1,600 type-resolved edges (851 `RECEIVER_RESOLVED` + 749 `CONSTRUCTION_RESOLVED`) out of 37,125 total TS edges, with 35,525 falling through to `EXTRACTED`. The codebase uses strict TS with native annotations on substantially every interface and function signature; a 4.3% rate is not the expected language-default behavior.

Trace of why our shipped fixes don't close this gap:

1. The [[1p2q9]] A tsconfig.paths alias resolution shipped in 1.3.6 binds `imports` edges from `@aceiss/foo` syntax to the resolved project file. That part works — `wave_graph_report` chokepoints no longer surface those imports as `external::*`.
2. But the receiver-type resolver at `_resolve_ts_call_target` (graph_indexer.py:3490) extracts the receiver's type name as a *string* (e.g. `"Foo"`), then does a per-file `symbol_lookup[f"Foo.{method_name}"]` check. When `Foo` was imported from `@aceiss/lib`, the per-file `symbol_lookup` does NOT contain `Foo` — it only contains symbols defined IN this file. The resolver falls through to `external::Foo.method`.
3. The cross-file rewrite pass at line 5420 then promotes ambiguous `external::Foo.method` to a project node *only if* `Foo.method` is unambiguous across all project nodes. On a 12K-node monorepo with names like `select` / `useState` / etc., ambiguity drops most edges.

Result: the receiver-type resolver knows the type name, the import resolver knows where the type comes from, but the two never meet at the call site. **The aliased-import resolution we shipped resolves imports but doesn't propagate the resolved binding into the type-name → class-id lookup.**

Operator-facing impact: `code_callhierarchy`, `code_impact`, and `code_definition` understate blast radius systematically on aliased-import-heavy TS codebases. The fallback rule shipped in [[1p2q9]] E (response-shape coverage-gap interpretation) corrects reviewer behavior on empty results, but the underlying graph still under-attributes the majority of typed calls.

## Approach

Plumb each TS file's resolved-import map into receiver-type resolution. When the call walker sees `foo.bar()` where `foo: Foo` and `Foo` was imported from `@aceiss/lib`, look up `Foo` in the per-file import-targets map (which now knows the resolved project node) and resolve the call to `<project_file>::Foo.bar` directly — without going through the unambiguous-cross-file-rewrite fallback.

**Mechanism — additive to today's resolver:**

1. At import-edge emission (existing site in `_extract_tree_sitter_artifact`), extract the **imported names** for each import statement (the curly-brace clause: `import { Foo, Bar } from '@aceiss/lib'` → `[Foo, Bar]`).
2. For each imported name, register `import_targets[imported_name] = resolved_target` where `resolved_target` is the project node id returned by `_resolve_ts_import_via_tsconfig` (or the existing `external::*` fallback).
3. Thread `import_targets` into `_resolve_ts_call_target` alongside the existing `symbol_lookup`.
4. In `_resolve_ts_call_target`, after the per-file `symbol_lookup` check fails, consult `import_targets` for `receiver_type`. If the imported target resolves to a project file (not `external::*`), construct the cross-file node id `<resolved_file>::<receiver_type>.<method_name>` and return it.
5. Default class-name exports (`import Foo from '@aceiss/lib'`) bind `Foo` to the imported module's default export — handled the same way (extract default-import alias as the imported name).
6. Type-only imports (`import type { Foo } from '@aceiss/lib'`) populate `import_targets` too — Teton's monorepo uses these heavily for strict-mode type-only references.

**Nx project graph awareness** is part of the same workstream. Nx generates `nx.json` and per-project `project.json` files declaring source roots and implicit dependencies. The TS extractor today treats every TS file as an independent unit; for cross-package receiver-type resolution to land cleanly on Nx-shaped repos, the resolver needs to know which TS file is the "real" entry point of a package, so an import of `@aceiss/foo` that resolves to `libs/foo/src/index.ts` correctly attributes types exported transitively from `libs/foo/src/internal/types.ts`.

For this change Nx awareness is **diagnostic only**: when an Nx project structure is detected (presence of `nx.json` at repo root), we record the per-project `sourceRoot` and treat the project root as the "package root" for tsconfig.paths resolution probing. Cross-file type tracing through re-exports stays out of scope here — its return on a typed monorepo is high but the implementation cost is substantial enough to warrant a separate change after this lands and gets measured.

## Requirements

1. Per-file `import_targets: dict[str, str]` accumulator built during import-edge emission in `_extract_tree_sitter_artifact` for `lang_key in ("typescript", "javascript")`.
2. Imported names extracted from each import statement: named imports (`{ Foo, Bar }`), default imports (`import Foo from`), namespace imports (`import * as Foo from`), and type-only imports (`import type { Foo }`).
3. `import_targets[imported_name]` value is the resolved project node id when `_resolve_ts_import_via_tsconfig` returned a project file, or `external::<spec>` otherwise.
4. `_resolve_ts_call_target` accepts an optional `import_targets: dict[str, str]` argument and consults it after the per-file `symbol_lookup` check fails.
5. When `import_targets[receiver_type]` resolves to a project file (not `external::*`), the resolver returns `<resolved_file>::<receiver_type>.<method_name>` and the edge is emitted with `confidence: "RECEIVER_RESOLVED"`.
6. When `import_targets[receiver_type]` resolves to `external::*`, the resolver returns the existing `external::<receiver_type>.<method_name>` form — no behavior change from today.
7. Nx project structure is detected via `nx.json` at repo root; presence is recorded in the per-build diagnostic surface but does not yet change resolution behavior beyond tsconfig.paths probing.
8. Regression test: synthetic Nx-shaped TS fixture with two libs and an aliased import + typed call — `code_callhierarchy(symbol='<receiver_method>', direction='incoming')` returns the caller from the other lib in `incoming` with `confidence: "RECEIVER_RESOLVED"`.
9. Regression test: same fixture but with an `external::*` import (e.g. `import React from 'react'`) — no false positive promotion; the call still resolves to `external::*`.
10. Regression test: type-only imports populate `import_targets` correctly (`import type { Foo } from '@aceiss/lib'`).
11. No regression on non-monorepo TS projects: existing TS regression tests pass without modification.
12. `wave_graph_report` `attribution_counts_by_language` for `typescript` improves measurably on the Aceiss / Teton-shaped synthetic fixture — at minimum the `RECEIVER_RESOLVED` count for the fixture rises from 0 to ≥1 on the typed cross-package call site.

## Scope

**Problem statement:** TypeScript receiver-type resolution doesn't use the per-file resolved-import context, so typed calls on imported classes drop to `EXTRACTED` and depend on the unambiguous-cross-file-rewrite fallback. On large monorepos with name collisions, the fallback fires rarely and the type-resolved share collapses (Teton: 4.3%).

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — `_extract_imported_names` helper; `import_targets` accumulator; thread through `_resolve_ts_call_target`; consult `import_targets` after `symbol_lookup` miss; Nx project-structure detection (diagnostic only)
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — Nx-shaped fixture covering named / default / namespace / type-only imports + the negative `external::*` case

**Out of scope:**

- Cross-file type tracing through re-exports. Significant uplift but high implementation cost; tracked as a follow-on once this change measures against real codebases.
- Per-tsconfig `include` / `exclude` honoring. Currently the resolver probes any file under baseUrl with the right extension; tsconfig may restrict the file set. Not load-bearing for the receiver-type fix.
- Nx `implicitDependencies` / `tags` honoring beyond presence detection. Same logic — diagnostic only at this stage.
- Lambda monolith bundle path heuristic exploration (Teton report Issue A.3). Diagnose only if 1p2tf's measurable improvement leaves a meaningful gap on the Lambda paths after re-validation.

## Acceptance Criteria

- [x] AC-1: `_extract_imported_names` returns the correct imported names for each import-statement shape (named, default, namespace, type-only) on TypeScript/JavaScript files.
- [x] AC-2: Per-file `import_targets` is populated at import-edge emission and contains the resolved project node id for tsconfig.paths-aliased imports.
- [x] AC-3: `_resolve_ts_call_target` accepts and consults `import_targets` after the local `symbol_lookup` check.
- [x] AC-4: On a synthetic Nx-shaped fixture, `code_callhierarchy(symbol='<typed_method>', direction='incoming')` returns the cross-package caller with `confidence: "RECEIVER_RESOLVED"`.
- [x] AC-5: On the same fixture, an `external::*` import (e.g. `react`) does NOT get promoted to a project node — `confidence` stays `EXTRACTED` and target stays `external::*`.
- [x] AC-6: Type-only imports populate `import_targets` for the named types they introduce.
- [x] AC-7: `nx.json` presence at repo root is detected and surfaced in the per-build diagnostic field (e.g. `nx_project_detected: true`).
- [x] AC-8: Synthetic fixture's `attribution_counts_by_language["typescript"]["receiver_resolved"]` is `>0` on the call-graph build (proves the new path landed at least one edge).
- [x] AC-9: Non-monorepo TS regression tests (no `tsconfig.paths`, no `nx.json`) pass without modification — additive change, no behavior regression on baseline TS.
- [x] AC-10: All existing 2,200 framework tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate (verify still open)
- [x] Add `_extract_imported_names(node, source_bytes, mode)` helper
- [x] Modify import-emission site in `_extract_tree_sitter_artifact` to populate `import_targets`
- [x] Modify `_resolve_ts_call_target` signature to accept `import_targets`
- [x] Implement the `import_targets` lookup branch in `_resolve_ts_call_target`
- [x] Add Nx detection (`nx.json` at repo root) — diagnostic only
- [x] Add regression tests per AC-4 through AC-8
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [x] Repackage; field-verify TS attribution share against Teton's `code_callhierarchy(symbol='getRootApplicationForInstallation')` reproducer

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| extract-imported-names | Engineering | — | New helper, per-import-shape extraction |
| import-targets-accumulator | Engineering | extract-imported-names | Per-file dict populated at emission |
| resolver-uses-import-targets | Engineering | import-targets-accumulator | Modifies `_resolve_ts_call_target` |
| nx-detection | Engineering | — | Independent diagnostic addition |
| tests | Engineering | resolver-uses-import-targets, nx-detection | Per-AC regression fixtures |

## Serialization Points

- `_extract_tree_sitter_artifact` orchestrates both the import walker and the call walker; the `import_targets` dict must be populated before the call walker runs (it already is — definition walker runs first).

## Affected Architecture Docs

N/A — extractor-internal change; no architectural boundary or data flow change. The call-target resolver's interface broadens by one optional parameter; edge payload shape is unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Extraction must work across all 4 import shapes before downstream resolution can land |
| AC-2 | required | Without populated `import_targets`, the new resolver path is dead code |
| AC-3 | required | The resolver-side wiring is the load-bearing change |
| AC-4 | required | The end-to-end measurable outcome — Teton's blast-radius questions become accurate |
| AC-5 | required | No false promotion of external imports — protects baseline correctness |
| AC-6 | important | Type-only imports are dominant in strict-TS codebases — coverage matters |
| AC-7 | important | Nx detection is diagnostic only this round; needs to land so it can drive the follow-on |
| AC-8 | required | Empirical proof the new path emits at least one RECEIVER_RESOLVED edge in the fixture |
| AC-9 | required | No baseline TS regression |
| AC-10 | required | No baseline regression on framework tests |

## Related Work

- Direct extension of [[1p2q9]] A (tsconfig.paths import resolution) — that change made `imports` edges resolve correctly; this change makes the resolution count for `calls` edges too.
- Companion to [[1p2td]] (overload self-edge classification) in the same wave round — both improve call-edge attribution honesty, for different language families.
- Field-feedback report from Teton team follow-up (2026-06-02).

## Risks

| Risk | Mitigation |
|---|---|
| Imported name extraction has edge cases (re-exports, default + named in one statement, `import * as X` patterns) | Per-shape unit tests cover the variants explicitly |
| `import_targets` lookup could falsely promote external imports to project nodes if `_resolve_ts_import_via_tsconfig` returns a path for an external alias | Same guard as [[1p2q9]] A: the resolver only returns a project path when the resolved candidate exists on disk under the repo root |
| Receiver-type extraction returns inaccurate type names (anonymous types, generic instantiations) | Existing resolver already handles these — falls through to `external::*` when the type name doesn't simplify cleanly. The new path is purely additive |
| Cross-package re-exports (`libs/lib/src/index.ts` re-exports from `libs/lib/src/internal/types.ts`) won't resolve through one level of indirection | Documented as out-of-scope; tracked as follow-on after measurement |
