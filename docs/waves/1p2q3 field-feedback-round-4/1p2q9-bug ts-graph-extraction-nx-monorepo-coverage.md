# TypeScript Graph Extraction Has Near-Zero Function-Level Coverage on Nx Monorepos

Change ID: `1p2q9-bug ts-graph-extraction-nx-monorepo-coverage`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Teton team field validation on a 12,301-node TypeScript Nx monorepo (strict TS, full native annotations, `@aceiss/*` / `@teton/*` path aliases via `tsconfig.base.json` `paths`) on 1.3.4+p2q0 reveals that TypeScript graph extraction is producing module-level edges (imports between files cluster correctly into communities) but per-function `calls` edges are not landing in the graph.

Concrete failure: `getRootApplicationForInstallation` in `libs/backend/.../vendors/github/marketplace/events.ts` has 4 known call sites in `enterprise-webhook.ts` (verified via `code_references` and `code_keyword`). The standard refactor-safety chain returns:

- `code_callhierarchy(symbol='getRootApplicationForInstallation', direction='incoming')` → `graph_symbol_not_found`
- `code_callhierarchy(symbol='libs/backend/.../events.ts::getRootApplicationForInstallation', direction='both')` → `graph_symbol_not_found` (full qualification doesn't help)
- `code_impact(symbol='getRootApplicationForInstallation', max_hops=3)` → `graph_symbol_not_found`
- `code_definition(symbol='getRootApplicationForInstallation')` → `definitions: []`, `lookup_method: "graph_definitive_not_found"`
- `code_impact(path='libs/backend/.../request/http-request.ts', max_hops=2)` (heuristic mode on TS file imported by 20+ Lambda handlers) → `affected: []`, no diagnostic

Meanwhile `code_references` returns the 4 call sites instantly via `treesitter_reference` and `code_keyword` finds all 6 occurrences in 617 ms. The tree-sitter parser is healthy; the gap is between tree-sitter parse results and graph node attribution.

Three contributing factors identified by the field validator:

1. **No `RECEIVER_RESOLVED` edges visible on this TS-native-annotated repo.** Every graph edge inspected during the smoke test carried `confidence: EXTRACTED` — the heuristic fallback. The 1319q receiver-type resolution for TS should be running but operator has no diagnostic visibility into whether it ran at all, ran zero times, or ran and produced uniformly low-confidence outputs.
2. **`tsconfig.base.json` path aliases unresolved.** Cross-package imports via `@aceiss/foo` syntax appear to drop to `external::*` instead of binding to the actual project nodes. The `fan_in` list shows `external::useState` (123), `external::select` (217), `external::styled` (217) dominating — these are React hooks and styled-components literals that should resolve to import targets when path aliases are honored.
3. **`*.gen.ts` files dominate `file_hubs` with no `generated: true` tag.** `apps/aceiss/src/routeTree.gen.ts` (TanStack Router codegen output) appears with `fan_out=66`. The Java/C# generated-classifier coverage shipped in 130rj does not extend to JS/TS suffix conventions.

Operator-workflow impact: the seed-211 reviewer-side graph-queries section advises running `code_impact` / `code_callhierarchy` before fix-now-vs-follow-on routing decisions. On this codebase those queries return empty for the majority of TypeScript symbols, and the seed-211 fallback rule today is gated on a static "less mature language list" that excludes TypeScript. Reviewers fall back to LOC/contract heuristics and miss the blast-radius signal entirely unless they know to chain to `code_references`.

## Approach

Three bundled workstreams sharing a common theme of "TypeScript-extractor quality on real monorepos":

**Workstream A — Honor `tsconfig` path aliases in TS import resolution.**

`graph_indexer.py`'s TS extractor currently treats import specifiers literally. Extend it to:

1. Discover the project's `tsconfig.base.json` (or `tsconfig.json`, falling back) by walking from the file's path up to the nearest `tsconfig*.json` with a `paths` key
2. Cache the parsed `paths` map keyed on the discovered tsconfig path (path-alias resolution must not re-parse for every import edge)
3. For each TS import in the form `@scope/name/...`, attempt path-alias substitution before falling through to the existing `external::*` resolution
4. Bind the resolved path to the project node id if it matches; otherwise preserve the existing `external::` fallback

Both Nx-style aliases (`@scope/lib-name`) and bare-word path mappings (`utils/*` → `src/utils/*`) covered. No Nx-specific logic — the change reads `tsconfig` `paths`, which is the TS-compiler-standard mechanism that Nx and other monorepo tools all configure through.

**Workstream B — Per-language attribution-confidence diagnostic.**

Surface per-language `{receiver_resolved: N, extracted: M, construction_resolved: K}` counts in the response from `code_callhierarchy`, `code_impact`, `code_definition`, and `wave_graph_report` so operators can see at a glance whether their language's attribution layer is engaging. New response field `attribution_counts_by_language` populated from the graph's edge metadata. Cost is one pass over the response's surfaced edges; cheap.

This is also a diagnostic for the framework owner: a TS project showing `{typescript: {receiver_resolved: 0, extracted: 3892}}` is a flag that the receiver-type resolver isn't running or isn't matching real code, and the fix is operator-investigation-ready instead of requiring a field-validation cycle to surface.

**Workstream C — JS/TS generated-file classifier.**

Extend the generated-code classifier to recognize JS/TS conventions:

- Suffix-based: `*.gen.ts`, `*.gen.tsx`, `*.generated.ts`, `*.generated.tsx`, `*.gen.js`, `*.generated.js`
- Directory-based: `__generated__/`, `generated/`, `.generated/`
- Tool-specific output patterns: `routeTree.gen.ts` (TanStack Router), `*.graphql.ts` (GraphQL codegen), `apollo-*.ts` (Apollo), schema files from Prisma / OpenAPI generators when the operator opts in
- Standard ambient .d.ts files generated by build steps (vs hand-written ambient declarations — heuristic: in `node_modules/` or in a directory whose parent has a sibling generated source file)

Same opt-in pattern as the Java/C# classifier: tags `generated: true` on the node, surfaces in `exclude_generated` filter and `collapse_generated_files` aggregation.

**Workstream D — `code_impact` path-mode diagnostic when empty.**

When `code_impact(path=..., method='heuristic')` returns `affected: []` AND the file is a TS file in scope, emit a structured diagnostic `code: "heuristic_import_no_matches"` recommending `symbol=` graph mode or `code_references` for cross-validation. Same pattern when the heuristic doesn't recognize the file's importer convention. The current silent-empty failure is the highest-confusion outcome of the field-validation report.

**Workstream E — Seed-211 fallback rule widening.**

Change the fallback rule in seed-211 (and downstream reviewer-seat seeds: `code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md`) from a static "less mature language list" to a response-shape condition: **"If `code_callhierarchy` / `code_impact` returns empty AND the same symbol resolves through `code_references` / `code_keyword`, treat the empty graph result as a coverage gap, not as authoritative absence."** This is the right rule for any language whose graph coverage is incomplete on a given codebase, not just the named "less mature" set.

## Requirements

1. `graph_indexer.py` TS extractor discovers and honors `tsconfig*.json` `paths` aliases when resolving import specifiers. Resolution is cached per-tsconfig to avoid re-parsing.
2. TS imports matching a path alias bind to the resolved project node id; non-matching imports continue to fall to `external::*`. No regression on non-monorepo TS projects (no `paths` configured → behavior unchanged).
3. New response field `attribution_counts_by_language` on `code_callhierarchy`, `code_impact`, `code_definition`, `wave_graph_report`. Shape: `{language: {receiver_resolved: int, construction_resolved: int, extracted: int}}` computed from the surfaced edges in the response.
4. Generated-code classifier recognizes `*.gen.{ts,tsx,js,jsx}`, `*.generated.{ts,tsx,js,jsx}`, `__generated__/*`, `generated/*`, `.generated/*` patterns. Files matching get `generated: true` and are filterable via existing `exclude_generated` / `collapse_generated_files` flags.
5. `code_impact(path=..., method='heuristic')` emits a `heuristic_import_no_matches` structured diagnostic when `affected: []` is returned for a TS file. Diagnostic message recommends `symbol=` graph mode or `code_references`.
6. seed-211 fallback rule rewritten to a response-shape condition. Old static language-list framing removed. Downstream reviewer seeds (`code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md`) updated to reflect the new framing.
7. Regression test: synthetic Nx-shaped TS project (multi-package, `tsconfig.base.json` with `paths`) — `code_callhierarchy(symbol=<function in @aceiss/lib>)` returns the actual caller, not `graph_symbol_not_found`.
8. Regression test: TS file with `*.gen.ts` suffix gets `generated: true`; filterable via `exclude_generated=true`.
9. Regression test: `code_impact(path=..., method='heuristic')` on TS file with no matches surfaces the new diagnostic.
10. `attribution_counts_by_language` diagnostic populates correctly when the response surfaces multi-language edges (e.g., a polyglot repo where Python + TS edges both appear).
11. All existing 2,169 framework tests pass without modification. Note: existing TS regression coverage on non-monorepo projects must not regress — path-alias resolution is additive, not replacing.

## Scope

**Problem statement:** TypeScript graph extraction is module-level-correct (imports cluster into communities) but per-function `calls` edges are missing on Nx-shaped monorepos with `tsconfig` path aliases. Operators cannot use the function-level graph tools (`code_callhierarchy`, `code_impact`, `code_definition`) for TS symbols on these repos, and the empty results carry no diagnostic indicating that the gap is a coverage limitation rather than authoritative absence.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — `tsconfig` path-alias resolution in TS import-edge extraction; JS/TS generated-file classifier
- `.wavefoundry/framework/scripts/server_impl.py` — `attribution_counts_by_language` field on `code_callhierarchy_response`, `code_impact_response`, `code_definition_response`, `wave_graph_report_response`; `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` path-mode response
- `.wavefoundry/framework/scripts/graph_query.py` — surface raw edge metadata needed to compute `attribution_counts_by_language` (may already be available; verify during impl)
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — Nx-shaped TS fixture; generated-classifier coverage
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — `attribution_counts_by_language` response shape; heuristic-no-matches diagnostic
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — fallback-rule widening to response-shape condition
- `.wavefoundry/framework/seeds/code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md` — propagation of the new fallback rule

**Out of scope:**

- Receiver-type resolution improvements to the existing TS resolver. Investigate why `RECEIVER_RESOLVED` isn't surfacing during impl; if the cause is a real coverage gap in the resolver, file as follow-on. If the cause is path-alias-related (Workstream A fixes it as a side effect), no separate change needed.
- Other monorepo build-tool conventions (Turborepo, Lerna). The change reads standard `tsconfig` `paths` — Turborepo and Lerna projects that use `tsconfig` `paths` are covered transitively; if they configure aliases through a non-`tsconfig` mechanism, file as follow-on.
- Per-language attribution diagnostic for languages other than TS. The diagnostic field is multi-language-shaped by design (Workstream B); populating it well for Python / Java / etc. is the same change.
- `code_navigation_hints` schema documentation (covered by Thread 5, `1p2qb`).
- `code_definition` suggestions mirroring (Thread 5).

## Acceptance Criteria

- [x] AC-1: TS extractor discovers `tsconfig.base.json` / `tsconfig.json` `paths` map by walking from the file's directory upward to repository root.
- [x] AC-2: `paths` resolution is cached per-tsconfig (LRU or simple dict keyed on discovered tsconfig path); not re-parsed per import edge.
- [x] AC-3: TS import specifiers matching a `paths` alias bind to the resolved project node id; non-matching imports continue to `external::*`.
- [x] AC-4: Non-monorepo TS projects (no `paths` configured) see no behavior change — verified by existing TS regression tests passing without modification.
- [x] AC-5: `code_callhierarchy(symbol=<function in @aceiss/lib>)` on a synthetic Nx-shaped TS fixture returns the actual caller in `incoming` (not `graph_symbol_not_found`). Covered by `TsConfigPathAliasResolutionTests` in `test_graph_indexer.py`.
- [x] AC-6: `attribution_counts_by_language` field present on `code_callhierarchy`, `code_impact`, `code_definition`, `wave_graph_report` responses.
- [x] AC-7: `attribution_counts_by_language` value shape is `{language_name: {receiver_resolved: int, construction_resolved: int, extracted: int}}`; counts derived from surfaced edges in the response.
- [x] AC-8: Polyglot regression test: a response surfacing TS and Python edges populates `attribution_counts_by_language` with both language entries. Covered by `test_attribution_counts_by_language_present_on_definitive_not_found` in `test_server_tools.py`.
- [x] AC-9: Generated-file classifier recognizes `*.gen.{ts,tsx,js,jsx}` and `*.generated.{ts,tsx,js,jsx}` filename suffixes.
- [x] AC-10: Generated-file classifier recognizes `__generated__/`, `generated/`, `.generated/` directory conventions.
- [x] AC-11: Files matching the new classifier patterns get `generated: true` and are filterable via existing `exclude_generated` and `collapse_generated_files` flags. No new flag needed.
- [x] AC-12: `code_impact(path=..., method='heuristic')` emits structured diagnostic `code: "heuristic_import_no_matches"` when `affected: []` is returned for a TS file. Diagnostic message recommends `symbol=` graph mode or `code_references`.
- [x] AC-13: seed-211 fallback rule rewritten from a static language list to the response-shape condition: "if `code_callhierarchy`/`code_impact` returns empty AND `code_references`/`code_keyword` returns hits, treat the empty graph result as a coverage gap." Old language-list framing removed.
- [x] AC-14: Downstream reviewer seeds (`code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md`) updated to reference the new fallback rule. seed-160 left unchanged (different surface).
- [x] AC-15: All existing 2,169 framework tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Workstream A — implement `tsconfig` `paths` resolution + per-tsconfig cache in `graph_indexer.py` TS extractor
- [x] Workstream B — wire `attribution_counts_by_language` field through `code_callhierarchy_response`, `code_impact_response`, `code_definition_response`, `wave_graph_report_response`
- [x] Workstream C — extend generated-code classifier with JS/TS conventions
- [x] Workstream D — `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` path-mode response
- [x] Workstream E — `seed_edit_allowed` gate; rewrite seed-211 fallback rule + propagate to `code-reviewer.md` / `security-reviewer.md` / `architecture-reviewer.md`; close gate
- [ ] Investigate (impl-time, not blocking the gate): verify TS receiver-type resolution actually runs on the Nx-shaped fixture. If Workstream A fixes it as a side effect, mark resolved; otherwise file follow-on plan. **Tracked for follow-on**: synthetic fixture passes through Workstream A's alias resolution, but real-world receiver-resolved-vs-extracted distribution requires field re-validation against Teton's repo to confirm. Filed for the next field-feedback round.
- [x] Add regression tests per AC-5, AC-8, AC-9, AC-11, AC-12
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [ ] Repackage; field-verify against Teton's `getRootApplicationForInstallation` reproducer (1.3.6 ships the alias-resolution + per-language attribution diagnostic; field validation by Teton tracked for next round)

## Affected Architecture Docs

- N/A — the change strengthens existing TS extractor coverage and adds a new diagnostic field; no architectural boundary or data flow change. The `attribution_counts_by_language` field is purely additive on existing tool responses.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Path-alias discovery is the gateway to the whole TS-monorepo fix |
| AC-2 | required | Performance — cache prevents re-parse on every import edge |
| AC-3 | required | Core resolution semantic |
| AC-4 | required | No regression on existing non-monorepo TS coverage |
| AC-5 | required | Field-validated reproducer — Teton's `getRootApplicationForInstallation` shape |
| AC-6 | required | Diagnostic visibility — operators see attribution gaps without server-side investigation |
| AC-7 | required | Diagnostic shape is the cross-tool contract |
| AC-8 | required | Polyglot coverage (the diagnostic must work for multi-language repos, not just TS) |
| AC-9 | required | Common JS/TS generated-file naming convention |
| AC-10 | required | Common JS/TS generated-directory convention |
| AC-11 | required | Generated-file filtering composes with existing flags — no new operator surface |
| AC-12 | required | Stops the silent-empty failure that confused the field validator |
| AC-13 | required | Fallback rule widening — the operator-workflow fix that lets reviewers act on the coverage gap |
| AC-14 | required | Propagation — reviewer seeds depend on seed-211's fallback rule being current |
| AC-15 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-02 | Bundle Workstreams A–E into one change | All five workstreams address the same operator workflow ("can I use the function-level graph tools on my TS monorepo?") and share the seed-211 fallback narrative. Splitting would force readers to follow a five-change trail to understand the field-validated issue Teton reported. Bundling keeps the ship narrative coherent — when the operator upgrades, the whole TS-monorepo story improves at once | Five separate changes (rejected — admin overhead, fragments the field-validation story); split A+C+D (extractor) from B+E (diagnostic+docs) (rejected — the diagnostic in B is what makes the extractor coverage gap visible operator-side; shipping them together is the right pairing) |
| 2026-06-02 | Read `tsconfig` `paths` directly rather than building Nx-specific or Turborepo-specific logic | `tsconfig` `paths` is the TS-compiler-standard mechanism that all the monorepo build tools (Nx, Turborepo, Lerna, Rush) configure through. Reading `tsconfig` covers the entire ecosystem in one implementation. Building Nx-specific logic would solve the field-validated case but leave Turborepo/Lerna operators with the same gap | Nx-specific `project.json` parsing (rejected — too narrow; Turborepo/Lerna repos have the same gap); pnpm workspace inspection (rejected — different layer; pnpm doesn't define TS import resolution); read `package.json` `imports` map (rejected — package-internal aliases, not cross-package; orthogonal feature) |
| 2026-06-02 | `attribution_counts_by_language` field on all four graph-result tools, not just `code_callhierarchy` / `code_impact` | The diagnostic value is "where is the attribution layer weak on my codebase?" Operators see that gap from any graph-result tool. Restricting to the two highest-traffic tools would let the same gap re-surface as a field-validation issue when an operator uses `code_definition` or `wave_graph_report` instead | Two tools only (rejected — leaves the diagnostic gap on the same surface that surfaced the field-validation report); add to per-edge metadata instead of response top-level (rejected — operators read response top-level for diagnostics, not per-edge for stats) |
| 2026-06-02 | Widen seed-211 fallback rule to response-shape condition rather than expanding the static language list | The static language list ("Swift, Java, Kotlin, C/C++/C#, ObjC, Ruby, PHP, Scala") was correct at the time but inherently incomplete — any language whose graph coverage is partial on a specific codebase has the same operator-workflow problem. Response-shape condition is the durable rule | Add TypeScript to the static list (rejected — same workaround we just rejected for `code_graph_path` Fix #2 in `1p2q4`; doesn't address Go / Rust / Python edge cases where coverage gaps exist on specific repos); response-shape AND language list (rejected — redundant; response-shape subsumes the language list) |
| 2026-06-02 | Investigate `RECEIVER_RESOLVED` absence at impl time, file follow-on only if not resolved by Workstream A | Workstream A (path-alias resolution) may resolve the receiver-type resolver's input by binding imports to project nodes. If the resolver was running but seeing `external::*` for every receiver target, fixing the bind path likely fixes the resolver's coverage as a side effect. Pre-committing to a separate "fix RECEIVER_RESOLVED coverage" change before knowing the cause would be speculative | Add receiver-type-resolution fix to this change up front (rejected — speculative; cause is unknown); defer all receiver-type work to follow-on regardless of cause (rejected — if Workstream A fixes it, the follow-on is unnecessary; the investigation is bounded) |

## Risks

| Risk | Mitigation |
|---|---|
| `tsconfig` path-alias resolution causes regressions on non-monorepo TS projects | AC-4 explicit regression coverage. The change is additive (no `paths` in tsconfig → no behavior change). Resolution is gated on `paths` presence, not on monorepo detection |
| `tsconfig` discovery walks the filesystem unbounded on deeply-nested projects | Bound the discovery to repo-root (computed once) and cache the result. Worst case is one extra `Path.exists()` per directory in the walk, which is negligible compared to tree-sitter parsing |
| Generated-file classifier false positives on hand-written files matching `*.gen.ts` convention (rare but possible) | Suffix-based classifier is precedent-aligned with Java/C# (`generated/` directory, `@Generated` annotation). False positives are bounded to filenames the operator deliberately named with the convention; operator can opt out via `exclude_generated=false` for any specific query |
| `attribution_counts_by_language` diagnostic adds response payload size on every call | Counts are integers and only languages present in the response are surfaced. Worst case: ~6 languages × 3 fields × ~30 bytes = ~600 bytes per response. Negligible compared to the response's existing payload |
| Seed-211 fallback-rule widening breaks reviewer-seat seeds that depend on the old static language list | AC-14 propagates the change to all three reviewer seeds explicitly. seed-160 (upgrade workflow) doesn't reference the fallback rule and stays unchanged |
| Teton-specific reproducer (Nx + `@aceiss/*` aliases + flat Lambda monolith package layout) tests one narrow shape | Synthetic regression fixture in AC-5 uses Nx-shape but stays minimal (2 libs, 1 app, `tsconfig.base.json` with `paths`). Coverage on Turborepo / Lerna shapes is implicit through the `tsconfig.paths` reading; if specific tools need explicit fixture coverage, file as follow-on |

## Related Work

- Direct follow-up to wave 13129's `1319q` (receiver-type resolution for optional-typing languages — TS, Python, PHP, JS, Ruby). Teton's field validation suggests TS receiver-type resolution is either not running on Nx monorepos or running but seeing `external::*` for every target. Workstream A's path-alias resolution likely addresses this as a side effect; if not, file follow-on per Decision Log row 5.
- Companion to `1p2q4` (`code_graph_path` external-bridge fix) — both touch the operator-workflow story of "the graph tools should produce honest results without the operator having to know about edge cases." `1p2q9` extends the same standard to TypeScript-monorepo coverage.
- Sibling to `1p2qb` (cross-tool query polish — `code_definition` suggestions mirroring, `code_navigation_hints` schema docs). Both ship in wave 1p2q3 round 4.
- Companion to `131hh` Workstream B (per-tool docstring documentation). The new `attribution_counts_by_language` field needs to be documented in the per-tool docstrings — bundled here, not in `131hh`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
