# Factor 13 — API First Review Agent

## What This Factor Covers

API as a first-class integration contract consumed by other systems or services.

## Why This Factor Is Applicable to Wavefoundry

The future MCP tool surface (`wave.current`, `wave.validate`, `wave.resolve_seed`, `wave.prompt_surface_audit`, `code.search`, `code.read`) is a first-class integration contract. Tool contracts are defined before implementation per AGENTS.md Initial MCP Tool Surface. MCP clients (Claude Code, Cursor, Copilot) consume these tools as a stable interface.

Evidence: `AGENTS.md` Initial MCP Tool Surface and Later MCP Tool Surface; `docs/missing-docs.md` flags `docs/specs/mcp-tool-surface.md` as needed.

## Review Questions

When evaluating a wave touching MCP tool contracts or server implementation:

1. Is the tool contract specified in `docs/specs/mcp-tool-surface.md` before implementation begins?
2. Do tool responses use structured JSON with stable field names (not ad-hoc strings)?
3. Are error responses structured (error code + message) rather than raw exceptions?
4. Is the input schema for each tool explicit (required vs optional params, types)?
5. Are breaking changes to tool signatures treated as major changes requiring `architecture-reviewer` and `docs-contract-reviewer`?
6. Is the read-only tool surface stable before mutation tools are introduced?
7. Are tools defensive: do they validate allowed-roots before reading, and fail fast with a clear error when outside configured roots?

## Findings

Advisory for Wavefoundry. Record in wave `## Review checkpoints`.
