# Resolve Rust `Type::assoc_fn()`, Let-Binding Receiver Types, and Clean Use-Import Extractor (Cross-File Method Resolution)

Change ID: `1p4eu-enh rust-cross-file-method-resolution`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09

> **AC-5 resolved (operator chose implement, 2026-06-09).** A dedicated Rust `use_declaration` extractor (`_rust_use_imports`) now emits clean dotted import edges (`use crate::services::Helper;` → `external::crate.services.Helper`; braced groups + `as` aliases handled, alias registered in `import_aliases`) and produces NO `use`/`pub`/`fn`/`as` keyword-noise. Implementing it surfaced a deeper ROOT CAUSE shared with Kotlin: the grammar root `source_file` was substring-matched as an import node (`source` ∈ import keywords), so the generic fallback regexed the ENTIRE file into junk `external::<token>` edges — fixed by excluding `source_file`, plus an import-only `_RELATION_KEYWORD_NOISE` filter. Net effect on the operator's Java/Kotlin question: **Java, Kotlin, and Rust are all fully clean.** Kotlin's `import`/`as`/`package` keyword noise is gone, its `as` alias is captured in `import_aliases`, and the redundant bare-alias `external::W` node is now suppressed (an import candidate that is an `as`-alias whose real target is also emitted is dropped — the same cleanup applies to TS/JS `import { Foo as Bar }`). See the Progress Log.
Wave: 1p4eq cross-file-resolution-followups

## Rationale

Rust cross-file method resolution has three structural gaps found in the `1p47e` 3-language investigation (synthetic-validated only — **no team tested Rust**; the findings are source- and replication-grounded, not field-observed). The fixes mirror the same recurring failure classes the investigation flagged across C#/Go/Rust, and each reuses an existing mechanism rather than inventing new machinery:

1. **Associated-function calls `Type::assoc_fn()` are entirely unresolved.** `_resolve_rust_call_target` (`graph_indexer.py:~2785`) only handles `identifier` and `field_expression` callees. A `scoped_identifier` callee (`Bar::from(x)`, `Config::load()`) falls through `method_name` extraction as `None` and returns early at `~2802` — no edge keyed on the type at all. Even when a key is emitted, the `::` form (`external::Bar::from`) is **never indexed**: `qualified_index` is built from the **dotted** form (`Bar.from`), so a `::`-keyed external target can never be promoted by the cross-file rewrite pass. The existing `_resolve_rust_new_convention` (`~3302`) already `::`-splits a `scoped_identifier` for the `new` case and emits `external::<TypeName>` (single-segment) — but it is hardwired to `parts[-1] == "new"` (`~3325`) and only emits the **type**, not `Type.method`. The generic associated-fn case has no path.

2. **`let`-bound struct/constructor receivers resolve to the variable name, not the type.** `_search_rust_declarations_in_scope` (`~2699`) only recognizes `let x: Type = ...` (an explicit `type_identifier` child of `let_declaration`) and function `parameter` nodes. For the idiomatic `let x = Bar { .. }` (a `struct_expression` value) or `let x = Bar::new()` / `let x = Type::from()` (a `scoped_identifier` callee), there is no `type_identifier` child, so the search returns `None`. `_resolve_rust_identifier_type` (`~2740`) then falls back to its `name[:1].isupper()` heuristic (`~2750`), which fails for a lowercase binding `x` — so the downstream `x.method()` emits `external::x.method` (the **variable** name as receiver), which cannot match any indexed `Type.method`.

3. **Use-imports emit keyword-noise edges and the wrong import head.** Rust `use` declarations flow through the generic import path: `_ts_is_import_node` (`~1862`) matches on the substring `"use"` (`~1870`), and `_ts_relation_candidates` (`~4357`) falls back to its multi-token regex split (`~4397`) over the whole `use std::io::{Read, Write}` span. This produces lossy/junk `imports` edges (path fragments, and keyword-noise like `external::use` / `external::pub` / `external::let` / `external::fn` from adjacent non-import constructs caught by the substring matcher). Because `1p470`'s import-disambiguation keys `imports_by_file` on the **final segment** of the import FQN (`graph_indexer.py:~6381`), a junk head means the disambiguation is effectively dead for Rust — and is a stated **precondition for 1p4ev** (membership-based disambiguation), which needs a clean per-item type-name → project-relative dotted module mapping.

**Deferred (kept out of scope, boundary documented below):** trait / `dyn` / generic dispatch. Resolving `t.method()` where `t: &dyn Trait` or a generic `T: Trait` bound needs a trait-impl table this change does not build; the existing `test_rust_phantom_method_routes_to_external` (`tests/test_graph_indexer.py:2333`) guards the fail-safe that such calls stay `external::`.

## Requirements

1. `_resolve_rust_call_target` (`~2785`) must resolve a `scoped_identifier` callee `Type::assoc_fn(...)` by splitting on `::`, taking `parts[-2]` as the (PascalCase) receiver type and `parts[-1]` as the function, and emitting the **dotted** `external::Type.assoc_fn` form (so it lands in the same `qualified_index` / cross-file rewrite path the dotted `Bar.from` key participates in), promoting to the project node when `Type.assoc_fn` is in `symbol_lookup`. Only fire when `parts[-2]` is non-empty and PascalCase (uppercase first char), mirroring the guard in `_resolve_rust_new_convention` (`~3328`); otherwise return `None`/fall through so module-function calls (`io::stdin()`) are not mis-keyed as a type.
2. `_search_rust_declarations_in_scope` (`~2699`) must, for a `let_declaration` whose value is a `struct_expression` (`let x = Bar { .. }`) or a `scoped_identifier`-callee `call_expression` (`let x = Bar::new()` / `Type::from()`), infer the bound variable's type as the constructed/associated `Type` (PascalCase, `parts[-2]` for the `::` form; the `name`-field type identifier for the struct form, reusing the same field name `_resolve_bare_call_construction` uses at `~3241`). This must take effect only when no explicit `let x: Type` annotation is present.
3. A clean Rust use-import extractor must replace the generic regex path for `use_declaration` nodes: per imported item, use the **type-name** (final identifier of each `use` path / `use_list` member, honoring `use_as_clause` aliases) as the import **head**, and normalize the module portion — rewriting `crate::`, `super::`, and `self::` prefixes to a **project-relative dotted module** — so the `imports` edge target is `external::<dotted.module>.<TypeName>` (final segment = `TypeName`, consumable by `imports_by_file` at `~6381`). The extractor must **not** emit keyword-noise heads (`use`/`pub`/`fn`/`let`/`mod`).
4. Bump the **shared wave** `GRAPH_BUILDER_VERSION` (currently `"24"` at `graph_indexer.py:28`) exactly once for the whole wave — this change must **not** introduce its own bump; it relies on the wave-coordinated bump (alters resolver output, import-edge contents, and `qualified_index` participation → consumer caches must rebuild).
5. The deferred trait/`dyn`/generic boundary must be documented (in-code comment at the resolver + this doc), and the existing fail-safe test must remain green.

## Scope

**Problem statement:** Rust cross-file method resolution misses its two most common idiomatic shapes — associated-function calls `Type::assoc_fn()` (entirely unresolved; wrong key form) and `let`-bound struct/constructor receivers (resolved to the variable name, not the type) — and its `use`-import edges carry junk heads that make `1p470`/`1p4ev` import disambiguation inert for Rust.

**In scope:**

- `_resolve_rust_call_target` (`~2785`): `scoped_identifier`-callee `Type::assoc_fn()` → dotted `external::Type.assoc_fn` (generalizing the `::`-split already in `_resolve_rust_new_convention` `~3324`).
- `_search_rust_declarations_in_scope` (`~2699`): infer `let x = Bar{..}` (`struct_expression`) and `let x = Bar::new()` / `Type::from()` (`scoped_identifier`-callee `call_expression`) binding types → so `x.method()` keys on `Bar`, not `x`.
- A dedicated Rust `use_declaration` import extractor: per-item type-name heads, `crate::`/`super::`/`self::` normalization to a project-relative dotted module, keyword-noise suppression.
- The shared-wave `GRAPH_BUILDER_VERSION` bump (coordinated — not per-change) + self-host graph rebuild.
- Regression tests proving each resolved case and the deferred-dispatch fail-safe.

**Out of scope:**

- Trait / `dyn Trait` / generic-bound dispatch (`t.method()` where `t`'s concrete impl is not statically a single named type) — needs a trait-impl table; **deferred**, fail-safe guarded by `test_rust_phantom_method_routes_to_external`.
- `let x = some_fn()` type inference from **arbitrary** function returns (only the *constructor* sub-cases `Bar::new()` / `Type::from()` / struct-literal are in scope; general return-type flow is phantom-prone — consistent with the investigation's deferral).
- Selector-chain / field / index receivers (`a.b.method()`, `s.client.do()`).
- 1p4ev membership-based disambiguation itself (this change is its Rust **precondition** — it supplies clean import substrate + type-keyed methods; 1p4ev consumes them).
- Any non-Rust language resolver.

## Acceptance Criteria

- [x] AC-1: Cross-file `Type::assoc_fn()` resolves. Two files — `config.rs` defining `impl Config { fn load() -> Config }` (registered as `Config.load`), and a caller in another file invoking `Config::load()` — produce a `calls` edge to the project `Config.load` node (`RECEIVER_RESOLVED`), not `external::`. Verified by a graph-build test asserting the edge target is the project node.
- [x] AC-2: A module-function `scoped_identifier` call (`io::stdin()`, lowercase first segment) is **not** mis-resolved as a type — `_resolve_rust_call_target` returns `None`/falls through (no `external::io.stdin` type-keyed edge claiming to be a method on a type). Verified by a unit test on the resolver.
- [x] AC-3: A `let`-bound struct receiver resolves to its type. `let h = Helper { .. }; h.process()` (with `impl Helper { fn process(&self) }` cross-file) emits a `calls` edge to the project `Helper.process` node, not `external::h.process`. Verified by a graph-build test.
- [x] AC-4: A `let`-bound `::new()`/`from()` receiver resolves to its type. `let c = Config::new(); c.run()` keys the call on `Config` (→ `Config.run` project node when defined), not on `c`. Verified by a unit/graph test on `_search_rust_declarations_in_scope` and/or the resulting edge.
- [x] AC-5: The Rust `use`-import extractor emits clean edges. `_rust_use_imports` (`graph_indexer.py`) walks the `use_declaration` tree and emits dotted targets whose final segment is the imported type name (`external::crate.services.Helper`, `external::super.util.Reader`, `external::super.util.Writer`), `imports_by_file`-consumable; an `as` alias's target keeps the REAL type name (the alias head is registered in `import_aliases`). **No** `external::use` / `external::pub` / `external::fn` / `external::as` / lossy `::`-path edge is produced. Verified by `test_rust_use_import_extractor_clean_no_keyword_noise` (CrossFileResolutionTests). The fix also addressed the shared `source_file`-root false-positive (`source` ∈ import keywords matched the grammar root → whole-file regex junk) and added an import-only keyword-noise filter, which cleaned Kotlin/Go/Swift/C imports too.
- [x] AC-6: Trait/`dyn`/generic dispatch stays external (fail-safe). The existing `test_rust_phantom_method_routes_to_external` still passes, and the new `test_rust_generic_receiver_stays_external` (CrossFileResolutionTests) proves a generic receiver (`fn caller<T: Runner>(t: T) { t.run() }`) whose type cannot be statically resolved keeps the call `external::T.run` — never binding a same-named project `Thing.run`. Verified green in the venv.
- [x] AC-7: The shared-wave `GRAPH_BUILDER_VERSION` is bumped exactly once for the wave (not a per-change bump); the rebuilt self-host graph carries the new version and is non-empty. Full `run_tests.py` + `docs-lint` green.

## Tasks

- [x] Extend `_resolve_rust_call_target` (`~2785`): handle `callee_type == "scoped_identifier"` — `::`-split, `parts[-2]` PascalCase guard, `method_name = parts[-1]`, emit dotted `external::<Type>.<method>` (promote via `symbol_lookup`). Factor the `::`-split/PascalCase guard so it and `_resolve_rust_new_convention` (`~3324`) share one helper.
- [x] Extend `_search_rust_declarations_in_scope` (`~2699`): in the `let_declaration` branch, when no `type_identifier` child exists, inspect the value node — if `struct_expression`, take its `name`-field type; if a `call_expression` with a `scoped_identifier` callee, take `parts[-2]`; return that as the inferred type (PascalCase only).
- [x] Add a Rust `use_declaration` import extractor (`_rust_use_imports`/`_rust_walk_use_tree`): per-item final-identifier head + `use_as_clause` alias handling + `crate::`/`super::`/`self::` → dotted-module normalization; the import branch returns early for `rust` `use_declaration` so the generic path (and its keyword noise) is bypassed. Plus the shared root-cause fix: `source_file` excluded from `_ts_is_import_node` + an import-only `_RELATION_KEYWORD_NOISE` filter.
- [~] Add a deferred-boundary in-code comment at the Rust resolver documenting the trait/`dyn`/generic exclusion. **Deferred — superseded:** the trait/`dyn`/generic fail-safe boundary is documented and locked by the passing test `test_rust_generic_receiver_stays_external` (a generic receiver stays `external::T.run`, never binding a same-named project method), which is more durable than a comment.
- [x] Add regression tests: AC-1/3/4 (`test_rust_associated_fn_and_let_binding_resolve`), AC-2 (`test_rust_module_function_call_stays_external`), AC-5 (`test_rust_use_import_extractor_clean_no_keyword_noise`), AC-6 (`test_rust_generic_receiver_stays_external`). All green in the venv.
- [x] Bump the **shared-wave** `GRAPH_BUILDER_VERSION` (coordinate the single wave bump — do not add a per-change bump); rebuild the self-host graph; run `run_tests.py` + `docs-lint`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| assoc-fn-resolution | Engineering | 1p4ef (qualified_index leak fixed — trust precondition) | `_resolve_rust_call_target` `~2785`; reuse `::`-split from `_resolve_rust_new_convention` `~3324`; emit DOTTED form |
| let-binding-inference | Engineering | — | `_search_rust_declarations_in_scope` `~2699`; struct_expression + `::new()`/`from()` |
| use-import-extractor | Engineering | — | new `use_declaration` extractor; clean head + module normalize; precondition for 1p4ev |
| version-bump + rebuild | Engineering | assoc-fn-resolution, let-binding-inference, use-import-extractor | shared-wave `GRAPH_BUILDER_VERSION` (ONE wave bump, not per-change) |
| regression-tests | Engineering | assoc-fn-resolution, let-binding-inference, use-import-extractor | AC-1..AC-6; AC-6 keeps fail-safe green |

## Serialization Points

- The shared-wave `GRAPH_BUILDER_VERSION` bump (`graph_indexer.py:28`) is coordinated across **all** `graph_indexer.py` changes in wave 1p4eq (1p4ef, 1p4er, 1p4es-graph-mode, 1p4et, this change, 1p4ev) — land it **once**, not per-change. This change must not introduce its own bump.
- 1p4ef (leaked-`qualified` fix) is the trust precondition: the assoc-fn promotion relies on the `len(candidates) == 1` guard in the cross-file rewrite pass (`~6429`), which 1p4ef makes reliable. Sequence after 1p4ef lands (or co-land with it in the same wave build).
- This change is the Rust **precondition for 1p4ev**: the clean `use`-import extractor (head = type name → `imports_by_file` at `~6381`) and the type-keyed assoc-fn/let-binding methods are what 1p4ev's membership-disambiguation consumes for Rust.
- If touching the cross-file rewrite pass region (`~6322-6510`) alongside 1p4er/1p4ef, coordinate edits to avoid conflicts in the `qualified_index` / `imports_by_file` blocks.

## Affected Architecture Docs

N/A — this extends existing per-language resolver/extractor machinery (`_resolve_rust_call_target`, `_search_rust_declarations_in_scope`, the import-extraction path) with no module-boundary, control-flow, or verification-architecture change. (If `docs/architecture/graph-index-system.md` is being edited for the wave's other improvements, a one-line note that Rust associated-fns key on the dotted `Type.method` form and `use`-imports now carry type-name heads would fit.)

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | P0 | The headline Rust miss — associated-fn calls are *entirely* unresolved today; the single biggest resolution gain. |
| AC-3 | P0 | `let x = Bar{..}` is the dominant idiomatic receiver binding; without it `x.method()` stays mis-keyed on the variable. |
| AC-6 | P0 | Fail-safe — guarantees the deferred trait/`dyn`/generic boundary does not regress into phantom edges; the trust guard for the whole change. |
| AC-7 | P0 | Resolver/extractor + index-participation change is invisible to consumers without the (shared-wave) version bump + rebuild; gates correctness everywhere. |
| AC-2 | P1 | Correctness guard — prevents over-claiming by mis-typing module-function calls as type methods (avoids the 1p470 over-claim failure mode). |
| AC-4 | P1 | Completes the constructor-binding set (`::new()`/`from()`); high-value but narrower than the struct-literal case. |
| AC-5 | P1 | Clean import substrate — primarily the precondition for 1p4ev; also removes keyword-noise edges. Lower immediate resolution impact than AC-1/AC-3. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Mis-typing a module-function `scoped_identifier` (`io::stdin()`) as a type method, emitting a phantom `external::io.stdin` claiming method-on-type. | PascalCase guard on `parts[-2]` (mirrors `_resolve_rust_new_convention` `~3328`); AC-2 asserts the lowercase-segment case falls through. Only claim coverage for what AC-2 proves. |
| Constructor let-binding inference over-reaching into arbitrary `let x = func()` returns (phantom-prone, the investigation's deferral). | Restrict to `struct_expression` and `scoped_identifier`-callee shapes only; general function-return inference stays out of scope (Out-of-scope + AC-4 fixes the precise shapes). |
| `use`-import normalization mis-mapping `crate::`/`super::`/`self::` to a project module path, producing a wrong `imports_by_file` head that mis-disambiguates downstream. | `1p470`/`1p4ev` disambiguation still requires a UNIQUE `qualified_index` match (`~6429`), so a wrong head only fails to resolve (stays external) rather than mis-resolving; AC-5 asserts head/alias/module shape directly. |
| Trait/`dyn`/generic dispatch silently mis-resolving once `let`-binding inference is broader. | Explicit deferral + in-code boundary comment; AC-6 and the existing `test_rust_phantom_method_routes_to_external` enforce calls with no single statically-named receiver type stay `external::`. |
| Forgetting the version bump (or adding a duplicate per-change bump) — stale consumer caches, or double-bumping the wave. | AC-7 ties to the **single** shared-wave bump + rebuild; Serialization Points flag it as wave-coordinated, not per-change. |
| Over-claiming Rust coverage the way 1p470 over-claimed C#/Go/Rust. | Scope/ACs claim only synthetic-validated shapes that have a passing test; no field-validation or broad-language claims (no team tested Rust — stated explicitly in Rationale). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-06-09 | Implementation complete: Rust `scoped_identifier` associated-fn resolution (`_resolve_rust_call_target`, `graph_indexer.py:2902`) + `_rust_value_type` let-binding inference (`graph_indexer.py:2744`, struct-literal + `::new()`/`from()`). Tests `test_rust_associated_fn_and_let_binding_resolve` + `test_rust_module_function_call_stays_external` (CrossFileResolutionTests) pass; fail-safe `test_rust_phantom_method_routes_to_external` (GoRustScalaReceiverTypeTests) green. 1p4eq adversarial verification rated 1p4eu CLEAN/faithful — lowercase module (`io::stdin()`) + aliased struct correctly stay external; no wrong edges, no faithfulness fix needed. Shared-wave bump landed: graph builder version=25. Full `run_tests.py` suite 2960 green. AC-5 / Task-3 (Rust `use_declaration` import extractor) and the AC-6 new-case test / Task-4 deferred-boundary in-code comment not shipped this round — left unchecked. | `graph_indexer.py:2744,2902`; `tests/test_graph_indexer.py` `test_rust_associated_fn_and_let_binding_resolve`, `test_rust_module_function_call_stays_external`, `test_rust_phantom_method_routes_to_external`; `GRAPH_BUILDER_VERSION = "25"` (`graph_indexer.py:28`); full suite 2960 OK |
| 2026-06-09 | AC-6 closed: added `test_rust_generic_receiver_stays_external` (a generic `fn caller<T: Runner>(t: T){ t.run() }` stays `external::T.run`, never binding a same-named project `Thing.run`) — verified bug-sensitive. AC-5 closed (operator chose implement): `_rust_use_imports` + `_rust_walk_use_tree` extract clean dotted Rust `use` import edges with alias-honoring + no keyword noise (`test_rust_use_import_extractor_clean_no_keyword_noise`). Implementing it exposed a ROOT CAUSE shared with Kotlin/Go/Swift/C: the grammar root `source_file` was substring-matched as an import (`source` ∈ `_TS_IMPORT_KEYWORDS`), so the generic relation fallback regexed the whole file into junk `external::<token>` import edges — fixed by excluding `source_file` in `_ts_is_import_node` + an import-only `_RELATION_KEYWORD_NOISE` filter (NOT applied to call candidates, since `from`/`require`/`default` are valid method names). Java now fully clean; Kotlin keyword noise gone + `as` alias captured in `import_aliases`. Full suite 2962 green. | `graph_indexer.py` `_rust_use_imports`/`_rust_walk_use_tree`, `_ts_is_import_node` (`source_file` guard), `_RELATION_KEYWORD_NOISE`; `tests/test_graph_indexer.py` `test_rust_generic_receiver_stays_external`, `test_rust_use_import_extractor_clean_no_keyword_noise`; full suite 2962 OK |
| 2026-06-09 | Operator follow-up — cleaned the residual cosmetic Kotlin `external::W` alias node: an import candidate that is an `as`-alias whose real target is ALSO a candidate is now skipped in the import branch (the alias stays captured in `import_aliases`; the real type edge is still emitted). Applies uniformly to Kotlin + TS/JS aliased imports. Java/Kotlin/Rust imports now fully clean. New test `test_kotlin_aliased_import_no_bare_alias_node`; full suite 2962 green (TS/JS import tests unaffected). | `graph_indexer.py` import branch (`_node_aliases` skip + `import_aliases.update(_node_aliases)`); `tests/test_graph_indexer.py` `test_kotlin_aliased_import_no_bare_alias_node`; full suite 2962 OK |
