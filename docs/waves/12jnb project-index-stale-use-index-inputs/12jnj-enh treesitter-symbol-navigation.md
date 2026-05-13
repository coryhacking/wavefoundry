# MCP: Tree-Sitter Symbol Navigation For Java, C#, JavaScript, TypeScript

Change ID: `12jnj-enh treesitter-symbol-navigation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The MCP symbol-navigation layer now supports multi-language definitions and references, but the current non-Python implementation for Java, C#, JavaScript, and TypeScript still relies on structural regexes or text matching. Those languages already have tree-sitter parse support in the chunker, so the navigation layer should use the same parser infrastructure for better precision.

## Requirements

1. `code_definition` must use tree-sitter-backed navigation for Java, C#, JavaScript, and TypeScript when parser support is available.
2. `code_references` must use tree-sitter-backed identifier traversal for Java, C#, JavaScript, and TypeScript when parser support is available.
3. Existing Python behavior must remain intact.
4. Regex/text fallback must remain available when tree-sitter is unavailable or a language is outside this upgraded scope.
5. Live docs and tool descriptions must describe the stronger method split accurately.
6. Verification must cover the tree-sitter-backed languages.

## Scope

**Problem statement:** the navigation layer is leaving precision on the table for languages that already have tree-sitter parsing in the indexing layer.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
  - Add a safe chunker/tree-sitter loader for navigation
  - Use tree-sitter-backed definitions/references for Java, C#, JavaScript, and TypeScript
  - Preserve fallback behavior outside that scope
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
  - Add/update regressions for Java, C#, JavaScript, and TypeScript tree-sitter navigation
- `AGENTS.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/search-architecture.md`

**Out of scope:**

- Tree-sitter-backed navigation for every indexed language
- LSP-grade semantic reference resolution

## Acceptance Criteria

- AC-1: Java symbol definitions are returned from tree-sitter-backed navigation rather than regex fallback when parser support is available.
- AC-2: C# symbol definitions are returned from tree-sitter-backed navigation rather than regex fallback when parser support is available.
- AC-3: JavaScript/TypeScript symbol definitions are returned from tree-sitter-backed navigation rather than regex fallback when parser support is available.
- AC-4: Java, C#, JavaScript, and TypeScript references are returned from tree-sitter-backed navigation when parser support is available.
- AC-5: Python behavior remains intact and non-upgraded languages still have fallback paths.
- AC-6: Verification passes.

## Tasks

- Add chunker-backed tree-sitter loader in `server.py`
- Implement tree-sitter definitions/references for JS/TS/Java/C#
- Update tests and live docs
- Run framework verification and docs lint

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Requested precision upgrade |
| AC-2 | required | Requested precision upgrade |
| AC-3 | required | Requested precision upgrade |
| AC-4 | required | References should improve alongside definitions |
| AC-5 | required | Must not regress existing users |
| AC-6 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created to move Java, C#, JavaScript, and TypeScript symbol navigation onto the existing tree-sitter parser layer already used by the chunker. | `.wavefoundry/framework/scripts/chunker.py`; `.wavefoundry/framework/scripts/server.py` |
| 2026-05-12 | Implemented tree-sitter-backed definitions and references for Java, C#, JavaScript, and TypeScript, preserved Python behavior and fallback paths, and updated the live tool-contract docs. | `.wavefoundry/framework/scripts/server.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `AGENTS.md`; `docs/specs/mcp-tool-surface.md`; `docs/architecture/current-state.md`; `docs/architecture/data-and-control-flow.md`; `docs/architecture/search-architecture.md`; `docs/prompts/agents/code-insight-agent.prompt.md`; `python3 -B .wavefoundry/framework/scripts/run_tests.py`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Reuse the existing chunker tree-sitter loader/patterns for navigation rather than building a separate parser stack | Keeps parser behavior aligned between indexing and symbol navigation | Keep regex/text-only navigation for these languages (rejected: lower precision than the repo already supports) |

## Risks

| Risk | Mitigation |
|------|------------|
| Importing chunker from the server path could create dependency/load fragility | Use a cached local loader scoped to navigation and preserve regex/text fallbacks on failure |
| Tree-sitter identifier traversal may still include declarations/comments in references | Keep method provenance explicit and retain broad fallback as a safety net |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
