# Missing Docs

Owner: Engineering
Status: active
Last verified: 2026-04-28

Tracks known documentation gaps — items that should exist but don't yet, or items flagged as needing verification.

## Active Gaps

| Gap | Why Needed | Priority |
|-----|-----------|---------|
| `docs/specs/mcp-tool-surface.md` | Formal tool contracts for wave.current, wave.validate, code.search, etc. once MCP server is scaffolded | high |
| `docs/architecture/decisions/DEC-001-self-hosting-symlink.md` | Record the decision to use a symlink rather than a copy for self-hosting | medium |
| `docs/architecture/decisions/DEC-002-mcp-transport.md` | Record transport decision (stdio vs socket) once MCP server design is finalized | medium |
| `docs/contributing/docs-maintenance.md` | Explains doc freshness expectations, metadata update triggers | low |
| Factor 07 (port binding) ADR | Need decision on MCP server transport before this factor can be fully evaluated | medium |
| Factor 09 (disposability) ADR | Depends on MCP server process model | medium |

## Watchpoints

- MCP server design: multiple architectural decisions are deferred until `src/wavefoundry/` is scaffolded. Re-run `seed-060` and update factor review once the server topology is clear.
- `code_patterns` in `docs/repo-profile.json`: currently `{"status": "insufficient_history"}`. Revisit once MCP implementation sources exist (≥3 source files with meaningful implementation).
