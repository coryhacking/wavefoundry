# Graph model: extends/implements inheritance edges for Java and C#, with inherited-method resolution and dispatch-aware impact

Change ID: `1p9qa-enh inheritance-edges-java-csharp`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

The graph has **no inheritance model for any language**: the emitted relation vocabulary is `defines`/`calls`/`imports`/`reads`/`reads_config`/doc-refs plus DI `binds`/`injects`; `extends`/`implements`/`throws` exist only in stop-word suppression sets (`_TS_STOP_JAVA`, `graph_indexer.py:1090-1096`), confirmed against `docs/specs/mcp-tool-surface.md:223,238` and the live payload (guru investigation, 2026-07-03).

For enterprise Java and C# — interface-driven by convention (Spring services behind interfaces, DAO/repository interfaces, .NET service abstractions) — this makes the graph blind at exactly the seams those codebases organize around:

- Interface → implementation navigation is impossible (`code_references` on an interface method finds call sites but not implementations).
- `code_impact` through an interface call dies at the interface: callers of `UserService.find()` show no blast radius into `UserServiceImpl`.
- Calls to methods defined only on a supertype never resolve: `_resolve_java_call_target` builds the literal `ReceiverType.method` and looks it up (`graph_indexer.py:5098-5102`) with no supertype walk, so `repo.save()` where `save` lives on the base class lands on `external::Repo.save` even with everything in-project.
- `super.foo()` is explicitly deferred (`graph_indexer.py:2685-2686`, "uncertain — defer inheritance walk").

Both grammars expose the facts directly (Java `superclass`/`super_interfaces` fields; C# `base_list`), and the existing unique-candidate cross-file machinery can resolve supertype names with the same discipline as receiver types. Scope is Java + C# (the two enterprise targets); Kotlin is deferred — its supertype syntax differs enough to deserve its own calibration, and the mechanism table this change builds makes adding it cheap.

## Requirements

1. **New edge relations.** `extends` (class → superclass; interface → extended interfaces) and `implements` (class → interface) join the relation vocabulary. Targets resolve through the existing import/unique-candidate machinery; unresolved supertypes get `external::<Name>` targets (qualified where the declaration is), never dropped. Confidence follows the existing taxonomy (declaration-derived resolution ≥ `RECEIVER_RESOLVED`-class evidence; ambiguous → `external::`).
2. **Java extraction.** `class_declaration.superclass`, `super_interfaces`, `interface_declaration.extends_interfaces`, `enum_declaration.interfaces`, `record_declaration.interfaces` produce the edges. Generic type arguments are stripped to the raw type name (`List<Foo>` → `List`).
3. **C# extraction.** `base_list` entries produce edges; the first base resolving to a project `class` is `extends`, project `interface` candidates are `implements`; when the kind of an unresolved base is unknowable (C# grammar does not distinguish), emit `implements` for `I`-prefixed-convention names ONLY if that convention check is measurement-validated in calibration, else emit a single conservative `extends_or_implements`-free choice: unresolved bases uniformly emit `implements` is a guess — instead emit relation `extends` for the first unresolved base and `implements` for the rest, and record the convention explicitly in the doc (C# semantics: at most one base class, listed first). Nested/qualified names normalize per `1p9q5`'s namespace keys if that change has landed; otherwise exact-string.
4. **Inherited-method resolution.** When `ReceiverType.method` fails lookup, walk the receiver's `extends`/`implements` chain (project-resolved edges only, breadth-first, bounded depth constant) and bind to `Supertype.method` when exactly **one** supertype in the walk defines it; multiple definers → `external::ReceiverType.method` (never guess an override winner). `super.foo()` resolves via the enclosing class's single `extends` target when project-resolved. **Bind provenance (council finding, prepare review 2026-07-03):** every inherited-method bind carries an edge property recording the supertype hop it resolved through — a wrong supertype edge amplifies into many wrong call binds, and provenance is what makes that failure mode auditable in calibration and adversarial review rather than invisible.
5. **Dispatch-aware impact.** `code_impact` traverses `implements`/`extends` edges in the callee direction (a call on an interface method includes implementations in the blast radius) at a distinct, documented traversal weight (down-weighted like `EXTRACTED` edges — dispatch is potential, not proven). `code_graph_path` treats inheritance edges as structural (existing high structural cost tier, like `imports`/`defines`) so call paths still dominate.
6. **Consumers + version bump.** `GRAPH_BUILDER_VERSION` bumped; `docs/specs/mcp-tool-surface.md` relation vocabulary updated; graph report/community/cluster passes accept the new relations without special-casing (verify the derived-undirected projection in `graph_cluster.py` simply includes them).
7. **Calibration gate.** Multi-language pack Java (existing) and C# fixtures gain inheritance scenarios; before/after resolution counts recorded; a hand-verified sample of inherited-method binds at ≥95% precision.
8. **Adversarial review.** Binding-faithfulness change (the supertype walk is a new binding mechanism) → adversarial review lane at wave review per the standing rule.

## Scope

**Problem statement:** No inheritance edges exist for any language, so interface→implementation structure, supertype-defined method calls, `super.` calls, and dispatch-aware impact are all invisible in the two languages whose enterprise codebases are organized around inheritance.

**In scope:**

- `extends`/`implements` extraction for Java and C#; unique-candidate supertype resolution; generic-argument stripping.
- Bounded single-definer inherited-method resolution + `super.` resolution.
- Impact/path traversal semantics for the new relations; spec doc update; version bump.
- Pack fixtures (Java + C#) with calibration counts and precision sample.

**Out of scope:**

- Kotlin, Go (embedding), Rust (traits), TS/Python inheritance — each needs its own semantics pass; the relation vocabulary this change adds is language-neutral so they can follow.
- `throws` edges (no consumer identified; revisit on demand).
- Override-graph modeling (which override wins at a virtual call site) — the single-definer rule deliberately refuses that question.
- MRO/diamond resolution beyond the single-definer refusal.

## Acceptance Criteria

- [ ] AC-1: Java — classes/interfaces/enums/records with superclass/interface lists emit `extends`/`implements` edges to project-resolved targets (unique-candidate; ambiguous stays `external::`); generic arguments strip to the raw name. Unit-tested per declaration form plus an ambiguity refusal case.
- [ ] AC-2: C# — `base_list` produces edges per the first-base-is-class convention; project-resolved bases get their true kind-based relation; nested/compound namespace targets resolve. Unit-tested including the unresolved-base convention case.
- [ ] AC-3: Inherited-method resolution — `receiver.method()` where `method` is defined on exactly one project-resolved supertype binds to it; defined on two supertypes in the walk → `external::` refusal; `super.foo()` binds via the single `extends` target; depth bound respected. Unit-tested each way (single, multiple-definer refusal, super, depth cap).
- [ ] AC-4: `code_impact` on an interface method includes implementing classes' methods at the documented down-weighted confidence; `code_graph_path` does not prefer inheritance edges over real call chains (cost-tier test). Unit-tested against a fixture graph.
- [ ] AC-5: Cluster/report/community passes ingest payloads with the new relations without error, and the graph payload `counts` remain consistent. Integration-shaped test.
- [ ] AC-6: Calibration recorded — pack Java + C# inheritance fixtures pass; before/after resolution counts and a hand-verified ≥95%-precision sample of inherited-method binds in the Progress Log.
- [ ] AC-7: `GRAPH_BUILDER_VERSION` bumped; `docs/specs/mcp-tool-surface.md` relation vocabulary updated; adversarial review lane run and findings dispositioned.
- [ ] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Add the `extends`/`implements` relations to the graph model constants and emission paths; Java extraction from the five declaration forms; generic stripping.
- [ ] C# extraction from `base_list` with the first-base convention; namespace-key normalization hook.
- [ ] Supertype unique-candidate resolution reusing the import/disambiguation machinery (including `1p9q9`'s wildcard facts when landed).
- [ ] Inherited-method walk (bounded BFS, single-definer rule) + `super.` resolution in `_resolve_java_call_target` and the C# resolver.
- [ ] Impact/path traversal weights for the new relations; spec doc vocabulary update.
- [ ] Pack fixtures + unit tests per AC-1..AC-5; calibration run + precision sample.
- [ ] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-model-and-java | implementer | — | Relation constants + Java extraction + supertype resolution. |
| ws2-csharp | implementer | ws1-model-and-java | C# `base_list` extraction on the settled model. |
| ws3-inherited-resolution | implementer | ws1-model-and-java | Bounded walk + single-definer rule + `super.`; the binding core, smallest reviewable diff. |
| ws4-consumers | implementer | ws1-model-and-java | Impact/path weights; cluster/report ingestion check; spec update. |
| ws5-tests-calibration | implementer | ws2-csharp, ws3-inherited-resolution, ws4-consumers | Fixtures, adversarial cases, calibration + precision sample. |
| ws6-adversarial-review | reviewer | ws5-tests-calibration | Faithfulness red-team on the supertype walk (wrong-definer, diamond, external-bridge cases). |


## Serialization Points

- Land after `1p9q9` (import fixes) — supertype resolution consumes import facts; building on broken wildcard handling would double-test the same paths.
- The relation-vocabulary constants (ws1) gate every other workstream.
- Coordinate the wave-level `GRAPH_BUILDER_VERSION` bump; `docs/specs/mcp-tool-surface.md` is also touched by wave `1p9q3` (`wave_graph_report` metadata) — merge order on that doc at integration.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — relation vocabulary (`:223,238`) gains `extends`/`implements`, and `code_impact`/`code_graph_path` entries document dispatch traversal semantics. Any capability matrix describing per-language extraction gains the inheritance column. This is a graph-model contract change — record the relation addition and the single-definer refusal stance as a decision note.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Java inheritance edges are the core capability. |
| AC-2 | required | C# parity is the operator-directed scope of this wave. |
| AC-3 | required | Inherited-method resolution is the recall payoff; the refusal cases are its faithfulness guard. |
| AC-4 | required | Wrong traversal semantics would corrupt impact/path results for every consumer. |
| AC-5 | required | New relations must not break downstream analysis passes. |
| AC-6 | required | Calibrate-don't-guess; the precision sample is the shipping evidence. |
| AC-7 | required | Standing version/spec/adversarial-review rules for model + binding changes. |
| AC-8 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Confirmed: no inheritance relations exist for any language (stop-word-only occurrences, `graph_indexer.py:1090-1096`; spec `:223,238`; live payload relation census); resolver has no supertype walk (`graph_indexer.py:5098-5102`), `super.` deferred (`:2685-2686`); Java/C# grammars expose superclass/base_list fields. | Guru investigation 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Model-level relations + single-definer inherited resolution + down-weighted dispatch traversal, Java + C# together (approach A). | One builder-version bump and one consumer migration for both enterprise languages; the single-definer rule extends the never-guess stance to inheritance (refuses override-winner questions); down-weighting keeps dispatch potential from polluting proven call paths. | (B) Java only, C# later — weakness: second model bump + second consumer pass for a language whose grammar exposes identical facts; operator directed C# inclusion. (C) Resolve inherited methods without persisting inheritance edges (walk at resolution time only) — weakness: leaves interface→implementation navigation and dispatch impact unsolved; the edges are the durable value, resolution is a beneficiary. (D) Full override modeling (virtual dispatch winners) — weakness: unsound without whole-program analysis; the single-definer refusal is the faithful boundary. |
| 2026-07-03 | Kotlin deferred. | Different supertype syntax (constructor-call supertypes, delegation `by`) deserves its own fixtures/calibration; the language-neutral relation vocabulary makes the later addition cheap. | Include Kotlin now — rejected: scope growth in the wave's riskiest change; revisit after Java/C# calibration. |
| 2026-07-03 | `throws` not added. | No consumer identified for exception-flow edges; adding unconsumed relations violates simplest-solution-first. | Add for completeness — rejected: speculative. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The supertype walk binds through a wrong-twin supertype (ambiguous supertype name resolved incorrectly). | Supertype names resolve through the same unique-candidate machinery with refusal; the walk uses only project-resolved edges (never walks through `external::`); adversarial review targets wrong-twin and diamond shapes; AC-3 refusal tests. |
| Dispatch traversal explodes impact results on wide interfaces (one interface, 40 implementations). | Down-weighted confidence + existing impact weakest-link combining keeps dispatch-derived paths visibly lower-confidence; result-shaping limits unchanged; calibration observes result-size deltas on pack fixtures. |
| C# first-base-is-class convention mislabels an unresolved interface as `extends`. | The relation kind for project-resolved bases uses the true target kind; the convention applies only to unresolved (`external::`) bases where the mislabel is inert for resolution and impact (both relations traverse identically); documented explicitly. |
| Downstream consumers (cluster projection, report) choke on unknown relations. | AC-5 ingestion test; the cluster projection is relation-agnostic (derived-undirected) by design — verified, not assumed. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
