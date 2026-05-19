# Dashboard Open Browser — `wave_dashboard_open` MCP Tool

Change ID: `12qme-enh dashboard-open-browser`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: TBD

## Rationale

`wave_dashboard_start` spawns the dashboard and opens the browser on first start, but if the dashboard is already running it returns `already_running: True` with the URL and does nothing else — the browser is never opened. Agents and users who call `wave_dashboard_start` when the dashboard is already up receive a URL they must manually copy-paste. There is also no dedicated "open browser" tool, so there is no ergonomic path for an agent to say "open the dashboard I know is running."

This change adds `wave_dashboard_open`, a dedicated MCP tool that always opens the browser to the dashboard URL: it opens the browser if the dashboard is running, or starts the dashboard (which opens the browser at startup) if it is not. As a complementary improvement, `wave_dashboard_start` gains a `next_tools: ["wave_dashboard_open"]` hint when it detects an already-running server, signalling that the agent can call `wave_dashboard_open` if the user wants the browser opened.

## Requirements

1. A new `wave_dashboard_open_response(root: Path) -> dict[str, Any]` function in `server.py`:
   - Reads the dashboard metadata file (`dashboard-server.json`) exactly as `wave_dashboard_start_response` does.
   - If the dashboard is running (pid alive, url present): calls `webbrowser.open(url)` and returns `_response("ok", {"opened": True, "url": url}, usage=url)`.
   - If the dashboard is not running: delegates to `wave_dashboard_start_response(root)` (which spawns the server with `--open`, opening the browser at startup) and returns its result.
2. `wave_dashboard_start_response` — when the dashboard is already running — includes `next_tools=["wave_dashboard_open"]` in its `_response(...)` call so agents know they can open the browser without restarting the server.
3. A new `wave_dashboard_open` MCP tool registered in `build_server()` adjacent to the existing dashboard tools, annotated `_MUTATING_TOOL` (it has a side-effect: browser open).
4. `webbrowser.open(url)` is used for cross-platform browser opening — no subprocess, no platform-specific logic.
5. The new tool and `wave_dashboard_start` modification are covered by unit tests.

## Scope

**Problem statement:** There is no way to open the browser to a running dashboard via MCP; `wave_dashboard_start` silently no-ops when already running.

**In scope:**

- New `wave_dashboard_open_response` function in `server.py`
- New `wave_dashboard_open` MCP tool in `build_server()`
- `wave_dashboard_start_response` `already_running` path: add `next_tools=["wave_dashboard_open"]`
- Unit tests for both behaviors (running → browser open; not running → delegates to start)

**Out of scope:**

- Changing `--open` flag behavior of `dashboard_server.py`
- Auto-opening browser when agent receives `already_running` (agent makes the call; server provides the hint)
- Dashboard stop/restart behavior

## Acceptance Criteria

- AC-1: `wave_dashboard_open` MCP tool exists and is callable.
- AC-2: When the dashboard is running, calling `wave_dashboard_open` opens the browser (`webbrowser.open` called with the dashboard URL) and returns `{"opened": True, "url": <url>}`.
- AC-3: When the dashboard is not running, calling `wave_dashboard_open` starts the dashboard (equivalent to `wave_dashboard_start`) and returns the start response.
- AC-4: `wave_dashboard_start` — when the dashboard is already running — returns a response that includes `next_tools: ["wave_dashboard_open"]`.
- AC-5: All existing dashboard tool tests continue to pass.

## Tasks

- Add `wave_dashboard_open_response(root)` to `server.py` (framework gate required)
- Modify `wave_dashboard_start_response` already-running branch to pass `next_tools=["wave_dashboard_open"]`
- Register `wave_dashboard_open` tool in `build_server()` adjacent to `wave_dashboard_start`
- Add unit tests: `test_dashboard_open_when_running` and `test_dashboard_open_when_not_running`
- Run full test suite

## Agent Execution Graph

| Workstream      | Owner              | Depends On | Notes                                       |
| --------------- | ------------------ | ---------- | ------------------------------------------- |
| server-impl     | framework-engineer | —          | open_response + start_response patch        |
| tool-register   | framework-engineer | server-impl | build_server() registration               |
| tests           | framework-engineer | server-impl | Unit tests for open behavior              |

## Serialization Points

- `server.py` — single shared file; all workstreams in sequence

## Affected Architecture Docs

N/A — new tool follows existing dashboard tool pattern; no boundary, flow, or schema change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. `wave_dashboard_open_response` added to server.py; `wave_dashboard_start_response` already-running branch updated with `next_tools=["wave_dashboard_open"]`; `wave_dashboard_open` tool registered in `build_server()` adjacent to start/stop/restart; 3 unit tests added covering AC-2/3/4; tool name added to registered-tools assertion (AC-1). 580 server tests pass. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'` — 580 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | `wave_dashboard_open` delegates to `wave_dashboard_start_response` when not running | Avoids duplicating spawn logic; start already opens browser via `--open` flag | Duplicate spawn logic in open_response |
| 2026-05-18 | `webbrowser.open(url)` for browser open | Cross-platform stdlib; no subprocess needed | `subprocess.Popen(["open", url])` macOS-only |
| 2026-05-18 | `wave_dashboard_start` adds `next_tools` hint rather than auto-opening | Agent decides; auto-open on start response would be surprising for non-interactive use | Auto-open in start response |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `webbrowser.open` may silently fail on headless servers | Acceptable — headless deployments don't use the dashboard UI; tool is primarily for local dev |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
