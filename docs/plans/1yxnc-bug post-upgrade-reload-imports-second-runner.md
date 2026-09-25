# Post-Upgrade In-Process Reload Imports A Second Runner

Change ID: `1yxnc-bug post-upgrade-reload-imports-second-runner`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-25
Wave: TBD

## Rationale

After a successful upgrade through the `wf_upgrade` tool, `wf_upgrade_response` in `wf_server/upgrade_handlers.py` reloads the server in process with `import server as _srv` followed by `_srv.perform_mcp_reload()`. In production the runner is `__main__`, because `.mcp.json` launches `server.py` as a script, and nothing registers `sys.modules["server"]`. So `import server` executes `server.py` a second time as a new module whose `_handler` and `_root` are `None`. Its `perform_mcp_reload()` then reports `handler_not_ready`, and the automatic post-upgrade reload does not reload the served implementation. Only the explicit `wf_reload_mcp` tool (the `__main__` closure) reaches the live runner.

The readiness inventory of wave `1yzd0` found this, and the alias demonstration there modelled it (`evidence/demo/main_alias/`: `'import server -> perform': 'handler_not_ready'`). It predates the `wf_server` package move and was left out of that wave as unrelated functional work. Tests do not see it, because the test seam `server_tools_support.load_server` registers `sys.modules["server"]` itself.

## Requirements

1. The post-upgrade in-process reload reaches the running runner module, the one that owns the live handler, and never executes `server.py` a second time.
2. When no live runner is reachable (for example, the upgrade response runs outside a served process), the response reports that the reload was skipped and names `wf_reload_mcp`, rather than reporting a reload that did not happen.
3. The fix works when `server.py` is the `__main__` module, which is the production launch shape, and the regression test reproduces that shape instead of relying on the `sys.modules["server"]` test seam.

## Scope

**Problem statement:** the automatic reload after `wf_upgrade` targets a second, handler-less copy of the runner, so the upgraded implementation is not served until an explicit `wf_reload_mcp` or a restart.

**In scope:**

- How `upgrade_handlers` locates the live runner and triggers its reload.
- A regression test with `server.py` launched as `__main__`.

**Out of scope:**

- Changing `wf_reload_mcp` or the runner's reload sequence.
- Runner-file changes that still need a full restart (`runner_stale`).

## Acceptance Criteria

- [ ] AC-1: With `server.py` running as `__main__` and a live handler, a successful `wf_upgrade` response triggers the reload on that runner (fresh handler and re-registered surface), and no second `server` module is created.
- [ ] AC-2: With no live runner reachable, the response carries a diagnostic that the in-process reload was skipped and names `wf_reload_mcp`, and it does not claim a reload.
- [ ] AC-3: The regression test drives the production launch shape (`server.py` as `__main__`, no `sys.modules["server"]` registration) and fails against the current `import server` code.

## Tasks

- [ ] Reproduce the second-module behavior with a `__main__`-launched runner.
- [ ] Route the post-upgrade reload to the live runner and report the skip case.
- [ ] Add the regression test and update the upgrade prompt or spec text if it describes the automatic reload.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduce and fix | implementer | readiness | Single write owner |
| Verification | code, qa reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/server.py`

## Affected Architecture Docs

`N/A`: confined to how one handler reaches the runner; no boundary, flow or verification structure changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The automatic reload is the reported behavior |
| AC-2 | required | A skipped reload must not read as a successful one |
| AC-3 | required | The existing seam hides the defect |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Planned from wave `1yzd0` readiness finding A4 | `docs/waves/1yzd0 server-package-boundary/evidence/readiness-inventory.md` (A4) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | Plan separately from the package move | The move adds no functional change; this defect predates it | Fix inside `1yzd0` (scope creep into an organization-only wave) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Reaching the runner through `sys.modules["__main__"]` misfires when another program imports the handlers | Identify the runner by an explicit marker the runner sets, and report a skip otherwise |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
