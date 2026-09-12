# 1xny4-adr — Separate graph storage consolidation from query-cache replacement

Owner: Engineering
Status: accepted
Last verified: 2026-09-11

## Context

Wavefoundry already stores semantic chunks, vectors, FTS and index state in SQLite. The structural graph still has a separate SQLite extraction cache, compressed assembled graph/community artifacts and a full in-memory adjacency index. Wave 1xny3 evaluates whether native graph tables can lower serving memory and simplify publication without losing behavior.

The experiment uses a stable completed epoch with 41,490 nodes and 119,543 edges. It compares the current graph (A), lazy native tables (B), the same tables in a copy of the semantic database (C), and bounded adjacency caching over native tables (H). Retrieval ordering and Cypher are independent decisions. All databases and injected failures are isolated; no production store or shipped source changed.

## Decision

**Continue toward shared SQLite persistence, while retaining the deployed graph until a separate conversion wave qualifies the complete lifecycle.** Evaluate the serving cache separately. The single-transaction benefit is real in the isolated producer prototype; it does not require replacing the existing fast in-memory graph algorithms with per-request SQL hydration.

| Question | Recommendation | Basis |
| --- | --- | --- |
| Shared semantic/graph database | Preferred direction for a subsequent conversion | Actual graph extraction state, resolved graph, communities and a small real semantic delta can publish together and recover from SQLite authority. Complete production epoch and reader integration remains unimplemented. |
| Native tables and query cache | Keep current serving behavior as the baseline; do not adopt the lazy adapter wholesale | Bounded traversal performs well, but complete reports expose hydration costs. The broader workload does not reproduce the earlier graph-worker memory saving. |
| Graph expansion before reranking | Retain current ordering | The clean baseline exceeded the fixed five-second deadline before paired observations; no quality improvement was measured. |
| Cypher / graph extension | Defer | Current typed graph tools cover existing use. No measured benefit justifies another dependency. |

At the time this ADR was written, the above was a proposed design direction, not an approved production cutover. It has since been implemented and this ADR is **accepted**; see *Decisions as delivered* below. A compact graph snapshot stored inside SQLite and loaded into the existing cache was the other plausible design; it was not selected, because stable per-row identities are what make change-sized incremental writes possible and a whole-graph snapshot rewrite would have kept the prototype's full-rewrite cost.

## Decisions as delivered (wave `1xny6`, change `1xny5-ref`)

Implemented in [One SQLite database for semantic and graph indexing](../../waves/1xny6%20unified-index-database/1xny5-ref%20unify-graph-index-storage.md). The evidence in this ADR is the wave-`1xny3` evaluation and is preserved unedited; the decisions below are what actually shipped.

| Question | Decision as delivered |
| --- | --- |
| **Production representation** | Native, stably identified graph tables in the shared database, NOT the prototype's replace-everything layout and not a compact snapshot blob. `graph_nodes` is keyed by the existing public symbol id; `graph_edges` is keyed by source ownership plus the full evidence identity plus an occurrence discriminator, so repeated evidence survives and an edge triple alone is deliberately not a storage identity. `graph_file_state` and `graph_merge_state` are keyed PER FILE rather than as one corpus blob, which is what makes a small edit write a small number of rows. External endpoints need no declaration row, and symbol-to-chunk links allow zero, one and many. |
| **Filename** | `.wavefoundry/index/index.sqlite`. This **supersedes** gate 3's proposed destination of `index-state.sqlite`: the file already held indexed content rather than bookkeeping alone, and renaming during the same controlled conversion avoided a second migration later. `index_paths` is the single definition of the current and legacy names and deliberately refuses to decide authority when both exist. |
| **Schema version** | An explicit new resident schema `8`, as gate 3 required. The 7-to-8 arm is additive and preserves FTS tables, digests and lexical statistics; the historical 4/5/6 reset is retained verbatim; a migratable version belonging to neither set refuses rather than falling into the destructive path. |
| **Serving cache** | Kept, as this ADR recommended. The resident `GraphQueryIndex` and the igraph/Leiden algorithms are unchanged; per-request SQL hydration was not adopted. |
| **Generation and reads** | A reader takes a generation-bound SNAPSHOT: open read-only, read build state, graph meta, graph rows and community rows from one SQLite snapshot, roll back and close, returning immutable content rather than a handle. A context-bound pin gives one generation per whole response, satisfying this ADR's whole-response-snapshot requirement — including communities — which per-operation transactions alone could not guarantee. Per-layer publication state is recorded, with the scalar generation left as the reader token. |
| **Publication** | One `BEGIN IMMEDIATE` carries semantic rows and the graph, extraction, community, merge and per-layer bookkeeping rows. The named control transactions that remain outside it are the durable build-start fence, the secret-scan cache write, the post-commit derived-FTS verify and repair, the freshness/drift/reap residents, and the completion compare-and-set that solely advances the generation. The version-mismatch graph reset became scoped deletes INSIDE that transaction, and the delete-on-error reset was removed. |
| **Migration** | A versioned kind carrying a **version-2 receipt in the same `sqlite-migration.json` file**. Version-1 code rejects an unknown receipt version outright, and that rejection IS the old-code fence: once a v2 record exists an old runner refuses before it can open or create any database. The kind requires `storage_migration_protocol >= 2`; a coordinator declaring less receives the ordinary restart handoff. **No bridge release.** The graph is rebuilt from current sources into the staged database rather than converted, so a missing, stale or corrupt old graph does not block the upgrade; compatible vectors, canonical chunks and FTS transfer without re-embedding. |
| **Recovery** | **Forward-only.** A failed or refused cutover is recovered by re-running the standard upgrade from the retained source and the recorded rollback identities. There is no backward rollback to the old runner, and the rollback copy is never read back into service by product code. |
| **Cleanup** | Gate 6 is satisfied and tightened: the whole `graph/` directory IS removed, but only after a pre-deletion inventory lstats every entry without following links and classifies it against an owned-name allowlist composed from producer constants. Any unknown name, nested directory or symlink at any depth preserves the whole folder and records `retained_unowned_contents`. Cleanup is plan-then-apply, so every refusal is reached while the source is still intact. |
| **Maintenance** | One physical database receives exactly one maintenance pass and one storage/reclamation entry; the graph-only auto-vacuum arm is retired with its parameter, stage and result key. Routine passes remain opt-out of full `VACUUM`, as gate 7 required. Bounded incremental reclamation converges at exactly its configured per-pass bound. |
| **Preparation memory** | Ordinary updates retain operations in memory under a 64 MiB accounting limit, spilling lazily to an owned index-directory spool. Per-add rollback and caller-owned publication remain intact. This reduces temporary writes for small updates; large replay RSS and spill WAL peaks can increase, so it is not a general memory-saving claim. |
| **Cypher / graph extension** | Still deferred. Unchanged by this wave. |
| **Retrieval ordering** | Unchanged, as this ADR decided. |

**Measured consequences, restated against the delivered build.** This ADR's evaluation table remains the wave-`1xny3` prototype record. The conversion wave's retained graph-only baseline (169.9 s rebuild, 160.3 s builder-bump rebuild, 8.18 s incremental median) measures a different path from the final complete semantic-plus-graph coordinator. On the latter, ten real-model rename/remove/restore deltas measured a 12.02 s median against 12.05 s before the change. The acquired writer interval was p50 1,161.98 ms and p95/max 1,188.46 ms, against baseline p50 1,159.70 ms and max 1,183.79 ms; ordinary same-file edits were about 30 ms. These intervals start after `BEGIN IMMEDIATE` returns and end after `COMMIT` returns. Earlier pre-execution timing claims are superseded. A representative actual-model full rebuild covered 423 chunks in 18.45 s with a 44.72 ms acquired writer interval and no preparation files; it is not a paired full-corpus rebuild benchmark. The operator's protected metric remains incremental latency, and these paired deltas show no material regression. The evaluation's unexplained maintenance assertion used an over-strong page-count-must-not-grow predicate for a delete-then-repopulate cycle; corrected reuse and bounded reclamation checks qualify the delivered maintenance path. See the conversion wave's runtime qualification for raw records and measurement limits.

**Known limitation carried forward.** `graph_symbol_chunks` ships with its storage contract tested but no production producer. This is not a regression: the pre-wave graph carried no symbol-to-chunk mapping either.

## Evidence and consequences

| Fresh paired metric | A: current | Shared SQLite prototype |
| --- | ---: | ---: |
| Scoped risk, pooled p95, ms | 35.0 | 353.2 (J) |
| Complete report, pooled p95, ms | 560.6 | 887.3 (J) |
| Filtered complete report, pooled p95, ms | 570.4 | 894.5 (J) |
| Graph-only source rebuild median, s | 141.69 | 142.14 (C) |
| Source edit-to-publication median, s | 7.26 | 10.33 (C) |
| Inclusive authoritative persistence, MiB | 223.1 | 266.8 (C) |

Each query row pools 300 observations per variant, with 900 exact paired responses. J passes the 500 ms scoped-risk screen; complete reports exceed their retained baseline-relative allowance and add roughly 327–324 ms. Broad-worker peak maxima were A 313.5 MiB and J 376.8 MiB, so the earlier bounded-worker memory saving cannot be generalized. Rebuild rows have three observations per variant; deltas have ten. C restores staging on every edit, contributing to its higher median. The original production-adoption gate remains unmet.

Maintenance evidence is mixed: an initial combined reuse/no-growth assertion failed without saving its counts. One subsequent observation reused 11,460 pages without file growth, but it does not explain or erase that failure. Production maintenance and long-running behavior still require qualification.

The source-rebuild cohort contains the same 41,490 nodes but 119,668 edges. Compared with the frozen served graph, 130 document-to-code references were added and five removed; every other relation and node agrees. A and C match on the fresh source cohort. The historical difference is disclosed rather than normalized away or attributed to this storage prototype.

The lifecycle prototype prepares extraction, embeddings, relationship resolution and communities outside the writer transaction. One `BEGIN IMMEDIATE` publishes their prepared state. Rollback, interrupted writes, old/new reader snapshots, reconstruction after removing disposable artifacts and real FTS/vector retrieval are tested. The small replacement fixture regenerates actual CPU FP32 embeddings; graph-only rebuilds preserve existing semantic vectors. These are scoped publication and recovery proofs, not a complete production semantic-plus-graph rebuild.

The normalized layout replaces all graph rows and rebuilds its ordinal/key mapping at each publication. That is a conservative prototype, with larger disk usage and a substantial writer lock; it does not establish efficient incremental graph writes. Production conversion must use stable identities and measured change-sized publication, or justify another representation. No claim of lower total MCP memory follows from isolated worker RSS.

**Preserve contracts:** graph symbols remain distinct from semantic chunks, including zero/one/many mappings and external endpoints. Retain independent edge evidence, deterministic filters/limits/errors, current public revisit-based cycle flags and edge-triple projection. A read snapshot must cover the whole response, including communities; per-operation transactions alone do not guarantee this. Keep igraph/Leiden and its fallback where still used.

## Gates for a subsequent conversion

1. Choose persistence representation and serving cache separately. Preserve the current query APIs, qualify generation-specific invalidation and a whole-response snapshot, and compare full reports/risk/community workloads as well as bounded traversal. Do not carry a memory result from one workload into another.
2. Extend the measured graph-only source rebuilds and deltas to the production semantic-plus-graph build path, including build-layer bookkeeping and global epochs. Preserve fences until every reader and writer uses the integrated boundary. Use stable graph IDs and change-sized writes; qualify mapping coverage and zero/one/many relationships without assuming every structural symbol has a semantic chunk.
3. Use `.wavefoundry/index/index-state.sqlite` as the proposed shared destination. Allocate an explicit new schema version in the conversion wave; do not reuse schema 7 silently. Prepare extraction/embeddings/resolution outside a bounded writer transaction. Reuse compatible semantic vectors.
4. Stage beside the owned index on the same filesystem. Prefer rebuilding derived graph rows from current sources when formats or extraction semantics differ. Record source/package identity by content and a resumable migration receipt; package paths are locators. Require host quiescence only where actual incompatible reader/writer or publication behavior demands it, and expose any stop as an expected checkpoint with exact CLI continuation.
5. Verify complete node/edge/evidence/mapping counts, semantic/FTS/vector integrity, public query parity, interrupted publication, restart, concurrent readers and changed cross-file relationships. Preserve the original graph/state until fresh-process verification succeeds. A failed stage must leave the old usable graph intact.
6. Remove only verified obsolete owned artifacts: `graph/project-graph.json`, `graph/project-graph-state.sqlite` and their owned companions, and `graph/project-graph-clusters.json` only if its replacement is implemented and verified. Never remove the whole graph directory blindly. Retain needed extraction/community state and unrelated indexes; remove no shared dependency still used elsewhere.
7. Test standard upgrades and recovery on native macOS ARM64/Intel, supported Linux and Windows targets with local packages. This evaluation executes only macOS ARM64. Measure rollback and checkpoint/compaction behavior; routine full VACUUM is not the default maintenance policy.

## Alternatives Considered

| Alternative | Reason not selected now |
| --- | --- |
| Immediately replace full adjacency with uncached lazy SQL | Small traversal is bounded, but broader hydration/materialization regresses and production lifecycle metrics are incomplete. |
| Adopt shared storage without rewriting extraction publication | Leaves the actual split boundary in place while implying an atomicity guarantee it does not provide. |
| Shared persistence with the existing resident graph cache | Viable next design when transaction simplicity is the priority; retains serving memory and needs integrated startup/invalidation measurements. |
| Add GraphQLite 0.8.0 | MIT and actively evolving, but APSW/extension coexistence, supported-platform execution and exact path/evidence semantics remain unqualified. |
| Add agentflare sqlite-graph | Explicit alpha with documented path/isolation limitations. |
| Change retrieval ordering alongside storage | Confounds quality and backend effects; the independent baseline already reached its screening stop. |

## References

- [Implementation change (wave 1xny6)](../../waves/1xny6%20unified-index-database/1xny5-ref%20unify-graph-index-storage.md)
- [Evaluation plan and results](../../waves/1xny3%20sqlite-graph-consolidation-evaluation/1xny2-task%20evaluate-sqlite-graph-consolidation.md)
- [Benchmark receipt](../../waves/1xny3%20sqlite-graph-consolidation-evaluation/benchmark-results.json)
- [Current graph architecture](../graph-index-system.md)
- [Semantic storage ADR](1xjmn-adr%20unified-sqlite-vector-storage.md)
- [SQLite recursive CTEs](https://www.sqlite.org/lang_with.html)
- [GraphQLite 0.8.0](https://pypi.org/project/graphqlite/0.8.0/)
- [agentflare implementation and maturity](https://github.com/agentflare-ai/sqlite-graph)
