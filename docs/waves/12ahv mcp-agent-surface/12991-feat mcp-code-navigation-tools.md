# MCP Code Navigation Tools

Change ID: `12991-feat mcp-code-navigation-tools`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-29
Wave: `12ahv mcp-agent-surface`

## Rationale

Wavefoundry's MCP server has semantic docs/code search, but it does not yet expose the basic code-navigation operations agents need to stay inside the MCP interface: keyword search, file listing, ranged file reads, and symbol-oriented definition/reference lookup. Agents can fall back to shell tools such as `rg`, `sed`, and language-specific tooling, but that reintroduces ad hoc command discovery and weakens the MCP-first workflow.

## Requirements

1. Add lightweight MCP code-navigation tools:
  - `code_keyword_search(query, glob?)`
  - `code_read(path, start_line?, end_line?)`
  - `code_list_files(glob?)`
2. Keyword search must respect the target repository root and existing ignore/index exclusion rules.
3. File reads must reject paths outside the target root and return line-numbered text for requested ranges.
4. File listing must support a simple optional glob and exclude generated index/binary/cache paths.
5. Add symbol navigation as a second milestone:
  - `code_definition(symbol_or_path_position)`
  - `code_references(symbol_or_path_position)`
6. Definition/reference support must start with a deliberately small implementation path, such as Python AST support or an explicit adapter boundary for future tree-sitter/LSP integration.
7. Symbol tools must return clear "unsupported language" or "not found" responses rather than pretending full-language coverage.
8. Tests must cover root safety, ignore behavior, line ranges, keyword results, file listing, and representative symbol lookups.

## Scope

**Problem statement:** Agents need to navigate code through the Wavefoundry MCP server without dropping to shell commands for every exact lookup or file read. Semantic search is useful but insufficient for deterministic code review, implementation, and debugging.

**In scope:**

- Exact keyword search over repository files
- Safe file listing
- Safe ranged file reads
- Initial definition/reference tools with limited language coverage and explicit unsupported-language behavior
- Tests for code-navigation helpers and MCP tool registration
- Architecture and AGENTS.md updates describing the navigation surface

**Out of scope:**

- Full IDE-grade language intelligence for every language
- Remote indexing or hosted search
- Mutation/editing tools
- Replacing shell access entirely
- Replacing semantic `code_search`; these tools complement it

## Acceptance Criteria

- `code_keyword_search` returns deterministic path/line/snippet results for exact text queries.
- `code_read` returns line-numbered file content for full-file and bounded range reads.
- `code_list_files` returns repository-relative paths and supports an optional glob.
- All file-navigation tools reject absolute/path-traversal reads outside the target root.
- Tools respect hardcoded exclusions for `.git`, index directories, caches, binaries, and ignored files.
- `code_definition` works for at least one supported language or explicitly returns unsupported for others.
- `code_references` works for the same initial supported scope or explicitly returns unsupported for others.
- MCP tool registration tests include the new navigation tools.
- Architecture docs describe semantic search, exact search/read, and symbol navigation as separate layers.

## Tasks

- Inspect current `indexer.py` file-walk and ignore helpers for reuse in exact navigation.
- Add safe root-relative path normalization helper in `server.py`.
- Implement `code_list_files`.
- Implement `code_read` with optional `start_line` / `end_line`.
- Implement `code_keyword_search` with line-numbered snippets.
- Choose initial symbol-navigation backend and document its limits.
- Implement `code_definition` for the initial supported scope.
- Implement `code_references` for the initial supported scope.
- Add unit tests for helpers and MCP tool registration.
- Update AGENTS.md and architecture docs.
- Run framework tests and docs lint.

## Agent Execution Graph


| Workstream        | Owner       | Depends On                          | Notes                                                      |
| ----------------- | ----------- | ----------------------------------- | ---------------------------------------------------------- |
| exact-navigation  | implementer | —                                   | Keyword search, list files, read file/range                |
| symbol-navigation | implementer | exact-navigation                    | Definition/reference support with explicit language limits |
| tests             | implementer | exact-navigation, symbol-navigation | Root safety and tool registration are required             |
| docs              | implementer | exact-navigation                    | Explain semantic vs exact vs symbol navigation             |


## Serialization Points

- Tool names and response shapes should be settled before implementation because MCP clients may start depending on them.
- Symbol backend choice should be recorded before adding broad language claims.

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/domain-map.md` if code-navigation becomes a named MCP domain boundary.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale                                                          |
| ---- | --------- | ------------------------------------------------------------------ |
| AC-1 | required  | Exact keyword search is the practical first navigation gap         |
| AC-2 | required  | Ranged file reads are necessary for code review and implementation |
| AC-3 | required  | File listing is basic navigation substrate                         |
| AC-4 | required  | Root safety is part of the MCP safety model                        |
| AC-5 | required  | Ignore behavior prevents noisy and unsafe results                  |
| AC-6 | important | Definition lookup is valuable but can start with limited support   |
| AC-7 | important | References are useful but should not overclaim language coverage   |
| AC-8 | required  | Tool registration must be tested                                   |
| AC-9 | important | Architecture docs should explain the three navigation layers       |


## Progress Log


| Date       | Update                                                                        | Evidence                                             |
| ---------- | ----------------------------------------------------------------------------- | ---------------------------------------------------- |
| 2026-04-29 | Planned MCP code-navigation tools covering exact navigation and symbol lookup | `docs/plans/12991-feat mcp-code-navigation-tools.md` |
| 2026-05-01 | Implementation complete (both milestones). Exact navigation: `code_list_files`, `code_read`, `code_keyword_search` with root-safety, ignore-rule reuse, and line-numbered output. Symbol navigation: `code_definition` (Python AST), `code_references` (Python text-based), both with explicit unsupported-language responses and `code_keyword_search` fallback hints. 25 navigation tests added. `test_all_tools_registered` updated. AGENTS.md three-layer table added. Architecture docs (current-state.md, data-and-control-flow.md) updated. 369 tests pass. docs-lint clean. | `python3 .wavefoundry/framework/scripts/run_tests.py` → 369 OK; `.wavefoundry/bin/docs-lint` → ok |


## Decision Log


| Date       | Decision                                                                            | Reason                                                                                                                   | Alternatives                                                   |
| ---------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| 2026-04-29 | Keep exact navigation and symbol navigation in one feature with separate milestones | They share the same user-facing "codebase navigation" surface, but exact search/read can land before symbol intelligence | Split into two features; deferred unless scope grows too large |


## Risks


| Risk                                       | Mitigation                                                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| Symbol tools overpromise IDE-grade support | Start with explicit supported-language behavior and clear unsupported responses               |
| Exact search duplicates shell `rg` poorly  | Keep response shape deterministic and MCP-safe rather than trying to match every `rg` feature |
| Path handling creates root escape risk     | Centralize path normalization and add traversal tests                                         |
| File listing becomes noisy                 | Reuse indexer ignore/exclusion rules                                                          |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.