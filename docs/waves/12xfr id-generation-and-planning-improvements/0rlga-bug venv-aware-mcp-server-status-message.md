# Venv-Aware MCP Server Status Message

Change ID: `0rlga-bug venv-aware-mcp-server-status-message`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

The `setup_index.py` completion message currently hardcodes `python3` in the suggested MCP server command. That is misleading when the script is already running under the shared tool venv, and it makes the output look like the update path fell back to system Python even when it did not.

## Requirements

1. The final `setup_index.py` status line should print the resolved venv Python when available instead of hardcoding `python3`.
2. The test suite should cover the status line so it cannot drift back to the system Python form.

## Scope

**Problem statement:** The update-index completion message is cosmetically wrong and suggests system Python even when the venv launcher is available and in use.

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

**Out of scope:**

- Any change to the index build command itself
- Any change to venv bootstrap or re-exec behavior

## Acceptance Criteria

- [x] AC-1: The completion message prints the resolved venv Python path when one is available.
- [x] AC-2: Regression coverage verifies the message no longer hardcodes `python3`.

## Tasks

- [x] Update the completion message in `setup_index.py`
- [x] Add a regression assertion for the message text
- [x] Verify the output in the setup-index test suite

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| status-message update | implementer | — | Replace the hardcoded launcher string with the resolved venv python |
| regression coverage | implementer | status-message update | Assert the completion message uses the resolved interpreter |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

N/A. This is a message-format fix within an existing script and its tests.

## AC Priority

Required ACs are the message text and its regression test.


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Avoids suggesting the system Python path when the venv is present |
| AC-2 | required | Prevents regression of the completion message |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Change doc created for venv-aware MCP status messaging | |
| 2026-05-26 | Status message now prints the resolved venv Python path and is covered by tests | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_setup_index.py' -v` |


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
