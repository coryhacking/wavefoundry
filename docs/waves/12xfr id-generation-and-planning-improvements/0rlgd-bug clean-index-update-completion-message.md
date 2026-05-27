# Clean Index Update Completion Handoff Message

Change ID: `0rlgd-bug clean-index-update-completion-message`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

`update-indexes` currently ends with a completion line that reads like an MCP server status echo. That wording is confusing when the command was run manually, because the actual work completed was a project index refresh, not a server launch.

## Requirements

1. The index-update completion message should name the completed work directly.
2. Any MCP-related handoff should be clearly labeled as a handoff, not as the index-update result.

## Scope

**Problem statement:** The current message blurs two separate concerns: index refresh completion and MCP session handoff.

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

**Out of scope:**

- Any change to index refresh behavior
- Any change to MCP launch mechanics

## Acceptance Criteria

- [x] AC-1: `update-indexes` prints a direct project-index completion message.
- [x] AC-2: Any MCP-related follow-up is labeled as a handoff, not as the primary completion status.

## Tasks

- [x] Update the completion wording in `setup_index.py`
- [x] Update regression coverage for the new wording

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The command should clearly report the completed work |
| AC-2 | important | Keeps the MCP handoff distinct from the index refresh result |

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| completion wording | implementer | — | Replace the misleading status line |
| regression coverage | implementer | completion wording | Lock the new wording into tests |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created for index-update completion wording cleanup | |
| 2026-05-26 | Completion wording updated and regression verified | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_setup_index.py' -v` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
