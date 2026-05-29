# Graph Step Logging And Overlap

Change ID: `12xwa-enh graph-step-logging-and-overlap`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph build path is currently observable only as one broad index rebuild. That makes it hard to tell where time is going and whether graph extraction or clustering is the slow part when a rebuild stalls. The build pipeline should emit explicit graph phase logs so operators can see graph extraction, graph write, and cluster write as separate steps.

There is also a safe internal concurrency opportunity: LanceDB table maintenance/compaction and graph artifact generation operate on different outputs from the same frozen file snapshot. The indexer can overlap graph extraction/clustering with the LanceDB write/compaction work, then join once both complete. That keeps the index build single-threaded from the operator’s point of view while reducing idle time inside the process.

## Requirements

1. Log graph extraction and clustering as explicit build phases.
2. Log when cluster backend selection falls back from Leiden to the compatibility path.
3. Overlap graph artifact generation with LanceDB write/compaction where it is safe to do so.
4. Preserve the current index lock and final commit semantics.
5. Keep the graph artifact shape unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py` if bootstrap messaging needs coverage

**Out of scope:**

- graph schema changes
- cluster artifact shape changes
- dashboard visualization changes

## Acceptance Criteria

- [x] AC-1: Graph rebuilds emit distinct log lines for graph extraction, graph write, graph clustering, and cluster write.
- [x] AC-2: Graph build logs clearly report whether Leiden or the fallback path handled clustering.
- [x] AC-3: The indexer overlaps graph artifact generation with LanceDB write/compaction without changing the whole-index lock behavior.
- [x] AC-4: Tests cover the new logging and the graph path still produces the same persisted outputs.

## Tasks

- [x] Add explicit graph phase logging to the graph indexer and cluster writer.
- [x] Add a thread-safe overlap point so graph artifact generation can run while LanceDB writes/compaction are in flight.
- [x] Update tests for the graph build path and any changed log text.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Planned as a graph-build observability follow-up after the community clustering work landed. | `indexer.py`, `graph_indexer.py`, `graph_cluster.py` |
| 2026-05-27 | Implemented graph phase logging and overlapped graph artifact generation with LanceDB writes via a background executor. | `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/graph_indexer.py`, `.wavefoundry/framework/scripts/graph_cluster.py`, `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_cluster.py` |

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Operators need phase-level visibility into graph build work |
| AC-2 | required | Backend choice should be visible during rebuilds for troubleshooting |
| AC-3 | required | The overlap only matters if it shortens the critical path safely |
| AC-4 | important | Graph outputs must remain stable while the plumbing changes |
