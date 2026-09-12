# Evaluate SQLite graph consolidation

Change ID: `1xny2-task evaluate-sqlite-graph-consolidation`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-11
Wave: 1xny3 sqlite-graph-consolidation-evaluation

## Rationale

Determine whether native SQLite graph tables can simplify Wavefoundry's local index, reduce memory and maintenance costs, and preserve structural retrieval quality. The audience is framework maintainers and operators; the deliverable is a measured recommendation, including reasons to retain the current design if it wins. Evaluate storage representation, transaction consolidation and retrieval ordering independently. Cypher is an optional query-language comparison, not a presumed dependency.

Wave 1xjmm consolidated semantic chunks, FP32 vectors, FTS and maintenance state in `.wavefoundry/index/index-state.sqlite`. Graph extraction state still uses a separate SQLite store; assembled graph artifacts are compressed JSON loaded into a cached in-memory adjacency index. Existing capabilities include typed relationships, graph-assisted retrieval, traversal, confidence-weighted paths, impact and community analysis. Preserve that actual capability set.

Baseline source anchors are `graph_indexer.py` (store schema and `read_graph_payload`), `graph_query.py` (`GraphQueryIndex`) and `server_impl.py` (`search_combined`) under `.wavefoundry/framework/scripts/`. Reconfirm source revision at execution. Currently, initial candidates are reranked before graph expansion and selected graph-citation insertion; pre-rerank expansion is a distinct behavior experiment.

## Requirements

1. Inventory the baseline's artifacts, process caches, extraction/resolution, public tools, algorithms, publication fences and close-wave maintenance. Identify removable duplication and derived data still needed.
2. Compare A: current SQLite state/compressed artifacts/in-memory adjacency; B: normalized node/edge tables in a separate SQLite database; C: the same representation alongside semantic tables in a copied `index-state.sqlite`. B gates C. A bounded hybrid cache variant may be tested if B measurements justify it. Never benchmark by converting the live index.
3. Compare identical graphs and workloads before changing retrieval. Test indexed neighbor queries and recursive CTEs against current incoming/outgoing calls, imports, inheritance, doc links, confidence-weighted paths, impact and community consumers. Preserve stable identity, relation types, confidence, provenance, multi-edge evidence, unresolved external targets, deterministic ordering and limits. Symbols and chunks are not one-to-one: assess an explicit mapping. Foreign-key design must accommodate legitimate external targets.
4. Probe cycles, repeated paths, high fan-out, disconnected nodes and selective relation/path filters with bounded work. UNION over `(id, depth)` does not deduplicate nodes globally: specify visited-node, cycle, shortest-path and result-budget semantics. Recursive CTEs do not replace igraph/Leiden; account for retaining or replacing those computations explicitly.
5. Measure warm/cold traversal and full tool p50/p95/p99, startup/cache construction, RSS/peak RSS, CPU, total disk including tables/indexes/WAL/artifacts, and dependency footprint separately in MiB. Measure incremental throughput, file-change-to-queryable latency, rebuild stages, branch churn, delete/reinsert, concurrent readers, writer-lock duration, checkpoint progress and compaction. Use a fair warm cached baseline; a fresh process alone is not an OS-cold-cache measurement.
6. Use this repository's actual graph and deterministic topology-aware fixtures at roughly 1x, 5x and 10x its size where resources permit, plus adversarial fan-out. Record the observed crossover or bounded resource stop, never extrapolated qualification. Retain raw observations/repetition counts, fixture hashes, source revision, hardware, OS, Python, SQLite/binding versions, schemas/indexes and effective PRAGMAs.
7. Use deployed SQLite settings as the control. Test bounded cache/mmap/batch-size changes only where measurements identify a bottleneck; count all connections and aggregate memory. Evaluate WAL readers, prepared work outside the lock, bounded BEGIN IMMEDIATE publication, passive checkpoints and reusable free space. A shared file or routine full VACUUM is not inherently an optimization.
8. For C, prepare extraction, embeddings and global resolution outside the transaction. Probe atomic publication of affected chunks/FTS/vectors/nodes/edges/state, including cross-file relationship invalidation; rollback, interruption/restart, readers spanning publication and graph-only builds. Preserve epoch/recovery fences until evidence supports simplification. Include total memory for global algorithm materialization.
9. Independently compare current retrieval ordering with bounded graph expansion before reranking. Hold embedding/chunking, FTS behavior, query corpus, initial candidates, reranker and final top-K constant; declare extra graph-candidate and rerank budgets. Measure relevant-candidate recall, final citation coverage/relevance/noise, full latency and reranker cost on judged multi-file questions and negative controls. Baseline-result agreement is distinct from judged relevance; do not attribute ranking gains to storage.
10. Evaluate Cypher on representative existing and awkward ad hoc queries: expressiveness, maintainability, supported semantics, and value to maintainers versus agents. Review current primary documentation for GraphQLite and agentflare sqlite-graph: licenses, versions, platform binaries, maturity, algorithms and dated roadmaps. Distinguish shipped, announced and speculative features; check licensing/compatibility before any isolated optional probe. No production extension or arbitrary-query MCP tool is introduced.
11. Recommend retain/adopt/defer separately for native tables, shared storage, retrieval ordering and Cypher. Record decisions in one ADR, including measured tradeoffs and unexecuted platforms. For a recommended conversion, propose schema/versioning, staged rebuild versus conversion, quiescence/restart/resume, verification, rollback and removal of old graph artifacts only after verified publication. Production conversion requires a separately admitted and readied change.

## Scope

**In scope:** architecture/ecosystem research; reproducible isolated harnesses/prototypes after Prepare; copied stores and fixtures; consistency/recovery probes; retrieval experiments; one consolidated result and one ADR.

**Out of scope:** production query/schema changes, live conversion, installing dependencies into shared environments, new public MCP query tools, removal of existing algorithms, hosted services, unrelated CoreML/rebuild-notice fixes and release packaging.

Keep narrative results in this change doc. Use one compact machine-readable benchmark receipt and the minimum runnable harness/fixture definitions. Large databases/raw logs stay outside version control. Required wave.md/events.jsonl carry lifecycle evidence; do not create per-pass Markdown reports.

## Evaluation Gates

1. **Readiness:** confirm the capability matrix and the protocol below before benchmarks. The prior operator-approved 100 ms vector allowance is context, not automatically a graph or end-to-end budget. Report absolute/relative deltas and reranking's share of total latency.
2. **Native parity:** B must pass correctness and bounded-work probes before C advances. Failure yields an evidenced retain/defer decision, not a consolidation qualification.
3. **Consolidation:** C must pass publication/recovery/concurrency probes and show material operational benefit within frozen budgets. A shared filename alone is insufficient.
4. **Retrieval:** decide pre-rerank expansion separately against judged quality and frozen budgets; storage adoption does not require adopting that pipeline change.
5. **Decision:** retain/defer is a valid outcome. Downstream phases stopped by a failed prerequisite are explicitly recorded as not run with evidence. Closing this evaluation neither authorizes production conversion nor proves unexecuted platform compatibility.

## Fixed Evaluation Protocol

These are conservative screening rules for this evaluation, not new product SLAs or permission to weaken existing contracts. Apply stricter existing structural budgets from `docs/architecture/performance-budget.md` where relevant. Budget changes require a documented reason and a fresh paired run; retain the original result.

- **Semantic parity:** zero unexplained differences in node/edge identity, evidence, reachable sets, confidence-weighted path results, limit/error behavior, and unchanged public graph fixtures. Define canonical tie handling before comparison; ordering differences permitted by an existing contract are classified explicitly, never silently discarded.
- **Independent structural oracle:** add tiny hand-derived fixtures for a directed cycle, acyclic diamond, parallel evidence, external endpoints/bridges, confidence-weighted alternatives and bounded/filter queries. Expected answers must not be generated by A or B. Compare mathematical expectations, stored evidence and public projections separately: current traversal can flag a revisit as `has_cycles` and deduplicate public edges by source/target/relation. Preserve and disclose pre-existing anomalies; changing those public semantics requires separately admitted scope.
- **Performance screening:** at the real local corpus, warm p95 for bounded 1–3-hop graph expansion must be below 100 ms; whole-tool warm p95 and incremental file-change-to-queryable p95 may increase by at most the larger of 10% or 10 ms versus A. Report every query family separately. Full-rebuild median and startup p95 may increase by at most 10%; cold first-query latency remains separately visible. If A itself exceeds a screen, record a baseline failure and require improvement or defer qualification, rather than rewriting the threshold. Scaled/adversarial graphs identify limits, not mandatory production capacity.
- **Material benefit:** recommend storage adoption only with correctness and latency gates met plus at least 20% improvement in total steady RSS, peak RSS, persistent footprint, startup or update latency; alternatively, demonstrated removal of the cross-store publication/reconciliation boundary with no more than 10% regression in any measured resource category. Report which criterion won and all tradeoffs. A decision to retain A is successful evaluation work.
- **Retrieval corpus:** freeze at least 30 questions before variants run: 15 multi-file mechanisms, 5 exact-owner lookups, 5 negative/irrelevant-expansion controls and 5 inheritance/doc-link/impact questions. Map expected relevant files/symbols and required chain links from source; QA checks judgments independently before comparing variant outputs. Use candidate Recall@K at the actual candidate pool, final citation precision/recall and required-chain coverage; report per-question losses, not only averages. Acceptance requires no lost required chain or exact-owner result, no decrease in macro final precision/recall, and an improvement on at least two mechanism questions; otherwise retain current ordering. Report inconclusive outcomes rather than claiming statistical generalization from 30 questions.
- **Candidate cost:** run an equal-total-candidate-budget arm first; a separate expanded-budget arm may add at most 30 graph candidates and 25% of the baseline reranker candidate count (whichever is smaller). Keep original retrieval inputs fixed, show deduplication/admission rules, and satisfy the whole-tool latency gate. An unavailable reranker or changed hardware provider makes that paired run unqualified; do not substitute lexical fallback as equivalent evidence.
- **Repetitions:** three interleaved A/B (and eligible C) runs, each with 10 warm-up queries and at least 100 timed observations per graph-query family. Pool at least 10 startup/update observations per variant across those runs, retaining run labels; their p95 is a coarse descriptive estimate and p99 from small samples is descriptive only. For full rebuilds, use three complete interleaved paired observations per variant and compare medians; retain all durations and the maximum, with no p95/p99 or population-tail claim. Stop early on a correctness failure or resource limit and preserve the failure evidence. Run the real-corpus screening before exploratory scales. Fewer than three complete rebuild pairs, or missing mandatory observations for another metric, leaves that metric unqualified. A stopped optional scaled run does not invalidate completed real-corpus evidence. Do not repeatedly run expensive full rebuilds once a failure has decided the gate.
- **Resource envelope:** one benchmark worker/configuration at a time, up to 30 minutes per configuration and 4 hours total before a recorded bounded stop; aggregate benchmark-process RSS at most the smaller of 4 GiB or 25% physical RAM; scratch allocation at most the smaller of 8 GiB or 25% initially free disk. Sample RSS/disk while running, enforce per-query 5-second cancellation and an owned-worker watchdog, and terminate only processes created by the harness. Never drop the host OS cache or stop another repository's processes. Cold runs are labelled process-cold unless OS-cache state is independently controlled without host-wide mutation.
- **Isolation:** use SQLite online backup or an equivalent consistent snapshot, not a bare copy of a live WAL database. Bind graph and semantic snapshots to a stable completed epoch; retry acquisition if the epoch changes, and record artifact hashes. Do not hold a live transaction while benchmarking. All writes, crash injection, branch churn and cleanup operate under a freshly created dedicated scratch root with resolved-path ownership checks; branch churn uses fixture changes, never checkout in the working repository. Reject live-index paths and symlink escapes before mutations. An isolated harness subprocess is the only crash target. Committed evidence contains identifiers/metrics and hashes; avoid duplicating repository text, credentials or full database contents.

## Continued evaluation — operator direction, 2026-09-10

The operator accepts 300–500 ms for this graph work and explicitly values a single database/transaction. Continue the isolated evaluation before selecting a production conversion. The original protocol and all first-round results above/below remain historical evidence; do not relabel them as measurements made under the revised budget.

For fresh paired runs, use **500 ms warm p95 for graph query work**, including scoped risk/report queries and bounded expansion. Report p50/p95/p99 and absolute/relative changes; a large percentage increase from a tiny baseline is not itself rejection inside this operator-approved absolute allowance. Existing complete tools already above 500 ms retain their previous whole-tool allowance of max(10%,10 ms) over A; 500 ms is not imposed on model initialization, embeddings, rebuilds or maintenance. The five-second individual query guard and resource envelope remain unchanged. Full-rebuild/startup gates remain separately reported, rather than silently waived. Correctness and retrieval-quality requirements remain unchanged; AC4's independent ranking experiment stays deferred.

The continuation has three ordered outputs:

1. Repeat broad risk/report workloads with real same-scope outputs and the existing three-run/100-observation protocol. Evaluate native SQL filtering/aggregation or bounded materialization only where those measurements identify unnecessary full scans; compare to A and preserve the first lazy-adapter results. Measure the cached adapter against the shared file, not only separate B.
2. Extend the shared prototype toward actual producer integration: current source extraction and global resolution, extraction-state persistence, community computation/publication, graph-only rebuilds, changed-file/branch-like deltas and real symbol/chunk overlap mapping. Use the real producers on an owned copy. Prepare expensive work outside the writer lock, then verify a single transaction can publish all affected state. State exactly which producers/state are integrated and which still require separate fences. No fake embedding is accepted as a freshly regenerated semantic vector.
3. Run paired source-rebuild/publication and mutation/recovery probes where integrated, including cross-file edge invalidation, concurrent readers, interrupted publication, reusable free pages and total memory/disk. If a full semantic-plus-graph producer cannot be integrated within this bounded prototype, retain that explicit gap; do not call prepared row updates a complete index rebuild. Update the single receipt and ADR with the measured recommendation and remaining production gates.

Coordinator owns plan/results/ADR and `graph_eval.py`; a senior-data-engineer builder may own one additional wave-local lifecycle harness, importing the existing isolation/measurement helpers. Independent reviewers inspect the revised budget and transaction boundary before new harness code. Benchmark workers remain serialized by the existing real OS flock, and writes remain entirely in the owned scratch copy. No production schema/source change, live conversion, dependency install, packaging or closure is authorized by this continuation.

## Plan Review Questions

- **Must Cypher or shared storage win?** No; independent retain/adopt/defer decisions satisfy the brief. Baseline and native SQL are mandatory; extension execution is optional after license/compatibility review.
- **Does a shared filename prove atomicity?** No; use prepared publication and cross-file invalidation probes, keeping existing epoch fences until proven unnecessary (`docs/architecture/graph-index-system.md`, shared build-epoch contract).
- **Are graph nodes interchangeable with chunk IDs?** No; retain separate identities and measure the mapping (`GraphQueryIndex` versus canonical semantic chunk tables).
- **Does this authorize production conversion or a new SLA?** No; the fixed budgets screen an isolated evaluation and any implementation requires a new readiness gate.
- **Stop condition:** the scope and experimental protocol are fixed; empirical winners remain the evaluation's output. No operator-only decision is currently needed to prepare this evaluation.

## Acceptance Criteria

- [x] AC-1: The inventory and capability matrix cover current storage, public graph behavior, algorithms, retrieval ordering and lifecycle maintenance, with source references and the evaluation budgets fixed below.
- [x] AC-2: A reproducible A/B comparison reports correctness, bounded traversal, scale, latency, memory, disk and updates with runtime/configuration provenance and honest cache limitations.
- [x] AC-3: The C evaluation records shared-publication/recovery/concurrency evidence, or an explicit Gate 2 stop without a consolidation qualification claim.
- [~] AC-4: The independent retrieval experiment reports judged candidate/final-result quality and full latency/cost under fixed inputs and explicit expansion budgets. *Paired ranking/quality qualification intentionally deferred after the clean baseline API exceeded the frozen five-second deadline in its first warm-up. Thirty source-grounded questions and independent QA are frozen; CPU fallback and 119+3 successful reranks are recorded. Neither variant ran; current ordering is retained without an adoption claim.*
- [x] AC-5: The Cypher/extension assessment compares concrete queries, shipped capabilities, licenses, compatibility and dated roadmap evidence without assuming adoption.
- [x] AC-6: One ADR records separate decisions, tradeoffs, proposed safe upgrade/cleanup for any recommended conversion, and remaining implementation/platform gates.

## Tasks

- [x] Inventory the baseline and instantiate the fixed workload, resource limits and decision budgets without changing thresholds after seeing results.
- [x] Build and verify isolated A/B harnesses; capture current and scaled graph results.
- [x] Evaluate shared storage and publication safety if native parity passes; otherwise record the gated stop.
- [~] Run the independent graph-expansion/reranking comparison on judged queries. *Deferred with AC-4 after the clean baseline screening stop; zero paired observations, no ranking-quality claim.*
- [x] Assess Cypher implementations, licenses, compatibility and roadmaps.
- [x] Consolidate results and benchmark receipt; author the ADR and proposed migration/cleanup gates.
- [x] Run change-local checks and required review lanes; resolve findings and validate authored documents.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Baseline and benchmark design | coordinator / architecture reviewer | — | Freeze inputs and thresholds before execution. |
| Native tables and shared publication | implementer | baseline | Isolated prototypes; B gates C. |
| Retrieval ordering | implementer / QA reviewer | baseline | Independent from storage adoption. |
| Cypher and synthesis | coordinator / architecture reviewer | measured results for final synthesis | Primary-source research can proceed independently. |

## Serialization Points

Coordinator owns this plan, result receipt and ADR. Harnesses remain wave-local and are not packaged. Runtime source below is read-only investigation scope; no production edits are authorized.

**Review targets (repo-relative paths):**

- `docs/waves/1xny3 sqlite-graph-consolidation-evaluation/`
- `docs/architecture/decisions/`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/sqlite_runtime.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`

## Affected Architecture Docs

`docs/architecture/decisions/`: one evaluation ADR. `docs/architecture/graph-index-system.md` and `docs/architecture/data-and-control-flow.md` are baseline references; preserve their deployed-behavior descriptions. A subsequent conversion wave updates them when implementation changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establish the real baseline and prevent moving goalposts. |
| AC-2 | required | Demonstrate native graph viability and measurable value. |
| AC-3 | required | Qualify consistency or record the prerequisite stop. |
| AC-4 | required | Separate retrieval quality from engine performance. |
| AC-5 | required | Resolve the query-language question. |
| AC-6 | required | Make the decision durable and implementation reviewable. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-10 | Readback: AC1–6 evaluate existing A, isolated native B, gated shared C, independent retrieval ordering and Cypher; only wave-local harnesses/receipts and one ADR change. | User authorized execution; wf_implement_wave opened 1xny3. |
| 2026-09-10 | Thought: snapshot a complete epoch; inventory actual structures; run independent oracles then paired A/B; run eligible C; serialize retrieval measurements; synthesize ADR and change-local checks. Builders: coordinator graph/SQL, implementer retrieval, research lane Cypher. | Fixed Evaluation Protocol; benchmark workers serialized. |
| 2026-09-10 | Observe: 48 independent fixture combinations and 396 real-graph comparisons passed; all 600 public response hashes per variant match A. H improves graph-worker RSS about 62%; broad consumers and complete lifecycle remain unqualified. | benchmark-results.json; final source-grounded matrix. |
| 2026-09-10 | Reflect: first producer patch reached the wrong namespaced loader; discarded those runs and pinned the actual accessor, requiring 220 invocations per worker. Earlier overlapping measurements were discarded and replaced by OS-lock-serialized runs. | Receipt history; no discarded run contributes to current aggregates. |
| 2026-09-10 | Observe: ownership-bypass mutant is detected; removed-finally diagnostic-write mutant exits 1 instead of guarded 89; synthetic configured-RSS-cap-plus-one trips exit 88. Unpinned cache mutant fails the same neighborhood assertion after a writer changes a hydrated node label. | graph_eval.py safety / extended; final_guard_cache_probes; independent focused QA rechecked results. |
| 2026-09-10 | Observe: clean retrieval baseline exceeded its frozen deadline; AC4 and matching task are intentionally deferred, with zero paired results. Full focused re-Prepare restored current authority without widening production scope. | reprepare_scope_review; typed readiness approvals in events.jsonl. |
| 2026-09-10 | Verification: change-local syntax, counts, hashes, negative controls and full docs validation pass. Formal delivery lanes/council and the final review task remain pending; no closure or commit performed. | benchmark-results.json; docs-lint clean with no long-line scanner skip. |
| 2026-09-10 | Readback: operator accepts 300–500 ms graph work and prioritizes shared transactions. Continue with a fresh 500 ms p95 graph screen, broader-query samples and source/lifecycle integration; preserve previous results and AC4's independent deferral. | Continued evaluation section; AC2/3/6 and their tasks reopened for the additional evidence. |
| 2026-09-10 | Thought: re-Prepare the revised protocol, investigate producer/state boundaries, then extend isolated query/lifecycle harnesses, serialize fresh paired measurements and revise the ADR. | No new source/harness edit until current readiness authority is restored. |
| 2026-09-10 | Observe: fresh isolated council and five readiness lanes passed; implementation reopened. Actual broad risk/report producers compare A with shared cached H and per-request materialized M; initial responses match exactly, complete reports expose costs absent from algorithm-only probes. | Round-2 samples are separate from the original receipt; warm percentile qualification and actual source lifecycle remain in progress. |
| 2026-09-09 | Planned and admitted at operator request; no evaluation benchmarks executed. | Wave 1xny3; source inspection and primary documentation. |
| 2026-09-10 | Observe: fresh three-run query pairs, six source rebuilds and twenty source deltas recorded; scoped parity and shared producer recovery pass, with query/update/disk tradeoffs and a retained maintenance failure. | continuation_round2 in benchmark-results.json; source and query cohorts explicitly separate. |
| 2026-09-10 | Reflect: favor shared persistence as the next design direction, while preserving the current serving path until complete production epoch/cache and incremental-write qualification. | Revised ADR; no production conversion or ranking change. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-09 | Select staged native-table then shared-store evaluation, with independent retrieval experiment. | Attributes gains/regressions to each change and preserves a viable baseline. | Immediate full consolidation confounds storage/concurrency/ranking; extension-first adoption adds dependency questions before proving query value; retaining today's design without measurement leaves possible memory/consistency savings unexplored. |
| 2026-09-09 | Evaluation only; production implementation is separately gated. | User requested an evaluation wave and feasibility remains unproven. | Direct conversion would prejudge the outcome. |

## Readiness Refinements

Before benchmark execution, the plan stress-test replaced unspecified budgets with the fixed protocol. Council review then added the independent structural oracle and clarified resource-stop qualification. Full rebuild sampling changed from ten observations/p95 to three paired observations/median because repeated whole-store rebuilds can exhaust the 30-minute configuration cap; this was decided before results existed, and all durations/maxima remain visible. Startup/update samples pool across runs rather than multiplying their count accidentally.

The ADR must weigh retaining compact persistence with an addressable representation and bounded hot-neighbor cache as the strongest narrower alternative. This is a decision comparison, not an automatic additional prototype; execute it only if measured bottlenecks justify the already allowed bounded hybrid variant.

## Risks

| Risk | Mitigation |
| --- | --- |
| SQL loses semantics or trails warm in-memory traversal. | Differential probes on full evidence; baseline may win. |
| Shared storage increases contention/failure scope. | Prepared updates, interruption/concurrency probes and lock-duration measurements. |
| Synthetic topology/cache effects overstate gains. | Real graph, representative fixtures, repetitions and explicit cache labels. |
| Global algorithms still require whole-graph RAM. | Count total process usage including materialized graph/cache representations. |
| Roadmaps/binaries are mistaken for supported execution. | Pin versions; separate announced capability, wheel inventory and native execution. |

## Research References

- [SQLite recursive CTEs](https://www.sqlite.org/lang_with.html)
- [Cypher graph patterns](https://www.neo4j.com/docs/cypher-manual/5/patterns/)
- [GraphQLite](https://github.com/colliery-io/graphqlite)
- [agentflare sqlite-graph](https://github.com/agentflare-ai/sqlite-graph)

Recheck versions/licenses/roadmaps during execution; links are research inputs, not benchmark evidence.

## Session Handoff

Evaluation implementing. Production conversion remains separately gated. Benchmark data and experiment state will be recorded below.

## Cypher assessment — 2026-09-10

Defer a Cypher dependency. The current typed API already covers neighbors, reverse impact and confidence-weighted paths. Cypher makes repeated compound patterns easier to express, such as methods that call one helper and write one table, but it does not supply missing extraction facts. A plain shortest-path clause does not reproduce confidence costs, external-endpoint rules, evidence ordering or public limits.

| Option | Shipped capability and qualification | Decision |
| --- | --- | --- |
| Native SQLite | Recursive CTEs and indexed joins use our existing runtime. A depth column means UNION deduplicates whole `(id, depth)` rows, not visited nodes; explicit cancellation and bounds remain necessary. | Continue native-table measurement. |
| GraphQLite 0.8.0, released 2026-09-07 | MIT; package labels Beta. Cypher, PageRank, Louvain, Dijkstra, BFS/DFS; optional Leiden uses graspologic. Four wheels: macOS ARM64, Linux x86_64/ARM64 and Windows x64, plus source archive. APSW transaction integration and sqlite-vec coexistence are untested. | Defer; no demonstrated benefit justifies another native dependency yet. |
| agentflare sqlite-graph 0.1.0-alpha.0 | MIT; explicitly not recommended for production. Its published roadmap still marks weighted-path correctness and write isolation incomplete. Past roadmap target quarters do not establish delivery. | Exclude from a production conversion. |

GraphQLite 0.8.0 adds anchored variable-path CTEs, property indexing and bounded statement caching. Its SQL row interface still materializes native results; true streaming is a stated follow-up, not a promised release. These improvements are worth watching, but vendor performance claims are not measurements of our graph. No extension was installed or executed. Exact query comparisons, platform artifacts and dated sources will accompany the benchmark receipt.

Sources: [SQLite recursive CTEs](https://www.sqlite.org/lang_with.html), [GraphQLite 0.8.0 package](https://pypi.org/project/graphqlite/0.8.0/), [GraphQLite release](https://github.com/colliery-io/graphqlite/releases/tag/v0.8.0), [GraphQLite changelog](https://github.com/colliery-io/graphqlite/blob/main/CHANGELOG.md), [agentflare project](https://github.com/agentflare-ai/sqlite-graph), [agentflare roadmap](https://github.com/agentflare-ai/sqlite-graph/blob/main/ROADMAP.md).

## Baseline inventory and capability matrix

The following inventory describes the initial prototype; the continued evaluation below extends its lifecycle participants. The frozen served graph has 41,490 nodes and 119,543 edges at complete build epoch 1176, source revision `884f46bbeb496851288020a993f57c6fa5f08530`. Its relationships include definitions, calls, imports, configuration/data reads, document links and memory targets. Hand-derived fixtures supply cycles, diamonds, inheritance, parallel evidence, disconnected nodes and external bridges that this particular corpus does not cover uniformly.

| Concern | Deployed A | Native-table B / shared C experiment |
| --- | --- | --- |
| Extraction state | `graph/project-graph-state.sqlite`: per-file compressed records and a merged-state cache | Retained in this prototype; removing it needs an incremental extraction/resolution design. |
| Published graph | `graph/project-graph.json`: compressed, atomically replaced JSON | Complete node/edge payloads in addressable rows with ordinal ordering and integer endpoint keys. |
| Query cache | GraphQueryIndex materializes all nodes, edges and incoming/outgoing adjacency | Lazy SQL hydration; H adds two bounded LRU adjacency caches. |
| Communities | `graph/project-graph-clusters.json`, igraph/Leiden when available, label-propagation fallback | Retained. CTEs do not replace community computation or eliminate its global materialization. |
| Query semantics | Visited-node BFS; public edge-triple deduplication; revisit-based has_cycles; confidence-weighted paths; external endpoints cannot bridge unrelated symbols | Existing algorithms run over lazy collections. CTE reachability is a separately bounded experiment, not an automatic API replacement. |
| Graph tools | Definition/reference/dependency, call hierarchy/path, impact/risk, reports and community queries | Adapter probes cover storage fidelity and selected public producers; untouched LSP/file paths are not claimed as measured. |
| Retrieval | Dense + lexical candidates, initial rerank, graph rescue/citation merge that can trigger another rerank | Independent experiment counts both rerank stages and preserves the initial pool. |
| Publication | Per-file extraction/global resolution plus assembled artifacts, held together by current build-epoch fences | Shared transaction probes retain fences. A filename alone does not make extraction caches or whole tool calls atomic. |
| Maintenance | Integrity/FTS checks, passive checkpoint, incremental reclamation and planner optimize; known old graph files may need a one-time auto-vacuum format migration | Same deployed settings are the control. No routine full VACUUM or larger cache is presumed beneficial. |

Source anchors: `graph_indexer.GraphStateStore`, `_encode_state_record`, `_write_json`, `read_graph_payload`; `graph_query.GraphQueryIndex`, `traverse`, `one_hop_neighbors`, `shortest_path`, `graph_impact`, `risk_score`, `report`; `graph_cluster._run_clustering` / `_build_leiden_clusters`; `server_impl.search_combined`; and `index_state_store.py` maintenance around lines 5223–5302. The graph schema allows external keys without requiring an owned-node record. Edge ordinals preserve independent evidence even when the public traversal projects one source/target/relation triple.

No additional package is needed for B/C/H: APSW and sqlite-vec are already deployed. Added dependency storage is **0 MiB**; this does not mean the existing dependencies or global algorithms use zero memory. The SQL prototype retains JSON metadata for fidelity rather than claiming a final minimal schema.

## Initial shared-publication result

C passed on an online backup of the actual schema-7 semantic store with prototype graph tables added. Assertions compare changed text, vector bytes, node payload, edge payload and publication revision exactly. FTS triggers expose the committed token and exclude the rolled-back token. A reader spanning the writer commit keeps the complete old view; a new read sees the complete new view. An owned child exits during a transaction and the reopened database retains the last committed state with quick_check and FTS integrity passing. A graph-only publication changes graph rows while preserving semantic text and vectors.

The lazy adapter also passed a writer commit injected between adjacency reads, and H passed a commit injected between cache validation and subsequent SQL reads. A read transaction is explicitly established before cache validation. Cache entries invalidate after later commits. These are algorithm-boundary tests: a production MCP response containing several graph operations still needs one documented epoch policy.

Twenty source-location overlap joins demonstrate that graph symbols can locate canonical code chunks. A separate zero/one/many overlap oracle illustrates the mapping contract; neither constitutes a full-corpus identity/multiplicity census. Extraction state, global relationship invalidation and community artifacts remain outside C in this prototype. **Atomic row publication is demonstrated; removal of the complete cross-store lifecycle boundary is not qualified.**

## Retrieval-order screening result

Retain current ordering. The clean baseline exceeded the frozen five-second per-query deadline during its first warm-up, after successfully reranking 119 initial passages (2.102 seconds) and three graph-rescue passages (0.063 seconds). No timed paired observations completed; neither pre-rerank variant ran. There is no measured quality improvement, regression, precision/recall score or reranking-share-of-completed-response claim.

The 30 source-grounded queries and independent QA are retained. Their expected anchors and required pairs are a useful minimum oracle, not exhaustive relevance judgments. Actual query embedding and reranking used CPU after CoreML's safety child exited -11. The paired-provider requirement and original deadline were preserved. The clean configuration used a peak 1,464.30 MiB aggregate monitored RSS and 2,981.50 MiB scratch, within the resource caps.

Four earlier attempts are excluded from the current result. They include model initialization failures and trials where isolated model caches polluted the repository walk; those caches were moved to `.wavefoundry/index/` and the final preflight confirmed that none appeared among 2,262 eligible paths. Six contaminated samples survive only in the receipt's excluded history. No shared model cache, live index or unrelated process was modified.

## Initial measured storage and query results

The initial real-corpus runs contain three interleaved runs per A/B/C/H variant, ten warm-ups and 100 timed observations per query family per run (300 observations per family). Each process used the same frozen graph and relation-specific hot/medium/cold seeds; weighted timing pairs have known one-hop endpoints; longer competing routes are covered by independent correctness fixtures, not a qualified long-path latency distribution. The public-producer tests exercise the actual call-hierarchy and graph-path response functions plus JSON encoding through an asserted frozen backend accessor. All 600 response hashes per variant match A exactly. MCP transport and the model pipeline are outside those graph-tool measurements.

| Metric | A: current | B: SQL | C: shared SQL | H: SQL + cache |
| --- | ---: | ---: | ---: | ---: |
| Max steady graph-worker RSS, MiB | 276.2 | 81.8 | 84.2 | 105.7 |
| Peak public-producer worker RSS, MiB | 381.0 | 156.3 | 156.1 | 154.2 |
| Incoming calls, 3-hop p95, ms | 3.100 | 21.419 | 22.627 | 3.397 |
| Outgoing calls, 3-hop p95, ms | 0.318 | 1.722 | 1.752 | 0.344 |
| Document links, 3-hop p95, ms | 1.074 | 40.945 | 53.675 | 1.057 |
| Filtered imports, 3-hop p95, ms | 0.103 | 1.507 | 1.563 | 0.125 |
| Bounded neighbors p95, ms | 0.037 | 0.980 | 0.628 | 0.833 |
| Known reachable weighted path p95, ms | 0.087 | 0.274 | 0.266 | 0.120 |
| Public call-hierarchy producer p95, ms | 768.792 | 769.978 | 772.411 | 775.454 |
| Public graph-path producer p95, ms | 0.145 | 0.325 | 0.533 | 0.231 |
| Inclusive semantic + graph persistence, MiB | 225.96 | 293.57 | 270.19 | 293.57 |
| Additional dependency installation, MiB | 0 | 0 | 0 | 0 |

The graph worker is an isolated process, **not total MCP RSS**. H lowers that serving footprint by about 62%, with bounded traversal near A and public-producer regressions inside the frozen relative allowance. Its two 8 MiB cache budgets count serialized edge payloads; actual resident memory is measured separately. B/C save more serving RAM but hydrate rows repeatedly. SQL is larger on disk: the graph table/index file is 69.50 MiB, whereas A's complete compressed graph/state/community footprint is about 13.15 MiB. The inclusive totals retain extraction/community state and include observed sidecars; C reuses free pages in the semantic backup, so its net growth differs from a separate B file. This is not a text-deduplication saving.

Ten process-start observations per A/B/C give graph-construction p95 of 194.6/45.5/45.2 ms, excluding interpreter/import startup. H has only its three worker-start observations and no separately qualified startup tail. The OS file cache was uncontrolled; a new process is not a physical cold-disk test. Raw p50/p95/p99, first-query values, CPU times and sample/resource counts are retained in `benchmark-results.json`.

The original CTE plan became roughly 334 ms p95 after planner maintenance. Covering `(source, relation, target)` and reverse indexes plus explicit join order brought the final CTE p95 to about 0.6 ms; the paired before/after-optimize probe measured 0.576/0.598 ms. This is a query/index correction, not a relaxed budget. The deployed 2 MiB suggested page cache and 256 MiB mmap limit were retained; no evidence justified raising every connection to 128 MiB.

Broad consumers remain a conversion risk. Exploratory identical-result probes measured scoped risk at 31.6 ms in A versus 314.5/318.1 ms in B/H, and report sections at 26.5 ms versus 457.4/563.8 ms. These single observations are not p95 qualification. Lazy collections still make global algorithms scan and hydrate large portions of the graph; the hot-neighbor cache does not solve that. Community materialization and complete source-rebuild memory remain unqualified.

Earlier prepared-publication probes measured one-node SQL transaction locks below a millisecond, and much less republishing work than rewriting/reloading A's assembled artifact. Three paired *prepared graph persistence* observations favored A (median 367 ms) over B (1,207 ms). These are not full source rebuilds or file-change-to-queryable timings: they omit extraction, cross-file resolution and embeddings, and predate the final relation indexes. No complete lifecycle/rebuild gate is claimed from them.

Exploratory topology replicas reached 207,450 nodes/597,715 edges (5x) and 414,900/1,195,430 (10x). Fixed-degree outgoing queries remained small, while a 10,000-callee fixture returned the same capped 30 results in both backends. Replicas do not increase local fan-out; A/B share the scale process and only one sample series ran. They establish neither a capacity crossover nor per-backend scaled RSS. The observed local limits are hydration/global scans and full integration gaps, not a demonstrated graph-size ceiling.

## Continued evaluation results — 2026-09-10

The fresh query comparison uses three interleaved A/J runs, 10 warm-ups and 100 timed observations per family per run. J bulk-decodes native SQL node/edge rows and constructs the existing GraphQueryIndex inside each timed request; it is the optimized materialization alternative, not a persistent query cache. Every one of the 900 paired ordered response hashes matches A. H was tested against the actual shared file for one complete 100-observation run per family; its roughly 3.3-second full-report p95 made it a diagnostic stop. M and K probes remain diagnostic, with no three-run tail qualification. There were no query errors or degraded-response substitutions in the qualified runs.

| Fresh paired metric | A: current | Shared SQLite prototype |
| --- | ---: | ---: |
| Scoped risk, pooled p95, ms | 35.0 | 353.2 (J) |
| Complete report, pooled p95, ms | 560.6 | 887.3 (J) |
| Filtered complete report, pooled p95, ms | 570.4 | 894.5 (J) |
| Graph-only source rebuild median, s | 141.69 | 142.14 (C) |
| Source edit-to-publication median, s | 7.26 | 10.33 (C) |
| Inclusive authoritative persistence, MiB | 223.1 | 266.8 (C) |

J passes the new 500 ms graph screen for scoped risk. Complete reports exceed the retained allowance for already-slower baseline tools: J adds 326.7 ms for the default report and 324.2 ms for the filtered report. These are full producer plus serialization timings, excluding MCP transport and models. The old bounded-worker H memory result does not generalize: fresh broad-worker peak maxima are A 313.5 MiB and J 376.8 MiB. End-of-worker residency, CPU, per-run values and p50/p95/p99 remain in the receipt; none is total MCP RSS.

Three actual graph-only source rebuild pairs pass exact A/C graph, community and preserved-semantic digests; C's median is 0.32% higher. All ten paired changed-file observations also match, including rename/removal/reversal with unchanged caller hash and mtime after initial creation, and the final incremental graph agrees with a fresh source rebuild. Delta medians increase 42.4%; C deliberately reconstructs disposable state from SQLite every edit while A retains its native state. C's median costs include 759 ms restoration, 1380 ms SQL preparation and 919 ms writer hold. This conservative prototype rewrites every graph row and is not optimized incremental publication. Three rebuilds support median/max only; the nearest-rank p95 of ten deltas is the maximum, a coarse descriptive value (12.29/10.74 s), not a reliable population tail or evidence that the higher median is harmless.

The actual producer prototype stores extraction files/compressed records/merge state, resolved graph and community artifact in the shared database. Expensive work occurs outside `BEGIN IMMEDIATE`. Real chunking and offline CPU FP32 embeddings replace two code chunks in the same transaction as graph state. Both tiny and full-corpus recovery probes verify rollback, an owned crash with exit 77, old readers before/after COMMIT, fresh-reader state, FTS MATCH, native vector self-retrieval and reconstruction after disposable graph artifacts are removed. The full-corpus replacement writer held about 889 ms. Production build_state epochs, build-layer bookkeeping, whole-response cache/community integration and a complete semantic-plus-graph source rebuild remain unimplemented; the prototype does not authorize removing their fences.

A first full-corpus combined free-page reuse/no-growth assertion failed. Its original counts were not persisted, so the particular failed predicate is unknown. One bounded repeat records 68,404 pages unchanged and free pages 101 → 11,561 → 101; that is observation-only and does not erase the original failure or qualify long-running maintenance. Integrity and FTS checks passed, and passive checkpoint reported all 19,884 WAL frames checkpointed. No routine full VACUUM was introduced.

Source provenance is explicit: the 2,114-path producer census uses frozen copied bytes; all 810 persisted extraction-source hashes match. One changed wave document differs from semantic metadata and was not an extraction-store member, so complete semantic freshness is not claimed. Fresh source graphs have 41,490 nodes/119,668 edges, versus the original served query graph's 119,543 edges. The difference is 130 added/five removed doc_references_code edges; all nodes and other relations match. This historical drift is retained without a causal storage-regression claim. Query and source-rebuild cohorts are not interchangeable.

The real declaration-start overlap census retains all 27,008 matching-source-hash pairs: 21,609 mapped symbols, 18,545 unmapped symbols, 5,034 symbols mapping to multiple chunks and 694 chunks containing multiple symbols. Unmapped reasons were not individually audited; this is not whole-symbol semantic coverage. Graph and chunk identities must remain distinct.

An initial delta attempt stopped when the owned-child RSS monitor raced with another thread reaping a child. Four partial observations are excluded. Bounded retry and fail-closed controls (including actual removed-retry/fail-open mutations and 100 rapid owned children) passed; both stages were restored to the verified common baseline before all twenty qualified observations were rerun. Each receipt retains its executed harness hash. Shared monitoring now tolerates vanished disposable files, while unexpected stat failures propagate. Source and query measurements before the monitoring repair are not relabelled. Qualified lifecycle peak measured RSS was 1821.4 MiB and scratch 3630.0 MiB, within the unchanged envelope.

## Decision and remaining gates

Shared SQLite persistence remains the preferred direction for a subsequent conversion design; retain deployed A until that conversion is qualified. Choose persistence representation separately from the serving cache, and compare keeping the current fast GraphQueryIndex with a compact SQLite snapshot as well as normalized tables. The compact-snapshot alternative has not been measured here. Retain current ranking order and defer Cypher. The [ADR](../../architecture/decisions/1xny4-adr%20sqlite-graph-evaluation.md) records the separate decisions and safe upgrade/verification/cleanup gates.

Representation and source-mutation parity pass. Scoped J risk queries pass the revised graph screen; complete reports exceed their retained allowance. Actual graph-only source rebuild median passes the 10% screen; median deltas and disk increase materially. Shared producer transaction/recovery is demonstrated within the stated participants, while full production epoch/cache/semantic integration remains unqualified. The original material-benefit/adoption gate is not established; this evaluation recommends a design direction, not production adoption. The independent paired ranking experiment remains deferred at its original baseline stop.

## Reproduction and evidence boundaries

Use the existing tool interpreter with `-B`; do not install shared dependencies. `graph_eval.py snapshot` creates an owned scratch root using SQLite online backups and completed-epoch/artifact checks. Subsequent commands accept only that scratch root. Run `oracles`, `compare`, `shared`, `extended`, `safety`, then `prepare` to reset mutated probe databases. Run `planner`, then three interleaved `worker` and `public` commands for variants A/B/C/H (`--run 0`, `1`, `2`); run `startup` separately. `publication`, `maintenance`, `scale --factor 5/10` and `fanout` are explicitly scoped exploratory commands. Hold the common OS flock; do not run graph and retrieval workers concurrently. Both harnesses print their CLI via `--help`.

`retrieval_eval.py` uses the same snapshot, `retrieval_queries.json` and independent QA receipt. Its final clean attempt is retained without the contaminated source/citation payloads from discarded runs; the full local receipt is content-hashed. Committed evidence contains raw timing observations, seed identifiers, versions/PRAGMAs, schema, query/harness hashes, bounded stop reasons and comparison counts. Large copied databases and model caches remain outside version control. Native execution is macOS ARM64 only.

For the continuation, run `graph_eval.py candidates`, diagnostic `broad` A/H/M (`--run -1`) and J/K (`--run -2`), then three interleaved `broad --variant A/J --run 0/1/2` workers. J records `manifest_variant=M` plus its explicit bulk-decode strategy; K similarly refines H. The lifecycle harness commands are `fixture`, three interleaved `rebuild --variant A/C --run 0/1/2`, `deltas`, and `recovery`. `reset-deltas` is used only to restore a verified common baseline after an interrupted trial; archive partial observations first. It is not part of qualified delta timing. Commands share the original owned scratch/OS flock. Graph query percentiles retain the harness's floor-order statistic; lifecycle ten-sample p95 is explicitly labelled nearest-rank. Runtime source hashes, copied-source census, exact normalized wrapper fields, interrupted observations and maintenance limitations are recorded under `continuation_round2` in the single receipt.
