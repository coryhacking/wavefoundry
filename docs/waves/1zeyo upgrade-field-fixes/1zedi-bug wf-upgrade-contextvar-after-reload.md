# wf_upgrade Reports an Error When a Mid-Call Reload Swaps the Navigation ContextVar

Change ID: `1zedi-bug wf-upgrade-contextvar-after-reload`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zeyo upgrade-field-fixes

## Rationale

Field report from a 1.28.0+ptgj test upgrade (macOS, Claude Code): both `wf_upgrade` calls completed every phase they ran (`.wavefoundry/logs/upgrade.log` shows `failed_phase: null`, docs gate passed, index published, cleanup removed the lock), yet each tool call returned `Error executing tool wf_upgrade: <Token var=<ContextVar name='wavefoundry_navigation_events' ...> was created by a different ContextVar`.

Cause, verified in code: every sync tool is wrapped by `noticed_call` in `wf_server/server_impl.py` (the navigation-notice wrapper from wave `1za2y`). It calls `_NAVIGATION_EVENTS.set([])` before the tool and `_NAVIGATION_EVENTS.reset(token)` in `finally`, looking the module global up each time. `wf_upgrade` reloads `server_impl` inside its own call (the automatic post-upgrade reload, `importlib.reload(server_impl)` in `server.py`), which rebinds `_NAVIGATION_EVENTS` to a new `ContextVar`. The `reset` then passes the old variable's token to the new variable, which Python rejects. Only `wf_upgrade` reaches that reload through the wrapper: in `apply` mode for `preflight_to_docs_gate` and `cleanup`, `wf_upgrade_response` calls `_reload_live_runner`, which runs `perform_mcp_reload`. `wf_reload_mcp` also reloads, but it is an async runner tool the wrapper skips.

Goal: a tool call that reloads the server module reports its real outcome. Consumer: agents driving `wf_upgrade` through MCP. Success: a successful upgrade returns its summary, not an error.

## Requirements

1. **Reset the variable that was set.** `noticed_call` captures the `ContextVar` object before calling the tool and resets that same object in `finally`, so a reload of `server_impl` during the call cannot mismatch the token. Events collected during the call are read from the captured variable.
2. **Every tool that can reload the module is covered.** The set is every tool whose call path can reach `importlib.reload` of `server_impl` (derived by tracing the reload call sites in `server.py` and the handler modules; today only `wf_upgrade`, in `apply` mode for `preflight_to_docs_gate` and `cleanup`, through `_reload_live_runner`; `wf_reload_mcp` is a runner tool the wrapper skips, and a test pins that it stays unwrapped). Each returns its own result, with no ContextVar error.
3. **Navigation notices are unchanged** for tools that do not reload: the wrapper still collects walker events and applies `_apply_navigation_notices` exactly as before.
4. **Platforms.** Behaviour is the same on Windows, macOS, Linux and WSL2 (pure Python context-variable handling).
5. **Transition.** The wrapper in effect is the one loaded when the call started. A server running a build without the fix reports the error once, on the call that performs the reload; that reload (automatic after `wf_upgrade`, or `wf_reload_mcp`) installs the fixed wrapper for later calls, so no restart is needed. 1.27.0 servers never carried the variable (it arrived with wave `1za2y`). The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** `wf_upgrade` returns an error after a successful upgrade because a mid-call module reload swaps the `ContextVar` the wrapper resets.

**In scope:**

- `noticed_call` in `wf_server/server_impl.py`; tests; CHANGELOG.

**Out of scope:**

- The reload mechanism itself; the upgrade phases; host-side backgrounding of long calls (the reported 120 s backgrounding is incidental).

## Acceptance Criteria

- [x] AC-1: a wrapped tool whose body rebinds `server_impl._NAVIGATION_EVENTS` to a new `ContextVar` (as `importlib.reload` does) returns its own result without raising, and a navigation event recorded before the rebind is still applied to that result.
- [x] AC-2: `wf_upgrade` driven through the registered wrapper, with a real `importlib.reload` of `server_impl` during the call (via `perform_mcp_reload`, run through `load_thin_runner` so the reload does not leak into sibling tests), returns its result rather than a ContextVar error; `wf_reload_mcp` is asserted to be unwrapped.
- [x] AC-3: for a tool that does not reload, the navigation notices and the setup notice are unchanged.
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Capture the ContextVar in `noticed_call`; confirm the reload call sites that reach it.
- [x] Tests for AC-1 to AC-3, including a real reload.
- [x] CHANGELOG `### Fixed` entry under 1.28.0.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Wrapper fix and tests | implementer | readiness | One function |
| Review | code-reviewer, qa-reviewer | Wrapper fix and tests | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- CHANGELOG.md

## Affected Architecture Docs

N/A: a one-function correctness fix inside the MCP wrapper; no boundary, flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect |
| AC-2 | required | The field-observed tool calls |
| AC-3 | required | No regression to 1za2y's notices |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Full-suite guards: the `wf_upgrade` tool docstring was corrected (stale `review_status_projection`), so its pinned handler digest in `tests/fixtures/register-surface-handler-digests.json` was refreshed; only `wf_upgrade` moved, name sets equal. `_MEMORY_BOOTSTRAP_MODULES` (1zesi) classified as a non-behaviour collection in the tool-name census (it lists modules; `memory_backfill` is also a tool name); the 1zesi derivation test now uses `framework_files` helpers | test_mcp_tool_registry, test_extension_tool_modules, test_server_package OK |
| 2026-09-30 | Implemented. `noticed_call` holds `events_var = _NAVIGATION_EVENTS` and sets, reads and resets that object. Reload census: the only wrapped tool reaching `importlib.reload(server_impl)` is `wf_upgrade` (via `_reload_live_runner` -> `perform_mcp_reload`); `wf_reload_mcp` is a runner tool the wrapper skips. Tests (`SetupReadinessOnStartAndReloadTests`): `test_wf_upgrade_survives_a_reload_during_its_own_call` drives the registered `wf_upgrade` wrapper with a body that records a navigation event and runs a real `perform_mcp_reload` (asserting the ContextVar was rebound); the result returns and carries the pre-reload `index_runtime_stale` notice (AC-1, AC-2); `test_wf_reload_mcp_stays_unwrapped`; existing wrapper tests unchanged (AC-3). Mutant: module-global reset restored; caught (the test errors with the field message). Gapfill: none for retrieval | test_server_tools classes OK |
| 2026-09-30 | Readiness review: B4 adopted (`wf_reload_mcp` is an async runner tool the wrapper skips; only `wf_upgrade` reaches the reload, via `_reload_live_runner`); Requirement 2, AC-2, Rationale and Goal corrected. R1 adopted: transition wording (the reload installs the fixed wrapper; 1.27.0 never carried the variable). QA: run the real reload through `load_thin_runner` / `perform_mcp_reload`; reverting to the module-global lookup must fail AC-1 and AC-2 | readiness review |
| 2026-09-30 | Planned from a 1.28.0+ptgj field test. Verified: `noticed_call` sets and resets the module-global `_NAVIGATION_EVENTS`; `server.py` reloads `server_impl` with `importlib.reload`, which re-executes the module-level `ContextVar(...)` | code reading |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Capture the ContextVar locally in the wrapper | Fixes every reloading tool at one site, keeps notices for all tools | Skip the wrapper for `wf_upgrade` (loses notices for that tool); keep the `ContextVar` in a module that is never reloaded (larger move) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Events recorded after the reload go to the new variable and are lost for that call | Acceptable: the reload is the last act of those tools; AC-1 pins the pre-reload events |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
