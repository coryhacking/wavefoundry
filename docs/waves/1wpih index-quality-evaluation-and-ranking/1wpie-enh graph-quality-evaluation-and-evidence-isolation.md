# Evaluate Graph Fidelity and Isolate Machine Evidence Communities

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-02
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

Graph tests provide substantial isolated fixture coverage but no representative mixed-artifact corpus reporting precision and recall by relation. The live audit found cross-domain false positives those fixtures missed. Architectural community reports are also dominated by machine evidence JSON: the second-largest current community contains 1,158 `freeze` nodes, yet is not classified as generated/evidence. The graph should retain evidence data for search while keeping it from masquerading as a production architecture domain.

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
11. Canonically ignored standing-retrieval artifacts — `docs/evals/retrieval-quality-golden.json` and `docs/reports/retrieval-quality-*.json` — SHALL remain absent from the graph and SHALL NOT be relabeled as Evidence/Data. `.wavefoundry/framework/scripts/retrieval_eval.py` SHALL remain ordinary framework code even when it co-clusters with machine artifacts. A nonignored synthetic machine-result artifact with explicit producer/schema provenance SHALL supply the positive Evidence/Data control.
12. The classifier SHALL be invariant to moving or renaming an otherwise identical provenance-backed machine-result artifact. Larger legitimate configuration, schema, design-token, prompt, and user-authored data fixtures SHALL remain in their ordinary domains. The scorer SHALL fail both an injected false-positive classification of one legitimate control and a false-negative classification of the provenance-backed machine-result control.

## Scope

**Problem statement:** Graph fidelity lacks end-to-end measurement, and machine evidence can dominate architectural orientation.

**In scope:** Representative graph evaluation, public-tool assertions, evidence/data classification or ranking policy, cluster tests, and measured before/after reports.

**Out of scope:** Removing historical evidence from the repository, excluding all JSON, rewriting Leiden clustering, and semantic retrieval evaluation owned by `1sear`.

## Acceptance Criteria

- [ ] AC-1: One local command builds the fixed corpus and reports the versioned schema, relation-to-public-tool matrix, and per-relation TP/FP/FN, precision, and recall through public graph responses.
- [ ] AC-2: The corpus covers every named adversarial and incremental case, flags deliberately seeded `cpu_count` and schema/config collisions, and reports zero such false positives in the corrected graph baseline.
- [ ] AC-3: In a fixture where Evidence/Data is larger than two legitimate production domains and `limit=2`, both production rows survive in every covered production section and Evidence/Data appears only in that section's exact parallel typed array without suppressing eligible production rows.
- [ ] AC-4: Evidence nodes and genuine cross-boundary edges remain available to targeted graph queries.
- [ ] AC-5: Community IDs and normalized scored results remain deterministic on two fresh fixed-corpus builds and zero-change reuse; the fixed corpus/report caps and exact rebuild/reuse timeout, p95, no-call, rewrite, and artifact-size thresholds in Requirement 10 pass for each recorded backend.
- [ ] AC-6: Graph architecture and testing documentation define the fidelity tier and evidence-community semantics; full tests pass.
- [ ] AC-7: Default and explicit requests for each partitioned section—including requests that omit `communities`—obey the exact five production/evidence array-pair schema, independent limits, empty-array, `exclude_generated`, and malformed/stale controls; `code_graph_community`, `code_graph_path`, and relation-appropriate targeted queries retain access to Evidence/Data nodes and boundary edges.
- [ ] AC-8: Positive configuration/design-token JSON controls remain in their legitimate domains; a same-fingerprint artifact at the landed predecessor cluster-builder version rebuilds under the next version, and the following unchanged invocation reuses it without rewrite.
- [ ] AC-9: The graph evaluation runner rejects an injected forbidden edge and a deleted expected edge, and its baseline/post reports carry every identity and schema field in Requirement 9.
- [ ] AC-10: Ignored standing fixture/report artifacts are absent from the graph, `retrieval_eval.py` remains ordinary framework code, and the explicit-provenance synthetic machine-result artifact enters Evidence/Data and remains queryable.
- [ ] AC-11: Move/rename invariance holds for the machine-result positive; large legitimate config/schema/design-token/prompt/user-data controls never enter Evidence/Data; and injected classifier false-positive and false-negative mutants fail the evaluator.

## Tasks

- [ ] Build and annotate the mixed-artifact ground-truth corpus.
- [ ] Add a public-tool evaluation runner and scored report.
- [ ] Freeze the relation/public-tool matrix, score normalization, report schema, evidence identities, and injected-scorer known-bads before graph-policy edits.
- [ ] Measure current community composition and label purity.
- [ ] Implement the smallest evidence/data classification or report-level isolation supported by the measurements.
- [ ] Apply the evidence partition before production top-N selection and add positive JSON classification controls.
- [ ] Add determinism, topology-preservation, size, and latency verification.
- [ ] Update graph and testing architecture documentation.
- [ ] Update the public graph-report response contract and tests for separate evidence-community reporting.
- [ ] Add exact public response/tool-description/spec tests for all five production/evidence array pairs, including single-section requests without `communities`.
- [ ] Add graph-absence assertions for ignored standing artifacts, ordinary-code assertions for `retrieval_eval.py`, and a nonignored provenance-backed machine-result positive.
- [ ] Add move/rename invariance plus legitimate-data false-positive and machine-result false-negative classifier tests.

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
| 2026-08-30 | Planned as later graph-quality work from the index audit. | Ten-case live sample; current graph report showing 1,158-node `freeze` community and machine-result hubs. |
| 2026-08-31 | Tightened Evidence/Data identity from closed-`1seaw` carrier findings and predecessor-version sequencing. | Standing retrieval artifacts are canonically ignored; evaluator source is ordinary code; graph-positive evidence now requires a nonignored provenance-backed fixture and predecessor-relative cluster invalidation. |
| 2026-08-31 | Made Evidence/Data carriers and graph-evaluation costs complete. | Final architecture/QA review required parallel typed arrays for every pre-top-N partitioned section plus fixed corpus/report and rebuild/reuse ceilings. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Establish the fidelity corpus first, classify evidence as a fixed auxiliary domain while retaining its graph nodes, and report it outside the production community ranking. | Measurement prevents a cosmetic clustering change, fixed-community extraction preserves topology, and response partitioning keeps architectural orientation useful. | **Exclude evidence from graph indexing:** loses useful relationships. **Relabel inside the same top-N:** the large bucket still dominates orientation. **Rewrite clustering:** disproportionate without evidence that Leiden is the limiting factor. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small corpus overstates global fidelity. | Report its bounded scope and supplement it with a live same-root-cause census. |
| Evidence classification overmatches legitimate configuration JSON. | Use path/role provenance with positive configuration controls. |
| Evaluator/report proximity becomes a proxy for machine evidence. | Require explicit producer/schema provenance, graph-absence controls for ignored artifacts, evaluator-code negatives, and move/rename invariance. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
