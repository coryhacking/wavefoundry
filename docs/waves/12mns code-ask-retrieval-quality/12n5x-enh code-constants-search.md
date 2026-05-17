# `code_constants` — Batch Constant Value Lookup

Change ID: `12n5x-enh code-constants-search`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: `12mns code-ask-retrieval-quality`

## Rationale

Agents reviewing or documenting retrieval behavior frequently need the current values of named constants — `VECTOR_TOP_K`, `MAX_SYMBOLS_EXTRACTED`, `RRF_NAVIGATIONAL_CODE_WEIGHT`, etc. — to write accurate documentation or verify behavior. No existing MCP tool answers this directly: `code_definition` finds function and class declarations, `code_keyword` returns raw line matches without value parsing, and `code_ask` is semantic routing, not a constant lookup.

The result is that agents reach for raw shell `grep`, which bypasses the MCP surface entirely. A dedicated `code_constants` tool closes this gap: given a list of symbol names and an optional glob scope, it returns each symbol's current value, file, and line — parsed from the assignment statement, not inferred.

Two-hop symbol expansion (`12n0e`) makes this pattern more frequent: after a retrieval pass surfaces new symbol names, agents immediately need to know whether those symbols are tuning constants and what their values are.

## Requirements

1. `code_constants(symbols: list[str], glob: str = "")` searches for module-level constant assignments matching each name in `symbols`. A constant assignment is a line of the form `NAME = <value>` (or `NAME: type = <value>`) at the start of a line (no leading indent), optionally preceded by a comment.
2. For each symbol, the tool returns: `name`, `value` (the right-hand side of the assignment, as a string, trimmed), `file` (repo-relative path), `line` (1-based), and `kind` (`"scalar"` for single-line values, `"multiline"` for values that continue across lines — frozenset, list, dict literals).
3. For multiline values (`frozenset({...})`, `[...]`, `{...}` that span lines), the tool collects continuation lines until the bracket depth returns to zero, and returns the full value string.
4. When a symbol is not found, its entry in the result list has `value: null` and `file: null` — it is included in the result so callers know the lookup was attempted.
5. The `glob` parameter scopes the search to matching file paths (same semantics as `code_keyword` glob). When omitted, the entire indexed repository is searched.
6. Results are ordered to match the input `symbols` list order, not discovery order.
7. The tool is read-only (`_READONLY_TOOL` annotation) and must not modify any file.

## Scope

**Problem statement:** Agents and documenters need the current values of named constants to write accurate docs, verify retrieval behavior, and understand tuning parameters. Today this requires either raw `grep` (bypassing MCP) or multiple `code_keyword` calls with manual value parsing. Neither is suitable for agentic use — grep is not an MCP tool, and keyword search returns raw lines that include the symbol name, `=`, and value mixed together without structure.

**In scope:**

- New `code_constants_response()` helper in `server.py`
- New `code_constants` MCP tool (read-only, `_READONLY_TOOL`)
- Single-line scalar detection: integers, floats, strings, booleans, `None`
- Multiline container detection: `frozenset({...})`, `[...]`, `{...}` — collect until bracket depth = 0
- Tests in `test_server_tools.py`
- `docs/specs/mcp-tool-surface.md` update

**Out of scope:**

- Expression evaluation or type inference (value is returned as a raw string, not parsed into a Python object)
- Class attributes or instance variables (only module-level `NAME = ...` patterns)
- Constants defined inside functions or conditionals
- Imported constants (only constants defined in the searched file, not re-exported names)
- Fuzzy or case-insensitive name matching

## Acceptance Criteria

- AC-1: `code_constants(symbols=["VECTOR_TOP_K", "MAX_SYMBOLS_EXTRACTED"])` returns both constants with their correct numeric values, file path (`server.py`), and line numbers.
- AC-2: A multiline constant (`_SYMBOL_BLOCKLIST = frozenset({...})` spanning multiple lines) is returned with the complete value string, not just the first line. A value that does not close within 50 continuation lines returns `kind: "multiline-truncated"` so callers can detect truncation.
- AC-3: A symbol not present in the codebase returns `{name: "UNKNOWN_CONST", value: null, file: null, line: null}` — not an error.
- AC-4: The `glob` parameter correctly scopes results: `code_constants(["VECTOR_TOP_K"], glob="**/server.py")` returns only matches from `server.py`; a glob that excludes `server.py` returns `value: null` for that symbol.
- AC-5: Results are returned in the same order as the input `symbols` list, regardless of which file or line each was found on.
- AC-6: The tool carries `_READONLY_TOOL` annotation and performs no file writes.
- AC-7: `test_server_tools.py` covers ACs 1–6.
- AC-8: When a symbol appears in multiple files without a `glob` scope, all matching file entries are returned (not just the first found). Test with a symbol defined in both `server.py` and a test file.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Core deliverable — scalar constant lookup |
| AC-2 | required  | Multiline constants (`frozenset`, `list`) are common in `server.py`; single-line only makes the tool unreliable |
| AC-3 | required  | Missing-symbol must not error — callers pass symbol lists without knowing in advance which exist |
| AC-4 | required  | Glob scoping is the primary way to restrict to a specific file |
| AC-5 | important | Ordered output simplifies callers that zip the result with the input list |
| AC-6 | required  | Read-only annotation is a security invariant for all search tools |
| AC-7 | required  | Tests required for all new MCP tools per wave watchpoint |
| AC-8 | important | Multi-file match is a documented behavior (Risks table); no AC coverage would let it go silently unimplemented |

## Tasks

- Implement `code_constants_response(root, symbols, glob)` in `server.py`: for each symbol, walk repo files (respecting glob and ignore rules), search for `^NAME\s*[:=]` lines, extract single-line or multiline value, return structured result
- Register `code_constants` as a FastMCP tool with `_READONLY_TOOL` annotation; write docstring with parameter and response field descriptions
- Write tests in `test_server_tools.py`: scalar lookup, multiline lookup, missing symbol, glob scoping, output order, read-only annotation
- Update `docs/specs/mcp-tool-surface.md` — add `code_constants` to Search and Retrieval table
- Update `AGENTS.md` — add `code_constants` to the exact-navigation tool group

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| `code_constants_response` helper | implementer | — | Core logic: file walk, pattern match, multiline collection |
| MCP tool registration | implementer | helper | FastMCP wrapper + docstring |
| Tests | implementer | MCP tool | `test_server_tools.py` |
| Docs update | implementer | tests passing | `mcp-tool-surface.md`, `AGENTS.md` |

## Serialization Points

- `server.py` — single implementation file; sequential workstream

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — new tool entry in Search and Retrieval. `AGENTS.md` — new tool in exact-navigation group alongside `code_keyword`. `docs/architecture/search-architecture.md` — add `code_constants` to the Layer 2 exact-navigation description (it is a deterministic filesystem tool, not semantic). `docs/architecture/domain-map.md` — no new boundary; tool reads repository files within the existing allowed-roots scope.

## Risks

| Risk | Mitigation |
|---|---|
| Multiline value collection runs past the end of a value (e.g. nested brackets in strings) | Track bracket depth with a simple counter; quoted string contents are not parsed — treat `"`, `'`, `` ` `` as opaque. Flag `kind: "multiline-truncated"` if depth doesn't close within 50 lines |
| False-positive matches on non-constant assignments (local variables that happen to be at column 0) | Pattern requires the name to appear at line start with no preceding indent; class bodies and function bodies have indentation in well-formatted Python |
| Symbol found in multiple files (e.g. `VECTOR_TOP_K` defined in both `server.py` and a test) | Return all matches when `glob` is not scoped; document that scoping with `glob` is the recommended pattern when a unique result is expected |

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-15 | Return value as raw string, not Python object | Avoids `eval()` security risk; callers can parse if needed |
| 2026-05-15 | Module-level only (no indented assignments) | Indented constants are not conventional; broadening scope increases false-positive risk |
| 2026-05-15 | Separate tool from `code_keyword` multi-query | Different return shape (structured value extraction vs. raw snippet); different use case (constant values vs. arbitrary pattern matches) |
| 2026-05-15 | Include not-found symbols in result with null value | Callers pass lists without pre-knowledge of which symbols exist; error-on-missing forces callers to guard every lookup |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-15 | Change doc created | Identified during documentation pass for two-hop symbol expansion: grep used to look up VECTOR_TOP_K and related constants instead of MCP tool |
| 2026-05-15 | Implemented: `_bracket_depth`, `code_constants_response`, `code_constants` MCP tool, 16 tests | `_bracket_depth` bug fixed (spurious `i += 1` inside inner sym loop caused line-skip); 1271 tests pass; docs updated: `AGENTS.md`, `mcp-tool-surface.md`, `search-architecture.md` |
