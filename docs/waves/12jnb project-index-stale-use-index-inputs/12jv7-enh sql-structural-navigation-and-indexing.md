# SQL Structural Navigation and Indexing

Change ID: `12jv7-enh sql-structural-navigation-and-indexing`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

SQL files are currently chunked with a regex-based SQL chunker, but they are not part of the structural navigation path used by `code_definition` and `code_references`. The repo already has a permissive tree-sitter SQL grammar available upstream, so SQL can likely be upgraded from regex-only chunking to structural indexing and symbol navigation without changing the broad retrieval contract for other languages.

## Requirements

1. SQL files should participate in structural chunking when a tree-sitter SQL grammar is available.
2. SQL definitions and references should use structural parsing where possible, not just regex or plain text matching.
3. SQL should still fall back safely to the existing regex chunker or text navigation when structural parsing is unavailable.
4. The existing broad `code_definition` / `code_references` behavior must remain intact for all other languages.

## Scope

**Problem statement:** SQL is indexed, but not structurally navigable. That leaves schema and script-heavy repos with weaker symbol lookup than Java/TS/Java/C#.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Rewriting the semantic index format
- Removing the existing regex SQL fallback
- Changing the non-SQL navigation contract

## Acceptance Criteria

- SQL files are chunked structurally when the grammar is present, with a documented fallback when it is not.
- `code_definition` can resolve SQL symbols with structural support where possible.
- `code_references` can surface SQL usages with the same broad evidence-complete contract used by other languages.
- Tests cover at least one SQL DDL symbol and one SQL usage/reference case.

## Tasks

- Wire tree-sitter SQL into the chunker/navigation stack
- Add SQL-aware definition/reference handling
- Add tests for structured SQL chunking and symbol lookup

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Structural chunking is the core improvement |
| AC-2 | required | SQL symbol resolution is the user-visible benefit |
| AC-3 | required | Broad fallback must remain available for safety |
| AC-4 | required | Tests prevent regressions in mixed repos |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Tree-sitter SQL grammar coverage differs by dialect | Keep the regex chunker and text fallback available |
| SQL symbol semantics vary across dialects | Start with conservative structural buckets and widen only with tests |
| Navigation becomes too noisy for query-heavy repos | Preserve the broad response and order structural matches ahead of lower-signal matches |
