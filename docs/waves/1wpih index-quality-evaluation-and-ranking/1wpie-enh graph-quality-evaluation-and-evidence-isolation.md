# Evaluate Graph Fidelity and Isolate Machine Evidence Communities

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

Graph tests provide substantial isolated fixture coverage but no representative mixed-artifact corpus reporting precision and recall by relation. The live audit found cross-domain false positives those fixtures missed. Architectural community reports are also dominated by machine evidence JSON. Re-derived from the persisted cluster artifact on 2026-09-02, after `1wpif` and `1wpig` closed and at graph builder version 46 with cluster builder version 12, the third-largest community holds 987 `freeze` nodes, behind the test community at 12,944 and the server-implementation community at 1,193; the per-wave evidence tree supplies 2,758 graph nodes in total. None of it is classified as generated/evidence. The graph should retain evidence data for search while keeping it from masquerading as a production architecture domain.

## Requirements

1. A committed mixed-language, mixed-artifact graph corpus SHALL define expected and forbidden edges across supported relation types.
2. Evaluation SHALL report per-relation true positives, false positives, false negatives, precision, and recall through a frozen relation-to-public-tool matrix. Every scored relation SHALL include at least one expected edge and one forbidden opportunity, with direction, confidence threshold, duplicate normalization, and external-node treatment defined before implementation.
3. The corpus SHALL include ambiguous names, overloads, constructors, external APIs, test/generated boundaries, config/schema data, doc references, and incremental removal/update cases.
4. Provenance-identified machine-result artifacts SHALL be classified into a fixed Evidence/Data community or excluded only from architectural rankings and label selection. Classification SHALL not infer machine evidence solely from a JSON/YAML extension, path prefix, file size, repeated-key shape, or co-clustering with an evaluator source file.
5. Evidence nodes SHALL remain queryable and their cross-boundary relationships SHALL not be silently discarded.
6. Community usefulness, purity, top-hub composition, determinism, build time, and artifact size SHALL be measured before selecting the isolation policy.
7. For every requested/default production section in the partition set, the public graph report SHALL return an exact parallel Evidence/Data array: `communities` + `evidence_communities`, `fan_in` + `evidence_fan_in`, `fan_out` + `evidence_fan_out`, `chokepoints` + `evidence_chokepoints`, and `file_hubs` + `evidence_file_hubs`. A corresponding evidence array SHALL be present and empty when no rows qualify, even when `communities` itself was not requested. Production/evidence arrays retain their section's existing compatibility fields; every evidence entry additionally carries `evidence_type="evidence_data"` and nonempty `classification_reasons`, while evidence-community entries also carry `community_type="evidence_data"`. The public limit applies independently to each production/evidence pair after partitioning, `exclude_generated` does not erase Evidence/Data, and Evidence/Data community IDs remain discoverable in the community catalog and queryable through `code_graph_community`. Tool descriptions, MCP specification, and response tests SHALL enumerate all five pairs and their presence/limit semantics.
8. Evidence/Data classification SHALL occur before top-N selection for `communities`, `fan_in`, `fan_out`, `chokepoints`, and `file_hubs`; evidence rows SHALL not consume production ranking slots and SHALL remain represented through their corresponding typed evidence array. The classification SHALL include positive controls for legitimate configuration and design-token JSON. Because predecessor `1wpaj` also changes cluster-artifact semantics, this wave SHALL read the landed predecessor `CLUSTER_BUILDER_VERSION`, bump to the next version, force a same-fingerprint predecessor-version artifact to rebuild, and preserve byte/mtime-identical zero-change reuse afterward; the plan SHALL NOT assume the historical v11 artifact is still the immediate predecessor.
9. `.wavefoundry/framework/scripts/graph_quality_eval.py` SHALL evaluate `docs/evals/graph-quality-golden.json` and write `docs/reports/graph-quality-baseline.json` / `docs/reports/graph-quality-post.json`. Both reports SHALL bind corpus digest, evaluator identity, graph/query production identity, graph and cluster builder/schema versions, graph input fingerprint, repository/artifact identity, environment/backend, run timestamp, and report-content identity. The report schema SHALL name every scored relation and public tool used.
10. The fixed graph corpus SHALL contain at most 128 files, 2,000 normalized nodes, and 5,000 normalized edges; each graph-quality report SHALL be at most 1 MiB and the baseline/post pair at most 2 MiB. Performance and determinism evidence SHALL record one untimed warm-up plus exactly three measured repetitions using nearest-rank p95. Each of two controlled rebuilds SHALL have one attempt and fail at 120 seconds; zero-change reuse SHALL fail at 10 seconds; and the full two-rebuild-plus-reuse sequence SHALL fail at 250 seconds. Public graph-report p95 SHALL be at most 1 second and no more than baseline plus `max(25%, 50 ms)`; cluster-stage time SHALL be at most baseline plus `max(25%, 1 second)`, graph-only rebuild above 30 seconds requires operator review, and compressed cluster artifact bytes SHALL be at most `max(2 * baseline, baseline + 2 MiB)`. Two fresh identical builds SHALL produce identical normalized scored rows/community IDs. Reuse SHALL preserve artifact SHA-256 and `mtime_ns`, invoke neither clustering nor centrality under instrumentation, and perform no rewrite.
11. Canonically ignored standing-retrieval artifacts — `docs/evals/retrieval-quality-golden.json` and `docs/reports/retrieval-quality-*.json` — SHALL remain absent from the graph and SHALL NOT be relabeled as Evidence/Data. `.wavefoundry/framework/scripts/retrieval_eval.py` SHALL remain ordinary framework code even when it co-clusters with machine artifacts. A nonignored synthetic machine-result artifact with explicit producer/schema provenance SHALL supply the positive Evidence/Data control. That control SHALL live under this wave's own evidence directory, `docs/waves/1wpih index-quality-evaluation-and-ranking/evidence/`. The location is load-bearing and is not a stylistic choice: a 2026-09-02 census of the persisted graph found `docs/evals/` and `docs/reports/` contribute **zero** nodes each, while the per-wave evidence tree contributes 2,758, so a control placed beside the other evaluation fixtures would never be indexed and could never be classified. Every assertion about the control's classification SHALL be preceded by an assertion that the control's node is PRESENT in the graph, so an unindexed or relocated control fails the criterion instead of passing vacuously.
12. The classifier SHALL be invariant to moving or renaming an otherwise identical provenance-backed machine-result artifact. Larger legitimate configuration, schema, design-token, prompt, and user-authored data fixtures SHALL remain in their ordinary domains. The scorer SHALL fail both an injected false-positive classification of one legitimate control and a false-negative classification of the provenance-backed machine-result control.

## Scope

**Problem statement:** Graph fidelity lacks end-to-end measurement, and machine evidence can dominate architectural orientation.

**In scope:** Representative graph evaluation, public-tool assertions, evidence/data classification or ranking policy, cluster tests, and measured before/after reports.

**Out of scope:** Removing historical evidence from the repository, excluding all JSON, rewriting Leiden clustering, and semantic retrieval evaluation owned by `1sear`.

## Acceptance Criteria

- [x] AC-1: One local command builds the fixed corpus and reports the versioned schema, relation-to-public-tool matrix, and per-relation TP/FP/FN, precision, and recall through public graph responses.
- [x] AC-2: The corpus covers every named adversarial and incremental case, flags deliberately seeded `cpu_count` and schema/config collisions, and reports zero such false positives in the corrected graph baseline.
- [x] AC-3: In a fixture where Evidence/Data is larger than two legitimate production domains and `limit=2`, both production rows survive in every covered production section and Evidence/Data appears only in that section's exact parallel typed array without suppressing eligible production rows.
- [x] AC-4: Evidence nodes and genuine cross-boundary edges remain available to targeted graph queries.
- [x] AC-5: Community IDs and normalized scored results remain deterministic on two fresh fixed-corpus builds and zero-change reuse; the fixed corpus/report caps and exact rebuild/reuse timeout, p95, no-call, rewrite, and artifact-size thresholds in Requirement 10 pass for each recorded backend.
- [x] AC-6: Graph architecture and testing documentation define the fidelity tier and evidence-community semantics; this change's own suites and every test it adds pass, the documents it authors or edits validate, and no failure elsewhere is attributable to it.
- [x] AC-7: Default and explicit requests for each partitioned section—including requests that omit `communities`—obey the exact five production/evidence array-pair schema, independent limits, empty-array, `exclude_generated`, and malformed/stale controls; `code_graph_community`, `code_graph_path`, and relation-appropriate targeted queries retain access to Evidence/Data nodes and boundary edges.
- [x] AC-8: Positive configuration/design-token JSON controls remain in their legitimate domains; a same-fingerprint artifact at the landed predecessor cluster-builder version rebuilds under the next version, and the following unchanged invocation reuses it without rewrite.
- [x] AC-9: The graph evaluation runner rejects an injected forbidden edge and a deleted expected edge, and its baseline/post reports carry every identity and schema field in Requirement 9.
- [x] AC-10: Ignored standing fixture/report artifacts are absent from the graph, `retrieval_eval.py` remains ordinary framework code, and the explicit-provenance synthetic machine-result artifact enters Evidence/Data and remains queryable. Its graph node is asserted present before its classification is asserted, and moving that artifact to `docs/evals/` makes the criterion FAIL rather than pass.
- [x] AC-11: Move/rename invariance holds for the machine-result positive; large legitimate config/schema/design-token/prompt/user-data controls never enter Evidence/Data; and injected classifier false-positive and false-negative mutants fail the evaluator.

## Tasks

- [x] Build and annotate the mixed-artifact ground-truth corpus.
- [x] Add a public-tool evaluation runner and scored report.
- [x] Freeze the relation/public-tool matrix, score normalization, report schema, evidence identities, and injected-scorer known-bads before graph-policy edits.
- [x] Measure current community composition and label purity.
- [x] Implement the smallest evidence/data classification or report-level isolation supported by the measurements.
- [x] Apply the evidence partition before production top-N selection and add positive JSON classification controls.
- [x] Add determinism, topology-preservation, size, and latency verification.
- [x] Update graph and testing architecture documentation.
- [x] Update the public graph-report response contract and tests for separate evidence-community reporting.
- [x] Add exact public response/tool-description/spec tests for all five production/evidence array pairs, including single-section requests without `communities`.
- [x] Add graph-absence assertions for ignored standing artifacts, ordinary-code assertions for `retrieval_eval.py`, and a nonignored provenance-backed machine-result positive placed under the wave's own evidence directory, guarded by a graph-presence precondition so an unindexed control fails.
- [x] Add move/rename invariance plus legitimate-data false-positive and machine-result false-negative classifier tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluation runner and fixture schema | implementer | Wave readied/activated | Public-tool scorer and bounded corpus contract |
| Fidelity corpus approval/baseline | qa-reviewer | Evaluation runner | Expected and forbidden edges, frozen before policy edits |
| Evidence policy | implementer | Frozen fidelity baseline | Fixed community and ranking isolation |
| Verification/docs | qa-reviewer | Evidence policy | Metrics, determinism, architecture |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`, `.wavefoundry/framework/scripts/graph_query.py`, `.wavefoundry/framework/scripts/graph_cluster.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/graph_quality_eval.py`, `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`, `docs/evals/graph-quality-golden.json`, `docs/reports/graph-quality-*.json`
- `.wavefoundry/framework/scripts/tests/`, `docs/architecture/graph-index-system.md`, `docs/architecture/testing-architecture.md`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md` (public graph-report response contract)

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Supplies the missing representative fidelity measure. |
| AC-2 | required | Locks the defect classes that motivated the suite. |
| AC-3 | required | Delivers useful architectural orientation. |
| AC-4 | required | Isolation must not become graph content loss. |
| AC-5 | important | Quality improvements must preserve operational bounds. |
| AC-6 | important | The new evaluation and community contract require documentation. |
| AC-7 | required | A fixed evidence bucket must not remain in the production architecture top-N. |
| AC-8 | required | Prevents broad JSON overclassification and stale cluster artifacts. |
| AC-9 | required | Makes fidelity evidence auditable and proves the scorer detects both false positives and false negatives. |
| AC-10 | required | Prevents the evaluation corpus/reports from entering the graph and prevents evaluator code from being mislabeled by association. |
| AC-11 | required | Evidence isolation must follow provenance rather than path/shape heuristics that erase legitimate repository domains. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned as later graph-quality work from the index audit. | Ten-case live sample; the graph report **at that date** showed a 1,158-node second-largest `freeze` community and machine-result hubs. **Superseded 2026-09-02:** re-derivation after both predecessor waves closed returns 987 nodes at rank three. The 1,158 figure is retained here as the dated observation that motivated planning, not as a current measurement. |
| 2026-08-31 | Tightened Evidence/Data identity from closed-`1seaw` carrier findings and predecessor-version sequencing. | Standing retrieval artifacts are canonically ignored; evaluator source is ordinary code; graph-positive evidence now requires a nonignored provenance-backed fixture and predecessor-relative cluster invalidation. |
| 2026-08-31 | Made Evidence/Data carriers and graph-evaluation costs complete. | Final architecture/QA review required parallel typed arrays for every pre-top-N partitioned section plus fixed corpus/report and rebuild/reuse ceilings. |
| 2026-09-03 | **Execution step 4 landed: graph fidelity measurement (AC-1, AC-9).** | `graph_quality_eval.py`, `test_graph_quality_eval.py` (16 tests), and `docs/evals/graph-quality-golden.json` (4 files, `.aiignore`d). The corpus is materialised and built through the real `update_graph_index` entry, not a hand-made payload, so the scorer measures the product's extraction. Scored against a real build: all five relations report precision and recall of 1.0 with zero false positives, which is the corrected-baseline state AC-2 anticipates. |
| 2026-09-03 | The relation-to-tool matrix was **corrected by measurement**, not authored from assumption. | Two rules changed after building a real graph and reading the edges. `imports` now INCLUDES external targets: a Python `from svc.loader import load_settings` emits `imports -> external::svc.loader.load_settings` while the corresponding call resolves to the project node, so excluding externals would have left the relation with nothing to score and a vacuous 1.0. Separately, `doc_references_code` edges arrive at `AMBIGUOUS` confidence, a tier the ordering did not contain; it is now named explicitly as the weakest tier so those edges are excluded by decision rather than by an unrecognised label. |
| 2026-09-03 | Forbidden edges are real over-binding risks, not filler. | The sharpest is `load_settings -> config.json::queue_name`: the sibling key the loader never reads. A binder that matches a configuration FILE and attaches every key in it, instead of the literal used at the read site, emits exactly that edge. The others cover call attribution to the enclosing class rather than method, self-import, cross-file definition, and doc references binding every symbol in a mentioned class. |
| 2026-09-04 | **The community catalog resource still presented machine evidence as architecture.** | `wf_graph_report` partitioned correctly while `wavefoundry://graph/communities` sorted the raw cluster artifact by node count, so `freeze` (1,176 nodes) sat at rank two of the catalog unmarked. That resource is the surface `AGENTS.md` and seeds 180/211 tell a reader to consult BEFORE `code_graph_community`, so the orientation problem the wave exists to fix survived in the place orientation actually starts. The majority rule moved to `graph_query.is_evidence_community` and both surfaces now call it, because two copies would let the report and the catalog describe the same community differently. Evidence communities stay listed and queryable, as Requirement 7 requires, but they are marked with type, share, and reason, and ranked after production. Live catalog: 93 architectural, 7 Evidence/Data. Mutation: partition removed -> `test_the_evidence_community_is_marked_and_ranked_last` and `test_the_marking_states_why` fail. |
| 2026-09-04 | Gate-corpus contamination: re-derived, and it is not fitting. | The concern was that the standing retrieval gate cannot judge this wave because its fixtures point at files the wave edits. Re-derived against the current tree: 19 of 35 fixtures anchor on a modified path, 8 of them held-out. But the corpus was not fitted -- 35 fixtures at `HEAD` and 35 now, none added or removed, and no query, anchor set, or expected question type changed; every fixture carries `authorship_class: historical`. The residual is the corpus-drift attribution problem already documented in `docs/contributing/review-and-evals.md` from wave `1wybs`, with its established reading protocol (read a cross-generation `fail` together with the production diff). Recorded as a caveat with a re-derived census rather than a defect. |
| 2026-09-04 | **AC-9's report half was marked met without being delivered; now repaired.** | Requirement 9 names two artifacts by path and neither existed: `graph_quality_eval.py` had no report path at all, only a corpus-summary command line, so the 2026-09-03 entry below marked AC-9 on the injected-edge mutation controls alone. Added `build_report`, `write_report`, `verify_report_pair`, a `--report`/`--label` command line, and both named reports. The baseline runs the CURRENT evaluator against the HEAD production in a scratch checkout, so the instrument holds still and the delta is attributable: false positives 1 -> 0 (the seeded `os.cpu_count()` external-API collision, precisely the AC-2 case) with true positives and false negatives unchanged. `production_identity` carries `source_root`, so a baseline taken from a predecessor checkout is not misread as the working tree. Producing the reports also exposed that `docs/reports/graph-quality-*.json` was missing from `.aiignore` while every other standing report family was listed; the two new files entered the graph and `test_the_canonically_ignored_standing_artifacts_are_absent` caught it. |
| 2026-09-03 | Landing rule: four mutants, four named failures, one malformed and redone. | Forbidden edges stop counting as false positives → `test_an_injected_forbidden_edge_is_caught_as_a_false_positive`; external exclusion dropped → `test_external_targets_are_kept_for_imports_and_dropped_for_calls`; the both-buckets completeness check removed → `test_a_relation_without_a_forbidden_opportunity_is_refused`; the confidence floor always admits → `test_ambiguous_is_the_weakest_confidence_and_is_excluded_by_default` plus `test_an_unknown_confidence_label_is_refused_not_assumed_adequate`. The confidence mutant was malformed on the first attempt and produced an import error rather than a test failure, which proves nothing; it was rewritten to replace the function body and then killed properly. Full suite green at 8,236 across 72 files. |

### Requirement 10 thresholds: measured (2026-09-03)

One untimed warm-up plus exactly three measured repetitions, nearest-rank p95,
against the fixed corpus. Backend: label-propagation/Leiden as installed on this
host.

| Measure | Observed | Ceiling | Verdict |
| --- | --- | --- | --- |
| Controlled rebuild 1 | 0.197 s | 120 s | pass |
| Controlled rebuild 2 | 0.033 s | 120 s | pass |
| Zero-change reuse | 0.0001 s | 10 s | pass |
| Full rebuild+rebuild+reuse sequence | 0.230 s | 250 s | pass |
| Public graph-report p95 (FIXED CORPUS) | 0.039 ms | 1000 ms | pass |
| Public graph-report, real repository (single warm call) | 316 ms | 1000 ms | pass |
| Compressed cluster artifact | 904 B | 1 MiB | pass |

Reuse behaviour, asserted rather than inferred: the reuse path was taken
(`fingerprint match` in build output), and the artifact's SHA-256 and `mtime_ns`
were both preserved, so no rewrite occurred.

**Determinism.** Two fresh builds produce identical community ids and identical
member sets. Their artifact BYTES differ, and the cause was checked rather than
waved through: the only differing top-level key is `generated_at`, a wall-clock
stamp. Requirement 10 asks for identical normalized scored rows and community
ids, which is satisfied; byte-identity across independent runs is not claimed
and is not achievable while the artifact records when it was written.

**Scope of the p95 row (delivery review, PERF-DEL-4).** The 0.039 ms figure is measured against
the FIXED CORPUS, which Requirement 10 caps at 128 files / 2,000 nodes / 5,000 edges. It is not
coverage of the shipped tool: on the real 23,600-node graph a warm `wf_graph_report` call measures
316 ms, roughly 8,100x higher, and the evidence partition alone costs 8.33 ms there. Both pass the
1,000 ms ceiling, so this is a coverage-honesty note rather than a breach, but the corpus row must
not be read as a statement about production.

**One figure above a review line.** A graph-only rebuild of the WHOLE repository
took roughly 52 s, above Requirement 10's 30 s operator-review threshold. That
is the real-repository build (23,560 nodes / 69,340 edges), not the fixed corpus,
and it is reported here rather than omitted because the threshold names
graph-only rebuild without restricting it to the corpus. **Attribution (delivery review,
PERF-DEL-9):** the comparison is unlike-for-unlike. The standing 19.4 s figure in
`docs/architecture/performance-budget.md` was an INCREMENTAL merge; this wave bumps the graph
builder to 49 (48 when this row was measured) and the cluster builder to 13, which by the standing rule forces full re-extraction of
every file. 52 s is therefore the one-time cost OF the version bump, not a recurring per-build cost.
The budget document now carries both rows so the next wave does not read 19.4 s as the standing
expectation and 52 s as a fresh regression.

### Import-head authority: measured blast radius (2026-09-03)

The AC-2 repair changes production extraction, so it was measured by rebuilding the whole
repository graph on both sides and diffing the edge sets.

| Quantity | Value |
| --- | --- |
| Baseline edges (builder 47) | 69,313 |
| Edges removed | 123 |
| Edges added | 150 |
| Removed share of baseline | 0.18% |

Removed edges are `calls` (121) and `reads` (2); 125 of the 150 additions are the same
calls landing on their honest `external::` target instead. Every sampled removal was a
flagrantly wrong bind that the last-segment fallback had invented:

- `accel_embedder.py::build_static_onnx` calling `onnx.load()` was bound to a nested fake
  `load` method inside a test class. It is now `external::onnx.load`.
- `cli_stdio.py::isolated_stdout_fd` calling `sys.stdout.fileno()` was bound to a test
  helper's `fileno`. It is now `external::sys.stdout.fileno`.
- `context_efficiency.py` calling `sqlite3.connect()` was bound to `dashboard.js::App.connect`
  -- a **JavaScript** method reached from Python. It is now `external::sqlite3.connect`.

The fix is therefore a precision repair rather than a recall cut: it removes cross-language
and test-into-production phantom edges that were actively misleading impact analysis.

**Incremental locality.** The first formulation keyed the decision on the imported FQN's
first segment, which is not derivable from the edge alone. The differential-equivalence
fuzz caught it immediately (seed 2026, right after the last file of a package was deleted):
incremental and full builds disagreed because unchanged files never re-resolved. The landed
version keys on the BARE receiver head, which the edge does carry, and declares it as a
lookup key (`modhead:` prefix) so a changed or removed file that adds or drops that head
invalidates every edge consulting it. All 40 differential cases pass.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Establish the fidelity corpus first, classify evidence as a fixed auxiliary domain while retaining its graph nodes, and report it outside the production community ranking. | Measurement prevents a cosmetic clustering change, fixed-community extraction preserves topology, and response partitioning keeps architectural orientation useful. | **Exclude evidence from graph indexing:** loses useful relationships. **Relabel inside the same top-N:** the large bucket still dominates orientation. **Rewrite clustering:** disproportionate without evidence that Leiden is the limiting factor. |
| 2026-09-03 | Place the Evidence/Data positive control under this wave's own evidence tree, and guard every classification assertion with a presence assertion. | A re-derived census of the persisted graph shows `docs/evals/` and `docs/reports/` contribute **zero** nodes each while wave evidence trees contribute 2,758, so a control filed beside the other eval fixtures would never be indexed and would pass vacuously. | **Beside the other eval fixtures:** never indexed. **Assert classification without a presence guard:** an unindexed control reads as "no mismatch, therefore correct". |
| 2026-09-03 | Fix the `cpu_count` over-binding rather than record it as a known gap. | AC-2 requires zero false positives on the seeded external-API collision. `os.cpu_count()` was binding to a project function that merely shared the bare name, which is the most misleading class of false edge the graph can emit. The fix makes an explicitly imported receiver head authoritative, matching the principle the Go package-qualified branch already used. | **Record as a known gap:** AC-2 forbids it. **Deny-list stdlib names:** brittle, and unable to generalise to third-party packages. |
| 2026-09-03 | Split the corpus gate into a hard zero-false-positive assertion plus a declared-gap set that must match the actual misses exactly. | A false positive is an untrue edge and is never acceptable; a recall gap is a measured limitation. Pinning the gap SET in both directions means a new miss fails as undeclared and a repaired miss also fails, so an improvement cannot land while the corpus still calls it broken. | **Assert zero false negatives:** would have forced either a node-identity rewrite or silent deletion of real expectations. **Drop the missed expectations:** hides measured limitations. |
| 2026-09-03 | Record the single-class-file node-identity collapse as a finding rather than fixing it here. | A file whose only top-level construct is one class gets no module node; the class takes the file's id, so `svc/session.py` is ambiguous between file and class. Correcting the identity scheme would change every single-class file in every consuming repository, which is far outside a measurement wave's scope. | **Fix now:** disproportionate blast radius, unrelated to this wave's requirements. **Ignore:** the corpus surfaced it, so it belongs on the record. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small corpus overstates global fidelity. | Report its bounded scope and supplement it with a live same-root-cause census. |
| Evidence classification overmatches legitimate configuration JSON. | Use path/role provenance with positive configuration controls. |
| Evaluator/report proximity becomes a proxy for machine evidence. | Require explicit producer/schema provenance, graph-absence controls for ignored artifacts, evaluator-code negatives, and move/rename invariance. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
