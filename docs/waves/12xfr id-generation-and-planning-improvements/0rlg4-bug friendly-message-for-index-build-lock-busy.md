# Friendly Message For Index Build Lock Busy

Change ID: `0rlg4-bug friendly-message-for-index-build-lock-busy`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

`update-indexes` currently surfaces a traceback when `setup_index.py` hits the known project-index lock-busy case. The lock collision is expected during concurrent refreshes, so the user-facing behavior should be a concise message that explains the index build is already running and that the command is continuing or skipping rather than failing with a stack trace.

## Requirements

1. When the project index build lock is already held, `setup_index.py` should print a friendly one-line message instead of a traceback.
2. The known-lock case should not abort the surrounding `update-indexes` flow.

## Scope

**Problem statement:** The current index update path treats an already-running project index as an exception-worthy failure, even though it is a normal concurrent condition.

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

**Out of scope:**

- Any change to index locking semantics
- Any change to the indexer's lock acquisition behavior

## Acceptance Criteria

- [x] AC-1: A project-index lock collision prints a concise known-scenario message without a traceback.
- [x] AC-2: `update-indexes` continues past the known lock collision instead of surfacing a hard failure.

## Tasks

- [x] Add known-lock handling in `setup_index.py`
- [x] Add regression coverage for the friendly message path
- [x] Verify the update flow continues when the lock is busy

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| setup_index handling | implementer | — | Catch the known lock collision and print a concise message |
| regression coverage | implementer | setup_index handling | Prove the lock-busy path no longer emits a traceback |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

N/A. This is a narrow error-handling improvement in the existing index-update path with no architecture boundary change.

## AC Priority

Required ACs are both behavior and regression coverage.


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the traceback for the known lock-busy case |
| AC-2 | required | Keeps `update-indexes` usable during a concurrent refresh |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Change doc created for known lock-busy messaging | |
| 2026-05-26 | Friendly lock-busy message implemented and verified | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_setup_index.py' -v` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
