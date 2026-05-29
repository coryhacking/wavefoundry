# Graph Dependency-Injection Wiring

Change ID: `12ynp-enh graph-dependency-injection-wiring`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-28
Wave: `12xr2 graph-query-surface`

## Rationale

The graph indexer extracts structural relations by reading what is literally written in source: `defines`, `imports`, and `calls` edges from tree-sitter/AST analysis, plus inferred `doc_references_code` edges. That model captures static wiring accurately, but it is blind to **dependency-injection (DI) frameworks**, where the concrete collaborator a class uses is chosen by a container at runtime rather than named at the call site.

In a Spring (Java/Kotlin), Jakarta CDI, Guice/Dagger, or .NET `Microsoft.Extensions.DependencyInjection` codebase, a consumer typically depends on an **interface** and the container binds that interface to a concrete **implementation** elsewhere (an `@Component`/`@Service` class, an `@Bean`/`@Provides` method, or a `services.AddScoped<IFoo, Foo>()` registration). Static extraction sees the consumer importing/using `IFoo`, but never draws an edge to `Foo`. The result is a graph that systematically under-reports the real dependency structure of the most common enterprise stacks:

- `code_impact` (planned in `12xr2 graph-query-surface`) under-reports blast radius — changing a concrete implementation looks like it affects nothing because no edge points to it.
- `code_callgraph` stops at the interface boundary instead of following the wired implementation.
- Orphan / fan-in analysis misclassifies injected implementations as unused.

This change teaches the graph extractor to recognize DI wiring patterns and emit explicit **injection edges** so the graph reflects how the application is actually composed, not just how the syntax reads. Java and .NET are the priority targets; the design must be extensible to other DI ecosystems.

## Requirements

1. Add a directional injection relation to the graph edge vocabulary that links a consumer (or registration site) to the dependency it receives, distinct from `calls`/`imports`. Suggested relations:
   - `injects` — consumer → the dependency type it receives (constructor/field/setter/parameter injection).
   - `binds` — a container registration (interface or token) → the concrete implementation it resolves to.
   - The two together let traversal hop consumer → interface → concrete implementation even when no static edge exists.
2. Extract injection edges for the priority frameworks:
   - **Java / Kotlin — Spring & JSR-330/Jakarta CDI**: provider stereotypes (`@Component`, `@Service`, `@Repository`, `@Controller`, `@RestController`, `@Configuration`, `@Named`, CDI beans); `@Bean`/`@Produces` factory methods; injection points via `@Autowired`, `@Inject`, `@Resource`, constructor injection on annotated beans, and `@Qualifier`/`@Named` disambiguation.
   - **Java — Guice / Dagger**: `bind(IFoo.class).to(Foo.class)` in `AbstractModule`s; Dagger `@Module` + `@Provides`/`@Binds` methods; `@Inject` injection points.
   - **.NET / C#**: `IServiceCollection` registrations (`AddSingleton`, `AddScoped`, `AddTransient`, `AddHostedService`, and `TryAdd*` variants) in both generic (`AddScoped<IFoo, Foo>()`) and factory-lambda forms; constructor injection into resolved types; `[FromServices]`; common third-party containers (Autofac `RegisterType<Foo>().As<IFoo>()`) where cheaply detectable.
3. Resolve binding targets to existing graph nodes where possible (the implementation class node, the `@Bean` method node, the interface node) so injection edges connect real nodes rather than dangling string targets; degrade to a labeled unresolved target only when no node match exists.
4. Tag injection-edge provenance and confidence honestly:
   - Explicit registrations with both interface and implementation named (`AddScoped<IFoo, Foo>()`, `bind(...).to(...)`) are higher-confidence.
   - Annotation-only inference (e.g., a single-implementation `@Service` matched to an injected interface) is `INFERRED` and must carry `evidence`.
   - Never silently fabricate a binding when an interface has multiple candidate implementations and no qualifier disambiguates them; record ambiguity rather than guessing a single edge.
5. Preserve the canonical graph contract: directional `source` → `target` edges, per-edge provenance/`evidence`, and the existing persisted schema/versioning. Bump `GRAPH_BUILDER_VERSION` so existing caches force a clean rebuild when this extractor lands.
6. Keep extraction grammar-aware (tree-sitter where the language is supported) with regex only as an explicit fallback, consistent with `12y4x-enh graph-tree-sitter-language-coverage`.
7. Make framework coverage explicit and individually testable, so reviews can verify which DI patterns each ecosystem supports and so unsupported patterns degrade safely rather than emitting noise.
8. Structure extraction as a two-phase collect-then-resolve pipeline (see **Tree-Sitter Support and Recommended Extraction Strategy**): collect per-file DI signal records during the tree walk, and resolve them into `binds`/`injects` edges in the global assembly pass that already has the whole-repo node/symbol view.

## Scope

**Problem statement:** The graph cannot represent runtime dependency wiring established by DI containers, so structural queries (`code_impact`, `code_callgraph`, fan-in/orphan analysis) are misleading on Spring, CDI, Guice/Dagger, and .NET DI codebases.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — new injection-edge extraction, edge vocabulary, binding resolution, confidence tagging, builder-version bump.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — representative fixtures per framework.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — only if graph API snapshots need new edge-kind assertions.
- Documentation of the new edge relations and their confidence semantics.

**Out of scope:**

- Full runtime resolution semantics: bean scopes/lifecycles, Spring profiles/`@Conditional`, AOP proxies, lazy/factory indirection, generic-type fan-out, assembly-scanning conventions.
- New tree-sitter grammars beyond the chunker's existing surface.
- Semantic/LLM-derived edges.
- Dashboard styling beyond what is needed to render and label the new edge kinds.
- Query-surface tools themselves (`code_impact`, `code_callgraph`) — those are owned by `12xr2 graph-query-surface`; this change only supplies the edges they will traverse.

## Framework Coverage Target

| Ecosystem | Provider / binding signals | Injection-point signals |
| --------- | -------------------------- | ----------------------- |
| Spring (Java/Kotlin) | `@Component`/`@Service`/`@Repository`/`@Controller`/`@RestController`/`@Configuration`, `@Bean` methods | constructor injection on beans, `@Autowired`, `@Inject`, `@Resource`, `@Qualifier`/`@Named` |
| Jakarta CDI / JSR-330 | managed beans, `@Produces` | `@Inject`, `@Named`, `@Qualifier` |
| Guice | `bind(...).to(...)`, `@Provides` in `AbstractModule` | `@Inject` |
| Dagger | `@Module` + `@Provides`/`@Binds` | `@Inject` |
| .NET DI | `Add{Singleton,Scoped,Transient}[<I,Impl>]`, `TryAdd*`, `AddHostedService` | constructor injection, `[FromServices]` |
| Autofac (.NET) | `RegisterType<Impl>().As<I>()` | constructor injection |

Each row must be independently covered by tests, and a framework with no detectable signals must produce no injection edges rather than spurious ones.

## Tree-Sitter Support and Recommended Extraction Strategy

**What tree-sitter does and does not provide.** Tree-sitter is purely syntactic. Grammars are per-*language*, not per-*framework* — there is no "Spring" or ".NET DI" grammar. What the Java/Kotlin/C# grammars do expose as first-class structured nodes is exactly what DI detection needs: annotations (`annotation` / `marker_annotation` / `annotation_argument_list`), C# attributes (`attribute` / `attribute_list` / `attribute_argument`), generic type arguments, constructor parameters, and invocation expressions. That makes *detecting* DI signals (e.g. `@Bean`, `@Autowired`, `[FromServices]`, `AddScoped<IFoo, Foo>()`) robust and grammar-anchored instead of regex-led. Tree-sitter provides **no semantic support** for the part that matters most: name resolution, type binding, single-implementation inference, and qualifier disambiguation are all on us. In short, tree-sitter helps with **signal detection**, never with **binding resolution**.

**Two extraction mechanisms are available:**

1. **Extend the existing manual walker** (`walk_definitions` / `walk_calls` in `graph_indexer.py`) to recognize annotation/attribute/registration nodes. Consistent with the current code and with `12y4x-enh graph-tree-sitter-language-coverage`.
2. **Introduce the tree-sitter query API** (`.scm` S-expression patterns with `#eq?`/`#match?`/`#any-of?` predicates) as a new, declarative pattern surface specifically for DI patterns. The extractor does **not** use this API today.

**Recommendation — a two-phase "collect-then-resolve" pipeline using mechanism (1):**

- **Phase 1 — per-file signal collection (in the existing tree walk).** Recognize provider declarations (stereotype-annotated classes, `@Bean`/`@Provides`/`@Binds` methods, `IServiceCollection`/Autofac registrations) and injection points (constructor/field/setter parameters and their annotations). Do **not** resolve targets here. Emit lightweight **signal records** alongside the existing per-file `nodes`/`edges` artifact, each capturing: signal kind, the owning node id and source location, the type name(s) exactly as written, and any qualifier/name. This is the "walk the tree and collect certain attributes like annotations" half of the idea.
- **Phase 2 — global resolution (in the existing assembly pass).** The assembly stage already builds the combined cross-layer `node_map` and a whole-repo symbol-term index, and already performs inferred cross-file linking (`doc_references_code`) and short-symbol pruning there. Resolve the collected signal records against that whole-repo symbol table into `binds`/`injects` edges, applying interface → implementation matching, qualifier disambiguation, single-implementation inference, and honest confidence assignment. Unresolved or ambiguous signals are recorded explicitly rather than guessed. This is the "query them at the end across all files for matches / marry them up in the graph" half of the idea.

**Why this shape.** DI bindings are inherently cross-file — the registration lives in a `Startup`/`Module`/`@Configuration` file, the implementation in another file, and the consumer in a third. A per-file walk cannot resolve them in isolation, so resolution must run after all files are parsed. The indexer already follows this exact collect-then-resolve pattern for symbol-term doc linking, so adding a DI resolution step to the assembly pass is architecturally consistent and low-risk. Keep the `.scm` query API (mechanism 2) as an optional future optimization if the annotation-matching branches in the walker become unwieldy; do not adopt it as a parallel mechanism in this change. Note that Phase 2 "querying" is plain Python over the global tables, not tree-sitter queries.

## Acceptance Criteria

- [ ] AC-1: The graph edge vocabulary includes directional injection relation(s) (`injects`, and a registration `binds` relation) distinct from `calls`/`imports`, with per-edge provenance and confidence.
- [ ] AC-2: Spring/CDI/JSR-330 provider stereotypes and injection points produce injection edges connecting consumers to the resolved implementation (directly, or via interface → implementation binding).
- [ ] AC-3: .NET `IServiceCollection` registrations in generic and factory forms produce `binds` edges from the service type to the implementation type, and constructor-injected consumers produce `injects` edges.
- [ ] AC-4: Guice/Dagger module bindings (`bind().to()`, `@Provides`/`@Binds`) produce `binds` edges to the provided implementation.
- [ ] AC-5: Binding targets resolve to existing graph nodes when a match exists; unresolved targets are labeled explicitly rather than dropped or fabricated.
- [ ] AC-6: Confidence is honest — explicit interface+impl registrations are higher-confidence than annotation-only inference; ambiguous single-interface/multi-implementation cases do not emit a guessed single edge.
- [ ] AC-7: The canonical graph contract is preserved (directional edges, provenance, versioned persistence); `GRAPH_BUILDER_VERSION` is bumped so stale caches rebuild.
- [ ] AC-8: Tests cover each framework row in the coverage table, including a negative case proving no injection edges are emitted when signals are absent.
- [ ] AC-9: Extraction follows the two-phase design — per-file signal collection during the tree walk and cross-file resolution in the global assembly pass — verified by a test where a registration, an implementation, and a consumer live in three separate files and still resolve into connected `binds`/`injects` edges.

## Tasks

- [ ] Define the injection edge relation(s) and confidence conventions; document them alongside existing relations.
- [ ] Add a per-file DI **signal-record** collection layer to the existing tree walk (Phase 1), without resolving targets.
- [ ] Add Java/Kotlin annotation and module signal collection (Spring, CDI/JSR-330, Guice, Dagger) on the tree-sitter path with regex fallback.
- [ ] Add .NET registration and constructor-injection signal collection (Microsoft DI + Autofac) on the tree-sitter path with regex fallback.
- [ ] Implement Phase 2 resolution in the global assembly pass: match signals to nodes, disambiguate qualifiers, infer single-implementation bindings, emit `binds`/`injects` edges, and record unresolved/ambiguous signals explicitly.
- [ ] Bump `GRAPH_BUILDER_VERSION` and confirm cache invalidation behaves like other extractor-semantic changes.
- [ ] Add per-framework fixtures and negative tests in `test_graph_indexer.py`, plus a cross-file resolution test (registration, implementation, consumer in three files).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| edge vocabulary + confidence model | implementer | existing graph baseline | New `injects`/`binds` relations, provenance contract |
| jvm DI extraction | implementer | edge vocabulary | Spring, CDI/JSR-330, Guice, Dagger |
| dotnet DI extraction | implementer | edge vocabulary | Microsoft DI + Autofac |
| binding resolution | implementer | jvm + dotnet extraction | Resolve targets to nodes; handle unresolved/ambiguous |
| tests | qa-reviewer | implementation | Per-framework fixtures + negative cases |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py` (edge vocabulary and builder-version bump are shared touchpoints for all extraction workstreams)
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` and `docs/architecture/chunking-and-indexing-pipeline.md` should note that the graph extractor now emits DI/injection edges for supported frameworks and that these edges carry `INFERRED` confidence for annotation-only inference. No layering-rule or domain-map boundary changes are expected.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Injection edges need a first-class, distinct relation to be queryable |
| AC-2 | required | Spring is the dominant Java DI target this change exists to address |
| AC-3 | required | .NET DI is the dominant target on the other priority stack |
| AC-4 | important | Guice/Dagger broaden JVM coverage but are secondary to Spring |
| AC-5 | required | Edges must connect real nodes to be useful for impact/callgraph |
| AC-6 | required | Dishonest confidence would poison downstream impact analysis |
| AC-7 | required | The persisted graph contract must stay stable and rebuildable |
| AC-8 | required | Coverage and negative tests are needed before non-trivial reliance |
| AC-9 | required | DI wiring is inherently cross-file; resolution must work across separate files |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-28 | Drafted as a future-wave enhancement to extend graph extraction with DI/injection wiring for Java and .NET frameworks. | `graph_indexer.py` (current `defines`/`imports`/`calls` model), `12xr2 graph-query-surface/wave.md` |
| 2026-05-28 | Added the tree-sitter capability analysis and recommended a two-phase collect-then-resolve extraction pipeline grounded in the indexer's existing global assembly pass. | `graph_indexer.py` per-file `walk_definitions` + global `node_map`/symbol-term assembly stage |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-28 | Model DI wiring as new `injects`/`binds` edge relations rather than overloading `calls`. | Keeps static call semantics clean and lets query tools treat runtime wiring distinctly with its own confidence. | Reuse `calls` (rejected: conflates static and container-resolved relations) |
| 2026-05-28 | Annotation-only inference is `INFERRED` with mandatory evidence; explicit interface+impl registrations are higher-confidence. | Container resolution is heuristic; downstream impact analysis must be able to discount low-confidence edges. | Treat all injection edges as `EXTRACTED` (rejected: overstates certainty) |
| 2026-05-28 | Scope the priority frameworks to Spring/CDI/Guice/Dagger (JVM) and Microsoft DI/Autofac (.NET), with an extensible design. | Matches the requested Java/.NET focus while leaving room for Angular/NestJS/FastAPI later. | Attempt all DI ecosystems at once (rejected: scope/noise risk) |
| 2026-05-28 | Treat tree-sitter as a signal-*detection* aid only, not a binding-*resolution* aid. | Tree-sitter is purely syntactic — it surfaces annotation/attribute/registration nodes reliably but has no name resolution, type binding, or framework knowledge; interface→impl resolution is custom logic regardless. | Assume tree-sitter can resolve wiring (rejected: it cannot) |
| 2026-05-28 | Adopt a two-phase collect-then-resolve pipeline: collect DI signal records per file during the tree walk, resolve to `binds`/`injects` edges in the global assembly pass. | DI bindings are inherently cross-file (registration, implementation, and consumer live in different files), so resolution must run after all files are parsed; the indexer already uses this exact pattern for symbol-term doc linking and short-symbol pruning, making it consistent and low-risk. | Resolve during the per-file walk (rejected: cannot see other files); resolve eagerly without a signal-collection layer (rejected: duplicates cross-file bookkeeping the assembly pass already owns) |
| 2026-05-28 | Implement Phase 1 by extending the existing manual tree walker rather than introducing the tree-sitter `.scm` query API. | Keeps one extraction mechanism consistent with the current code and `12y4x`; the `.scm` query API would add a parallel pattern surface to maintain. | Use `.scm` queries now (deferred: kept as an optional future optimization if annotation-matching branches grow unwieldy) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Annotation/registration heuristics produce false or noisy edges | Require explicit evidence, record ambiguity instead of guessing, and gate each framework behind tests including negative cases |
| Single-interface-to-many-implementations cases fabricate misleading edges | Do not emit a guessed single binding when multiple candidates exist and no qualifier disambiguates |
| Extractor change silently reuses stale graph caches | Bump `GRAPH_BUILDER_VERSION` to force a clean rebuild |
| Coverage drifts from the chunker's tree-sitter surface | Keep extraction grammar-aware with regex fallback, aligned with `12y4x` |
| DI edges inflate graph size on large enterprise repos | Keep edges symbol-oriented and provenance-tagged; measure node/edge growth on a representative fixture |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
