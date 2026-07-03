# Graph accuracy: Python receiver resolution from annotations and constructor assignments

Change ID: `1p9q4-enh python-receiver-annotation-resolution`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Python extraction uses native `ast.parse` (`_extract_python_artifact`, `graph_indexer.py:5665`) but has no receiver-type resolution path: while Java, Kotlin, C#, Go, Rust, Scala, Swift, PHP, and TS/JS each have a `_resolve_*_call_target` resolver (e.g. `graph_indexer.py:5066,3241,3493,4463`), Python method calls through a receiver (`self.store.put(...)`, `client.fetch(...)`) resolve only when the bare-name/unique-candidate machinery happens to bind them — otherwise they stay `external::` or, worse for recall, produce no `RECEIVER_RESOLVED` edges at all. Python is the framework's own implementation language, so this is the single largest recall gap in the self-hosted graph (7,674 function nodes; `calls` edges dominated by `EXTRACTED` confidence).

Python offers deterministic, no-inference-engine signals that a resolver can use without guessing:

- parameter and attribute annotations (`def f(store: ArtifactStore)`, `self.store: ArtifactStore = ...`),
- direct constructor assignment (`self.store = ArtifactStore(...)`, `store = ArtifactStore(...)` in local scope),
- module-level constants assigned from constructors.

Binding only on these explicit signals — same-file or import-resolvable class targets, unique-candidate rule unchanged — upgrades a meaningful slice of Python `calls` edges to `RECEIVER_RESOLVED` while preserving the framework's core faithfulness stance: never bind on ambiguity, dynamic dispatch stays unresolved. This directly improves `code_impact`/`code_graph_path` quality, since path costs and blast-radius confidence both key off edge confidence (`_path_edge_cost` `graph_query.py:836-844`, `_EXTRACTED_EDGE_WEIGHT` `graph_query.py:856`).

## Requirements

1. **Annotation-based receiver typing.** The Python extractor records receiver types from: function/method parameter annotations, annotated attribute assignments (`self.x: T`, class-body `x: T`), and annotated locals. String annotations and `Optional[T]`/`T | None` unwrap to `T`; any other generic/union/dynamic annotation is treated as unresolvable (no guess).
2. **Constructor-assignment typing.** `name = ClassName(...)` (local, `self.attr`, module-level) types `name` as `ClassName` when `ClassName` resolves to a same-file class or an imported class per the existing import machinery. Reassignment with a different resolved type demotes the name to unresolvable (conflicting evidence → no bind).
3. **Resolution and confidence semantics.** A receiver call `recv.method(...)` with a typed receiver resolves to `Class.method` only if that method exists on the resolved class node (same file or cross-file via the existing unique-candidate pass); annotation-typed bindings emit `RECEIVER_RESOLVED`, constructor-assignment bindings emit `CONSTRUCTION_RESOLVED` — matching the existing confidence taxonomy exactly. No inheritance walking in this change: if the method is not defined on the named class itself, the call stays `external::` (documented limitation; see Decision Log).
4. **Faithfulness invariants.** The unique-candidate rule is unchanged; no binding on: untyped receivers, multiply-assigned conflicting types, star imports, dynamic attribute access (`getattr`), or ambiguous cross-file candidates. Every new bind must be traceable to one explicit signal.
5. **Calibration gate.** Precision/recall measured before/after on (a) the self-hosted repo (Python oracle: hand-verified sample of ≥50 newly-bound edges, target ≥95% correct) and (b) the multi-language consumer test pack where Python fixtures exist. Confidence-mix delta (EXTRACTED vs resolved) recorded.
6. **Version bump.** `GRAPH_BUILDER_VERSION` bumped (node/edge content changes).
7. **Adversarial review.** Binding-faithfulness change → adversarial review lane at wave review per the standing security-control-faithfulness rule.

## Scope

**Problem statement:** Python — the framework's own language — is the only major supported language with no receiver-type call resolution, leaving Python `calls` edges at heuristic confidence and depressing impact/path quality on every Python target repo.

**In scope:**

- Annotation + constructor-assignment receiver typing in the Python extractor; `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` emission through the existing confidence and unique-candidate machinery.
- Negative-space handling (unions beyond Optional, conflicting reassignment, getattr, star imports) with explicit no-bind.
- Adversarial twin tests mirroring the existing pattern (`test_ambiguous_simple_name_stays_external` et al.) for every new bind path.
- Calibration measurements + hand-verified precision sample; version bump.

**Out of scope:**

- Inheritance/MRO method lookup, type inference beyond the two explicit signal classes, stub/typeshed consumption, decorator unwrapping.
- Any non-Python language.
- Framework-internal test-file indexing changes (tests remain excluded from the semantic code index per existing policy).

## Acceptance Criteria

- [ ] AC-1: Annotated-parameter, annotated-attribute, and annotated-local receivers resolve method calls to the annotated class's methods with `RECEIVER_RESOLVED` confidence, same-file and cross-file (unique candidate). Unit-tested per signal form, including string annotations and `Optional[T]` unwrap.
- [ ] AC-2: Constructor assignments (`local`, `self.attr`, module-level) resolve with `CONSTRUCTION_RESOLVED`; conflicting reassignment yields no bind. Unit-tested.
- [ ] AC-3: Faithfulness negatives — untyped receivers, non-Optional unions, `getattr`, star imports, ambiguous cross-file twins, and methods absent from the resolved class all stay `external::`/unbound; adversarial twin tests added in the style of the existing ambiguity suite. Unit-tested.
- [ ] AC-4: Calibration recorded — before/after confidence mix on the self-hosted repo plus a hand-verified ≥50-edge sample of new binds at ≥95% precision; multi-language pack Python fixtures pass. Results in the Progress Log.
- [ ] AC-5: `GRAPH_BUILDER_VERSION` bumped; incremental state invalidation verified (pre-change cached artifacts fully re-extract).
- [ ] AC-6: Adversarial faithfulness review lane run at wave review; findings dispositioned before close.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Implement receiver-type collection in the Python extractor (annotations: params/attributes/locals; constructor assignments; conflict demotion; Optional/string-annotation normalization).
- [ ] Wire receiver-typed calls into target resolution honoring unique-candidate + method-exists-on-class checks; emit correct confidence levels.
- [ ] Adversarial twin/negative tests + per-signal positive tests.
- [ ] Calibration run: confidence-mix before/after, ≥50-edge hand-verified sample, multi-lang pack Python fixtures; record in Progress Log.
- [ ] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-receiver-typing | implementer | — | Signal collection + normalization + conflict demotion in the Python extractor. |
| ws2-resolution-wiring | implementer | ws1-receiver-typing | Typed-receiver → target binding through existing unique-candidate machinery; confidence emission. |
| ws3-tests-calibration | implementer | ws2-resolution-wiring | Positive/negative/twin tests; calibration measurements + hand-verified sample. |
| ws4-adversarial-review | reviewer | ws3-tests-calibration | Faithfulness red-team at wave review (what dynamic patterns could over-bind?). |


## Serialization Points

- Shares `graph_indexer.py` (Python extractor region) with `1p9q6` (oversized-file fallback) and the cross-file pass with `1p9q5` — disjoint functions, but coordinate the single wave-level `GRAPH_BUILDER_VERSION` bump.
- If wave `1p9q3` (efficiency) implements first, this change's re-extraction lands on the incremental-merge path — the differential harness there is a free extra oracle for this change's binds.

## Affected Architecture Docs

Audit docs that enumerate per-language resolution capability (`docs/specs/mcp-tool-surface.md` code-tool notes; any graph capability matrix in `docs/references/` or seeds). Update the Python row from "no receiver resolution" to the two-signal model with its documented limitations. No boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Annotation binding is the core new capability. |
| AC-2 | required | Constructor assignment is the second signal; conflict demotion is its faithfulness guard. |
| AC-3 | required | Never-bind-the-wrong-twin is the framework's core graph invariant; negatives are not optional. |
| AC-4 | required | Calibrate-don't-guess: the precision sample is the evidence the change helps rather than pollutes. |
| AC-5 | required | Standing artifact-shape/version rule. |
| AC-6 | required | Standing adversarial-review rule for binding-faithfulness changes. |
| AC-7 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Confirmed: Python uses `ast.parse` with no `_resolve_python_call_target` peer to the nine other languages' resolvers; self-hosted graph has 7,674 function nodes with `calls` edges predominantly `EXTRACTED`; edge confidence directly weights path cost and impact propagation (`graph_query.py:836-869,886-893`). | `graph_indexer.py:5665,5066,3241,3493,4463`; `graph_query.py:836-893`; evaluation 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Two explicit signals only — annotations + constructor assignments (approach A). | Deterministic, AST-local, zero-inference; each bind is traceable to one syntactic fact, matching the framework's never-guess stance; covers the dominant real-world patterns in typed and semi-typed Python codebases. | (B) Flow-based local type inference (assignments through calls, returns) — weakness: an inference engine's error modes are exactly the silent over-binding the faithfulness rule exists to prevent; complexity disproportionate. (C) Consume typeshed/stubs or run a checker (mypy/pyright) at index time — weakness: heavy external dependency + environment coupling against the local-only stance; index build must not require a type-checker toolchain. |
| 2026-07-03 | No inheritance/MRO walk — method must exist on the named class. | Inheritance walking without full-fidelity MRO risks binding to the wrong override; the explicit-signal tier should be unimpeachable first. Documented limitation; a later change can add single-base walking with its own calibration. | Walk bases when unique — deferred: promotes recall at precision risk before the baseline precision is measured. |
| 2026-07-03 | Emit existing confidence levels (`RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED`), no new tier. | The taxonomy already distinguishes exactly these two evidence classes; downstream weights (`graph_query.py`) work unchanged. | A new `ANNOTATION_RESOLVED` tier — rejected: consumer churn for no added signal; annotations are receiver-type evidence, same class as the existing tiers. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-binding via stale/wrong annotations (annotation lies about runtime type). | Accepted as the semantics of annotation-trusting tools; confidence tier communicates evidence class; calibration sample (AC-4) quantifies real precision; adversarial review hunts systematic cases. |
| Reassignment/aliasing patterns produce a wrong single-type conclusion. | Conflict demotion (Requirement 2) + negative tests (AC-3); only same-scope direct assignment counts — no alias chasing. |
| Recall win too small to justify the code. | Calibration before/after confidence mix is the measurement; if the delta is negligible on the self-hosted repo the change is re-scoped before merge (recorded honestly, not shipped on faith). |
| Interaction with incremental invalidation (wave `1p9q3`): typed receivers create new cross-file sensitivity. | Bindings still flow through the same unique-candidate cross-file pass whose symbol-scoped invalidation `1p9q2` owns; the differential harness covers composed cases if both waves land. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
