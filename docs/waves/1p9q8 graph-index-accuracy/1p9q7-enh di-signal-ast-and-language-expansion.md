# Graph accuracy: DI binding/injection signals for Python and TypeScript, AST-anchored

Change ID: `1p9q7-enh di-signal-ast-and-language-expansion`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1p9q8 graph-index-accuracy`

> **RECONCILIATION NOTE (reality-checker freshness lane, 2026-07-05): the origin-check convention this change cites as its own contribution now has a LANDED precedent to align with.** Waves 1p9qf/1p9qi (embedded-SQL capture) shipped the framework's canonical origin-check discipline FIRST: a **negative** origin check for distinctive sink names + a **positive** origin check for generic names (`graph_indexer.py:6114-6125`), and a **relation-scoped reserved-namespace** invariant for unresolved targets (`external::sql::<name>`, `graph_indexer.py:12361`; `_sql_embedded_has_interior_error:6180`). 1p9q7's DI idiom-origin requirement (Requirement 4 / the over-fire Risk row — "the idiom callable itself must resolve to the expected import origin") should be framed as ALIGNING with this landed negative/positive convention, and its unresolved-target `external::` handling should consciously decide whether to adopt a reserved-namespace form (e.g. `external::di::`) mirroring `external::sql::` rather than a plain `external::`. The core change (Python/TS DI coverage) is still valid and NOT obsoleted — no Python/TS collectors exist (verified live: `graph_di_signals.py` has only `_collect_java_kotlin_signals`/`_collect_csharp_signals`). See the 2026-07-05 Progress Log row.

## Rationale

Dependency-injection wiring is where call graphs go dark: the framework's `binds`/`injects` edges exist to recover it, but coverage is **Java/Kotlin and C# only**, and the extraction is **regex-based**, not AST-based (`collect_di_signals`, `graph_di_signals.py:47-53`; Java/Kotlin collector `_collect_java_kotlin_signals:56-134`, C# collector `_collect_csharp_signals:137-191`; signals collected at `graph_indexer.py:11608` and merged into the edge map via `resolve_di_edges` at `graph_indexer.py:12148`). Two gaps follow:

1. **Language coverage.** Python and TypeScript target repos get zero DI edges despite hosting the most decorator-explicit DI idioms in current use: FastAPI `Depends(get_service)` (the dependency is a named callable at the call site), and NestJS/InversifyJS constructor injection (`@Injectable()` classes, `@Inject(TOKEN)` params, `@Module({providers: [...]})` registrations, `bind(TOKEN).to(Impl)`).
2. **Extraction fidelity.** Regex over source text cannot see scope, comments, or strings; both extractors for the new languages can be AST-anchored instead — Python via the `ast` module the extractor already uses, TS via the tree-sitter tree already parsed for extraction — so signals attach to real nodes with real source locations rather than pattern offsets.

Scope discipline: this change **adds** AST-anchored Python/TS DI signals; it does **not** rewrite the working Java/Kotlin/C# regex module (regression risk for shipped behavior with no field complaint — see Decision Log). Same edge relations (`binds`, `injects`), same confidence semantics, same unique-candidate refusal on ambiguous targets. Framework-idiom detection is explicit and conservative: signals fire only on the named idioms, not on generic decorator shapes.

## Requirements

1. **Python (FastAPI-idiom) `injects`.** A parameter default of `Depends(callable_ref)` (also `Annotated[T, Depends(callable_ref)]`) emits an `injects` edge from the enclosing function to the resolved `callable_ref` when it resolves same-file or via imports under the unique-candidate rule; unresolved refs follow the existing `external::` convention. `Depends()` with no argument (annotation-driven) emits nothing (no guess).
2. **TypeScript (NestJS/Inversify idioms).** (a) `@Injectable()`-decorated class constructors: each constructor parameter with a class type annotation emits `injects` to the resolved class. (b) `@Inject(TOKEN)` parameters: `injects` to the token's resolved symbol (class or exported const token); string tokens stay `external::`. (c) `@Module({providers: [...]})` provider lists and `bind(X).to(Y)`/`toClass(Y)` calls emit `binds` (interface/token → implementation) mirroring the existing Guice/Autofac edge shape.
3. **AST anchoring.** Python signals come from the existing `ast` walk; TS signals from the existing tree-sitter tree. No regex over raw source for the new languages. Signals carry real source locations.
4. **Resolution and refusal.** All targets resolve through the existing import/unique-candidate machinery; ambiguity → `external::`, never a guess. Decorators/idioms outside the named set emit nothing. Idiom identification is alias-aware (council finding, prepare review 2026-07-03): `from fastapi import Depends as D` / `import { Inject as I } from '@nestjs/common'` must still be recognized (resolve the local name through the import binding to its origin), and a local user-defined `Depends`/`Inject` that does not originate from the idiom's library must NOT fire the signal.
5. **Calibration gate.** Multi-language pack gains a FastAPI-idiom Python fixture and a NestJS/Inversify-idiom TS fixture with known wiring; extracted `binds`/`injects` edge sets asserted exactly (no extras, no misses) — the same exact-set discipline as the JVM/.NET DI tests.
6. **Version bump + adversarial review.** `GRAPH_BUILDER_VERSION` bumped; adversarial faithfulness review at wave review (DI edges are binding claims; over-extraction pollutes impact analysis).

## Scope

**Problem statement:** DI edges exist only for JVM/.NET idioms via regex; Python/TS repos — where DI wiring is decorator-explicit and AST-visible — get no `binds`/`injects` edges, so impact and path analysis go dark exactly at injection seams.

**In scope:**

- AST-anchored Python `Depends` (+`Annotated`) `injects` extraction.
- AST-anchored TS `@Injectable` constructor / `@Inject` param / `@Module` providers / `bind().to()` extraction (`injects` + `binds`).
- Exact-set fixtures in the multi-language pack; adversarial non-idiom/ambiguity tests; version bump.

**Out of scope:**

- Rewriting the existing Java/Kotlin/C# regex module to AST (working, shipped; no field defect — standing decision below).
- Other Python DI frameworks (injector, dependency-injector, wired) and Angular DI — idiom set can grow later behind the same conservative gate.
- Runtime container semantics (scopes, factories, multibindings) — edges record declared wiring only.
- Any new edge relation — `binds`/`injects` only.

## Acceptance Criteria

- [x] AC-1: Python — `Depends(ref)` in defaults and `Annotated[...]` forms emits `injects` to the resolved callable (same-file and imported); bare `Depends()` and non-idiom decorators emit nothing; ambiguous refs stay `external::`; alias-imported `Depends` (`import ... as`) is recognized and a same-named non-FastAPI `Depends` is not. Unit-tested each form including both alias cases. Evidence: `test_python_fastapi_depends_exact_set` (exact-set: 2 same-file + 1 cross-file `injects`, bare `Depends()` yields nothing), `test_python_depends_alias_recognized`, `test_python_depends_impostor_refused` (local-def AND foreign-import impostors), `test_python_depends_ambiguous_stays_external`.
- [x] AC-2: TS — `@Injectable` constructor params, `@Inject(TOKEN)` params, `@Module` providers, and `bind().to()`/`toClass()` each emit the specified edges with resolved targets; string tokens and ambiguous targets stay `external::`; undecorated classes emit nothing. Unit-tested each form. **AND (origin-check faithfulness, mirroring AC-1's Python treatment per Requirement 4): an alias-imported idiom (`import { Inject as I } from 'inversify'`) IS recognized, and a same-named user-defined/non-Inversify `Inject` is REFUSED — the distinctive→negative / generic→positive origin-check discipline applies symmetrically across both new languages, not just Python. Unit-tested both the alias-recognition and impostor-refusal directions.** Evidence: `test_ts_nestjs_injectable_inject_module_exact_set` (exact-set: class-type + `@Inject` identifier resolve, `@Inject('CONFIG')` string → `external::`, primitive param skipped, `@Module` `{provide,useClass}` → `binds`), `test_ts_inversify_alias_recognized_and_bind` (`Inject as I` + lowercase `injectable` recognized; `bind(X).to(Y)`), `test_ts_inject_impostor_and_bind_without_import_refused` (local `function Inject` refused; `bind().to()` without inversify import refused).
- [x] AC-3: AST anchoring — signals carry correct source locations, and idiom text inside strings/comments produces no edges (the regex failure mode explicitly tested against). Unit-tested. Evidence: `test_di_ast_anchoring_ignores_strings_and_comments` (Python `Depends(prov)` in comment + string literal, TS `@Injectable` in comment + string literal → zero edges).
- [x] AC-4: Exact-set calibration — pack fixtures for FastAPI-idiom and NestJS/Inversify-idiom apps assert the complete expected `binds`/`injects` edge sets with zero extras; recorded in the Progress Log. Evidence: `test_python_fastapi_depends_exact_set` and `test_ts_nestjs_injectable_inject_module_exact_set` assert the FULL edge set via `assertEqual` (zero extras); calibration counts in the Progress Log 2026-07-05 row.
- [x] AC-5: Existing JVM/.NET DI extraction byte-identical on its existing test corpus (no shared-code regression). Asserted by the existing suite plus an explicit no-change check on a JVM fixture's DI edge set. Evidence: existing `test_spring_three_file_di_resolution` + `test_dotnet_registration_and_injection` green; new `test_jvm_di_edge_set_unchanged_by_python_ts_expansion` pins the exact Spring DI edge set. The shared `resolve_di_edges` change is opt-in per-signal (`faithful_external`/`*_token` flags set only by the AST collectors), so JVM/.NET signals route through the unchanged path.
- [x] AC-6: `GRAPH_BUILDER_VERSION` bump DEFERRED to the coordinated wave-level 39→40 bump at integration (per wave Journal Watchpoint — `graph_indexer.py` is the shared hub across 1p9q4/1p9q5/1p9q6/1p9q7; a single bump covers all four). The adversarial faithfulness review lane (over-extraction / wrong-target binding) is the mandatory delivery-review lane selected at prepare and runs at wave review. Extraction faithfulness is pre-covered by the exact-set + impostor + AST-anchoring tests. — **[integration 2026-07-05]** the bump portion is DONE: coordinated `39→40` landed (the new Python/TS `injects`/`binds` DI edges + the `external::` unresolved-target decision are named in the changelog head). The remaining clause — the adversarial faithfulness review lane — RAN at delivery review 2026-07-06 (PASS on impostor/over-extraction: non-idiom decorators emit nothing, local/foreign-module impostors refused, aliases recognized, both languages; the code lane separately found the TS `binds` ambiguity bug (arbitrary same-name pick), FIXED in the review fix round with unique-candidate refusal + regression test, primer-verified). Findings dispositioned. AC complete — flipping to [x].
- [x] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes (4,656 tests, was 4,646 baseline + 10 new DI tests); `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [x] Python: `Depends`/`Annotated` detection in the `ast` walk (`collect_python_di_signals`, `graph_di_signals.py`); target resolution through the shared `resolve_di_edges` machinery; `injects` emission. Wired into `_extract_python_artifact` return dict.
- [x] TS: decorator/provider/bind detection in the tree-sitter walk (`collect_ts_di_signals`, `graph_di_signals.py`); token/class resolution; `injects`/`binds` emission. Wired into `_extract_tree_sitter_artifact` (TypeScript only).
- [x] Merge path: new signals route through the shared `resolve_di_edges` (now at `graph_indexer.py:12935`) unchanged in wiring; the AST collectors' signals are MERGED with the text collector (`collect_di_signals`, now `graph_indexer.py:12395`) rather than overwritten — the collect-side merge fix. Faithfulness expressed via opt-in per-signal flags (`faithful_external`, `*_token`) so the JVM/.NET path stays byte-identical.
- [x] Fixtures + tests per AC-1..AC-5 (idiom forms, strings/comments adversarial, ambiguity refusal, exact-set fixtures, JVM/.NET no-change check) + a Java+Python coexistence test (`test_di_signals_java_and_python_coexist`). 10 new tests in `GraphDependencyInjectionTests`.
- [x] Bump `GRAPH_BUILDER_VERSION` — **[integration 2026-07-05]** coordinated wave-level `39→40` bump landed (shared-hub watchpoint); the changelog head names the Python/TS DI edges + the `external::` unresolved-target decision. `run_tests.py` + `wave_validate` (clean) run; `__pycache__` cleaned.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-python-di | implementer | — | `Depends`/`Annotated` AST extraction + resolution + emission. |
| ws2-ts-di | implementer | — | NestJS/Inversify decorator/provider/bind extraction + resolution + emission (parallel to ws1; different extractor). |
| ws3-tests-calibration | implementer | ws1-python-di, ws2-ts-di | Idiom/adversarial/exact-set/no-regression tests; pack fixtures. |
| ws4-adversarial-review | reviewer | ws3-tests-calibration | Red-team: which decorator shapes over-fire, which wiring silently misses? |


## Serialization Points

- ws1/ws2 are genuinely parallel (Python extractor vs TS extractor); both meet at the DI merge point — do not change its shape.
- Shares the Python extractor region with `1p9q4` — coordinate merge order on `graph_indexer.py`; single wave-level `GRAPH_BUILDER_VERSION` bump.
- Pack fixture directory convention shared with `1p9q5` — agree once.

## Affected Architecture Docs

Update DI-signal coverage documentation (wherever `graph_di_signals` scope is described — capability matrix / `docs/specs/mcp-tool-surface.md` graph notes): coverage becomes JVM/.NET (regex, unchanged) + Python/TS (AST-anchored, named idioms), with the conservative idiom-gate stance recorded. No boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Python idiom coverage is half the change. |
| AC-2 | required | TS idiom coverage is the other half. |
| AC-3 | required | AST anchoring is the fidelity claim; strings/comments immunity is its proof. |
| AC-4 | required | Exact-set assertion is the standing DI-test discipline; anything looser hides over-extraction. |
| AC-5 | required | The shipped JVM/.NET path must be provably untouched. |
| AC-6 | required | Standing version-bump and adversarial-review rules for binding-claim changes. |
| AC-7 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Confirmed: DI module is regex-based, Java/Kotlin/C# only (`graph_di_signals.py:47-53,289,333`); merged at `graph_indexer.py:7514-7541`; Python extractor is `ast`-based and TS extraction already holds a tree-sitter tree — both give AST anchoring for free; live self-hosted graph has zero `binds`/`injects` (Python project, no coverage). | `graph_di_signals.py:1-53,289,333`; `graph_indexer.py:7514-7541`; evaluation 2026-07-03. |
| 2026-07-05 | **Implemented (implementer lane).** Python `collect_python_di_signals` + TS `collect_ts_di_signals` added to `graph_di_signals.py`; wired into `_extract_python_artifact` / `_extract_tree_sitter_artifact`; collect-side merge fixed (extend, not overwrite) at `graph_indexer.py:12395`; `resolve_di_edges` gained opt-in `faithful_external`/`*_token` handling (`_external_di_node`, `_resolve_di_target`) leaving the JVM/.NET path byte-identical. **Calibration counts (exact-set fixtures):** Python FastAPI fixture = **3 `injects`, 0 `binds`** (list_items→get_current_user, list_items→get_session [cross-file], show→get_current_user; bare `Depends()` → 0). NestJS/Inversify fixture = **3 `injects` + 1 `binds`** (UserService→UserRepository [type], UserService→`external::CONFIG` [string token], UserService→LoggerToken [`@Inject` id]; primitive param → 0; `@Module` DBToken→PgDb). JVM no-change pin = **1 `binds` + 1 `injects`** (byte-identical to pre-change capture). 10 new tests; full suite **4,656 ok** (baseline 4,646); `wave_validate` clean; `__pycache__` cleaned. Version bump DEFERRED (coordinated 39→40 at integration). | `graph_di_signals.py` (collectors + resolve flags); `graph_indexer.py:12395` (merge), `:12935` (resolve); `tests/test_graph_indexer.py::GraphDependencyInjectionTests`. |
| 2026-07-05 | **Freshness reconciliation (reality-checker lane). Verdict: READY-WITH-CORRECTIONS-APPLIED.** Premise VALID — DI coverage is still Java/Kotlin/C#-only and regex-based; no Python/TS collector exists (`graph_di_signals.py` has only `_collect_java_kotlin_signals:56-134`, `_collect_csharp_signals:137-191`, `resolve_di_edges:245-338`). STALE-ANCHOR fixes: collector anchors `:289`/`:333` were shifted (those lines now fall inside `resolve_di_edges`; the collectors moved to `:56`/`:137`); **DI merge point moved out of the `7514-7541` region entirely (now SQL-recovery code) → `collect_di_signals` call at `graph_indexer.py:11608`, `resolve_di_edges` at `:12148`.** RECONCILIATION: the origin-check discipline 1p9q7 relies on now has a landed precedent (1p9qf/1p9qi negative/positive origin checks `graph_indexer.py:6114-6125`; reserved `external::sql::` namespace `:12361`) — Requirement 4 should align with it, and the unresolved-DI-target namespace should consciously choose plain `external::` vs a reserved `external::di::` form mirroring `external::sql::`. Coordinated version bump target now **39→40**. | live verify 2026-07-05: `graph_di_signals.py:47,56,137,245`; `graph_indexer.py:6114-6125,11608,12148,12361`. |
| 2026-07-06 | **Delivery-review fixes applied (fix lane, within v40 — NO re-bump).** **FIX 2 (WRONG-BIND, code Finding 2):** confirmed the `binds` endpoint resolver `_resolve_di_target` (`graph_di_signals.py`) picked an ambiguous same-name twin ARBITRARILY via `_pick_node` — a repro with two `PgDb` classes bound `useClass: PgDb` / `bind(DBToken).to(PgDb)` to `src/a.ts::PgDb` (shortest-length pick) instead of refusing. Fixed: the faithful branch now applies the injects-path unique-candidate discipline (dedup `_index_type_nodes` double-listing; resolve only on `len==1`, else `external::`). Repro now yields `binds DBToken → external::PgDb`. JVM/.NET (`faithful=False`) path unchanged. Two new tests (`test_ts_binds_ambiguous_useclass_twin_stays_external`, `test_ts_inversify_binds_ambiguous_impl_twin_stays_external`). **FIX 3 (perf):** `collect_python_di_signals`/`collect_ts_di_signals` ran a full extra AST/tree-sitter walk on every file even with zero DI idioms; added a cheap raw-source substring pre-check (`_PY_DI_TRIGGER`, `_TS_DI_TRIGGER_TOKENS`) that short-circuits to `[]` before the walk. Token set is a strict SUPERSET of the collectors' emitting idioms (no false negatives — pinned by `DiSignalPrecheckTests`). | `graph_di_signals.py` (`_resolve_di_target`, trigger constants + both collector pre-checks); `graph_indexer.py:11058` (pass `source_text`); `tests/test_graph_indexer.py::GraphDependencyInjectionTests` (+2), `::DiSignalPrecheckTests` (+5). |
| 2026-07-06 | **Recorded follow-up candidate (performance lane, PRE-EXISTING — not this wave).** `_source_location`'s `splitlines()`-per-symbol call is a hotspot — measured ~42% of Python graph extraction on the self-hosted corpus. It re-splits the whole source once PER extracted symbol; a single memoized line-offset index per file would collapse it to one split. Longstanding (predates 1p9q8), a large future perf lever, and out of scope here — captured so a later performance wave can pick it up. | performance delivery-review lane 2026-07-06; `graph_indexer.py` `_source_location`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Add AST-anchored Python/TS extraction; leave the JVM/.NET regex module untouched (approach A). | Highest-value gap is coverage, not refactoring: Python/TS get edges they never had, AST-anchored because both extractors already hold trees; the shipped regex path has no field defect and rewriting it risks regressing working detection for zero user-visible gain (don't-touch-unrelated principle). | (B) Also port JVM/.NET to AST now — weakness: regression risk on shipped behavior + doubles scope for fidelity parity no one reported missing; revisit on field evidence. (C) Regex for Python/TS too (fastest) — weakness: imports the known string/comment false-positive mode into two new languages when AST is already available; rejected. |
| 2026-07-03 | Conservative named-idiom gate (FastAPI; NestJS/Inversify) rather than generic decorator heuristics. | A generic "decorator with a class arg = DI" heuristic over-fires across the decorator ecosystem (validators, routes, ORMs); named idioms keep every edge a defensible claim. Idiom set is a table — cheap to extend deliberately. | Heuristic decorator matching — rejected as the over-extraction failure mode the adversarial review exists to catch; explicit-idiom refusal is the safe default. |
| 2026-07-03 | Bare/annotation-only `Depends()` emits nothing. | The dependency there is the parameter *type*, resolvable only through annotation semantics owned by `1p9q4`'s signal model; guessing here would double-handle. If both changes land, a follow-up can connect them; not silently in scope. | Emit `injects` to the annotated type — deferred to avoid cross-change entanglement inside one wave. |
| 2026-07-05 | An unresolved/ambiguous DI provider target mints a PLAIN `external::<name>` node, NOT a reserved `external::di::` form. | An unresolved DI provider is an ordinary code symbol in the same namespace as any other `external::` code target (a call that didn't bind, an import that didn't resolve). The reserved `external::sql::` namespace exists because a SQL table is a FOREIGN artifact class that must never collide with a code symbol; a DI provider has no such foreignness. Reflexively mirroring `external::sql::` would fragment the code namespace for no invariant benefit. | (A) Reserved `external::di::` mirroring `external::sql::` — rejected: no cross-artifact collision to prevent; adds a namespace with no consumer. |
| 2026-07-05 | Origin-check reconciled to the landed 1p9qi discipline and applied SYMMETRICALLY across Python and TS: distinctive idiom names (`Depends`, `@Injectable`/`@injectable`, `@Inject`, `@Module`) use a NEGATIVE check (fire unless the local name resolves to a non-DI-library origin; an unbound canonical spelling self-identifies and fires); the generic name `bind` uses a POSITIVE check (emit `bind().to()` only when the file imports the Inversify container). Alias-imported idioms resolve through the import binding to their origin; same-named user-defined idioms are refused. | Matches the framework's shipped negative/positive origin-check convention (`graph_indexer.py` embedded-SQL sinks); keeps every DI edge a defensible claim while recognizing legitimate aliasing. Symmetric treatment closes both the over-fire (impostor) and under-fire (alias) failure modes in both new languages per the qa-amended AC-2. | (A) Positive check for ALL idioms (original Requirement 4 wording) — rejected: over-refuses an unbound canonical `@Injectable`/`Depends` that is genuinely the idiom (e.g. star-imported), which the negative check correctly fires on. (B) No origin check (name-only) — rejected: the over-extraction failure mode the adversarial lane exists to catch. |
| 2026-07-05 | Collect-side plumbing MERGES extractor-sourced AST signals with the text-based `collect_di_signals`, rather than the text collector overwriting them. | The AST-anchored Python/TS signals originate in the language extractors and are already on `artifact["di_signals"]` when the unconditional text collector runs at the call site; the prior `artifact["di_signals"] = collect_di_signals(...)` would wipe them (the text collector returns `[]` for Python/TS). The resolve side is unchanged in wiring — all signals, regardless of source language, flow through the single `resolve_di_edges` call. | Overwrite (status quo) — rejected: silently drops every Python/TS AST signal. Second resolve pass for AST signals — rejected: needless duplication of the merge point. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Idiom detection over-fires on similarly-named non-DI decorators/functions (`Depends` from another library, a local `bind()`). | Resolution requirement: the idiom callable itself must resolve to the expected import origin where checkable (e.g. `fastapi.Depends` import path), else no edge; adversarial tests include same-named impostors; exact-set fixtures catch extras. |
| TS decorator syntax variance (experimental vs standard decorators, parameter properties) misses wiring. | Fixtures cover both decorator emit modes; misses are visible in the exact-set assertion; unsupported forms are a documented limitation, not a silent gap (fallback = no edge, never a guess). |
| Shared-code drift regresses JVM/.NET DI. | New code lives in the two language extractors, meeting only at the merge point; AC-5 no-change check pins the existing edge sets. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
