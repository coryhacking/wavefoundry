# A Doc-Link Edge Into a Deleted Doc Resurfaces on the Next Unrelated Build

Change ID: `1x5pc-bug dangling-doc-link-edge-after-linked-doc-deletion`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: TBD

## Rationale

Found by the red-team seat during the delivery review of wave `1x54z`
(RED-RV2-1) and reproduced byte for byte on the pre-wave tree, so it is not
that wave's defect. When a doc that another doc links to is deleted, the
first build after the deletion prunes the target's node and the
`doc_references_doc` edge from the served payload. On the next build that
does not touch the linking doc (an unrelated code edit), the edge comes back
into `project-graph.json` with no target node and no store row for the
target, and it persists across further unrelated builds until a full
rebuild. The comment above the merge's prune in `GraphIndexSession.finalize`
predicts it: the prune repairs the payload only, while the linking doc's
persisted fragment keeps whatever edges it carried, and a removed doc path
(unlike a removed symbol) never triggers a re-resolution of the fragments
that point at it. The `finalize` docstring's incremental-equals-full
invariant is therefore violated for this shape.

A second variant of the same class was found in the same review (ARCH-RV3-1):
since wave `1x54z` the merge keeps the stored fragment of a doc under a
directory the walk could not read and skips it in the impacted-docs rescan,
so when a symbol that doc mentions is renamed during the outage the fragment
keeps its `doc_references_code` edge to the removed symbol id. The
removed-symbols prune masks that edge for one build; the next merge for any
change re-emits it with no target node, and it persists until the doc is
edited or a full rebuild. The code's own note above the reverse-invalidation
block predicts it. Both variants are fragment edges whose endpoint is gone
from the node set at payload assembly.

## Requirements

1. After a linked doc is deleted, no later incremental build SHALL serve an
   edge whose target is that path, without requiring a full rebuild.
2. The repair SHALL either re-resolve the fragments of docs that linked into
   a removed doc path (add removed doc paths to the impacted-docs rescan) or
   filter, at payload assembly, any fragment edge whose endpoint node is
   absent from the node set, which covers both the removed-doc-path variant
   and the removed-symbol variant left by a doc the merge could not rescan
   during a walk-shadow outage; the Decision Log SHALL record which and why.
3. A test SHALL pin the sequence: link, delete the target, build, unrelated
   edit, build, and assert the edge is absent after both builds and that the
   payload equals a from-scratch build's edge-key set.

## Scope

**Problem statement:** the merge's payload prune removes an edge into a
deleted doc once, but the linking doc's stored fragment re-emits it on the
next unrelated build.

**In scope:**

- The doc-path branch of the merge's edge re-resolution in `finalize`.
- One differential test against a full rebuild.

**Out of scope:**

- The eligibility reap, the breaker policy and the walk-shadow preservation
  itself (wave `1x54z`); this change repairs what the merge serves from a
  preserved fragment, not whether it is preserved.

## Acceptance Criteria

- [ ] AC-1: After deleting a linked doc and running two incremental builds (the second after an unrelated edit), the payload carries no edge into the deleted path.
- [ ] AC-2: The payload's edge-key set after that sequence equals a full rebuild's.
- [ ] AC-3: The existing merge equivalence suites stay green.
- [ ] AC-4: After a symbol a shadowed doc mentions is renamed during a walk-shadow outage, then recovery and an unrelated edit, the payload carries no edge whose target node is absent.

## Tasks

- [ ] Decide between fragment re-resolution and payload filtering; record it.
- [ ] Implement the chosen branch in `finalize`.
- [ ] Add the differential test and record the mutation.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                     |
| ---------- | ----------- | ---------- | ----------------------------------------- |
| decide     | implementer | —          | One Decision Log row.                     |
| repair     | implementer | decide     | `finalize` only.                          |
| pin        | implementer | repair     | Differential against `full=True`.         |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` (the orphan-retirement and
incremental-merge paragraphs, if the chosen branch changes what the prune
repairs).

## AC Priority


| AC   | Priority | Rationale                                              |
| ---- | -------- | ------------------------------------------------------ |
| AC-1 | required | The defect itself.                                     |
| AC-2 | required | The merge's own documented invariant.                  |
| AC-3 | required | The merge's equivalence suites are the regression net. |
| AC-4 | required | The second variant of the same class (ARCH-RV3-1). |


## Progress Log


| Date       | Update                                                                                                 | Evidence                                         |
| ---------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| 2026-09-04 | Filed from the `1x54z` delivery review (RED-RV2-1, probe R1b on the cycle-2 tree and on the pre-wave control). | Wave `1x54z` events ledger, finding RED-RV2-1.    |
| 2026-09-04 | Widened to the removed-symbol variant left by a doc the merge could not rescan during an outage (ARCH-RV3-1, probe2_nodes on the cycle-3 tree). | Wave `1x54z` events ledger, finding ARCH-RV3-1. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                             | Mitigation                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------- |
| Re-resolving fragments on every doc deletion costs a rescan per linking doc. | The impacted set is bounded by the docs that link to the removed path. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
