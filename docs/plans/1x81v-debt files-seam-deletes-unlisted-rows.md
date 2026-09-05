# The Explicit files= Build Seam Deletes Every Unlisted Row

Change ID: `1x81v-debt files-seam-deletes-unlisted-rows`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: TBD

## Rationale

Recorded by the red-team seat of wave `1x6ti`'s readiness council
(RED-PREP-5), executing `build_index(files=[...])` against a temp repository:
the explicit `files=` seam never walks, but it runs the build-path reap over
its one-file eligible set and, because change detection treats every path
absent from the eligible set as removed, it deletes the Lance rows, the
bookkeeping entries and the layer hashes of every unlisted path; the next
walk build re-indexes them all. The seam has no production caller (the
indexer command line has no files option and every non-test `build_index`
call passes none), so the behaviour is unreachable from any registered tool
and is recorded here rather than repaired in a wave scoped to something else.
Wave `1x54z` disclosed the same seam as walk-free (SEC-DEL-3) and wave
`1x6ti` corrected its plan text to say the seam does reap.

## Requirements

1. A `files=` build SHALL either restrict its removal set to the listed paths
   (treating unlisted paths as unchanged) or be removed as a public parameter
   if no caller is ever expected; the Decision Log SHALL record which.
2. A test SHALL pin that a `files=` build of one path leaves every other
   path's rows, bookkeeping and layer hashes intact.

## Scope

**Problem statement:** a programmatic single-file build treats every other
indexed file as removed.

**In scope:**

- The eligible-set and removal-set derivation on the `files=` branch of
  `_build_index_locked`.
- One pin.

**Out of scope:**

- The walk seams and the reap policy (waves `1x54z`, `1x6ti`).

## Acceptance Criteria

- [ ] AC-1: A `files=` build of one path leaves every other indexed path's Lance rows, bookkeeping entry and layer hashes unchanged.
- [ ] AC-2: The following walk build re-indexes nothing that the `files=` build did not touch.

## Tasks

- [ ] Decide restrict-versus-remove; record it.
- [ ] Implement and pin.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                       |
| ---------- | ----------- | ---------- | --------------------------- |
| decide     | implementer | —          | One Decision Log row.       |
| repair     | implementer | decide     | `_build_index_locked` only. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` item 15 (the `files=` caveat).

## AC Priority


| AC   | Priority | Rationale                                  |
| ---- | -------- | ------------------------------------------ |
| AC-1 | required | The defect itself.                         |
| AC-2 | required | The observable cost of the defect.         |


## Progress Log


| Date       | Update                                                               | Evidence                                              |
| ---------- | -------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-04 | Filed from wave `1x6ti`'s readiness council (RED-PREP-5, executed). | Scratch `prep_redteam/probe_b2_files_seam.py`.        |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                | Mitigation                                     |
| --------------------------------------------------- | ---------------------------------------------- |
| A future caller adopts the seam before the repair.  | The plan is listed; the seam is documented as walk-free and row-deleting. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
