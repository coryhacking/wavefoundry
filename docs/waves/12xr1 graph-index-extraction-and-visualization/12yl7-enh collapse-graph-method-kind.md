# Collapse Graph Method Kind

Change ID: `12yl7-enh collapse-graph-method-kind`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-28
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph currently distinguishes `function` and `method` nodes, but the distinction is mostly visual taxonomy: both represent executable symbols, and ownership is already encoded by qualified IDs and containment structure. Keeping both kinds adds cognitive noise to graph filtering and display without providing enough value.

## Requirements

1. Collapse graph extractor output so class/object-owned callables are emitted as `function` nodes, not `method` nodes.
2. Keep existing symbol IDs and labels stable; only the graph node kind changes.
3. Remove dashboard-specific visual branching for `method` if it becomes unreachable.
4. Update tests that assert method-specific node kinds.

## Scope

**Problem statement:** Function and method nodes are operationally the same graph concept and should be displayed as one callable kind.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- Graph indexer/dashboard tests that assert node kind behavior

**Out of scope:**

- Changing symbol IDs
- Changing call/import/contains edge extraction
- Reworking graph layout or filters beyond removing the method kind branch

## Acceptance Criteria

- [x] AC-1: The graph extractor no longer emits `kind: "method"` for callable definitions.
- [x] AC-2: Class-owned callable IDs remain qualified, e.g. `path::Class.method`.
- [x] AC-3: Dashboard visual handling no longer needs a distinct `method` node kind branch.
- [x] AC-4: Existing graph extraction, clustering, and dashboard tests pass after expectation updates.

## Tasks

- [x] Update graph kind classification to map methods/constructors/member callables to `function`.
- [x] Update Python and fallback extraction paths that explicitly emit `method`.
- [x] Remove or collapse dashboard method visual handling.
- [x] Update graph tests.
- [x] Run focused and full framework tests.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| extractor | implementer | — | Collapse node kind without touching IDs |
| dashboard | implementer | extractor | Remove unreachable method branch |
| tests | qa-reviewer | implementation | Ensure graph output has no method nodes |


## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- Graph indexer/dashboard tests

## Affected Architecture Docs

N/A — this is a narrow taxonomy simplification inside the graph extractor and dashboard display.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Core behavior change |
| AC-2 | required | Stable IDs preserve graph continuity |
| AC-3 | important | Dashboard should not carry unreachable visual taxonomy |
| AC-4 | required | Graph behavior is test-covered |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-28 | Planned after deciding methods and functions should be one graph callable kind. | Operator request |
| 2026-05-28 | Collapsed emitted graph callable kind to `function`, removed dashboard `method` branch, and verified focused plus full framework tests. | `run_tests.py` passed: 1718 tests across 22 files |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-28 | Collapse `method` into `function` instead of preserving both kinds. | Qualified IDs and containment already carry ownership; separate visual kind adds noise. | Keep separate kinds — rejected as low-value taxonomy |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Graph consumers may expect `method` kind | Current graph query surface is not shipped yet; update tests and dashboard together before downstream promotion |
| Collapsing kind could hide ownership | Preserve qualified symbol IDs and contains/call edges |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
