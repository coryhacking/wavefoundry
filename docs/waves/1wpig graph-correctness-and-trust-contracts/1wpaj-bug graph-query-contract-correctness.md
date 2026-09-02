# Restore Graph Query Filtering and Edge-Trust Contracts

Change ID: `1wpaj-bug graph-query-contract-correctness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-02
Wave: 1wpig graph-correctness-and-trust-contracts

## Rationale

`wf_graph_report` truncates ranked sections before applying external/generated filters. A `limit=1` project-only fan-in request therefore returns an empty list even though project nodes exist below the external top result, regressing the completed public requirement that filtering precede truncation. `code_callhierarchy` also projects away edge relation and confidence plus node kind and ID, so consumers cannot apply the documented trust policy to individual hierarchy entries.

## Requirements

1. Graph-report eligibility filters SHALL run before top-N truncation for every affected ranking section and supported collapse view.
   The required matrix for `fan_in`, `fan_out`, `chokepoints`, and `file_hubs` is all eight boolean combinations of the public `collapse_generated_files`, `collapse_class_module_pairs`, and `collapse_package_to_directory` flags, crossed with filter modes none, external-only, generated-only, and combined. For every applicable cell, the metamorphic oracle is the first requested `N` eligible rows from that exact collapsed topology's complete deterministic unfiltered candidate order. `betweenness` is supported only when all three collapse flags are false: any collapsed request that includes it SHALL return no stale base-topology ranking, set `betweenness_computed=false`, and expose `betweenness_skipped_reason="unsupported_for_collapsed_view"`; the uncollapsed cell is crossed with all four filter modes. `communities` remains an artifact-defined base-topology section: collapse flags do not project or rerank it, its complete base order SHALL be invariant across all eight flag combinations, and supported generated eligibility SHALL run before top-N; external filtering is not applicable because community members are project nodes. `orphan_docs` is an unranked diagnostic set and is outside the refill matrix.
2. When eligible candidates are at least the requested limit, each ranking section SHALL return that many entries.
3. Each call-hierarchy entry SHALL expose stable node ID, node kind, edge relation, and edge confidence in addition to presentation fields.
4. Existing aggregate external counts, communities, snippets, and compatibility fields SHALL remain intact.
5. Tool descriptions and Guru guidance SHALL describe the fields actually returned.
6. Uncollapsed betweenness refill SHALL operate on a persisted complete deterministic ranking, not only the current `BETWEENNESS_TOP_N` presentation prefix. Its exact candidate universe is every base-graph node whose computed centrality score is finite and strictly greater than zero, sorted by `(-score, node_id)`; zero/non-finite nodes remain excluded as today. Refill is required only within that universe: when fewer than `N` eligible positive-score rows exist, return all of them and expose truthful eligible/candidate counts. The cluster artifact SHALL retain the existing compact top-N metadata for compatibility while adding the complete scored base order needed by filtered public queries; `CLUSTER_BUILDER_VERSION` SHALL bump and old artifacts SHALL rebuild. No query-time centrality is permitted, and collapsed views SHALL use the explicit unsupported contract in Requirement 1 rather than serving base-topology scores as if they described the collapsed graph.
7. **Precommitted performance oracle:** measure two controlled current-repository cluster/graph rebuilds plus one zero-change reuse, with identical graph fingerprint and environment recorded and one attempt per controlled sample. Each rebuild SHALL time out and fail at 120 seconds, reuse SHALL time out and fail at 10 seconds, and the full two-rebuild-plus-reuse sequence SHALL time out and fail at 250 seconds. Cluster-stage post-change time SHALL be at most baseline plus `max(25% of baseline, 1 second)`; graph-only rebuild above 30 seconds requires operator review. Compressed cluster artifact bytes SHALL be at most `max(2 * baseline, baseline + 2 MiB)` and the report SHALL include complete-order rows, uncompressed JSON bytes, compressed bytes, compression ratio, and informational peak RSS when available. Reuse SHALL be proved by identical artifact SHA-256 and `mtime_ns` plus instrumentation showing clustering/centrality was not invoked. For filtered betweenness at limit 1 and the public maximum 100, three warm repetitions use nearest-rank p95; p95 SHALL be at most 1 second and at most baseline plus `max(25% of baseline, 50 ms)`. A zero-change pass SHALL neither recompute nor rewrite the artifact, and the complete internal order SHALL never appear in the public response.
8. Before graph production edits, the standing evaluator SHALL add `graph_cluster.py` and `CLUSTER_BUILDER_VERSION` to production identity and deterministic per-applicable-holdout-fixture comparison. The fixture oracle SHALL contain exactly one row for every applicable `(fixture_id, tool)` key in both reports, require identical key sets, compare every `FIXTURE_QUALITY_GATE_METRICS` value, and fail on duplicates, missing rows, incompatible nulls, or any regression. One bounded sequence driver SHALL own the exact A/B/C filenames and predecessor inputs. Fixture input is fixed to the frozen `docs/evals/retrieval-quality-golden.json`; baseline/output/report-manifest paths SHALL be regular direct children of `<root>/docs/reports`, reject outside-root paths, symlink components, hard-link/path aliases, and non-regular files, and never create caller-selected parent directories. The three closed-`1seaw` paths are protected inputs and cannot be destinations. For each comparison, the driver SHALL require externally supplied expected-baseline run ID, canonical content SHA, and expected closed-`1wpif` commit. It SHALL open the baseline once without following symlinks, hash the exact bytes from that handle before parsing, validate embedded run/commit identity, and fail if device/inode/size/mtime identity changes during the read; deriving expected values from the selected baseline itself is forbidden. Report writes SHALL use atomic exclusive creation: an existing destination or alias fails without changing bytes. Focused tests SHALL prove cluster-module/version drift changes production identity, one fixture can fail despite unchanged holdout aggregate/class metrics, an older otherwise-compatible report cannot substitute for the caller-declared predecessor, and path escape/symlink/alias/baseline-replacement/destination-preservation/protected-path mutants fail. The closed `1seaw` evaluator digest `61ec60daeb5347984f1e2c3e6f47a48d74931df11edf6f78ce84acb219c9207a` remains historical provenance only; after this scaffold lands, its successor evaluator digest SHALL be frozen before measurement while the 35-fixture corpus digest remains `bda675468d4da0184a97a94c4396cf8f379981a19339c1ad4958ba50f9466312`.
9. After `1wpif` closes, execution order is mandatory: land the Requirement 8 evaluator scaffold; freeze its successor digest; index that scaffold; record run A at `docs/reports/retrieval-quality-pre-1wpig-run1.json` with no baseline; record run B at `docs/reports/retrieval-quality-pre-1wpig.json` against caller-declared A on identical state/generation/production with measured jitter; only then begin graph production edits (`1wpai` before `1wpaj` query work); rebuild graph/cluster artifacts; and record run C at `docs/reports/retrieval-quality-post-1wpig-vs-pre.json` against caller-declared B. No graph production edit may precede successful A/B. The sequence permits at most four evaluator invocations (A, B, C, and one documented replay), retains every failed attempt under another unique exclusive-create filename, and requires operator direction after that budget is exhausted. Each invocation preserves the standing evaluator's caps of at most 48 fixtures, 512 UTF-8 query bytes, one warm-up plus exactly three measured repetitions, existing per-tool timeouts, and 1,200 seconds total; the full sequence has a 3,600-second timeout that takes precedence. Each report SHALL be at most 1 MiB and all sequence reports together at most 4 MiB. Before execution, the runner SHALL record and enforce a derived maximum public-call count of `4 * sum(applicable fixture/tool pairs) + fixed degraded/fallback probes`, with at most 12 fixed probes, therefore at most 780 calls per invocation and 3,120 across the four-invocation sequence. A successful invocation SHALL prove no concurrent publication occurred: refuse to start while the real index-build lock is held; record generation/attempt plus SHA-256 and builder metadata for graph, cluster, and index-state artifacts at start/end and around each public call; fail immediately without retry if the lock becomes held or any undeclared token/digest changes. A/B artifact identities SHALL match exactly; C may differ only through the declared versioned graph/cluster rebuild and SHALL remain internally stable. This fail-closed publication fence SHALL be bounded by existing call/sequence timeouts and SHALL NOT hold a run-wide build lock. The run-C production-path comparison SHALL pass with zero applicable-holdout-fixture, holdout-aggregate, holdout-class, critical-floor, latency, or payload violations; no active quality toggles; unchanged fixture/successor-evaluator identity; verified end-state digest; and an explicit controlled `cross_generation` receipt when the required builder-version rebuild changes generation. Run B's path, run ID, content SHA, generation/attempt, production digest, source builder constants, persisted graph/cluster/index-state artifact digests and builder metadata, and closed-`1wpif` commit SHALL be recorded; caller-supplied expected values SHALL make run B point to A and run C point to B exactly, and run C SHALL prove persisted artifact versions match post-change source constants. A fixed non-scored public carrier probe—`code_ask("What does update_graph_index call to protect native stdout during graph rebuilding?")`—SHALL record nonempty structural evidence, `graph_related` containing `isolated_stdout_fd`, and a `.wavefoundry/framework/scripts/graph_query.py` citation with `from_graph=true`; suppressing the graph carrier SHALL fail the probe. The existing 35-fixture `agentic-holdout-native-stdout`/`code_ask` row remains a scored regression control. Subprocesses SHALL remain argv-based with `shell=False`, bounded output/timeouts, offline model operation, and disclosed quality toggles. The three protected closed-`1seaw` reports named in the wave dependency record and every existing destination SHALL never be overwritten.

## Scope

**Problem statement:** Graph filters can manufacture empty/underfilled reports, and hierarchy projection hides the trust evidence needed to assess heuristic edges.

**In scope:** Report ranking/filter order, generated/external filters, complete persisted betweenness refill data, cluster artifact versioning, hierarchy response projection, MCP descriptions, public-handler regression tests, the bounded standing-evaluator identity/per-fixture/predecessor scaffold, and the unique run A/B/C graph-regression receipt chain.

**Out of scope:** Graph extraction accuracy, relation weighting, deeper hierarchy traversal, general retrieval-evaluator redesign, retrieval-ranking changes, and dashboard rendering.

## Acceptance Criteria

- [ ] AC-1: `fan_in(limit=1,exclude_external=true)` returns one project row on the current graph rather than `[]`.
- [ ] AC-2: Each applicable filtered report matrix cell fills its requested limit whenever enough eligible candidates exist; all eight public collapse-flag combinations are covered for topology-derived ranking sections, while collapsed betweenness returns the explicit unsupported contract instead of stale base-topology rows.
- [ ] AC-3: Incoming and outgoing hierarchy entries expose `node_id`, `kind`, `relation`, and `confidence` for resolved, construction-resolved, extracted, and external edges.
- [ ] AC-4: A client can deterministically retain only trusted confidence classes from a hierarchy response without calling a second graph tool.
- [ ] AC-5: Schema/tool descriptions, Guru guidance, focused tests, and the full framework suite agree with runtime behavior.
- [ ] AC-6: A builder-versioned cluster artifact persists the complete deterministic betweenness order required for filtering; filtered betweenness fills the requested public limit whenever enough eligible rows exist, old top-N consumers remain compatible, and rebuild time plus compressed artifact size stay within documented ceilings.
- [ ] AC-7: Every required section/collapse/filter matrix cell matches its specified metamorphic oracle; community order is collapse-invariant, collapsed betweenness is explicitly unsupported, positive-score exhaustion returns all eligible rows with truthful counts, and the precommitted rebuild timeout, artifact-size, instrumented zero-change reuse, and three-sample warm-query ceilings pass; peak RSS is recorded informationally when available.
- [ ] AC-8: The successor evaluator binds `graph_cluster.py`/`CLUSTER_BUILDER_VERSION`; enforces exact per-fixture key/metric/null semantics; rejects masked fixture regressions, path escape/symlink/alias/non-regular inputs, baseline read replacement, caller-declared predecessor run/SHA/commit mismatches, protected destinations, and atomic exclusive-write collisions; freezes its new digest; and preserves the closed `1seaw` evaluator digest only as historical provenance.
- [ ] AC-9: The mandatory scaffold→freeze→index→A→B→graph edits/rebuild→C order is enforced within the four-invocation, 3,600-second, 780-call-per-run, and report-size ceilings; run C points to caller-declared B by run ID/content SHA, proves stable persisted graph/cluster/index-state artifact digests and post-change source/version agreement, fails on concurrent/undeclared publication without a run-wide lock, passes every fixture/aggregate/class/floor/performance gate with inactive toggles and verified end digest, records `cross_generation` when required, passes the fixed `update_graph_index` graph-carrier probe and its suppression mutant, preserves bounded argv/offline execution, and never overwrites any existing or closed-`1seaw` report.

## Tasks

- [ ] Move eligibility filtering into report candidate ranking before slicing.
- [ ] Apply the ordering consistently across the exact eight-combination collapse matrix, preserve base-artifact community semantics, and reject collapsed betweenness with the documented structured reason.
- [ ] Propagate node and edge trust metadata through call-hierarchy projection.
- [ ] Add adversarial limit/refill and metadata-schema tests.
- [ ] Align tool descriptions and graph/Guru documentation.
- [ ] Extend and version the cluster artifact's betweenness payload, with compatibility, rebuild, determinism, size, and latency tests.
- [ ] Implement the complete section/collapse/filter matrix and the exact current-repository performance oracle before accepting delivery evidence.
- [ ] Extend and freeze the standing evaluator's cluster identity, exact per-fixture oracle, confined single-handle baseline/report I/O, caller-declared predecessor rejection, atomic exclusive report creation, publication/artifact fence, and fixed graph-carrier probe before measurement.
- [ ] Enforce the no-graph-edit-before-A/B sequence, then capture unique run A and jitter-bearing run B before publishing run C against exact caller-declared B with production/builder/commit/artifact and graph-carrier evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Report filtering | implementer | — | Eligibility before top-N |
| Hierarchy contract | implementer | — | Edge/node metadata |
| Standing evaluator scaffold | implementer | `1wpif` complete | Cluster identity, per-fixture oracle, exact predecessor chain; QA independently verifies |
| Public verification | qa-reviewer | All workstreams | MCP responses, graph-carrier proof, and current-graph probes |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_query.py`, `.wavefoundry/framework/scripts/graph_cluster.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`, `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `.wavefoundry/framework/scripts/retrieval_eval.py`, `.wavefoundry/framework/scripts/tests/test_retrieval_eval.py`, `docs/agents/guru.md`, `docs/architecture/graph-index-system.md`, `docs/architecture/testing-architecture.md`
- Frozen read-only input: `docs/evals/retrieval-quality-golden.json` at the Requirement 8 digest; implementation SHALL not edit it. The retrieval-quality receipts under docs/reports/ are run outputs, not declared paths.

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`
- `docs/architecture/testing-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces and closes the public-contract regression. |
| AC-2 | required | Prevents the same ordering defect across sibling sections. |
| AC-3 | required | Trust filtering depends on per-edge metadata. |
| AC-4 | required | This is the consumer-visible purpose of the metadata. |
| AC-5 | important | Public schema and guidance must remain synchronized. |
| AC-6 | required | Betweenness cannot satisfy refill correctness from a truncated persisted universe. |
| AC-7 | required | The refill and performance contracts need complete, independently falsifiable oracles. |
| AC-8 | required | Graph extraction/query modules participate in `code_ask`; the closed standing gate must detect citation regressions after rebuild. |
| AC-9 | required | The exact A/B/C receipt chain makes jitter, immediate-predecessor identity, graph-carrier exercise, and cross-generation delivery evidence auditable. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned from the graph audit lane. | Reproduced public report underfill and compared raw callgraph metadata with hierarchy output. |
| 2026-08-30 | Expanded filtered-refill scope to the persisted betweenness artifact after code review proved the current top-200 prefix cannot satisfy the unconditional public refill contract. | `compute_betweenness_ranking` slices to `BETWEENNESS_TOP_N`; code-review readiness finding. |
| 2026-08-30 | Replaced the nonexistent `collapse_to_files` test axis with the three real public collapse flags and bounded topology-sensitive artifact behavior. | All three collapse transforms run before `GraphQueryIndex.report`; persisted betweenness and communities describe the base topology, so collapsed betweenness is now explicitly unsupported and community ordering remains base-artifact invariant. |
| 2026-08-31 | Added the closed-`1seaw` standing retrieval gate as required delivery evidence. | The evaluator production identity includes graph extraction/query code, and graph signals can alter `code_ask` citation order after the required builder-version rebuild. |
| 2026-08-31 | Repaired the gate's evaluator-identity and receipt-chain contract before implementation. | Fresh code/QA review proved cluster identity would change the historical evaluator digest, aggregate/class checks could mask a fixture regression, and a three-run A/B/C chain is required to carry jitter into the controlled production/cross-generation comparison. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Filter the candidate universe before ranking truncation and preserve edge metadata in projection. | Directly restores both public contracts without heuristic overfetch. | **Overfetch by a fixed multiplier:** still underfills under larger skew. **Filter response after slicing:** current defect. **Require a second callgraph query:** keeps the preferred hierarchy tool unable to follow its own trust guidance. |
| 2026-08-30 | Persist the complete deterministic betweenness order beside the compatibility top-N view and bump the cluster builder version. | Public filtering cannot refill from the current bounded top-200 artifact even when eligible nodes exist below it. | **Narrow the public guarantee:** rejected because it would preserve a surprising underfill on a documented filter. **Fixed overfetch:** still fails under skew. **Recompute centrality per query:** violates the build-time centrality performance architecture. |
| 2026-08-30 | Support filtered betweenness only on the base topology and return a structured unsupported result for collapsed views. | Every collapse flag rewrites nodes or edges before report computation, while the persisted centrality artifact describes the base graph; serving that order under collapse is misleading, and persisting eight independent centrality universes is disproportionate to current user demand. | **Persist one order per collapse tuple:** substantially increases build/storage cost for an unvalidated use case. **Reuse base scores after collapse:** falsely labels base centrality as collapsed-graph centrality. |
| 2026-08-31 | Extend and freeze a successor evaluator before graph baselining rather than preserve the historical evaluator digest. | Cluster code/version and per-fixture/predecessor checks are required for this wave, and adding them necessarily changes evaluator source identity. | **Companion receipt beside the old evaluator:** splits one gate across two authorities. **Keep the old digest:** cannot bind the changed cluster carrier or detect masked fixture regressions. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pre-filtering changes historical rank composition. | Preserve sort keys and compare unfiltered results byte-for-byte. |
| Added response fields increase payload size. | Fields are compact and limited to already-returned entries; measure representative response size. |
| Complete betweenness order enlarges the cluster artifact. | Keep the compatibility top-N view, gzip the existing artifact as today, and gate compressed-size plus rebuild-time deltas on the current repository. |
| A caller expects betweenness to compose with collapse flags. | Return a stable, documented `unsupported_for_collapsed_view` reason and preserve all non-betweenness collapsed report sections. |
| The evaluator scaffold changes indexed source before baseline. | Land and index the bounded scaffold first, freeze its successor digest, then capture run A/B before any graph production edit. |
| Rebuild or evaluator retries make readiness evidence unbounded. | Enforce the per-sample and sequence timeouts, one rebuild attempt per sample, four evaluator invocations, explicit call/report-size ceilings, unique failed-attempt retention, and operator direction after exhaustion. |
| Caller paths or concurrent publication subvert an internally consistent receipt. | Use one sequence driver, fixed/direct-child regular paths, no symlinks/aliases, single-handle baseline hashing, atomic exclusive creation, start/end artifact digests, and fail-closed lock/token checks without a run-wide lock. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
