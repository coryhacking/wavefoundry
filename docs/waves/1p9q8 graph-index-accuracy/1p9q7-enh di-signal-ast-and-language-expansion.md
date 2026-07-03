# Graph accuracy: DI binding/injection signals for Python and TypeScript, AST-anchored

Change ID: `1p9q7-enh di-signal-ast-and-language-expansion`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Dependency-injection wiring is where call graphs go dark: the framework's `binds`/`injects` edges exist to recover it, but coverage is **Java/Kotlin and C# only**, and the extraction is **regex-based**, not AST-based (`graph_di_signals.py:47-53`; Spring/Guice at `:289`, .NET/Autofac at `:333`; merged into the edge map at `graph_indexer.py:7514-7541`). Two gaps follow:

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

- [ ] AC-1: Python — `Depends(ref)` in defaults and `Annotated[...]` forms emits `injects` to the resolved callable (same-file and imported); bare `Depends()` and non-idiom decorators emit nothing; ambiguous refs stay `external::`; alias-imported `Depends` (`import ... as`) is recognized and a same-named non-FastAPI `Depends` is not. Unit-tested each form including both alias cases.
- [ ] AC-2: TS — `@Injectable` constructor params, `@Inject(TOKEN)` params, `@Module` providers, and `bind().to()`/`toClass()` each emit the specified edges with resolved targets; string tokens and ambiguous targets stay `external::`; undecorated classes emit nothing. Unit-tested each form.
- [ ] AC-3: AST anchoring — signals carry correct source locations, and idiom text inside strings/comments produces no edges (the regex failure mode explicitly tested against). Unit-tested.
- [ ] AC-4: Exact-set calibration — pack fixtures for FastAPI-idiom and NestJS/Inversify-idiom apps assert the complete expected `binds`/`injects` edge sets with zero extras; recorded in the Progress Log.
- [ ] AC-5: Existing JVM/.NET DI extraction byte-identical on its existing test corpus (no shared-code regression). Asserted by the existing suite plus an explicit no-change check on a JVM fixture's DI edge set.
- [ ] AC-6: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane covers over-extraction (non-DI decorators) and wrong-target binding; findings dispositioned.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Python: `Depends`/`Annotated` detection in the `ast` walk; target resolution through existing machinery; `injects` emission.
- [ ] TS: decorator/provider/bind detection in the tree-sitter walk; token/class resolution; `injects`/`binds` emission.
- [ ] Merge path: route new signals through the existing DI merge point (`graph_indexer.py:7514-7541`) unchanged in shape.
- [ ] Fixtures + tests per AC-1..AC-5 (idiom forms, strings/comments adversarial, ambiguity refusal, exact-set pack fixtures, JVM/.NET no-change check).
- [ ] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

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


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Add AST-anchored Python/TS extraction; leave the JVM/.NET regex module untouched (approach A). | Highest-value gap is coverage, not refactoring: Python/TS get edges they never had, AST-anchored because both extractors already hold trees; the shipped regex path has no field defect and rewriting it risks regressing working detection for zero user-visible gain (don't-touch-unrelated principle). | (B) Also port JVM/.NET to AST now — weakness: regression risk on shipped behavior + doubles scope for fidelity parity no one reported missing; revisit on field evidence. (C) Regex for Python/TS too (fastest) — weakness: imports the known string/comment false-positive mode into two new languages when AST is already available; rejected. |
| 2026-07-03 | Conservative named-idiom gate (FastAPI; NestJS/Inversify) rather than generic decorator heuristics. | A generic "decorator with a class arg = DI" heuristic over-fires across the decorator ecosystem (validators, routes, ORMs); named idioms keep every edge a defensible claim. Idiom set is a table — cheap to extend deliberately. | Heuristic decorator matching — rejected as the over-extraction failure mode the adversarial review exists to catch; explicit-idiom refusal is the safe default. |
| 2026-07-03 | Bare/annotation-only `Depends()` emits nothing. | The dependency there is the parameter *type*, resolvable only through annotation semantics owned by `1p9q4`'s signal model; guessing here would double-handle. If both changes land, a follow-up can connect them; not silently in scope. | Emit `injects` to the annotated type — deferred to avoid cross-change entanglement inside one wave. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Idiom detection over-fires on similarly-named non-DI decorators/functions (`Depends` from another library, a local `bind()`). | Resolution requirement: the idiom callable itself must resolve to the expected import origin where checkable (e.g. `fastapi.Depends` import path), else no edge; adversarial tests include same-named impostors; exact-set fixtures catch extras. |
| TS decorator syntax variance (experimental vs standard decorators, parameter properties) misses wiring. | Fixtures cover both decorator emit modes; misses are visible in the exact-set assertion; unsupported forms are a documented limitation, not a silent gap (fallback = no edge, never a guess). |
| Shared-code drift regresses JVM/.NET DI. | New code lives in the two language extractors, meeting only at the merge point; AC-5 no-change check pins the existing edge sets. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
