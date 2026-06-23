# String-literal argument extraction for annotation and call-site bindings

Change ID: `1p7dh-enh string-literal-arg-extraction`
Change Status: `planned`
Owner: Engineering
Status: planned
Wave: `1p7de graph-edge-trust`
Last verified: 2026-06-22

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

- [ ] AC-1: the extractor captures string-literal arguments on annotations and the declared binding call sites, stored with the node.
- [ ] AC-2: advice-registration edges (advice-class → instrumented-type) and config-key→reader edges are emitted with an honest, distinct literal-derived `confidence`/`relation`.
- [ ] AC-3: the binding-site set is declared/bounded (catalog, project-tunable) — no open-ended string-literal scan; index size impact is measured and acceptable.
- [ ] AC-4: adversarial faithfulness review passes (external oracle where available) — literal-derived bindings are correct, not plausible-but-wrong.
- [ ] AC-5: `GRAPH_BUILDER_VERSION` bumped (shared with `1p7dg`); one-time re-extraction documented.
- [ ] AC-6: measured on the consumer pack — Java advice "who applies this" resolves; "which code reads `factor_review_policy`" resolves without hand-parsing; recorded as the value gate.
- [ ] AC-7: framework tests cover literal capture + both edge types + the bounded-scope guard, bytecode-free; `wave_validate` clean.

## Tasks

- [ ] Open `framework_edit_allowed`; close after.
- [ ] Add string-literal-arg capture (annotations + declared binding sites) + the declared binding-site catalog.
- [ ] Emit advice-registration + config-key→reader edges with literal-derived confidence.
- [ ] Coordinate the shared `GRAPH_BUILDER_VERSION` bump with `1p7dg`; upgrade-notes line.
- [ ] Tests (capture + edges + bounded-scope) bytecode-free; faithfulness review + consumer-pack measurement; record verdicts.

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


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Divergent pre-plan — selected: capture string-literal args + emit binding edges, bounded by a declared site catalog** | Unlocks the AOP + config-reader answer classes that two consumers needed, while the declared catalog keeps the index from bloating on every string literal. | (B) Index every string literal as a node — rejected: bloat + noise + false edges. (C) Leave it to query-time `code_keyword` — rejected: that is the hand-work this exists to remove, and it can't model the binding. |
| 2026-06-22 | Edges carry a distinct literal-derived confidence | Literal-derived bindings are weaker than resolved calls; consumers must be able to tell them apart (and traversal/`1p7df` can weight them). | Treat them as resolved — rejected: over-trust, the exact mistake we're fixing elsewhere. |
| 2026-06-22 | Defer the query-tool surface (`code_advice_sites` / config-xref) to a follow-on | Get the edges right + faithfulness-reviewed first; a tool over wrong edges is worse than no tool (the `code_risk_score` lesson). | Ship tool + edges together — rejected: couples a UX surface to an unproven extraction. |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Literal-derived edges are plausible-but-wrong                        | Distinct low confidence + adversarial faithfulness review with an external oracle (AC-4).           |
| Open-ended string scan bloats the index                             | Declared/bounded binding-site catalog (AC-3); measure index-size impact.                            |
| Heaviest of the three — scope creep                                  | Edges only; the query-tool surface is an explicit follow-on, not this change.                        |
| Double re-extraction with `1p7dg`                                    | Shared single `GRAPH_BUILDER_VERSION` bump (wave serialization).                                    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
