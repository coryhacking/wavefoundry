# A Doc Link Into a Target Created Later Never Gains Its Edge Until the Doc Is Re-Scanned

Change ID: `1x8e1-bug doc-link-into-later-created-target-never-gains-edge`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-05
Wave: TBD

## Rationale

Found by the code lane's cycle-2 reverification of wave `1x6ti` (CODE-RV2-1)
while probing the assembly-time dangling-endpoint filter, and reproduced
without any outage. Doc link resolution in the graph merge is
extraction-time against the session's current paths: a doc scanned while
its link target is absent (a doc written before the file it links to, or a
first build during a walk outage) stores a fragment with no edge, is pruned
as a zero-edge doc, and is not re-scanned when the target appears in a later
build without the doc itself changing. The served payload then lacks the
edge and the doc node while a from-scratch build carries both; nothing
re-emits the edge until the doc is edited. The impacted-docs rescan in
`GraphIndexSession.finalize` keys on changed symbols (`mentioned_symbols`),
not on newly current paths, so the create side has no trigger symmetric to
the delete side that wave `1x6ti` repaired. The filter never sees these
edges (`edges_dropped_dangling` stays 0), so the gap is silent.

## Requirements

1. The impacted-docs rescan SHALL also re-scan a stored doc fragment that
   recorded an unresolved link target (a path that was not current at scan
   time) when that path becomes current in a later build, so the edge is
   emitted without the doc changing.
2. Stored doc fragments SHALL record their unresolved link targets (paths
   only) so the trigger in Requirement 1 costs a set intersection, not a
   re-read of every doc.
3. A differential test SHALL pin the sequence (doc written, target created
   later, unrelated build) as equivalent to a from-scratch build under
   `assert_equivalent`, for a noded target and for a node-less target.

## Scope

**Problem statement:** a doc's link into a path that did not exist when the
doc was last scanned never appears in the served graph until the doc is
edited.

**In scope:**

- The impacted-docs rescan trigger and the unresolved-link record on doc
  fragments in `graph_indexer.py`.
- Differential tests in `test_graph_incremental_merge.py`.
- `GRAPH_BUILDER_VERSION` moves (fragment shape changes).

**Out of scope:**

- Doc mentions of symbols (already covered by the symbol-keyed rescan).
- The delete side (wave `1x6ti`, change `1x5pc`).

## Acceptance Criteria

- [ ] AC-1: After a doc linking to an absent target is scanned and the target is created in a later build, the next merge serves the edge and the doc node, equivalent to a from-scratch build under `assert_equivalent`, for a noded and a node-less target.
- [ ] AC-2: A doc whose unresolved targets never appear is not re-scanned on unrelated builds (the trigger is the intersection with newly current paths, pinned by a re-scan spy).
- [ ] AC-3: The change's own suites pass; the documents it edits validate; no failure elsewhere is attributable to it.

## Tasks

- [ ] Red first: the differential for the doc-before-target sequence, failing on the current merge.
- [ ] Record unresolved link targets on doc fragments; add the newly-current-paths trigger to the impacted-docs rescan; bump `GRAPH_BUILDER_VERSION` with its pins.
- [ ] Mutations in a scratch copy; record the table.
- [ ] Docs: `docs/architecture/graph-index-system.md` (the impacted-docs rescan passage); CHANGELOG under Unreleased.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                 |
| ---------- | ----------- | ---------- | ------------------------------------- |
| record     | implementer | —          | Unresolved link targets on fragments. |
| trigger    | implementer | record     | Newly-current-paths rescan.           |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `docs/architecture/graph-index-system.md`

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` (the impacted-docs rescan and the
incremental-equals-full invariant) gains the create-side trigger. No boundary
change.

## AC Priority


| AC   | Priority | Rationale                                    |
| ---- | -------- | -------------------------------------------- |
| AC-1 | required | The defect itself.                           |
| AC-2 | required | The trigger must not re-read every doc.      |
| AC-3 | required | Standard delivery gate.                      |


## Progress Log


| Date       | Update                                                                                       | Evidence                                              |
| ---------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from the wave `1x6ti` delivery review (CODE-RV2-1): reproduced without an outage through the merge harness; oracle-only edges and node after the target is created; re-scanning the doc restores equality. | Wave `1x6ti` events ledger, finding CODE-RV2-1; the code lane's `rv2_code_1x6ti/probe_b_classify.py`. |


## Decision Log


| Date       | Decision                                              | Reason                                                        | Alternatives                                                        |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| 2026-09-05 | Park as its own plan rather than repair in `1x6ti`. | Pre-existing, create-side, fragment-shape change with a builder bump. | Repair in-wave: a second builder bump and rescan redesign in a delivery cycle. |


## Risks


| Risk                                                        | Mitigation                                                     |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| The trigger re-scans many docs on a large path addition.    | Intersection with the recorded unresolved targets only.       |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
