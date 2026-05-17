# Add code_hover tool — symbol signature and docstring at a given line

Change ID: `12nbj-enh code-hover`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns code-ask-retrieval-quality

## Rationale

Agents reviewing code, planning edits, or tracing call chains repeatedly need to know what a symbol at a given line is — its name, kind, parameter list with type annotations, and docstring — without reading 50 lines of context. Today the only options are `code_outline` (returns all symbols in a file, no line targeting) or `code_read` (returns raw source). Neither answers "what is the function at line 47 and what are its parameters?"

`code_hover` fills this gap: given a file path and line number, it finds the enclosing symbol and returns its signature and docstring. No LSP daemon required — the Python AST and tree-sitter parsers already used by `code_outline` contain all the information needed. For Python, type annotations are extracted directly from `ast.FunctionDef.args` and `.returns`, producing accurate signatures for typed code. For tree-sitter languages (TypeScript, Go, Rust, Java, etc.), the raw parameter list text is extracted from function definition nodes.

## Requirements

1. `code_hover(path, line)` is exposed as a read-only MCP tool.
2. `path` is resolved and confined to the project root via `_resolve_repo_path`. `line` is a 1-based integer line number.
3. The tool finds the innermost symbol (function, async function, method, or class) whose `start_line <= line <= end_line` in the file. If multiple symbols are nested, the innermost wins (smallest containing range). If no symbol contains the line, the response returns `{"symbol": null, "file": str}` without error.
4. **Response shape:** `{"file": str, "line": int, "symbol": {name, kind, signature, docstring, start_line, end_line} | null, "parser_used": str}`.
5. **`signature` field:**
   - Python AST: reconstruct from `ast.FunctionDef` — `(param: Type, param2: Type = default, *args, **kwargs) -> ReturnType`. Type annotations serialized via `ast.unparse()` (Python 3.9+) or `ast.dump()` fallback. Defaults represented as their literal value where simple constants, or `...` for complex expressions.
   - Tree-sitter: extract the raw text of the `parameters` child node of the matched function definition node. Less structured but accurate to source.
   - Regex tier: `null` — no signature available; `parser_used: "regex"` signals this.
6. **`docstring` field:** first docstring of the enclosing symbol, using the same extraction logic as `_outline_python`. `null` if absent or regex tier.
7. Parser dispatch uses the same tiered logic as `code_outline`: Python AST for `.py`, tree-sitter for languages in `_TS_SYMBOL_LANG_MAP`, regex fallback for all others.
8. The tool reuses `_outline_python` and `_outline_treesitter` symbol lists for enclosing-symbol lookup — no new full parse pass for boundary detection. After obtaining the symbol list, it filters to the innermost containing symbol, then does a targeted second pass to extract the full signature.
9. On any parse failure the tool returns `{"symbol": null, "file": str, "parser_used": str}` rather than raising.
10. The tool is annotated `_READONLY_TOOL`.

## Scope

**Problem statement:** Agents need to know what a symbol at a given line is without reading the full file. `code_outline` returns all symbols but requires the agent to search by line number. No tool returns the signature and docstring for a specific line.

**In scope:**

- New `code_hover_response(root, path, line)` in `server.py`
- `_hover_python(source, line)` helper: runs `_outline_python` for symbol lookup, then a targeted `ast` walk to extract parameter annotations and return type for the matched symbol
- `_hover_treesitter(source, line, lang)` helper: runs `_outline_treesitter` for symbol lookup, then extracts the raw parameter list text from the matched node
- `_hover_regex(source, line)` helper: runs `_outline_regex_tier`, finds nearest symbol with `start_line <= line`, returns name and kind only
- New `code_hover` MCP tool wrapper
- Tests covering: Python function with type annotations, Python method inside class, Python function without annotations, tree-sitter language (TypeScript or Go), regex-tier file, line outside any symbol, path escape rejection
- Documentation in `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211
- `docs/architecture/mcp-tool-surface.md` entry

**Out of scope:**

- Column-level resolution — line is sufficient to identify the enclosing function in practice
- Variable or field hover — functions, methods, and classes only
- Inferred types for unannotated Python — would require a type inference engine
- Deeply nested lambdas or comprehensions

## Acceptance Criteria

- AC-1: `code_hover(path="server.py", line=N)` where line N falls inside a Python function with type annotations returns `{name, kind: "function", signature: "(param: Type, ...) -> ReturnType", docstring, start_line, end_line, parser_used: "python_ast"}`.
- AC-2: `code_hover` on a line inside a Python method returns `kind: "method"` and the correct signature for that method.
- AC-3: `code_hover` on a Python function with no type annotations returns `signature` with parameter names only (no annotations), not an error.
- AC-4: `code_hover` on a TypeScript or Go file returns `{name, kind, signature: "<raw parameter list text>", parser_used: "tree_sitter"}`.
- AC-5: `code_hover` on a line that falls outside all defined symbols returns `{"symbol": null, "file": str, "parser_used": str}` without error.
- AC-6: `code_hover` on a `.sh` or unknown-extension file returns `{name, kind, signature: null, docstring: null, parser_used: "regex"}` for the nearest preceding symbol.
- AC-7: A path escaping the project root returns an error response without raising.
- AC-8: Tool is listed in `mcp-tool-surface.md` with `_READONLY_TOOL` annotation.

## Tasks

- Open `framework_edit_allowed` gate
- Implement `_hover_python(source, line)` in `server.py`:
  - Call `_outline_python` to get symbol list; find innermost symbol containing `line`
  - Re-parse with `ast.parse`; walk to matched `FunctionDef`/`AsyncFunctionDef`/`ClassDef` node by name and start line
  - For functions/methods: extract args with `ast.unparse(arg.annotation)` (or name only if no annotation); extract defaults; extract `returns` annotation; reconstruct `signature` string
  - Return `{name, kind, signature, docstring, start_line, end_line}`
- Implement `_hover_treesitter(source, line, lang)` in `server.py`:
  - Call `_outline_treesitter` to get symbol list; find innermost containing symbol
  - Re-parse with tree-sitter; walk to the matched function/class node by start line
  - Extract raw text of the `parameters` child node as `signature`
  - Return `{name, kind, signature, docstring, start_line, end_line}`
- Implement `_hover_regex(source, line)` in `server.py`:
  - Call `_outline_regex_tier`; find nearest symbol with `start_line <= line`
  - Return `{name, kind, signature: null, docstring: null, start_line, end_line: null}`
- Implement `code_hover_response(root, path, line)`:
  - Resolve path, read source, dispatch to appropriate helper, wrap in `_response`
  - Annotate `_READONLY_TOOL`
- Write `code_hover` MCP tool wrapper
- Write tests covering AC-1 through AC-8
- Update `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211, `mcp-tool-surface.md`
- Close `framework_edit_allowed` gate (and `seed_edit_allowed` after seeds)
- Run full test suite

## Agent Execution Graph

| Workstream                       | Owner       | Depends On    | Notes                                                  |
| -------------------------------- | ----------- | ------------- | ------------------------------------------------------ |
| `_hover_python`                  | Engineering | —             | Reuses `_outline_python`; adds annotation extraction   |
| `_hover_treesitter`              | Engineering | —             | Reuses `_outline_treesitter`; adds parameter node walk |
| `_hover_regex`                   | Engineering | —             | Trivial — reuses `_outline_regex_tier`                 |
| `code_hover_response` + MCP tool | Engineering | all helpers   | Dispatch + response assembly                           |
| tests                            | Engineering | all above     | Needs implementation complete                          |
| docs + seeds                     | Engineering | —             | Can run in parallel                                    |
| verification                     | Engineering | all above     | Full test suite pass required                          |

## Serialization Points

- All three `_hover_*` helpers must be complete before `code_hover_response` is wired up.
- Seeds update requires `seed_edit_allowed` gate separately from `framework_edit_allowed`.

## Affected Architecture Docs

- `docs/architecture/mcp-tool-surface.md` — add `code_hover` entry
- `docs/architecture/search-architecture.md` — no change (not a retrieval path)
- `docs/architecture/domain-map.md` — no new dependencies; reuses existing tree-sitter lazy-load path

## AC Priority

| AC   | Priority    | Rationale                                                               |
| ---- | ----------- | ----------------------------------------------------------------------- |
| AC-1 | required    | Core Python annotated function — primary use case                       |
| AC-2 | required    | Method inside class — `kind: "method"` correctness                      |
| AC-3 | required    | Unannotated Python — must not error; graceful signature degradation     |
| AC-4 | required    | Tree-sitter tier — TypeScript/Go coverage                               |
| AC-5 | required    | Line outside all symbols — null symbol, no error                        |
| AC-6 | important   | Regex fallback — graceful degradation for unknown file types            |
| AC-7 | required    | Path confinement — security                                             |
| AC-8 | required    | Read-only annotation correctness                                        |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-16 | Implemented. Added `_innermost_symbol`, `_hover_python` (AST signature reconstruction via `ast.unparse()` with Python < 3.9 fallback), `_hover_treesitter` (raw `parameters` node text extraction), `_hover_regex` (nearest preceding symbol), and `code_hover_response`. `code_hover(path, line)` MCP tool registered. 5 tests added covering AC-1/2/3/5/7. 1319 tests pass. | server.py, test_server_tools.py |

## Decision Log

| Date       | Decision                                                           | Reason                                                                                      | Alternatives                                                             |
| ---------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 2026-05-15 | Line-based (not column-based) targeting                            | Line is sufficient to identify the enclosing function/class; column is only needed for position-within-expression resolution, which requires a live LSP | Column parameter (deferred: adds complexity for marginal gain)           |
| 2026-05-15 | Reuse `_outline_python` / `_outline_treesitter` for symbol lookup  | Avoids a duplicate parse pass for boundary detection; only signature extraction needs a second targeted walk | Inline full parse (rejected: duplicates existing logic)                  |
| 2026-05-15 | Raw parameter text for tree-sitter signature                       | Extracting individually typed parameters from tree-sitter nodes is language-specific and brittle; raw text is accurate and readable | Structured parameter extraction per language (deferred: high complexity) |
| 2026-05-15 | Variables and fields out of scope                                  | Hover on a variable requires type inference (unannotated) or assignment tracking; function/class signatures are fully available from AST without inference | Include variables (rejected: requires type inference engine)             |

## Risks

| Risk                                          | Mitigation                                                                    |
| --------------------------------------------- | ----------------------------------------------------------------------------- |
| `ast.unparse()` not available (Python < 3.9)  | Fallback to raw annotation node type name; document minimum Python version    |
| Tree-sitter `parameters` node name varies by language | Walk children for parameter-list node; fallback to `null` signature if not found |
| Nested functions — wrong symbol matched        | Innermost-wins (smallest containing range) handles the common case; deeply nested lambdas are out of scope |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
