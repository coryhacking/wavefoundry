# MCP: Expand Symbol Navigation Beyond Python

Change ID: `12jnh-enh multi-language-code-navigation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

`code_search` already supports multi-language semantic retrieval across Python, Java, C#, JS/TS, Go, Rust, Kotlin, Swift, and additional code/config formats. By contrast, `code_definition` and `code_references` remain Python-first and fall back to generic keyword matching for other languages. That mismatch makes the symbol-navigation layer weaker than the retrieval layer and leaves the current tool descriptions more constrained than the broader indexing surface.

## Requirements

1. `code_definition` must support multi-language symbol lookup beyond Python.
2. `code_references` must support multi-language symbol lookup beyond Python.
3. Python behavior must remain intact.
4. Tool descriptions and current MCP docs must reflect the new supported scope accurately.
5. Verification must cover both preserved Python behavior and non-Python symbol lookup.

## Scope

**Problem statement:** the MCP symbol-navigation tools lag behind the multi-language code-search/indexing surface, forcing non-Python users into lower-precision fallback paths.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
  - Expand `code_definition` to language-aware multi-language symbol lookup
  - Expand `code_references` to cross-language reference lookup
  - Update tool docstrings and help guidance
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
  - Add regressions for Java/C#/other non-Python symbol lookup
- `AGENTS.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/search-architecture.md`
- `docs/prompts/agents/code-insight-agent.prompt.md`

**Out of scope:**

- Full LSP-grade semantic reference resolution for every language
- Historical wave/archive doc rewrites

## Acceptance Criteria

- AC-1: `code_definition("MyClass")` can return structured non-Python definitions for supported non-Python languages.
- AC-2: `code_references("MyClass")` can return structured non-Python references for supported non-Python languages.
- AC-3: Python definition/reference behavior remains intact.
- AC-4: Live MCP docs and tool descriptions no longer describe the tools as Python-only.
- AC-5: Verification passes.

## Tasks

- Add multi-language definition extraction to `code_definition`
- Add multi-language reference scanning to `code_references`
- Update tool docstrings and MCP contract docs
- Add regressions for Python + non-Python cases
- Run targeted tests and docs lint

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core requested capability expansion |
| AC-2 | required | `code_definition` and `code_references` should stay symmetric |
| AC-3 | required | Existing Python users must not regress |
| AC-4 | required | Tool descriptions are part of the MCP contract |
| AC-5 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created after reviewing the MCP tool surface and confirming `code_search` is multi-language while `code_definition` and `code_references` remain Python-first. | `.wavefoundry/framework/scripts/server.py`; `.wavefoundry/framework/scripts/chunker.py`; `docs/specs/mcp-tool-surface.md`; `AGENTS.md` |
| 2026-05-12 | Expanded symbol navigation beyond Python, updated live MCP tool descriptions/docs, and verified preserved Python plus Java/C#/TS/Go behavior. | `.wavefoundry/framework/scripts/server.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `python3 -B .wavefoundry/framework/scripts/run_tests.py`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Expand symbol navigation to the language-aware capability level already implied by the chunker/indexer surface | Keeps the symbol-navigation layer aligned with the existing multi-language code-search model | Leave symbol navigation Python-only and merely soften docs (rejected: does not solve the capability gap) |

## Risks

| Risk | Mitigation |
|------|------------|
| Regex-based non-Python definition matching is less precise than AST/LSP resolution | Keep Python AST behavior, label methods clearly, and preserve keyword fallback for unmatched languages |
| Expanding supported scope could overstate precision in docs | Describe the method split explicitly in tool docs and contract docs |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
