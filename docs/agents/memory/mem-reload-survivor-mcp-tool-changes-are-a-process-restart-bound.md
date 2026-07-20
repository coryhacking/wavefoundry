# Reload-survivor MCP tool changes are a process-restart boundary

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-reload-survivor-mcp-tool-changes-are-a-process-restart-bound`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-07-20
Updated: 2026-07-20
Source event: `decision-log:1t3gs-ref mcp-tool-prefix-rename:1cf715487e05e4dd`
Validation: promote
Validated by: agent
Action delta: When renaming or removing a reload-survivor MCP tool (anything in _RELOAD_SURVIVOR_TOOLS), plan a host reconnect/process restart as part of the change; hot reload cannot apply it, and verification must use a fresh-process tools/list probe rather than the degraded live session.
Validation rationale: Lived this session: the in-memory old-name survivor tripped the new prefix guard during hot reload (register_surface_failed), while a fresh server.py process registered the full renamed surface exactly. The generalized constraint is durable (it applies to any future reload-survivor change, not just this rename) and the drafted candidate buried it in one-time AC bookkeeping prose.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Hot reload (wf_reload_mcp) re-imports server_impl but deliberately cannot replace the in-memory server.py runner, so tools in _RELOAD_SURVIVOR_TOOLS keep their old definition and name until the host process restarts. Renaming or removing a survivor therefore requires one host reconnect, and the old in-memory name can trip guards written against the new contract (observed: the prefix-contract check refused re-registration during the wave_ to wf_ rename). Verify such changes with a fresh-process MCP tools/list probe, never against the degraded live session.

## Evidence

- `1t3gs-ref mcp-tool-prefix-rename`
- `1t3gt`
- `.wavefoundry/framework/scripts/server.py`

## Targets

- `.wavefoundry/framework/scripts/server.py`
