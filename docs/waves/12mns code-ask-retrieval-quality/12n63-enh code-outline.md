# Add code_outline tool — live structural view of a source file

Change ID: `12n63-enh code-outline`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns

## Rationale

Agents navigating an unfamiliar file today must either read the entire file or run `code_definition` one symbol at a time. Neither is efficient for orientation. `code_outline` provides a structured symbol map of a source file — functions, classes, and top-level constants with line ranges and (where available) docstrings — without reading full implementations. This is the missing "get the shape of this file" tool.

## Requirements

1. `code_outline(path)` is exposed as a read-only MCP tool.
2. `path` is resolved and confined to the project root via `_resolve_repo_path` (or equivalent); paths escaping the root are rejected.
3. The tool returns a `symbols` list. Each entry contains: `name`, `kind` (`function` | `class` | `method` | `constant`), `start_line`, `end_line`, and `docstring` (first docstring or comment line immediately following the definition header, or `null` if absent).
4. Parsing is tiered:
   - **Tier 1 — Python AST**: used for `.py` files via `ast.parse`. Extracts functions, classes, async functions, and module-level assignments (constants).
   - **Tier 2 — tree-sitter**: used for JS/TS/Java/C#/Go/Rust/C/C++/Kotlin/Bash/SQL via the same 11-language stack as two-hop expansion (`_TS_SYMBOL_LANG_MAP`). Extracts function and class definitions.
   - **Tier 3 — regex fallback**: for all other file types; extracts lines matching common definition patterns (`def `, `class `, `function `, `func `, `fn `, `pub fn`, `sub `). Returns name and start_line only; `end_line` and `docstring` are `null`.
5. If the file cannot be parsed (binary, unreadable), the tool returns `{"error": "unparseable", "detail": "..."}` rather than raising.
6. The tool is annotated `_READONLY_TOOL`.
7. The response includes `parser_used`: one of `python_ast`, `tree_sitter`, or `regex`.

## Scope

**Problem statement:** No MCP tool gives agents a structural overview of a file. Agents read full files or make repeated single-symbol `code_definition` calls to understand file shape. `code_outline` provides this in a single call.

**In scope:**

- New `code_outline` function in `server.py`
- Tiered parser: Python AST → tree-sitter (11 languages) → regex fallback
- Symbol kinds: `function`, `class`, `method`, `constant` (Python AST and tree-sitter); `function` and `class` for regex tier
- `docstring` field: first `ast.get_docstring()` result for Python; first string-literal child of function/class body for tree-sitter; `null` for regex tier
- `parser_used` field in response
- Tests covering: Python file (AST tier), a tree-sitter language file, an unknown-extension file (regex tier), binary/unreadable file (error response), path escape rejection
- Documentation in `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211

**Out of scope:**

- Full implementation body extraction (return line range only)
- Import or dependency extraction
- Nested class/function nesting depth beyond top-level + class methods

## Acceptance Criteria

- AC-1: `code_outline(path="server.py")` returns a `symbols` list with correct `name`, `kind`, `start_line`, `end_line`, and `docstring` for Python functions/classes, and `parser_used: "python_ast"`.
- AC-2: `code_outline` on a `.ts` or `.go` file returns symbols via tree-sitter with `parser_used: "tree_sitter"`.
- AC-3: `code_outline` on a `.sh` or unknown-extension file returns symbols via regex fallback with `parser_used: "regex"` and `end_line: null`, `docstring: null`.
- AC-4: `code_outline` on a binary file returns `{"error": "unparseable", ...}` without raising.
- AC-5: A path escaping the project root is rejected (error response or empty symbols).
- AC-6: Tool is listed in MCP tool surface with `_READONLY_TOOL` annotation and does not invoke any write-path operation.
- AC-7: `docstring` field is populated for Python functions/classes that have a docstring; `null` for those that do not.
- AC-8: `code_outline` on a Python file containing a class with methods returns those methods as entries with `kind: "method"` (not `kind: "function"`) and correct `start_line`/`end_line`.
- AC-9: `code_outline` on a Python file containing module-level assignments (e.g. `FOO = 42`, `BAR: int = 7`) returns those as entries with `kind: "constant"` and correct `start_line`.

## Tasks

- Open `framework_edit_allowed` gate
- Implement `code_outline` in `server.py`:
  - Accept `path: str`
  - Resolve and confine via `_resolve_repo_path`
  - Dispatch to tiered parser based on file extension
  - Python AST tier: `ast.parse`, walk `ast.FunctionDef`, `ast.AsyncFunctionDef`, `ast.ClassDef`, module-level `ast.Assign` with simple name targets
  - Tree-sitter tier: lazy-load via `_get_chunker_module`; use `_TS_SYMBOL_LANG_MAP` for dispatch; query function/class definition nodes; extract start/end lines
  - Regex tier: line-by-line scan for common definition patterns; return start_line only
  - Wrap entire parse in try/except; on failure return `{"error": "unparseable", "detail": str(e)}`
  - Return `{"symbols": [...], "parser_used": str, "file": str}`
  - Annotate with `_READONLY_TOOL`
- Write tests covering AC-1 through AC-7
- Update `AGENTS.md` tool table with `code_outline` entry
- Update `docs/agents/code-insight-agent.md` Pass 3 tool list
- Update `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md` Pass 3 tool list
- Update `docs/architecture/mcp-tool-surface.md`
- Close `framework_edit_allowed` gate
- Run full test suite

## Agent Execution Graph

| Workstream              | Owner       | Depends On   | Notes                                             |
| ----------------------- | ----------- | ------------ | ------------------------------------------------- |
| server.py implementation| Engineering | —            | Open gate before; close after; tree-sitter reuses existing lazy-load path |
| tests                   | Engineering | server.py    | After implementation; needs test fixtures for each tier |
| docs + seeds updates    | Engineering | —            | Can run in parallel with server.py                |
| verification            | Engineering | all above    | Full test suite pass required                     |

## Serialization Points

- `server.py` implementation must be complete before tests run.
- Tree-sitter tier reuses `_get_chunker_module` and `_TS_SYMBOL_LANG_MAP` — no new coupling introduced; verify domain-map.md "Inbound Deps" is still accurate after implementation.

## Affected Architecture Docs

- `docs/architecture/mcp-tool-surface.md` — add `code_outline` entry
- `docs/architecture/domain-map.md` — verify MCP Server "Inbound Deps" still accurately describes tree-sitter coupling after `code_outline` reuses the same lazy-load path (no new languages added, so update is likely N/A — confirm at implementation time)
- `docs/architecture/search-architecture.md` — no change needed (outline is not a retrieval path)

## AC Priority

| AC   | Priority    | Rationale                                                  |
| ---- | ----------- | ---------------------------------------------------------- |
| AC-1 | required    | Core Python AST tier correctness                           |
| AC-2 | required    | Tree-sitter tier correctness                               |
| AC-3 | required    | Regex fallback tier — graceful degradation                 |
| AC-4 | required    | Error safety — no unhandled exceptions                     |
| AC-5 | required    | Security — path confinement                                |
| AC-6 | required    | Read-only annotation correctness                           |
| AC-7 | important   | Docstring quality; regex tier cannot provide this (null OK) |
| AC-8 | required    | `method` kind is a distinct behavior from `function`; must be verified |
| AC-9 | required    | `constant` kind is specified in Requirements 3 and 4; must have AC coverage |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-15 | Implemented: `code_outline_response` with tiered parser (Python AST → tree-sitter → regex); `_outline_python`, `_outline_treesitter`, `_outline_regex_tier` helpers; 10 tests added covering AC-1 through AC-9; 1299 tests pass | `run_tests.py` → 1299 OK |

## Decision Log

| Date       | Decision                                                  | Reason                                                              | Alternatives                                  |
| ---------- | --------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| 2026-05-15 | Tiered parser: AST → tree-sitter → regex                  | Maximizes accuracy for known languages; never fails on unknown types | Single tier only (too narrow or too noisy)    |
| 2026-05-15 | Reuse `_TS_SYMBOL_LANG_MAP` / `_get_chunker_module`       | No new coupling; keeps tree-sitter stack in one place               | Separate parser init (adds coupling)          |
| 2026-05-15 | Top-level + class methods only; no deep nesting           | Sufficient for orientation; deep nesting adds complexity for low ROI | Full recursive nesting (deferred)             |
| 2026-05-15 | `parser_used` field in response                           | Helps agents understand confidence level of the outline             | Omit (rejected: harder to debug)             |

## Risks

| Risk                                    | Mitigation                                                          |
| --------------------------------------- | ------------------------------------------------------------------- |
| Large file AST parse latency            | Python AST is fast; tree-sitter is incremental — acceptable         |
| Binary file passed to AST parser        | try/except at top level returns error response; AC-4                |
| tree-sitter grammar missing for language| Fallback to regex tier; `parser_used: "regex"` signals degradation  |
| Path escape via crafted path argument   | `_resolve_repo_path` confinement check before any file read         |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
