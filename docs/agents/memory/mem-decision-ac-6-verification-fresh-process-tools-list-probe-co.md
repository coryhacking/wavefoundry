# Decision: AC-6 verification: fresh-process `tools/list` probe confirm…

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-decision-ac-6-verification-fresh-process-tools-list-probe-co`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 584156
Source event: `decision-log:1t3gs-ref mcp-tool-prefix-rename:1cf715487e05e4dd`
Validation: rewrite
Validated by: agent
Action delta: When renaming or removing a reload-survivor MCP tool (anything in _RELOAD_SURVIVOR_TOOLS), plan a host reconnect/process restart as part of the change; hot reload cannot apply it, and verification must use a fresh-process tools/list probe rather than the degraded live session.
Validation rationale: Lived this session: the in-memory old-name survivor tripped the new prefix guard during hot reload (register_surface_failed), while a fresh server.py process registered the full renamed surface exactly. The generalized constraint is durable (it applies to any future reload-survivor change, not just this rename) and the drafted candidate buried it in one-time AC bookkeeping prose.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-reload-survivor-mcp-tool-changes-are-a-process-restart-bound`
## Summary

Decision (wave 1t3gt): AC-6 verification: fresh-process `tools/list` probe confirms 83 tools, zero `wave_`-prefixed (50 `wf_`, 7 `memory_`, 4 `index_`, plus docs/code/seed), all renamed tools present. Known one-time caveat: in-session hot reload cannot rename the reload-survivor tool itself — the old process's in-memory `wave_mcp_reload` trips the new prefix guard, so THIS rename requires one host reconnect (already a wave watchpoint). Future reloads are unaffected (`wf_reload_mcp` is the survivor from now on).. Rationale: Renaming the tool that performs hot reload is inherently a process-restart boundary; verified via MCP stdio client against a fresh `server.py` rather than the degraded live session..

## Evidence

- `1t3gs-ref mcp-tool-prefix-rename`
- `1t3gt`

## Targets

- `server.py`
