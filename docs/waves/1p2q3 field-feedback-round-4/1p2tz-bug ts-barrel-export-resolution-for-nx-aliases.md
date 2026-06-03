# TypeScript Barrel Export Resolution for Nx Path Aliases

Change ID: `1p2tz-bug ts-barrel-export-resolution-for-nx-aliases`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Wave 1p2q3 (1p2tf) shipped tsconfig.paths-aware import resolution in 1.3.7. Teton field validation against 1.3.7+p2th and 1.3.8+p2to (with builder-version bump forcing a clean re-extract) confirmed:

- The receiver-resolved share on the 12,301-node strict-TS Nx monorepo stayed at **4.3%** — byte-for-byte identical to 1.3.6's numbers
- `code_callhierarchy(symbol='getRootApplicationForInstallation')` still returns `graph_symbol_not_found`
- The fan-in distribution still shows `external::useState`, `external::select`, `external::trace`, `external::styled` dominating the top

Teton's configuration supplement (`docs/reports/wavefoundry-graph-feedback-2026-06-02-supplement.md`) pinpoints the gap. Every `paths` alias in their `tsconfig.base.json` points to a **single-file barrel re-export**:

```json
"paths": {
  "@aceiss/utils":  ["libs/utils/src/index.ts"],
  "@aceiss/hooks":  ["libs/hooks/src/index.ts"],
  "@teton/backend": ["libs/backend/src/index.ts"],
  …
}
```

Each `libs/<name>/src/index.ts` is a barrel:

```typescript
// libs/utils/src/index.ts
export { httpRequest } from './lib/http-request';
export { sanitize } from './lib/sanitize';
export * from './lib/types';
```

The actual `httpRequest` definition lives in `libs/utils/src/lib/http-request.ts`, not in `libs/utils/src/index.ts`. Our 1p2tf resolver:

1. Sees `import { httpRequest } from '@aceiss/utils'`
2. Resolves `@aceiss/utils` → `libs/utils/src/index.ts` ✓
3. Stores `import_targets["httpRequest"] = "libs/utils/src/index.ts"` ✓
4. At call site `httpRequest()`, looks up `import_targets["httpRequest"]` → `libs/utils/src/index.ts`
5. Constructs target node id `libs/utils/src/index.ts::httpRequest`
6. **No node with that id exists** — the index.ts file has no `httpRequest` definition, just a re-export — so the receiver resolver returns `external::httpRequest` and the edge lands as `EXTRACTED` low-confidence

Every aliased import in Teton's codebase hits the same wall. The fix landed the alias name lookup but stopped at the barrel boundary. To produce `RECEIVER_RESOLVED` edges on these call sites, the resolver must follow the barrel re-export to find the real definition file.

This is the load-bearing change for type-resolved share on Nx-shaped repos with barrel-export libraries — the same pattern used by `@aceiss/*`, `@teton/*`, `@scope/*` style monorepos, plus any TS workspace where `src/index.ts` per-package is a barrel (which is the dominant convention).

## Approach

Walk barrel re-exports at import-resolution time so `import_targets[name]` points at the actual definition file rather than the barrel.

**Mechanism:**

1. When `_resolve_ts_import_via_tsconfig` returns a project file for an aliased import (or a relative import), check whether the resolved target is a barrel by parsing its top-level `export` statements.
2. For each imported name, scan the barrel's re-exports:
   - `export { Foo } from './path'` — named re-export. If `Foo` matches the imported name, resolve `'./path'` to a file and recurse.
   - `export { Foo as Bar } from './path'` — renamed re-export. The locally-bound name is `Bar`; if the imported name (local side) matches `Bar`, recurse on the original name `Foo` against `'./path'`.
   - `export { default as Foo } from './path'` — default re-export with rename. Recurse with the default-export semantics on `'./path'`.
   - `export * from './path'` — wildcard re-export. The imported name *might* be defined there; recurse and probe.
3. Cache the parsed barrel structure per file (mtime-keyed) so each file is parsed once per build.
4. Bound the recursion depth to avoid cycles in pathological re-export chains.
5. When a re-export chain bottoms out at a file that declares the symbol directly (a `class Foo`, `function Foo`, `const Foo`, or `interface Foo` definition), set `import_targets[imported_name]` to that file's path. When the chain doesn't find a declaration, fall back to the last barrel target — at least the edge lands on a more-specific file than the original alias index.
6. Handle **alias collision** (two aliases pointing at the same physical file: `@aceiss/hooks` and `@teton/hooks` both → `libs/hooks/src/index.ts`) by recognizing that the *resolved target* is what matters; we don't need to de-dupe at the alias-name level since the import_targets map keys on the locally-bound name.

**Scope of barrel parsing:**

Pure-syntactic, no TS type-checker. Regex-based scan of the top-level export statements:
- `^export\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]`
- `^export\s*\*\s*from\s*['"]([^'"]+)['"]`
- `^export\s*\{\s*default\s+as\s+(\w+)\s*\}\s*from\s*['"]([^'"]+)['"]`

This is the canonical barrel shape — it handles the overwhelming majority of monorepo barrels without needing tree-sitter for the secondary parse. Trade-off: if a barrel uses a non-canonical shape (multi-line clause spanning newlines without `{` on the first line), the scan may miss it. Treated as `unknown` and falls back to the existing barrel target.

**moduleResolution: "Bundler" awareness:**

Teton's `tsconfig.base.json` declares `"moduleResolution": "Bundler"`. This mode (TS 5.x) prefers explicit `.ts` extensions when present and matches esbuild's resolution semantics. Our `_probe_ts_alias_target` already probes the canonical extensions; for bundler mode this is correct. No additional resolution-mode forking required for the barrel-following path — the extension probing logic is already extension-list-based.

**Nested tsconfig discovery:**

Teton's repo has 44 `tsconfig*.json` files (each project carries `tsconfig.json` + `tsconfig.lib.json` + `tsconfig.spec.json`). Our `_discover_tsconfig_for_file` walks up looking for the nearest tsconfig with `paths` — repos with project-local `paths` overrides are handled correctly by that walker. The barrel-resolution change is orthogonal: it operates after alias resolution, regardless of which tsconfig file the alias came from.

## Requirements

1. `_resolve_through_barrel(imported_name, barrel_path, root)` helper added — recursively follows `export { Name } from './path'`, `export { Name as Alias } from './path'`, `export { default as Name } from './path'`, and `export * from './path'` re-exports.
2. Per-file barrel-parse cache keyed on (file path, mtime) so each barrel is parsed once per build.
3. Recursion depth bound (≥ 5 hops; depth-N covers `index.ts → barrel-a.ts → barrel-b.ts → impl.ts` which is rare in practice but not pathological).
4. At import-edge emission (`_extract_tree_sitter_artifact` import branch in both `walk_definitions` and `walk_calls`), after resolving the target via tsconfig.paths, invoke `_resolve_through_barrel` to walk through to the actual definition file. `import_targets[imported_name]` is updated to point at the definition file.
5. When the chain doesn't bottom out at a declaration of the imported name (e.g. the symbol exists only through a wildcard re-export that we can't statically resolve), retain the last barrel target — never worse than today's behavior.
6. Cycle detection: a `_seen` set per recursion prevents infinite loops on `barrel-a → barrel-b → barrel-a` shapes.
7. Regression test (synthetic): two-hop barrel chain (`libs/utils/src/index.ts` re-exports from `libs/utils/src/lib/http-request.ts`); `code_callhierarchy(symbol='httpRequest', direction='incoming')` returns the cross-package caller with `confidence: "RECEIVER_RESOLVED"` and the target resolves to `libs/utils/src/lib/http-request.ts::httpRequest`, not `libs/utils/src/index.ts::httpRequest`.
8. Regression test: wildcard re-export (`export * from './lib/types'`) — the resolver probes the wildcard target and either resolves through or falls back gracefully.
9. Regression test: renamed re-export (`export { Foo as Bar } from './lib/Foo'`) — the locally-imported name `Bar` resolves to `libs/.../Foo.ts::Foo`.
10. Regression test: alias collision (`@aceiss/hooks` and `@teton/hooks` both → `libs/hooks/src/index.ts`) — both produce a `RECEIVER_RESOLVED` edge to the resolved definition; no duplicate or shadowed edges.
11. `attribution_counts_by_language["typescript"]["receiver_resolved"]` is measurably higher than the pre-change baseline on a synthetic Nx-shaped fixture with at least one barrel chain.
12. `GRAPH_BUILDER_VERSION` bumped `18 → 19` with the language-coverage callout convention (release notes lead with operator-action note explicitly naming affected languages).
13. No regression: all existing 2,220 framework tests pass.

## Scope

**Problem statement:** TypeScript receiver-type resolution lands the alias-name lookup but stops at the barrel boundary. On the dominant Nx convention (every package exports via `src/index.ts` barrel re-exporting from `./lib/<file>`), our resolver maps every import to the same 14 barrel nodes and never reaches the actual definition file. This drops type-resolved share to 4.3% on real codebases.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — `_resolve_through_barrel` helper, per-file barrel-parse cache, integration into import-target population at both walker entry points, `GRAPH_BUILDER_VERSION` bump 18 → 19
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-re-export-shape regression fixtures
- `.wavefoundry/CHANGELOG.md` — 1.3.9 entry leading with the Operator-action note for the v18 → v19 bump

**Out of scope:**

- TS-compiler-driven type checking. The fix is purely syntactic. Same-arity-different-types overloads, complex generic instantiation, and re-exports inside dynamically-evaluated expressions remain unresolved and fall back to existing behavior.
- Lambda Layer cross-runtime fan-in modeling. Teton's `aceissCorePackages/opt/packages/` is mounted at runtime to every Lambda; that fan-in is a deployment topology fact, not a source-code fact. Documented in the supplement as out-of-scope.
- Following `import` (rather than `export`) re-export aliasing inside the barrel. Real barrels only use `export`-side re-exports; the `import { Foo } from './x'; export { Foo };` pattern is rare and can be added later if observed in the wild.

## Acceptance Criteria

- [x] AC-1: `_resolve_through_barrel(imported_name, barrel_path, root)` recursively walks the four re-export shapes (named, renamed, default-as, wildcard) until the symbol's actual definition file is found.
- [x] AC-2: Per-file barrel-parse cache stores `(file_path → {imported_name: resolved_path})` keyed on file mtime; each barrel is parsed at most once per build.
- [x] AC-3: Recursion depth is bounded at ≥ 5 hops with cycle-set detection on the resolved-paths chain.
- [x] AC-4: When a re-export chain bottoms out at a file with a direct declaration of the imported name, `import_targets[name]` is updated to that file's repo-relative path.
- [x] AC-5: When the chain doesn't terminate at a declaration (wildcard re-export to a module that doesn't expose the name), `import_targets[name]` falls back to the last resolved barrel — never worse than baseline.
- [x] AC-6: Regression test: synthetic two-hop barrel chain produces a `RECEIVER_RESOLVED` edge targeting the definition file (not the barrel index.ts).
- [x] AC-7: Regression test: renamed re-export (`export { Foo as Bar }`) correctly tracks the locally-bound name across the chain.
- [x] AC-8: Regression test: wildcard re-export (`export * from './path'`) probes the wildcard target and resolves through or falls back gracefully.
- [x] AC-9: Regression test: two aliases (`@aceiss/hooks` + `@teton/hooks`) pointing at the same barrel file resolve to the same definition file with no duplicate edges.
- [x] AC-10: `attribution_counts_by_language["typescript"]["receiver_resolved"]` rises on the synthetic Nx-shaped fixture from pre-change baseline (proves the new path emits at least one cross-package RECEIVER_RESOLVED edge through a barrel).
- [x] AC-11: `GRAPH_BUILDER_VERSION` bumped 18 → 19 with a comment naming `1p2tz` + the affected language scope (TS/JS).
- [x] AC-12: CHANGELOG 1.3.9 entry leads with the Operator-action note convention (exact bump, rebuild trigger, affected languages, expected shift in attribution counts on barrel-export-heavy codebases).
- [x] AC-13: All existing 2,220 framework tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate (verify still open)
- [x] Implement `_resolve_through_barrel` helper + barrel-parse cache + integration at import-edge emission
- [x] Bump `GRAPH_BUILDER_VERSION` 18 → 19 with language-coverage comment
- [x] Add regression tests per AC-6 through AC-10
- [x] Run framework tests
- [x] Update CHANGELOG with 1.3.9 entry leading with Operator-action note
- [x] Close framework gate; mark change `implemented`
- [x] Build + package 1.3.9
- [x] Field-verify against Teton's `getRootApplicationForInstallation` reproducer once they pick it up

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| barrel-resolver | Engineering | — | `_resolve_through_barrel` + cache |
| import-targets-integration | Engineering | barrel-resolver | Update import_targets to point at definition files |
| version-bump | Engineering | barrel-resolver | 18 → 19 in same commit; comment names 1p2tz |
| tests | Engineering | import-targets-integration | Per-shape fixtures + counts assertion |
| changelog | Engineering | version-bump | Operator-action note per the convention |

## Serialization Points

- `_extract_tree_sitter_artifact` is the integration point. The barrel-resolution helper is module-level; the cache lives at module scope keyed by file path + mtime. Both walker branches (`walk_definitions` and `walk_calls`) populate `import_targets` and need the barrel-resolved values.

## Affected Architecture Docs

N/A — extractor-internal change. Edge shape unchanged; what changes is the *target* of receiver-resolved edges (specific file vs barrel file).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The helper is the load-bearing primitive |
| AC-2 | required | Per-file cache prevents repeated barrel parsing on large monorepos |
| AC-3 | required | Cycle detection — without it, malformed barrels can hang the build |
| AC-4 | required | The end-to-end measurable outcome |
| AC-5 | required | Graceful degradation when the chain can't terminate |
| AC-6 | required | Empirical proof the change resolves the Teton pattern |
| AC-7 | required | Renamed re-exports are common; coverage needed |
| AC-8 | important | Wildcard re-exports are less common; graceful fallback acceptable |
| AC-9 | required | Alias collision per Teton supplement |
| AC-10 | required | Attribution-counts proof — the measurable diagnostic Teton confirmed works |
| AC-11 | required | Version bump per [[graph-builder-version-bump-required]] memory rule |
| AC-12 | required | Release-note convention per the same memory |
| AC-13 | required | No baseline regression |

## Related Work

- Direct extension of [[1p2tf]] (cross-file receiver-type via imports) — that change landed the alias lookup; this change closes the barrel-traversal gap that prevented type-resolved share from improving on Nx-shaped repos.
- Field-feedback supplement from Teton team (`docs/reports/wavefoundry-graph-feedback-2026-06-02-supplement.md`) — provides the concrete tsconfig.paths layout, barrel-re-export shape, alias collision, and `moduleResolution: "Bundler"` configuration that motivate the design.
- Memory: [[framework-owns-generic-defaults]] (applies indirectly — the resolver fix is framework-generic; no per-project config needed).
- Memory: [[graph-builder-version-bump-required]] — bump + release-note convention enforced per AC-11 and AC-12.

## Risks

| Risk | Mitigation |
|---|---|
| Regex-based barrel parsing misses non-canonical shapes (multi-line export clauses, comments between `export` and `{`) | Treat as `unknown`; fall back to barrel target. Per-shape regression tests cover the canonical cases; non-canonical shapes degrade gracefully to baseline |
| Barrel chains span many hops on deeply-layered monorepos | Recursion bound at ≥ 5 hops; cycle-set detection on resolved paths. Real monorepos almost always bottom out at 2–3 hops |
| Per-file cache grows unbounded on very large repos | Cache keys are (path, mtime); evicted naturally on file changes. For multi-GB monorepos, cache size is bounded by total TS file count (typically < 50k entries) |
| Wildcard re-exports require probing every wildcard target | Stop at first wildcard hit; don't combinatorially expand. If the symbol isn't there, fall back to barrel |
| The fix changes the *target file* of receiver-resolved edges on existing graphs; downstream tools may have edge-targeting assumptions | Edge shape (source/target/relation/confidence) is unchanged. Only *which file* the target points at differs — that's the entire point of the fix. The `GRAPH_BUILDER_VERSION` bump forces clean re-extraction |

## Post-ship discovery: the leading-`@` strip bug

Implementing this change surfaced a separate latent bug in `_ts_clean_name` that, on inspection, is the **load-bearing root cause** Teton's report was actually pointing at — and the reason every scoped-import resolution failed on their codebase across 1.3.6 / 1.3.7 / 1.3.8 even after our resolver shipped.

The `_ts_clean_name` helper extracted the identifier portion of a TS/JS specifier via:

```python
match = re.search(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", value)
```

The character class doesn't include `@`. So for a scoped specifier `@aceiss/hooks`, the regex matched starting from the first valid identifier character — `a` — and returned `aceiss/hooks` (without the `@`). Every downstream consumer of the cleaned name then tried to match `aceiss/hooks` against tsconfig paths patterns whose keys contain `@aceiss/hooks` literally. No match → fall through to `external::*`.

This means every npm scoped package (`@aws-sdk/*`, `@nestjs/*`, `@nx/*`, `@aceiss/*`, `@teton/*`, etc.) was being silently mangled before reaching the alias resolver. Our 1p2tf (TS receiver-type via imports) shipped in 1.3.7 and was structurally correct, but its `_ts_relation_candidates` upstream was already stripping the `@` — so the resolver never saw a specifier the alias map could match. Teton's repo uses 14 distinct scoped aliases; this bug applied to all of them, which is the mechanism behind the byte-identical 4.3% rate across three releases.

Fix: preserve a leading `@` through `_ts_clean_name` so scoped specifiers survive. Bare `@` mid-string is not a valid identifier prefix in TS/JS, so the leading-character special case is unambiguous. Implementation in `graph_indexer.py:_ts_clean_name`.

This is shipped as part of 1p2tz because the discovery happened during 1p2tz implementation and the two fixes ship together — barrel-export resolution depends on the alias actually resolving in the first place. Tagged here for narrative honesty: 1p2tz's *headline* contribution is barrel-following, but the *largest measurable impact* from the same commit is probably the `@` preservation fix, which closes a latent gap that should have been caught when 1p2tf landed.

Memory entry queued: future TS/JS specifier-related work must verify `_ts_clean_name` round-trips the input shape (scoped packages, URL-like paths, relative-import sentinels) before downstream consumers assume identifier-only forms.

## Post-ship correction 2 (1.3.10): direct-function-call path + bundler-mode `.js` swap + barrel label deprioritization

Teton field validation on 1.3.9+p2vc confirmed three things at once:

1. **The community structure shifted** — barrels now hub communities, proving the leading-`@` fix + tsconfig.paths resolution finally work end-to-end. Imports DO resolve to barrels.
2. **Attribution numbers stayed at 4.3%** — byte-for-byte identical to v18. The barrel walker for *method calls* shipped correctly, but Teton's primary use case (free-function calls like `httpRequester(url)` after `import { httpRequester } from '@aceiss/utils'`) was untouched.
3. **Community labels regressed** — barrels became seeds because they outranked previous hubs by in-degree, so meaningful labels like `"SailpointIntegrationDetailsForm"` collapsed to generic `"src/index N"`.

Root cause for (2): the receiver-type resolver path in `walk_calls` only fires on **method calls** (`obj.method()` via `_resolve_ts_call_target`). Direct function calls (`func()`) fall through to the EXTRACTED path which calls `_ts_resolve_target` — that helper consults `import_aliases` (which holds bare-name → bare-name mappings populated by `_ts_import_aliases`) but NOT `import_targets` (which holds the walked-through target paths populated by the barrel walker). Every aliased free-function call landed as `external::<name>` regardless of how well the import side resolved.

Fix shipped together with two related corrections:

- **Direct-function-call promotion.** In `walk_calls`'s EXTRACTED fallback path, when the resolved target starts with `external::` AND `import_targets` carries a project-internal path for that bare name, the resolved target is rewritten to `<walked_path>::<name>` and the edge's confidence is promoted from `EXTRACTED` to `RECEIVER_RESOLVED`. This is the load-bearing fix for Issue A on real codebases — most aliased imports on Nx monorepos are free functions, not class methods.
- **Bundler-mode `.js` → `.ts` extension swap.** TS 5.x's `moduleResolution: "Bundler"` (used by Vite / esbuild / Nx defaults) allows source code to write `./foo.js` and have it resolve to `./foo.ts` at compile time. Barrel re-exports written `export { x } from './foo.js'` previously failed to walk through because `_probe_ts_alias_target` only tried the literal `.js` path. Added explicit `.js → .ts`, `.jsx → .tsx`, `.mjs → .mts/.ts`, `.cjs → .cts/.ts` fallbacks.
- **Community-label barrel deprioritization.** `_community_seed` in `graph_cluster.py` now treats nodes whose path matches a barrel filename (`index.{ts,tsx,js,jsx,mjs,cjs,mts,cts}`) with a sort-key penalty: non-barrels are preferred for the seed slot even when a barrel has higher degree. Barrels can still be picked when they're the only option in a community (e.g. an isolated barrel reference). `hub_node_id` and the structural graph are unchanged — operators caching by hub_node_id per the wave 1316r stable-reference contract are unaffected; only the human-readable label changes.

`GRAPH_BUILDER_VERSION` bumped 19 → 20 with the language-coverage callout per the release-note convention. Affects TypeScript and JavaScript only; other languages unchanged.

Test coverage: 6 new tests across `test_graph_indexer.py` and `test_graph_cluster.py`. Verified end-to-end on synthetic fixtures mirroring Teton's tsconfig.paths layout.

## Post-ship correction 3 (1.3.11): arrow-const function registration

Teton field validation on 1.3.10 confirmed the v19→v20 fix worked — TS receiver-resolved share rose 4.3% → 6.0% with +641 RECEIVER_RESOLVED edges as an exact migration from EXTRACTED. But three smoke-test symbols (`getRootApplicationForInstallation`, `setupCognitoUser`, `findOrCreateUserPool`) still returned `graph_symbol_not_found`. Diagnostic from Teton:

> `code_keyword` for `^export function ` and `^function ` (anchored) across all `libs/backend/**/*.ts` returned zero hits. There are no function declarations in the backend code — it's 100% `export const X = () => {}` arrow-const.

Tree-sitter parses arrow-const as `lexical_declaration → variable_declarator → arrow_function`, NOT as `function_declaration`. Our extractor's name-from-descendants extractor looked at direct children of `lexical_declaration` for an identifier, found none (the identifier is nested one level deeper inside `variable_declarator`), and the symbol never registered.

This is the dominant function shape in modern TS — particularly in Lambda + Nx layouts where every backend function is `export const ... = async (...) => { ... }`. Teton's estimate: TS resolved-share should rise from 6% range into 30–60% with this fix. The barrel + direct-call + arrow-const stack now closes end-to-end:

- Caller: `export const caller = async (): Promise<number> => { return await httpRequester('x'); }`
- Import: `import { httpRequester } from '@aceiss/utils'` (alias + barrel walk shipped in v19/v20)
- Target: `export const httpRequester = async (url: string): Promise<number> => { return 1; }`
- Edge produced: `apps/.../caller → libs/utils/src/lib/http-request.ts::httpRequester` with `RECEIVER_RESOLVED` confidence

Fix shipped in `_ts_extract_arrow_const_bindings` helper + walker integration:

- Detects `lexical_declaration` / `variable_statement` / `variable_declaration` nodes whose child `variable_declarator` binds an `arrow_function` or `function_expression`
- Registers each binding as a function symbol (kind `function`, not `variable`)
- Walks scope through the arrow body so calls FROM inside arrow-const-bound functions get attributed to the const name rather than the file
- Covers both `walk_definitions` (registration) and `walk_calls` (scope tracking for edge sources)

`GRAPH_BUILDER_VERSION` bumped 20 → 21 with the language-coverage callout. Affects TypeScript and JavaScript only — the canonical form occurs in both languages.

Test coverage: 3 new tests — arrow-const node registration, function-expression form, and call-attribution through the arrow body.

## Post-ship correction 4 (1.3.15): single-pass walker + pre-fork declared-names cache

After 1.3.12-1.3.14 closed the first wave of perf gaps (regex caches, lru_cache on path probes, parallel extraction across CPU cores), profiling pointed at two remaining sources of redundant work in the tree-sitter extractor:

1. The walker visited each AST twice — once via `walk_definitions` to register symbols, once via `walk_calls` to emit call edges. On large source files this duplicated descent dominated walker wall-time after the cache wins.
2. Parallel extraction warmed `_TS_FILE_DECLARED_NAMES_CACHE` per worker independently. Each fork started cold and re-ran the declared-names regex pass on the same files the barrel walker reached from every angle.

Two changes shipped together:

- **Single-pass walker** — `walk_definitions` now buffers call-shaped nodes (gated by `_ts_is_call_node` against the per-language profile) into a flat `buffered_calls` list while it walks. Post-walk, after `symbol_lookup` and `symbol_lookup_kinds` are built, a single loop over the buffer runs the full call-resolution pipeline per call: construction-resolved first, then per-language receiver-type resolution (`_resolve_java_call_target`, `_resolve_kotlin_call_target`, `_resolve_csharp_call_target`, `_resolve_go_call_target`, `_resolve_rust_call_target`, `_resolve_scala_call_target`, `_resolve_swift_call_target`, `_resolve_ts_call_target`, `_resolve_php_call_target`), then `_ts_relation_candidates` with `EXTRACTED`-to-`RECEIVER_RESOLVED` promotion via `import_targets`. The walker now threads `scope_signatures` alongside `scope_symbols` so self-edge overload classification still resolves correctly. The standalone `walk_calls` function is deleted (~232 lines).
- **Pre-fork declared-names cache warmup** — before submitting work to the ProcessPoolExecutor, parent runs `_prewarm_declared_names_cache(code_work_items, root)` which iterates the batch and populates `_TS_FILE_DECLARED_NAMES_CACHE[(path, mtime)] = frozenset(declared_names)` from the in-memory source text (no extra disk I/O). With the `fork` start method, workers inherit the populated cache via copy-on-write — the barrel walker now hits cache on cross-file declared-name lookups instead of each worker re-running the regex pass per file independently.

Output is byte-for-byte identical to 1.3.14 (no `GRAPH_BUILDER_VERSION` bump). Verified: 2244 framework tests pass; the construction-resolved, receiver-resolved, and overload self-edge classification test suites are unchanged.

## Post-ship correction 5 (1.3.16): TS/JS symbol-table promotion to RECEIVER_RESOLVED

Teton field validation on the v22 stable state (1.3.15 confirmed byte-identical to 1.3.14):

> No movement on resolved-share or the named-out intra-file arrow-const lift. The graph rebuild confirms the post-v22 state is stable across server-side patches. Next real signal will be when GRAPH_BUILDER_VERSION next bumps.
>
> `getRootToken incoming (intra-file arrow-const)` — 5 EXTRACTED.

The symbol IS registered (v21 arrow-const node-emission fix). The intra-file callers ARE recognized — they emit `calls` edges to the right target node. But the call edges land as `EXTRACTED`, not `RECEIVER_RESOLVED`, so they are silently dropped from `attribution_counts_by_language["typescript"]["receiver_resolved"]`. The resolved-share metric undercounts by exactly this gap.

Root cause: in the buffered-call drain (post-walker, in the single-pass extractor), bare-identifier calls like `getRootToken()` fall through `_resolve_ts_call_target` (which returns `None` when no receiver is present) into the `_ts_relation_candidates` fallback. There, `_ts_resolve_target` consults `symbol_lookup` and binds the identifier directly to the locally-defined symbol id — but the confidence stayed `EXTRACTED`. A symbol-table-resolved binding is high-confidence by construction (exact name match in a known table), not a low-certainty guess.

Two promotions ship together, both scoped to TS/JS only:

- **Extraction-time intra-file promotion.** In the buffered-call drain, when `lang_key in ("typescript", "javascript")` and `_ts_resolve_target` returns a non-`external::` project node, the edge confidence becomes `RECEIVER_RESOLVED` instead of `EXTRACTED`. Covers intra-file callers and any other case where the local `symbol_lookup` table already contains the target.
- **Cross-file AC-1 rewrite promotion.** In the post-extraction cross-file rewrite pass, the AC-1 branch (bare `external::name` rewritten via unique `simple_name_index[name]` match) now promotes the rewritten edge from `EXTRACTED` to `RECEIVER_RESOLVED` when the source file is `.ts/.tsx/.js/.jsx/.mjs/.cjs`. AC-2 (qualified-target simple-name fallback for shapes like `obj.method()` where `obj` is unannotated) intentionally stays `EXTRACTED` — that path is a phantom-prone type guess, not a deterministic bind. The existing test `test_javascript_unannotated_local_call_does_not_land_receiver_resolved` guards this distinction.

`GRAPH_BUILDER_VERSION` bumped 22 → 23. Affects TS/JS only — other languages' attribution counts are unchanged because they route through their per-language receiver resolvers + the rewrite path stays preserve-confidence for non-TS/JS sources.

Test coverage: 2 new regression tests — `test_intra_file_arrow_const_call_lands_receiver_resolved` (intra-file path, Teton's `getRootToken` shape), `test_cross_file_unique_simple_name_call_lands_receiver_resolved` (AC-1 cross-file path).

Expected field impact: Teton's `getRootToken` 5 incoming edges should migrate EXTRACTED → RECEIVER_RESOLVED after auto-rebuild. The total TS resolved-share (currently 8.3% on the 47,034-edge attributed bucket) should rise substantially because every intra-file arrow-const call and every cross-file bare-identifier unique-match was previously misclassified. The exact magnitude depends on the intra-file-call / cross-file-bare-call density in the codebase.
