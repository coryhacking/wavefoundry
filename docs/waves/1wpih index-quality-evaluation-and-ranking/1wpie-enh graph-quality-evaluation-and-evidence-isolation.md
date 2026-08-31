# Evaluate Graph Fidelity and Isolate Machine Evidence Communities

Change ID: `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

Graph tests provide substantial isolated fixture coverage but no representative mixed-artifact corpus reporting precision and recall by relation. The live audit found cross-domain false positives those fixtures missed. Architectural community reports are also dominated by machine evidence JSON: the second-largest current community contains 1,158 `freeze` nodes, yet is not classified as generated/evidence. The graph should retain evidence data for search while keeping it from masquerading as a production architecture domain.

## Requirements

1. A committed mixed-language, mixed-artifact graph corpus SHALL define expected and forbidden edges across supported relation types.
2. Evaluation SHALL report per-relation true positives, false positives, false negatives, precision, and recall through a frozen relation-to-public-tool matrix. Every scored relation SHALL include at least one expected edge and one forbidden opportunity, with direction, confidence threshold, duplicate normalization, and external-node treatment defined before implementation.
3. The corpus SHALL include ambiguous names, overloads, constructors, external APIs, test/generated boundaries, config/schema data, doc references, and incremental removal/update cases.
4. Wave evidence and comparable machine-result artifacts SHALL be classified into a fixed Evidence/Data community or excluded only from architectural rankings and label selection.
5. Evidence nodes SHALL remain queryable and their cross-boundary relationships SHALL not be silently discarded.
6. Community usefulness, purity, top-hub composition, determinism, build time, and artifact size SHALL be measured before selecting the isolation policy.
7. Whenever `communities` is requested explicitly or by default, the public graph report SHALL return both `communities` and `evidence_communities` arrays, using empty arrays when a partition has no rows. Both arrays retain the existing community-summary compatibility fields; evidence entries additionally carry `community_type="evidence_data"` and nonempty `classification_reasons`. The public limit applies independently after partitioning, `exclude_generated` does not erase Evidence/Data, and Evidence/Data community IDs remain discoverable in the community catalog and queryable through `code_graph_community`.
8. Evidence/Data classification SHALL occur before top-N selection for `communities`, `fan_in`, `fan_out`, `chokepoints`, and `file_hubs`; evidence rows SHALL not consume production ranking slots and SHALL remain represented through `evidence_communities`. The classification SHALL include positive controls for legitimate configuration and design-token JSON. The fixed-community/artifact-shape change SHALL bump `CLUSTER_BUILDER_VERSION` from 11 to 12, force a same-fingerprint v11 artifact to rebuild, and preserve byte/mtime-identical zero-change reuse afterward.
9. `.wavefoundry/framework/scripts/graph_quality_eval.py` SHALL evaluate `docs/evals/graph-quality-golden.json` and write `docs/reports/graph-quality-baseline.json` / `docs/reports/graph-quality-post.json`. Both reports SHALL bind corpus digest, evaluator identity, graph/query production identity, graph and cluster builder/schema versions, graph input fingerprint, repository/artifact identity, environment/backend, run timestamp, and report-content identity. The report schema SHALL name every scored relation and public tool used.
10. Performance and determinism evidence SHALL record one untimed warm-up plus exactly three measured repetitions using nearest-rank p95. Public graph-report p95 SHALL be at most 1 second and no more than baseline plus `max(25%, 50 ms)`; cluster-stage time SHALL be at most baseline plus `max(25%, 1 second)`, graph-only rebuild above 30 seconds requires operator review, and compressed cluster artifact bytes SHALL be at most `max(2 * baseline, baseline + 2 MiB)`. Two fresh identical builds SHALL produce identical normalized scored rows/community IDs, and a zero-change pass SHALL not rewrite artifacts.

## Scope

**Problem statement:** Graph fidelity lacks end-to-end measurement, and machine evidence can dominate architectural orientation.

**In scope:** Representative graph evaluation, public-tool assertions, evidence/data classification or ranking policy, cluster tests, and measured before/after reports.

**Out of scope:** Removing historical evidence from the repository, excluding all JSON, rewriting Leiden clustering, and semantic retrieval evaluation owned by `1sear`.

## Acceptance Criteria

- [ ] AC-1: One local command builds the fixed corpus and reports the versioned schema, relation-to-public-tool matrix, and per-relation TP/FP/FN, precision, and recall through public graph responses.
- [ ] AC-2: The corpus covers every named adversarial and incremental case, flags deliberately seeded `cpu_count` and schema/config collisions, and reports zero such false positives in the corrected graph baseline.
- [ ] AC-3: In a fixture where Evidence/Data is larger than two legitimate production communities and `limit=2`, both production rows survive in `communities`/covered ranking sections and Evidence/Data appears only in the typed auxiliary partition without suppressing eligible production rows.
- [ ] AC-4: Evidence nodes and genuine cross-boundary edges remain available to targeted graph queries.
- [ ] AC-5: Community IDs and normalized scored results remain deterministic on two fresh fixed-corpus builds and zero-change reuse; the exact time, p95, rewrite, and artifact-size thresholds in Requirement 10 pass for each recorded backend.
- [ ] AC-6: Graph architecture and testing documentation define the fidelity tier and evidence-community semantics; full tests pass.
- [ ] AC-7: Default and explicit `communities` requests, low limits, empty Evidence/Data, and malformed/stale cluster controls obey the exact dual-array schema; `code_graph_community`, `code_graph_path`, and relation-appropriate targeted queries retain access to Evidence/Data nodes and boundary edges.
- [ ] AC-8: Positive configuration/design-token JSON controls remain in their legitimate domains; a same-fingerprint v11 cluster artifact rebuilds under v12, and the following unchanged invocation reuses it without rewrite.
- [ ] AC-9: The graph evaluation runner rejects an injected forbidden edge and a deleted expected edge, and its baseline/post reports carry every identity and schema field in Requirement 9.

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

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fidelity corpus | qa-reviewer | — | Expected and forbidden edges |
| Evidence policy | implementer | Fidelity corpus | Fixed community or ranking isolation |
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

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned as later graph-quality work from the index audit. | Ten-case live sample; current graph report showing 1,158-node `freeze` community and machine-result hubs. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Establish the fidelity corpus first, classify evidence as a fixed auxiliary domain while retaining its graph nodes, and report it outside the production community ranking. | Measurement prevents a cosmetic clustering change, fixed-community extraction preserves topology, and response partitioning keeps architectural orientation useful. | **Exclude evidence from graph indexing:** loses useful relationships. **Relabel inside the same top-N:** the large bucket still dominates orientation. **Rewrite clustering:** disproportionate without evidence that Leiden is the limiting factor. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small corpus overstates global fidelity. | Report its bounded scope and supplement it with a live same-root-cause census. |
| Evidence classification overmatches legitimate configuration JSON. | Use path/role provenance with positive configuration controls. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
