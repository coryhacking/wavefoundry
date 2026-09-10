# Evaluate SQLite graph consolidation

Change ID: `1xny2-task evaluate-sqlite-graph-consolidation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-09
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
- **Performance screening:** at the real local corpus, warm p95 for bounded 1–3-hop graph expansion must be below 100 ms; whole-tool warm p95 and incremental file-change-to-queryable p95 may increase by at most the larger of 10% or 10 ms versus A. Report every query family separately. Full rebuild/startup p95 may increase by at most 10%; cold first-query latency remains separately visible. If A itself exceeds a screen, record a baseline failure and require improvement or defer qualification, rather than rewriting the threshold. Scaled/adversarial graphs identify limits, not mandatory production capacity.
- **Material benefit:** recommend storage adoption only with correctness and latency gates met plus at least 20% improvement in total steady RSS, peak RSS, persistent footprint, startup or update latency; alternatively, demonstrated removal of the cross-store publication/reconciliation boundary with no more than 10% regression in any measured resource category. Report which criterion won and all tradeoffs. A decision to retain A is successful evaluation work.
- **Retrieval corpus:** freeze at least 30 questions before variants run: 15 multi-file mechanisms, 5 exact-owner lookups, 5 negative/irrelevant-expansion controls and 5 inheritance/doc-link/impact questions. Map expected relevant files/symbols and required chain links from source; QA checks judgments independently before comparing variant outputs. Use candidate Recall@K at the actual candidate pool, final citation precision/recall and required-chain coverage; report per-question losses, not only averages. Acceptance requires no lost required chain or exact-owner result, no decrease in macro final precision/recall, and an improvement on at least two mechanism questions; otherwise retain current ordering. Report inconclusive outcomes rather than claiming statistical generalization from 30 questions.
- **Candidate cost:** run an equal-total-candidate-budget arm first; a separate expanded-budget arm may add at most 30 graph candidates and 25% of the baseline reranker candidate count (whichever is smaller). Keep original retrieval inputs fixed, show deduplication/admission rules, and satisfy the whole-tool latency gate. An unavailable reranker or changed hardware provider makes that paired run unqualified; do not substitute lexical fallback as equivalent evidence.
- **Repetitions:** three interleaved A/B (and eligible C) runs, each with 10 warm-up queries and at least 100 timed observations per graph-query family. Use at least 10 startup/update/rebuild observations for p95; mark p99 from small samples descriptive only. Stop early on a correctness failure or resource limit and preserve the failure evidence. Do not repeatedly run expensive full rebuilds once a failure has decided the gate.
- **Resource envelope:** one benchmark worker/configuration at a time, up to 30 minutes per configuration and 4 hours total before a recorded bounded stop; aggregate benchmark-process RSS at most the smaller of 4 GiB or 25% physical RAM; scratch allocation at most the smaller of 8 GiB or 25% initially free disk. Sample RSS/disk while running, enforce per-query 5-second cancellation and an owned-worker watchdog, and terminate only processes created by the harness. Never drop the host OS cache or stop another repository's processes. Cold runs are labelled process-cold unless OS-cache state is independently controlled without host-wide mutation.
- **Isolation:** use SQLite online backup or an equivalent consistent snapshot, not a bare copy of a live WAL database. Bind graph and semantic snapshots to a stable completed epoch; retry acquisition if the epoch changes, and record artifact hashes. Do not hold a live transaction while benchmarking. All writes, crash injection, branch churn and cleanup operate under a freshly created dedicated scratch root with resolved-path ownership checks; branch churn uses fixture changes, never checkout in the working repository. Reject live-index paths and symlink escapes before mutations. An isolated harness subprocess is the only crash target. Committed evidence contains identifiers/metrics and hashes; avoid duplicating repository text, credentials or full database contents.

## Plan Review Questions

- **Must Cypher or shared storage win?** No; independent retain/adopt/defer decisions satisfy the brief. Baseline and native SQL are mandatory; extension execution is optional after license/compatibility review.
- **Does a shared filename prove atomicity?** No; use prepared publication and cross-file invalidation probes, keeping existing epoch fences until proven unnecessary (`docs/architecture/graph-index-system.md`, shared build-epoch contract).
- **Are graph nodes interchangeable with chunk IDs?** No; retain separate identities and measure the mapping (`GraphQueryIndex` versus canonical semantic chunk tables).
- **Does this authorize production conversion or a new SLA?** No; the fixed budgets screen an isolated evaluation and any implementation requires a new readiness gate.
- **Stop condition:** the scope and experimental protocol are fixed; empirical winners remain the evaluation's output. No operator-only decision is currently needed to prepare this evaluation.

## Acceptance Criteria

- [ ] AC-1: The inventory and capability matrix cover current storage, public graph behavior, algorithms, retrieval ordering and lifecycle maintenance, with source references and the evaluation budgets fixed below.
- [ ] AC-2: A reproducible A/B comparison reports correctness, bounded traversal, scale, latency, memory, disk and updates with runtime/configuration provenance and honest cache limitations.
- [ ] AC-3: The C evaluation records shared-publication/recovery/concurrency evidence, or an explicit Gate 2 stop without a consolidation qualification claim.
- [ ] AC-4: The independent retrieval experiment reports judged candidate/final-result quality and full latency/cost under fixed inputs and explicit expansion budgets.
- [ ] AC-5: The Cypher/extension assessment compares concrete queries, shipped capabilities, licenses, compatibility and dated roadmap evidence without assuming adoption.
- [ ] AC-6: One ADR records separate decisions, tradeoffs, proposed safe upgrade/cleanup for any recommended conversion, and remaining implementation/platform gates.

## Tasks

- [ ] Inventory the baseline and instantiate the fixed workload, resource limits and decision budgets without changing thresholds after seeing results.
- [ ] Build and verify isolated A/B harnesses; capture current and scaled graph results.
- [ ] Evaluate shared storage and publication safety if native parity passes; otherwise record the gated stop.
- [ ] Run the independent graph-expansion/reranking comparison on judged queries.
- [ ] Assess Cypher implementations, licenses, compatibility and roadmaps.
- [ ] Consolidate results and benchmark receipt; author the ADR and proposed migration/cleanup gates.
- [ ] Run change-local checks and required review lanes; resolve findings and validate authored documents.

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
| 2026-09-09 | Planned and admitted at operator request; no evaluation benchmarks executed. | Wave 1xny3; source inspection and primary documentation. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-09 | Select staged native-table then shared-store evaluation, with independent retrieval experiment. | Attributes gains/regressions to each change and preserves a viable baseline. | Immediate full consolidation confounds storage/concurrency/ranking; extension-first adoption adds dependency questions before proving query value; retaining today's design without measurement leaves possible memory/consistency savings unexplored. |
| 2026-09-09 | Evaluation only; production implementation is separately gated. | User requested an evaluation wave and feasibility remains unproven. | Direct conversion would prejudge the outcome. |

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

Planned only. Next is Prepare wave and readiness review; do not open or implement implicitly.
