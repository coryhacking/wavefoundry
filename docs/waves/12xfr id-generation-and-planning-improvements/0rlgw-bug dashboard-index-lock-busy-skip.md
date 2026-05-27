# Dashboard Index Lock Busy Skip

Change ID: `0rlgw-bug dashboard-index-lock-busy-skip`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

The dashboard index builder currently treats the known "another index build is already running" case as a failed index refresh. That is a normal concurrent condition, not a build failure, so the dashboard should skip it cleanly and keep the health surface green.

## Requirements

1. The dashboard index worker should treat the known lock-busy case as a skip, not as a failed build.
2. The dashboard should log the skip clearly enough that operators can tell a concurrent build was already in progress.

## Scope

**Problem statement:** A normal lock collision during index refresh should not flip the dashboard into a failed state.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Any change to index locking semantics in the indexer itself
- Any change to background build scheduling

## Acceptance Criteria

- [x] AC-1: The dashboard worker returns success when the indexer reports the known lock-busy message.
- [x] AC-2: A regression proves the skip path returns 0 instead of a failure code.

## Tasks

- [x] Detect the known lock-busy message in the dashboard worker
- [x] Add a regression that writes a lock-busy message into the index log and expects a skip

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Prevents a normal concurrent refresh from surfacing as failed |
| AC-2 | required  | Locks the skip behavior into test coverage |

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| lock-busy detection | implementer | — | Convert the known busy case into a skip |
| regression coverage | implementer | lock-busy detection | Prove the worker does not fail on known contention |

## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created for dashboard lock-busy skip handling | |
| 2026-05-26 | Dashboard worker now skips known lock-busy collisions and regression passes | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py' -v` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
