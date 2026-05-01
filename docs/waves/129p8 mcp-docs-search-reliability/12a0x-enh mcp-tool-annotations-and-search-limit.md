# MCP Tool Annotations and Search Limit

Change ID: `12a0x-enh mcp-tool-annotations-and-search-limit`
Change Status: `complete`
Owner: implementer
Status: complete
Last verified: 2026-04-30
Wave: 129p8 mcp-docs-search-reliability

## Rationale

MCP design review (mcp-builder) identified multiple gaps against MCP best practices across tool annotations, search ergonomics, naming, error signalling, and client discoverability. Addressing these brings the server into full compliance with the MCP spec and best practices.

## Requirements

1. Every `@mcp.tool()` registration must include an `annotations` dict with `readOnlyHint`, `destructiveHint`, and `idempotentHint` (C-1).
2. `docs_search` must accept an optional `limit: int` parameter (default 5, clamped 1–20) passed through to `search_docs` / `search_docs_lexical` (C-2).
3. `code_search` must accept an optional `limit: int` parameter (default 5, clamped 1–20) passed through to `search_code` (C-2).
4. All `wave_new_*` compatibility wrapper docstrings must be prefixed with a note directing agents to prefer `wave_change_create` (I-2).
5. Missing `Args:` documentation must be added to `wave_remove_change`, `wave_close`, `wave_prepare`, and `wave_pause` tool docstrings (I-1).
6. The FastMCP server must be renamed from `"wavefoundry"` to `"wavefoundry_mcp"` to follow the `{service}_mcp` Python MCP naming convention (I-3).
7. Error envelopes returned when `status == "error"` must include `isError: True` at the top level for protocol-level error signalling to MCP clients (I-4).
8. `wave_list_waves` and `wave_list_plans` must support an optional `limit` parameter (default 50) and return `has_more` in their data payload (I-5).
9. `wave_garden` and `wave_sync_surfaces` must accept a `mode: str = "dry_run"` parameter consistent with the mutating tool contract (A-1).
10. The `kind` parameter on `docs_search` must use a `Literal` type annotation so FastMCP generates an enum schema (A-2).
11. A comment block must be added above the first `@mcp.tool()` registration explaining why `**kwargs` is present on every tool handler (A-3).
12. All changes must leave tests passing and `docs-lint` clean.

## Scope

**Problem statement:** The MCP server is functionally correct but non-compliant with several MCP best-practice requirements that affect client compatibility, agent discoverability, and operator ergonomics.

**In scope:**

- Tool annotations on all 40+ tool registrations (`server.py`)
- `limit` parameter for `docs_search`, `code_search`, `wave_list_waves`, `wave_list_plans`
- `wave_garden` and `wave_sync_surfaces` dry-run mode
- Server rename to `wavefoundry_mcp`
- `isError` in error envelopes
- `Literal` type for `docs_search` `kind`
- Deprecation notes on `wave_new_*` wrappers
- Missing `Args:` blocks on thin docstrings
- `**kwargs` explanation comment

**Out of scope:**

- Adding `mode: dry_run` to `wave_validate` (already has it per spec)
- Pagination cursor/offset implementation (limit + has_more is sufficient for current scale)
- `outputSchema` / `structuredContent` migration (requires FastMCP version bump)

## Acceptance Criteria

- AC-1: All tool `@mcp.tool()` calls include `annotations` with `readOnlyHint`, `destructiveHint`, `idempotentHint`.
- AC-2: `docs_search(query, kind, limit)` accepts `limit` (default 5, clamped 1–20), passed to search functions.
- AC-3: `code_search(query, language, limit)` accepts `limit` (default 5, clamped 1–20), passed to search function.
- AC-4: `wave_list_waves` and `wave_list_plans` accept `limit` (default 50) and include `has_more` in response data.
- AC-5: `wave_garden` and `wave_sync_surfaces` accept `mode: str = "dry_run"` and skip writes in dry-run mode.
- AC-6: FastMCP server name is `"wavefoundry_mcp"`.
- AC-7: `_response()` includes `"isError": True` when `status == "error"`.
- AC-8: `docs_search` `kind` uses `Literal` type annotation.
- AC-9: `wave_new_*` docstrings note the preferred `wave_change_create` path.
- AC-10: `wave_remove_change`, `wave_close`, `wave_prepare`, `wave_pause` have complete `Args:` blocks.
- AC-11: `**kwargs` comment block present above first `@mcp.tool()` registration.
- AC-12: Tests pass; `docs-lint` clean.

## Tasks

- Add `_READONLY_TOOL`, `_MUTATING_TOOL`, `_DESTRUCTIVE_TOOL` annotation dicts; apply to all tool registrations (`server.py`)
- Add `limit` param to `docs_search_response`, `code_search_response`, and their tool handlers
- Add `limit` + `has_more` to `wave_list_waves_response`, `wave_list_plans_response`, and their handlers
- Add dry-run support to `wave_garden_response` and `wave_sync_surfaces_response`
- Rename `FastMCP("wavefoundry")` → `FastMCP("wavefoundry_mcp")`
- Update `_response()` to set `"isError": True` when `status == "error"`
- Change `kind: str` to `kind: Literal[...]` on `docs_search`
- Prefix `wave_new_*` docstrings with compatibility note
- Add `Args:` to thin docstrings
- Add `**kwargs` explanation comment
- Run tests + docs-lint

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| annotations | implementer | — | Apply to all tools after defining helper dicts |
| search-limit | implementer | — | `docs_search`, `code_search` |
| list-limit | implementer | — | `wave_list_waves`, `wave_list_plans` |
| garden-dry-run | implementer | — | `wave_garden`, `wave_sync_surfaces` |
| envelope-isError | implementer | — | `_response()` helper |
| doc-polish | implementer | — | docstrings, comments, rename |
| verification | implementer | all above | tests + docs-lint |

## Serialization Points

- All changes are in `server.py`; implement in a single sequential pass.

## Affected Architecture Docs

N/A — MCP surface polish. `docs/specs/mcp-tool-surface.md` should eventually document the annotation contract; deferred to follow-on spec update.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Client compatibility for read-only/mutating/destructive distinction |
| AC-2 | required | Workflow gap — hardcoded 5 results too restrictive |
| AC-3 | required | Consistent with AC-2 |
| AC-4 | important | List tools return unbounded results |
| AC-5 | important | Mutating tool contract compliance |
| AC-6 | important | MCP naming convention compliance |
| AC-7 | important | Protocol-level error signalling |
| AC-8 | nice-to-have | Client enum schema generation |
| AC-9 | nice-to-have | Agent discoverability via list_tools |
| AC-10 | nice-to-have | Docstring completeness |
| AC-11 | nice-to-have | Future-dev explanation for **kwargs pattern |
| AC-12 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-04-30 | Created from mcp-builder design review | Review output in session |
| 2026-04-30 | All 12 ACs implemented and verified | 305 tests pass; docs-lint clean |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-04-30 | Use limit+has_more rather than full offset pagination | Sufficient for current scale; offset pagination is a larger change | Full pagination (deferred) |
| 2026-04-30 | Clamp limit to 1–20 for search | Prevents runaway embedding calls; consistent with default top_n=5 | Unclamped (rejected: too open-ended) |

## Risks

| Risk | Mitigation |
|------|-----------|
| FastMCP annotation API varies by SDK version | Annotations are passed as a dict; ignored silently on older versions |
| `isError` field might confuse existing callers checking `status` | Both fields are set; existing `status` checks continue to work |
| Renaming server breaks existing MCP config references | Low risk — stdio transport; client configs reference the binary path, not the server name |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.