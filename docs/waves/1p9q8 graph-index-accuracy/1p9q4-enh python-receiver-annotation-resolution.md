# Graph accuracy: Python receiver resolution from annotations and constructor assignments

Change ID: `1p9q4-enh python-receiver-annotation-resolution`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

## Rationale

Python extraction uses native `ast.parse` (`_extract_python_artifact`, `graph_indexer.py:9807`) but has no receiver-type resolution path: while Java, Kotlin, C#, Go, Rust, and TS/JS each have a `_resolve_*_call_target` resolver (`_resolve_kotlin_call_target:3619`, `_resolve_csharp_call_target:3803`, `_resolve_go_call_target:4090`, `_resolve_rust_call_target:4342`, `_resolve_java_call_target:5915`, all in `graph_indexer.py`; confirmed 2026-07-05 that no `_resolve_python_call_target` peer exists), Python method calls through a receiver (`self.store.put(...)`, `client.fetch(...)`) resolve only when the bare-name/unique-candidate machinery happens to bind them — otherwise they stay `external::` or, worse for recall, produce no `RECEIVER_RESOLVED` edges at all. Python is the framework's own implementation language, so this remains a meaningful recall gap in the self-hosted graph. **Freshness note (2026-07-05):** the doc's original "`calls` edges dominated by `EXTRACTED` confidence" framing is now STALE — wave 1p7dg (v34, "confidence promotion") already promotes every already-unique Python bind `EXTRACTED→RECEIVER_RESOLVED` (self-host lift recorded in the changelog: Python EXTRACTED 90.4%→31.9%, resolved 1,136→8,102). The gap 1p9q4 targets is the DISTINCT residue: receiver-typed calls that currently do not bind at all (stay `external::`), which 1p7dg does not touch. Re-run the confidence-mix baseline (AC-4) against the post-1p7dg state, not the 2026-07-03 numbers.

Python offers deterministic, no-inference-engine signals that a resolver can use without guessing:

- parameter and attribute annotations (`def f(store: ArtifactStore)`, `self.store: ArtifactStore = ...`),
- direct constructor assignment (`self.store = ArtifactStore(...)`, `store = ArtifactStore(...)` in local scope),
- module-level constants assigned from constructors.

Binding only on these explicit signals — same-file or import-resolvable class targets, unique-candidate rule unchanged — upgrades a meaningful slice of Python `calls` edges to `RECEIVER_RESOLVED` while preserving the framework's core faithfulness stance: never bind on ambiguity, dynamic dispatch stays unresolved. This directly improves `code_impact`/`code_graph_path` quality, since path costs and blast-radius confidence both key off edge confidence (`_path_edge_cost` `graph_query.py:1014`, `_EXTRACTED_EDGE_WEIGHT` `graph_query.py:1044`; `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` taxonomy at `graph_query.py:1005,1029,1074`).

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

- [x] AC-1: Annotated-parameter, annotated-attribute, and annotated-local receivers resolve method calls to the annotated class's methods with `RECEIVER_RESOLVED` confidence, same-file and cross-file (unique candidate). Unit-tested per signal form, including string annotations and `Optional[T]` unwrap. — `Python1p9q4ReceiverTests` (annotated self-attr, class-body attr, string forward-ref, string Optional unwrap); params/locals covered by `AnnotationReceiverTypeTests`.
- [x] AC-2: Constructor assignments (`local`, `self.attr`, module-level) resolve with `CONSTRUCTION_RESOLVED`; conflicting reassignment yields no bind. Unit-tested. — `test_local_construction_resolves_construction`, `test_self_attr_construction_resolves_construction`, `test_module_level_construction_resolves_construction`, `test_conflicting_reassignment_demotes`, `test_annotation_and_construction_same_type_prefers_receiver`.
- [x] AC-3: Faithfulness negatives — untyped receivers, non-Optional unions, `getattr`, star imports, ambiguous cross-file twins, and methods absent from the resolved class all stay `external::`/unbound; adversarial twin tests added in the style of the existing ambiguity suite. Unit-tested. — `test_non_optional_union_annotation_does_not_bind`, `test_pep604_multi_union_does_not_bind`, `test_getattr_receiver_does_not_bind`, `test_star_imported_class_not_construction_typed`, `test_ambiguous_cross_file_twin_stays_external`, `test_method_absent_from_resolved_class_stays_external`, `test_construction_from_non_class_factory_does_not_bind`, `test_module_type_shadowed_by_local_param_does_not_bind`, plus repointed `test_unannotated_receiver_guess_not_promoted`.
- [x] AC-4: Calibration recorded — before/after confidence mix on the self-hosted repo plus a hand-verified ≥50-edge sample of new binds at ≥95% precision; multi-language pack Python fixtures pass. Results in the Progress Log. — see Progress Log 2026-07-05 calibration entry (self-hosted graph delta + hand-verified sample).
- [x] AC-5: `GRAPH_BUILDER_VERSION` bumped; incremental state invalidation verified (pre-change cached artifacts fully re-extract). — **[integration 2026-07-05]** the coordinated `39→40` bump across `1p9q4`/`1p9q5`/`1p9q6`/`1p9q7` landed once in `graph_indexer.py`; a builder-version mismatch forces a full re-extract (pinned by `test_builder_version_bump_reextracts_full_corpus`), and the live full graph rebuild re-extracted the whole corpus clean (counts in the wave watchpoints).
- [x] AC-6: Adversarial faithfulness review lane run at wave review; findings dispositioned before close. — done 2026-07-06: the mandatory adversarial-faithfulness delivery lane ran (PASS — no wrong binds on any surface under live probes); the code lane found two faithfulness defects (this change's confidence-label honesty on unresolved typed calls — FIX 1 finalize downgrade; and 1p9q7's TS DI binds ambiguity) both fixed in the review fix round and verified by the delivery-council primer, which added the FIX-1 Java super/inherited scope correction + regression pin. Findings dispositioned.
- [x] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. — full suite green (count in Progress Log); `wave_validate` clean; `__pycache__` cleaned.

## Tasks

- [x] Implement receiver-type collection in the Python extractor (annotations: params/attributes/locals; constructor assignments; conflict demotion; Optional/string-annotation normalization). — `_py_extract_simple_type` (string forward-ref + faithful union/generic handling), `_py_build_local_types`, `_py_build_class_attr_types`, `_py_build_module_types`, `_py_construction_type`, `_py_finalize_types` in `graph_indexer.py`.
- [x] Wire receiver-typed calls into target resolution honoring unique-candidate + method-exists-on-class checks; emit correct confidence levels. — `CallCollector._resolve_call` (self-attr + module-level typed receivers; per-name confidence travels with the type) + emit loop; binds through the existing `symbol_lookup` / cross-file unique-candidate pass.
- [x] Adversarial twin/negative tests + per-signal positive tests. — `Python1p9q4ReceiverTests` (18 tests).
- [x] Calibration run: confidence-mix before/after, ≥50-edge hand-verified sample, multi-lang pack Python fixtures; record in Progress Log.
- [x] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`. — **[integration 2026-07-05]** coordinated `39→40` increment landed with the four-change changelog head; `run_tests.py` + `wave_validate` + `__pycache__` clean.

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
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Confirmed: Python uses `ast.parse` with no `_resolve_python_call_target` peer to the other languages' resolvers; self-hosted graph has 7,674 function nodes with `calls` edges predominantly `EXTRACTED`; edge confidence directly weights path cost and impact propagation (`graph_query.py:836-869,886-893`). | `graph_indexer.py:5665,5066,3241,3493,4463`; `graph_query.py:836-893`; evaluation 2026-07-03. |
| 2026-07-05 | **Freshness reconciliation (reality-checker lane).** Verdict: READY-WITH-CORRECTIONS-APPLIED. Premise still VALID — no `_resolve_python_call_target` exists (verified live); receiver-typed calls that fail to bind stay `external::`, and 1p9q4's two-signal model targets exactly that residue. STALE-ANCHOR fixes applied: `_extract_python_artifact` 5665→9807; resolver anchors 5066/3241/3493/4463 → 3619/3803/4090/4342/5915; `_path_edge_cost` 836-844→1014, `_EXTRACTED_EDGE_WEIGHT` 856→1044. **PARTIALLY-superseded rationale:** the "`calls` dominated by EXTRACTED" claim is stale post-1p7dg (v34) — Python resolved-share already lifted (EXTRACTED 90.4%→31.9%); re-baseline AC-4 against post-1p7dg state, NOT the 2026-07-03 mix. Mechanism/scope unchanged. Coordinated version bump target is now **39→40** (current `GRAPH_BUILDER_VERSION="39"`, `graph_indexer.py:38`). | live verify 2026-07-05: `graph_indexer.py:38,9807,3619,3803,4090,4342,5915`; `graph_query.py:1005,1014,1044`; changelog 1p7dg self-host lift. |
| 2026-07-05 | **Implemented (implementer lane).** Discovery: the premise "Python has no receiver resolution" is partly stale — wave 131bt (1319q) already resolves annotated **params** and annotated **`AnnAssign` locals** (`_py_build_local_types`), and the cross-file finalize already treats `CONSTRUCTION_RESOLVED` as a receiver-resolved peer (`_resolve_external_call_target:9305`). So the residue 1p9q4 fills is: (1) annotated **attributes** (`self.x: T`, class-body `x: T`) via a class-wide attr-type table, (2) **string forward-ref** annotations (`x: "Foo"`, parsed + recursed), (3) **constructor-assignment** typing (`x=Foo()`, `self.x=Foo()`, module-level) at `CONSTRUCTION_RESOLVED`, (4) **`self.x.method()`** receiver wiring, (5) **conflict demotion** (multiple resolved types → drop), and a faithfulness FIX — multi-member unions (`Union[A,B]`, `A\|B`) and non-Optional generics (`List[Foo]`) now return None instead of guessing the first/outer name (the old code over-bound `Union[A,B]`→A). Confidence now travels per-name with the type (annotation→RECEIVER_RESOLVED, ctor→CONSTRUCTION_RESOLVED; annotation wins when both agree). New helpers in `graph_indexer.py`: `_py_construction_type`, `_py_finalize_types`, `_py_build_class_attr_types`, `_py_build_module_types`, `_py_is_self_attr_target`; `_resolve_call`/`CallCollector` threaded with `attr_types`/`module_types`. **AC-4 CALIBRATION (honest, per re-scope clause):** true before/after (HEAD v39 vs working tree) on the self-hosted framework Python source (57 files): project-bound Python `calls` edges **3471→3481 = +10** (6 `CONSTRUCTION_RESOLVED`, 4 `RECEIVER_RESOLVED`), **0 lost binds (no regressions)**. Full Python `calls` mix after: RECEIVER_RESOLVED 3904 / EXTRACTED 952 / CONSTRUCTION_RESOLVED 40 (all 40 new; 6 project-bound, 34 external constructors). Delta is MODEST on this repo — expected, as the reality-checker predicted (framework Python is annotation-dense and already 131bt/1p7dg-resolved); recorded honestly, not inflated. Hand-verified sample: all **10/10 new binds correct → 100% precision** (only 10 exist, so full-census verification): `make_embedder`/`make_reranker` ctor→`offloads_to_gpu`; `self._store: GraphStateStore \| None`→`.ensure_current`/`.close` (self-attr + PEP604 unwrap); `session=GraphIndexSession(...)`→`.close_store`/`.finalize`/`.record_file`; `self.cache=McpRepoCache(...)`→`.invalidate` (self-attr ctor across methods); `index: "WaveIndex"` **string forward-ref**→`._layer_health`/`.search_combined`. Interaction with 1p7dg CLEAN — no double-labeling (`test_no_double_labeling_with_1p7dg_self_promotion`: `self.helper()` single RECEIVER_RESOLVED, `d.bar()` single CONSTRUCTION_RESOLVED). Tests: +18 in `Python1p9q4ReceiverTests` (per-signal positive + drop twins); repointed `test_unannotated_receiver_guess_not_promoted`/`test_python_unannotated_local_does_not_receiver_resolve` off `foo=Foo()` (now a valid ctor signal) to genuinely-untyped receivers. Full suite **4646 tests OK** (baseline 4628 + 18). `__pycache__` cleaned. **Version bump DEFERRED** to the coordinated wave `39→40` at integration (AC-5 `[~]`). | `graph_indexer.py` (`_extract_python_artifact` region); `tests/test_graph_indexer.py::Python1p9q4ReceiverTests`; before/after harness on 57 self-host `.py` files; `run_tests.py` 4646 OK. |
 | 2026-07-06 | **Delivery-review honesty fix (fix lane, within v40 — NO re-bump).** Code Finding 1: a typed-receiver call whose `{Type}.{method}` never bound a project node still carried `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` on the edge that STAYS `external::` (method absent from the resolved class; ambiguous cross-file same-name twin). Repro confirmed `external::Foo.missing` and `external::Dup.go` both stamped `RECEIVER_RESOLVED`. The emit site cannot gate on `external::` (a legitimate cross-file bind emits `external::{Type}.{method}` there and relies on the finalize rewrite), so the correction lives in the finalize pass: `_resolve_fragment_edge` now routes every resolved edge through `_downgrade_unresolved_typed_calls` — a `calls` edge that ends up STILL `external::` with a receiver/construction confidence is downgraded to `EXTRACTED`. Genuine cross-file binds (e.g. `self.dep = Dep(); self.dep.bar()`) still resolve to the project node keeping `CONSTRUCTION_RESOLVED`. Test blind spot closed (Finding 3): `Python1p9q4ReceiverTests._call_confs` filtered out `external::` targets, so the regression had no surface — added `_ext_call_confs` + assertions pinning `test_method_absent_from_resolved_class_stays_external` and `test_ambiguous_cross_file_twin_stays_external` to `EXTRACTED` on their external edge. Downstream note: impact weights INCOMING edges to project nodes and path treats `external::` as non-transitive leaves, so this is currently inert on those consumers — but the label is now honest. | `graph_indexer.py` (`_downgrade_unresolved_typed_calls`, `_resolve_fragment_edge` wrapper, emit-loop note); `tests/test_graph_indexer.py::Python1p9q4ReceiverTests` (`_ext_call_confs` + 2 pins). |
 | 2026-07-06 | **Delivery-council fix-now round: FIX-1 scope clarification + Java regression pin (within v40 — NO re-bump).** The delivery-council red-team primer found that `_downgrade_unresolved_typed_calls`'s docstring (and the mirroring arch-doc paragraph) FALSELY claimed the Java `super.`/`staticorinherited#` markers "never reach here as a plain dotted external" — they DO reach it, and the pass correctly downgrades them too: both refusal paths in `_apply_inheritance_output_passes`/`_arbitrate_static_or_inherited` (unresolved `super.` call to a library superclass; multi-definer `staticorinherited#` refusal) re-emit a DOTTED `external::` target while keeping the marker's extraction-time `RECEIVER_RESOLVED` confidence, so they land in the same finalize honesty pass as the Python case. This is SEMANTICALLY CORRECT and additionally desirable (not a defect): `RECEIVER_RESOLVED` on a genuinely-unresolved external super/inherited target was itself a pre-existing Java over-claim, now honested to `EXTRACTED` too. Fixed the false scope claim in both the docstring (`graph_indexer.py` `_downgrade_unresolved_typed_calls`) and `docs/architecture/graph-index-system.md` (Python receiver-resolution section, honesty-rule paragraph). Closed the test blind spot this false claim masked: `test_java_super_call_without_project_parent_stays_external_marker` and `test_multi_definer_with_static_import_refuses` previously asserted only the external target shape, not confidence — both now additionally pin `EXTRACTED` (repro-verified against the live build before pinning; previously would have silently passed with a `RECEIVER_RESOLVED` regression). Also addressed two minor council notes: `test_ts_trigger_tokens_superset_of_collector_idioms` was near-tautological (its reference idiom tuple was hand-copied identical to `_TS_DI_TRIGGER_TOKENS` itself) — rewritten to derive the reference set from real per-idiom TS/NestJS/Inversify fixtures run functionally through `collect_ts_di_signals` (each fixture must emit a signal AND be covered by a trigger-token substring), so a future collector idiom added without a matching trigger token now fails the test; and the TS DI pre-check (`collect_ts_di_signals`) gained the same `source_bytes and ...` empty-source guard the Python pre-check already has, for symmetry (inert today — tree-sitter always supplies non-empty bytes). Full suite 4,663 OK (no new test count — strengthened existing tests rather than adding new ones); `wave_validate` clean; `GRAPH_BUILDER_VERSION` unchanged at `"40"`. | `graph_indexer.py` (`_downgrade_unresolved_typed_calls` docstring); `graph_di_signals.py` (`collect_ts_di_signals` guard symmetry); `docs/architecture/graph-index-system.md` (honesty-rule paragraph); `tests/test_graph_indexer.py` (`JavaCSharpInheritanceTests::test_java_super_call_without_project_parent_stays_external_marker`, `JavaStaticImportInheritedShadowTests::test_multi_definer_with_static_import_refuses`, `DiSignalPrecheckTests::test_ts_trigger_tokens_superset_of_collector_idioms`); `run_tests.py` 4663 OK. |


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
