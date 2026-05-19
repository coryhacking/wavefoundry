# `wave_upgrade` MCP Tool

Change ID: `12r0b-feat wave-upgrade-mcp-tool`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

`upgrade-wavefoundry` (12r08) is a bin script callable from a shell. Agents operating through MCP have no direct access to shell scripts — they need an MCP tool entry point. Without `wave_upgrade`, an agent would have to call `wave_run_sensors` or a similar workaround, or the operator would have to manually invoke the bin script and relay results back.

`wave_upgrade` exposes the upgrade script over MCP so an agent can initiate the mechanical upgrade phases (0–3: pre-flight, surface rendering, pruning, docs gate) with a single tool call, and separately invoke phase 4 (index rebuild) and phase 5 (cleanup) as distinct calls after the editing pass.

## Requirements

1. A new `wave_upgrade_response(root, phase)` function in `server.py` that spawns `upgrade_wavefoundry.py` as a subprocess with `--yes` (non-interactive, since MCP has no TTY) and captures stdout/stderr, returning structured output.
2. `phase` parameter accepts: `"preflight_to_docs_gate"` (default, runs phases 0–3), `"rebuild_index"` (phase 4), `"cleanup"` (phase 5).
3. The response includes: `{"exit_code": int, "output": str, "phase": str}`. Non-zero exit code maps to `status: "error"` with the output included in diagnostics so the agent can see what failed.
4. The tool runs **synchronously** (not background): phases 0–3 are fast enough (< 30s typical) and the agent needs the result before proceeding to its editing pass. Phase 4 (index rebuild) spawns the code index in the background internally but the docs rebuild is blocking.
5. A new `wave_upgrade` MCP tool registered in `build_server()` as `_MUTATING_TOOL` (it modifies the filesystem).
6. `wave_upgrade` must be added to the registered-tool name assertion in `test_server_tools.py`.

## Scope

**Problem statement:** The `upgrade-wavefoundry` bin script has no MCP entry point, so agents cannot initiate an upgrade through the MCP protocol.

**In scope:**

- `wave_upgrade_response(root, phase)` in `server.py`
- `wave_upgrade` MCP tool registration in `build_server()`
- Unit test for the tool registration
- Update registered-tool assertion in tests

**Out of scope:**

- Background/async upgrade execution (phases 0–3 are fast; background would complicate error surfacing)
- Progress streaming over SSE (future enhancement)
- Exposing individual sub-phases (pre-flight, rendering, pruning, docs gate) as separate tools

## Acceptance Criteria

- AC-1: `wave_upgrade()` MCP tool exists and is registered.
- AC-2: `wave_upgrade(phase="preflight_to_docs_gate")` runs `upgrade_wavefoundry.py --yes` and returns the output and exit code.
- AC-3: `wave_upgrade(phase="rebuild_index")` runs `upgrade_wavefoundry.py --rebuild-index --yes` and returns the output and exit code.
- AC-4: `wave_upgrade(phase="cleanup")` runs `upgrade_wavefoundry.py --cleanup --yes` and returns the output and exit code.
- AC-5: A non-zero exit code from the script results in `status: "error"` with the output in diagnostics.
- AC-6: All existing server tests pass.

## Tasks

- Add `wave_upgrade_response(root, phase)` to `server.py`
- Register `wave_upgrade` in `build_server()`
- Add `"wave_upgrade"` to the registered-tool name set in `test_server_tools.py`
- Add unit test for non-zero exit mapping to `status: "error"`

## Agent Execution Graph

| Workstream    | Owner              | Depends On      | Notes                          |
| ------------- | ------------------ | --------------- | ------------------------------ |
| server-impl   | framework-engineer | 12r08 (upgrade script exists) | wave_upgrade_response + tool |
| tests         | framework-engineer | server-impl     | Registration + error mapping   |

## Serialization Points

- `server.py` — single shared file; must follow `upgrade_wavefoundry.py` being written

## Affected Architecture Docs

N/A — new tool follows existing MCP tool pattern; no boundary or schema change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core discoverability |
| AC-2 | required  | Primary use case |
| AC-3 | required  | Agent-callable index rebuild |
| AC-4 | required  | Agent-callable cleanup |
| AC-5 | required  | Error surfacing |
| AC-6 | required  | No regression |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Implemented. `wave_upgrade_response(root, phase)` added to server.py; `wave_upgrade` MCP tool registered as `_MUTATING_TOOL`; `wave_upgrade` and `wave_upgrade_status` added to registered-tool assertion; 5 unit tests added (invalid phase, success, nonzero exit, rebuild_index flag, cleanup flag). 589 server tests pass. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'` — 589 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-19 | Synchronous execution (not background) | Agent needs result before proceeding to editing pass; phases 0–3 are < 30s | Background with polling (adds complexity for no benefit) |
| 2026-05-19 | `phase` parameter (not separate tools per phase) | Single tool, self-describing; `wave_upgrade_status` already covers read-only state | Three separate tools (more surface area, less cohesive) |
| 2026-05-19 | Calls `upgrade_wavefoundry.py` as subprocess with `--yes` | Reuses all logic from the bin script; keeps server.py thin | Inline the phase logic in server.py (duplicates implementation) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Long-running docs rebuild may hit MCP request timeout | Docs rebuild is typically < 60s; code rebuild is background — acceptable; note in docstring |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
