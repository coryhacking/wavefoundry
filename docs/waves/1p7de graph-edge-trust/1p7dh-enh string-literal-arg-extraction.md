# String-literal argument extraction for annotation and call-site bindings

Change ID: `1p7dh-enh string-literal-arg-extraction`
Change Status: `implementing`
Owner: Engineering
Status: implementing
Wave: `1p7de graph-edge-trust`
Last verified: 2026-06-23

## Rationale

The graph index stores annotation and call **names** but not their **string-literal arguments**. That blind spot blocks a whole class of edges that real consumers needed:

- **AOP / advice (Java/ByteBuddy, AspectJ):** the index records that a class has `@Advice.OnMethodEnter` etc., but not the pointcut/type string that says *what it instruments*. So "where is this advice actually applied?" can't be answered from the graph — the Java consumer had to be told to `code_keyword` for the instrumentation registration by hand.
- **Config-key binding:** `workflow-config.json`/`repo-profile.json` keys appear as nodes, but there is no edge from a config key to the code that **reads** it. The `1p7ac` factor-gate bug was two config surfaces disagreeing (`repo-profile.factor_review` vs `workflow-config.factor_review_policy`); debugging it meant hand-parsing both JSON files because the graph couldn't answer "which code reads this key?".
- Similar gaps: route/endpoint strings → handlers, SQL identifiers, DI tokens.

This change **captures string-literal arguments** at annotations and selected call sites and emits the corresponding binding edges (advice-registration, config-key→reader). It is an **extractor change → shared `GRAPH_BUILDER_VERSION` bump with `1p7dg`**, and a binding change → faithfulness review. It is the heaviest of the three and unlocks both the AOP and config-cross-reference answer classes.

**Language/framework-specific, not universal (addressed at interrogation).** Annotations/decorators are a Java/Kotlin/C#/Python/TS construct — **not** Go/Rust/C natively (Go has struct tags, Rust attributes/macros — different shapes, out unless evidence warrants) — and config getters vary per language. So this is **not** a uniform-across-all-languages change: the binding-site + annotation catalog is declared **per language/framework**, an edge type is emitted for a language only where the construct exists **and** it clears the real-consumer-pack value gate, and the string-literal *capture* itself is syntactic (tree-sitter recovers it reliably) — it is the *binding* accuracy (literal → target) that is gated and faithfulness-reviewed.

## Requirements

1. **Capture string-literal args.** Extend the extractor to record string-literal arguments on (a) annotations (e.g. the type/pointcut string on advice annotations) and (b) a bounded, declared set of binding call sites (config getters, route registrars) — not every call (scope control). Store the literal alongside the existing annotation/call node.
2. **Emit binding edges.** From the captured literals, emit edges: advice-class → instrumented-type (AOP registration), and config-key → reader (the code site that reads a config key by its literal name). Use a distinct, honest `confidence`/`relation` so consumers can tell a literal-derived binding from a resolved call.
3. **Bounded, declared, per-language/framework scope.** The set of binding call sites + annotation patterns is declared **per language/framework** (a catalog, tunable per project like `code_navigation_hints`) — annotations are Java/Kotlin/C#/Python/TS (Go/Rust/C use different shapes, out unless evidence warrants); config getters vary per language. Not an open-ended scan of every string literal (index bloat + false edges). An edge type ships for a language only where the construct exists **and** it clears the consumer-pack value gate (R6) — no uniform-across-all-languages promise.
4. **Faithfulness review.** Adversarial review (external oracle where available — e.g. compare advice-registration edges against the actual instrumentation wiring on a sample Java repo) before close; literal-derived bindings are exactly where plausible-but-wrong edges hide.
5. **`GRAPH_BUILDER_VERSION` bump (shared with `1p7dg`).** New node/edge shape → bump so consumers re-extract; coordinate a single shared re-extraction with `1p7dg` (see wave serialization), and document it in the upgrade notes.
6. **Measured value on the real graphs.** On the consumer pack: advice-registration edges resolve the Java AOP "who applies this advice" question, and config-key→reader edges answer "which code reads `factor_review_policy`" without hand-parsing. Ship only where the new edges are correct + useful.

## Scope

**In scope:** string-literal-arg capture at annotations + a declared set of binding call sites in `graph_indexer.py`; the advice-registration + config-key→reader edges; the declared binding-site catalog; the shared `GRAPH_BUILDER_VERSION` bump; tests + the faithfulness review.

**Out of scope:** a new query tool surface to expose these (e.g. `code_advice_sites`) — that is a separate follow-on once the edges exist; receiver resolution (`1p7dg`); traversal confidence (`1p7df`); unbounded string-literal indexing.

**Depends on:** none for implementation; pairs with `1p7dg` on the shared builder bump.

## Acceptance Criteria

- [x] AC-1: string-literal-arg capture done on **both** surfaces and **both config ecosystems** — config getters/subscripts (`.get("KEY")`/`cfg["KEY"]`, Python) + **Java/Spring** `@Value("${key}")` placeholders and `getProperty`/`getRequiredProperty("key")`; and AOP **OTel `typeMatcher()` ByteBuddy matcher strings** (Java `_java_aop_matcher_strings` + `_AOP_TYPE_MATCHERS`, incl. multi-arg `namedOneOf` and structural-wrapper-nested matchers).
- [x] AC-2: both binding surfaces emitted with honest, distinct kinds — config-key→reader is an EDGE (`reads_config` relation, `LITERAL_DERIVED` confidence) to the config-key node it reads: `file.json::key` (Python/JSON) **and now `application.{yml,properties}::dotted.key` (Java/Spring)** — `.properties`/`.yml`/`.yaml` emit config-key nodes (yaml via the declared `tree-sitter-yaml` grammar, not pyyaml). AOP advice registration is a NODE PROPERTY (`instruments` on the instrumentation class) — reframed from an edge at the recon (`advises` dropped: OTel targets ~100% third-party, so an advice→project-type edge binds nothing; a property answers "what does this instrument" without inventing nodes or false-edge risk).
- [x] AC-3: bounded/declared — config edges are self-bounding (no literal nodes; emitted only on a unique config-key-node match) + triple-gated (`_is_config_file_path` + `_config_literal_is_distinctive` + unique). AOP capture is scoped to the SPI `typeMatcher()` method and a declared `_AOP_TYPE_MATCHERS` set (so `transform()` method/parameter matchers are excluded); no index bloat.
- [x] AC-4: **config** validated faithful on the self-host graph (43 `reads_config` edges; the loose first cut's ~137 false positives caught + fixed by the gates). **AOP `instruments` DOWNSTREAM-VALIDATED on `aceiss/javaagent`**: **14→24 classes**, all real external pointcut targets across 6 frameworks, method-matcher noise (`java.lang.String`/`isUserInRole`/`java.util.List`) fully excluded on real data. The `namedOneOf` + structural-wrapper (`implementsInterface`/`hasSuperType`) fix closed not just the 2 flagged classes (Neo4j/Shopizer) but 8 more using the same idioms (JDBC/LDAP/servlet/Hibernate/SpringWeb×2/SailPoint/ofbiz). No cross-node binding → no wrong-twin class.
- [x] AC-5: `GRAPH_BUILDER_VERSION` bumped **32→35** (coordinated with `1p7dg`; version-pin test tracks it). Each post-32 increment is an extraction-output change per the bump-on-logic-change discipline: 33 (the original wave bump), 34 (namedOneOf/structural-wrapper `instruments` refinement), 35 (`.properties`/`.yml` config-key nodes + Java `@Value`/`getProperty` capture). Consumers re-extract once at the wave's release.
- [x] AC-6: value confirmed on real data — **config** "which code reads `<config key>`" resolves (`1p7ac`; on Java, constant-keyed config served by the `reads`→constant relation, 26 ACEISS_* edges); **AOP** "what does this instrumentation weave into" now answerable from the `instruments` property on the real javaagent graph (hibernate/servlet/spring-security/broadleaf/ofbiz/sailpoint targets captured).
- [x] AC-7: framework tests cover Python/JSON config (`ConfigKeyReaderEdgeTests`, 6) + Java/Spring config (`JavaConfigReaderEdgeTests`, 5) + AOP (`OtelInstrumentsPropertyTests`, 6) + bounded-scope/faithfulness guards; full suite **3425 OK** bytecode-free; `wave_validate` clean.

## Tasks

- [x] Open `framework_edit_allowed`; close after.
- [x] Add string-literal-arg capture — config getters/subscripts (Python) + AOP OTel `typeMatcher()` matcher strings (Java).
- [x] Emit the binding surfaces — config-key→reader `reads_config` edge + AOP `instruments` node property (reframed from an edge per the recon).
- [x] Coordinate the shared `GRAPH_BUILDER_VERSION` bump with `1p7dg`; upgrade-notes line — done: 32→35; upgrade-path docs (seed 160 + prompt + `CHANGELOG [1.8.1]`) updated + the upgrade index phase re-extracts the graph symmetric with semantic.
- [x] Tests + bounded-scope/faithfulness guards — config (Python 6 + Java/Spring 5) + AOP (6) + upgrade graph-step (2); full suite **3427 OK**.
- [x] Downstream confirmation: `reads_config` validated (self-host 43 + javaagent 25 config keys); AOP `instruments` verified on `aceiss/javaagent` (24 classes / 36 targets, zero method-matcher noise).

## Agent Execution Graph


| Workstream      | Owner       | Depends On  | Notes                                                  |
| --------------- | ----------- | ----------- | ------------------------------------------------------ |
| literal-capture | implementer | —           | annotations + declared binding sites; bounded scope    |
| binding-edges   | implementer | literal-capture | advice-registration + config-key→reader            |
| builder-version | implementer | binding-edges | shared bump with `1p7dg`                             |
| faithfulness    | reviewer    | all above   | external-oracle adversarial review + consumer-pack gate |


## Serialization Points

- Shares the `GRAPH_BUILDER_VERSION` bump with `1p7dg` — one coordinated re-extraction for both extractor changes. The new-tool surface (`code_advice_sites` / config-xref) is an explicit follow-on, not this change.

## Affected Architecture Docs

- **Update:** the graph-extraction architecture doc — the new string-literal binding edges (advice-registration, config-key→reader) + the bounded-scope catalog + the builder-version bump. Crosses the extraction contract. Confirm scope at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Literal capture is the foundational deliverable. |
| AC-2 | required  | The binding edges are the point — with honest literal-derived confidence. |
| AC-3 | required  | Bounded/declared scope prevents index bloat + false edges from an open scan. |
| AC-4 | required  | Literal-derived bindings are where wrong-but-plausible edges hide — adversarial review is mandatory. |
| AC-5 | required  | Builder bump for the new edge shape; shared with `1p7dg`. |
| AC-6 | important | Real-graph value gate — the edges must answer the AOP + config-reader questions. |
| AC-7 | required  | Test-locked capture + edges + scope guard, bytecode-free. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created. Index stores annotation/call names but not string-literal args, blocking AOP advice-registration edges (Java consumer needed `code_keyword` by hand) and config-key→reader edges (the `1p7ac` factor-gate bug was two config surfaces disagreeing, debugged by hand-parsing JSON). Extractor change; shares the builder bump with `1p7dg`. The query-tool surface is a deferred follow-on. | MCP code-tool quality log session 6 (§3.1 code_advice_sites deferred); the `1p7ac` config-cross-reference debugging this session |
| 2026-06-23 | **config-key→reader edge IMPLEMENTED + validated faithful (local).** Capture `.get("KEY")`/`cfg["KEY"]` literals in the Python extractor (`graph_indexer.py` CallCollector), resolve to `file.json::key` config-key nodes in `finalize` → `reads_config` edge, `LITERAL_DERIVED` confidence. `ConfigKeyReaderEdgeTests` (6) + suite **3414 OK** bytecode-free. **KEY FAITHFULNESS LESSON:** the first cut matched any JSON key → ~137 edges with rampant false positives (`["source"]`/`.get("kind")`/`e.get("confidence")` binding to data-JSON keys in `retrieval_eval.json`/`source-map.json`) — **synthetic tests PASSED while the real graph was wrong.** Only real-graph inspection caught it; tightened with the config-file + key-distinctiveness gates → 43 edges, all genuine workflow-config/repo-profile keys. **Implication for AOP:** literal-derived faithfulness CANNOT be established by synthetic tests alone — the AOP advice-registration edge must be built against the real Java consumer graph (`aceiss/javaagent`) where false positives are inspectable, exactly as the wave's external-oracle review (AC-4) requires. AOP capture/edges deferred to that loop rather than built blind. | `graph_indexer.py` `_is_config_file_path`/`_config_literal_is_distinctive` + CallCollector config_reads + finalize config pass; real-graph rebuild (43 faithful edges) |
| 2026-06-23 | **Upgrade index phase now updates the GRAPH too (operator-directed; completes the re-extraction AC).** The upgrade detected + logged a `GRAPH_BUILDER_VERSION` transition but only acted on the chunker transition — the graph relied on the lazy first-query rebuild, so a graph-builder bump (like this wave's 32→35) didn't materialize during the upgrade for an incremental-update consumer. Fixed: `phase_index_update`/`phase_index_rebuild` now run `setup_index.py --graph-only` (update path) / `--graph-only --full` (rebuild path) blocking after the semantic step — version-aware (incremental, escalating to a full re-extract on a builder bump), symmetric with the semantic indexes; first-query rebuild remains the safety net. `upgrade_wavefoundry.py`; 2 tests (`test_phase_index_update_runs_graph_only_update`, `test_phase_index_rebuild_runs_graph_only_full`); suite **3427 OK**. Upgrade-path docs (seed 160 + `upgrade-wavefoundry.prompt.md` + `CHANGELOG [1.8.1]`) updated to the symmetric framing (replacing the stale "moving to 1.6.0 bumps both" examples). | operator: "run an update at the end of the upgrade — same as semantic"; `upgrade_wavefoundry.py` `phase_index_update`/`phase_index_rebuild` |
| 2026-06-23 | **`reads_config` EXTENDED to Java/Spring file config (builder 34→35).** Closes the deferred follow-on. New: `.properties`/`.yml`/`.yaml` files emit config-key NODES (`file::dotted.key`, kind `class`) — `.properties` via stdlib line parse, `.yml/.yaml` via the **declared `tree-sitter-yaml` grammar** (NOT pyyaml, which is undeclared — single path, no fallback). `_is_config_file_path`/`_is_json_config_node_id` extended to those suffixes + Spring `application*`/`bootstrap*` basenames. Java artifacts capture `@Value("${key:default}")` placeholders + `getProperty`/`getRequiredProperty("key")` into `config_read_candidates`; the language-agnostic finalize pass binds them on the existing unique config-file + distinctive-key gate (no false-positive surface added). `JavaConfigReaderEdgeTests` (5: yaml @Value→edge, properties getProperty→edge, `${k:default}` extraction, unmatched→none, non-config-yaml→none); Python/JSON `ConfigKeyReaderEdgeTests` unbroken; suite **3425 OK**. (Operator correction folded in: the first cut had a pyyaml-or-stdlib-fallback dual path — replaced with the single declared tree-sitter-yaml path.) | `graph_indexer.py` `_extract_config_artifact`/`_parse_properties_keys`/`_parse_yaml_keys` (tree-sitter) + `_java_value_annotation_keys`/`_java_config_getter_key` + the Java `config_read_candidates` flow; v35 |
| 2026-06-23 | **AOP gap fix VERIFIED on real data — broader than the 2 flagged + builder bumped 33→34.** Re-run on `aceiss/javaagent`: `instruments` coverage **14→24 classes** — the `namedOneOf`+structural-wrapper fix recovered the 2 flagged (Neo4j/Shopizer) PLUS 8 more on the same idioms (JDBC `java.sql.Driver`, LDAP/JNDI ×3, servlet Filter/Session lists, Hibernate, SpringWeb ×2, SailPoint, ofbiz `Security`). Method-matcher noise still NONE. **Builder bumped 33→34** because the `instruments` refinement is an extraction-output change: under the same v33 an incremental-update consumer (skips unchanged files unless builder_version changes) would NOT pick up the broadened targets — the operator confirmed v33-p7j5 only showed 24 via a FORCED rebuild. Version-pin test → "34"; suite 3420 OK. | operator downstream re-run; the builder-version-on-logic-change discipline (`feedback_graph_builder_version_bump`) |
| 2026-06-23 | **Both surfaces DOWNSTREAM-VALIDATED on `aceiss/javaagent` (v33 build) + an AOP coverage gap found & closed.** `instruments`: **14 TypeInstrumentation classes / 16 real external pointcut targets** across 6 frameworks (hibernate, servlet, spring-security, broadleaf, ofbiz, sailpoint) — method-matcher noise (`named("isUserInRole")`, `java.lang.String/Object` arg matchers in `transform()`) **completely excluded** (the `typeMatcher()` scoping held on real data). **Gap:** 2 classes (Neo4j, Shopizer) missed — they declare targets via `implementsInterface(namedOneOf(...))` / `hasSuperType(namedOneOf(...))`, idioms the first cut didn't read (no `namedOneOf`; only first arg captured). **Fixed same session:** added `namedOneOf`/`*OneOf` to `_AOP_TYPE_MATCHERS` + capture ALL string args; the inner `namedOneOf` is independently buffered so the structural wrappers need no explicit unwrapping (confirmed by `OtelInstrumentsPropertyTests` Neo4j/Shopizer cases). +3 tests; suite **3420 OK**. `reads_config`: on javaagent the config keys are **Java constants** (`AceissAutoConfiguration.ACEISS_*`, 26 `reads`→constant edges), not JSON — so the config-reader answer class is served by the pre-existing `reads`→constant relation there; my `reads_config` is Python/JSON-config-scoped (validated on the self-host graph, 43 edges). | operator downstream run on 1.8.1+p7j1 + the precise Neo4j/Shopizer diagnosis; `graph_indexer.py` `_AOP_TYPE_MATCHERS`/`_java_aop_matcher_strings` |
| 2026-06-23 | **AOP advice registration IMPLEMENTED as a node PROPERTY (operator chose option (i)).** Capture OTel `TypeInstrumentation.typeMatcher()` ByteBuddy matcher strings (`named(...)`/`nameStartsWith(...)`/… in `_AOP_TYPE_MATCHERS`) via `_java_aop_matcher_string`, scoped to the `typeMatcher()` method (so `transform()` method/param matchers are excluded), and attach as `instruments: [...]` on the enclosing instrumentation class node. Collapse-aware: falls back to the file/module node when the dominant class merged into it (`collapsed_pair`). NO edge, NO invented nodes → no false-binding risk; synthetic Java fixtures suffice (`OtelInstrumentsPropertyTests`, 3, incl. transform()-exclusion). Full suite **3417 OK** bytecode-free; `wave_validate` clean. Remaining: a downstream `instruments`-dump on `aceiss/javaagent` to confirm the real captures (descriptive, light); shared builder bump. | `graph_indexer.py` `_AOP_TYPE_MATCHERS`/`_java_aop_matcher_string` + buffered-calls capture + post-walk `instruments` attach; `tests/test_graph_indexer.py::OtelInstrumentsPropertyTests` |
| 2026-06-23 | **AOP Phase-0 recon (real Java graph) — KILLS the project-node `advises` edge model for this consumer.** `aceiss/javaagent` (233 .java, 591 project types) is **ByteBuddy-DSL** (104 signals: `named()`×54/`nameStartsWith()`×2 in OTel `InstrumentationModule`/`TypeInstrumentation` `typeMatcher()` + `@Advice.OnMethodEnter/Exit`×48), **0 AspectJ**. Make-or-break: of 56 captured matcher strings, **0% are project types**, 89.3% external (`org.hibernate.*`, `javax/jakarta.servlet.*`, `java.lang.*`), 10.7% method-name matchers (`isUserInRole`). An OTel agent instruments **third-party** types by design → an `advises` edge that binds only project-type nodes binds **nothing** here. The advice *class* is a project node; the *target* is external. So the edge must be reframed (advice→external-type node, or capture the matcher string as a node property) or dropped — NOT the original advice→project-type model. Recon caught this before any extractor was written. | `experiments/1p7dh-aop-surface-census.py` (Phase-0 census; operator-run, read-only); sample rows (`named("org.hibernate.boot.Metadata")` etc.) |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Divergent pre-plan — selected: capture string-literal args + emit binding edges, bounded by a declared site catalog** | Unlocks the AOP + config-reader answer classes that two consumers needed, while the declared catalog keeps the index from bloating on every string literal. | (B) Index every string literal as a node — rejected: bloat + noise + false edges. (C) Leave it to query-time `code_keyword` — rejected: that is the hand-work this exists to remove, and it can't model the binding. |
| 2026-06-22 | Edges carry a distinct literal-derived confidence | Literal-derived bindings are weaker than resolved calls; consumers must be able to tell them apart (and traversal/`1p7df` can weight them). | Treat them as resolved — rejected: over-trust, the exact mistake we're fixing elsewhere. |
| 2026-06-22 | Defer the query-tool surface (`code_advice_sites` / config-xref) to a follow-on | Get the edges right + faithfulness-reviewed first; a tool over wrong edges is worse than no tool (the `code_risk_score` lesson). | Ship tool + edges together — rejected: couples a UX surface to an unproven extraction. |
| 2026-06-23 | **Build the AOP advice-registration edge against the real Java consumer graph, not blind/synthetic** | The config slice proved literal-derived faithfulness is invisible to synthetic tests (they passed while the real graph had ~137 mostly-false edges; only real-graph inspection + tightening fixed it). AOP pointcut/DSL binding is more fragile and there is no local Java AOP to inspect — building it blind would ship the same false-positive class undetected. The wave already requires an external-oracle review (AC-4) on a real Java repo; do the build there. | (a) Build AOP now with synthetic tests only (the operator's "full now" choice) — revised by the faithfulness lesson: synthetic-only would give false confidence. (b) Drop AOP — no, it is the Java consumer's needed answer class; build it in the consumer-graph loop. |
| 2026-06-23 | **The original advice→project-type `advises` edge is NOT VIABLE for the real consumer — reframe or drop (operator decision pending)** | Phase-0 recon: OTel/ByteBuddy agents instrument THIRD-PARTY types (0% project, 89.3% external on `aceiss/javaagent`). A project-node→project-node edge binds nothing. The recon (running against the real graph before any build) is exactly what the consumer-graph loop is for — it caught a dead edge model cheaply. | Options now: (i) capture the matcher target string as a **property** on the OTel `TypeInstrumentation`/advice-class node ("instruments `org.hibernate.boot.Metadata`") — answers "what does this advise" without inventing nodes; (ii) emit advice→**external-type** synthetic nodes; (iii) drop the AOP edge from this wave (config-key→reader remains the shippable deliverable). |
| 2026-06-23 | AOP → **option (i), node property** (operator chose); then closed the `namedOneOf` + structural-wrapper (`implementsInterface`/`hasSuperType`) coverage gap surfaced by the real javaagent graph | Property answers the consumer's question with zero false-edge risk; the gap fix (multi-arg `namedOneOf` + capture-all-args; inner matcher buffered so no explicit unwrap) reached full 16/16-class coverage on the real repo, faithfulness-safe. | (ii)/(iii) not taken. |
| 2026-06-23 | **`reads_config` left Python/JSON-config-scoped; Java constant-keyed config served by the existing `reads`→constant relation — unify/extend deferred (follow-on)** | On `aceiss/javaagent` the config keys are Java CONSTANTS (`AceissAutoConfiguration.ACEISS_*`), not JSON, and the pre-existing `reads`→constant relation already answers "which code reads this key" there (26 edges). Extending `reads_config` to Java getter+constant config is real but the answer class is already met, so it is not in this wave. | (a) Extend `reads_config` to Java now — deferred (answer class already served by `reads`); (b) unify `reads_config` into `reads` — a relation-contract change, follow-on. |
| 2026-06-23 | **Follow-on DONE: `reads_config` extended to Java/Spring FILE config** (operator: "definitely worth it, proceed") | The valuable Java gap is file-based Spring config (`@Value("${k}")`, `application.{yml,properties}` by literal) — NOT the constant-keyed case (`reads`→constant already covers that). Built: `.properties`/`.yml`/`.yaml` config-key nodes + Java `@Value`/`getProperty` capture; the existing finalize gate provides faithfulness. | n/a — the constant-keyed sub-case stays on `reads`→constant by design. |
| 2026-06-23 | **YAML keys parsed via the declared `tree-sitter-yaml` grammar, NOT pyyaml** (operator: "assume pyyaml available or don't — don't do both") | pyyaml is NOT in `REQUIRED_IMPORTS`, so "assume it" would be a latent ImportError downstream; `tree-sitter-yaml` IS declared and is the indexer's native parser for every other format. Single path, no fallback, no undeclared dep. | (a) Assume pyyaml — rejected (undeclared). (b) pyyaml-with-stdlib-fallback (the first cut) — rejected: two parsers, the "both" the operator flagged. |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Literal-derived edges are plausible-but-wrong                        | Distinct low confidence + adversarial faithfulness review with an external oracle (AC-4).           |
| Open-ended string scan bloats the index                             | Declared/bounded binding-site catalog (AC-3); measure index-size impact.                            |
| Heaviest of the three — scope creep                                  | Edges only; the query-tool surface is an explicit follow-on, not this change.                        |
| Double re-extraction with `1p7dg`                                    | Shared single `GRAPH_BUILDER_VERSION` bump (wave serialization).                                    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
