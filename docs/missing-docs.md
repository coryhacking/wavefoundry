# Missing Docs

Owner: Engineering
Status: active
Last verified: 2026-05-08

Tracks known documentation gaps — items that should exist but don't yet, or items flagged as needing verification.

## Active Gaps

| Gap | Why Needed | Priority |
|-----|-----------|---------|
| `docs/architecture/decisions/<id>-adr framework-location.md` | Record the decision to place framework content at `.wavefoundry/framework/` as the canonical directory | medium |
| `docs/architecture/decisions/<id>-adr mcp-transport.md` | Record transport decision (stdio vs socket) once MCP server design is finalized | medium |
| `docs/contributing/docs-maintenance.md` | Explains doc freshness expectations, metadata update triggers | low |
| Factor 07 (port binding) ADR | Need decision on MCP server transport before this factor can be fully evaluated | medium |
| Factor 09 (disposability) ADR | Depends on MCP server process model | medium |

## Watchpoints

- MCP server design: multiple architectural decisions are deferred until the MCP
  server contract and implementation settle. Re-run `seed-060` and update factor
  review when the guided MCP contract work is complete.
- `code_patterns` in `docs/repo-profile.json`: currently `{"status": "insufficient_history"}`. Revisit once MCP implementation sources exist (≥3 source files with meaningful implementation).
