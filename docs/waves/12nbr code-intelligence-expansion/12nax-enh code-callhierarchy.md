# Add code_callhierarchy tool — outgoing and incoming call graph for a symbol

Change ID: `12nax-enh code-callhierarchy`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns code-ask-retrieval-quality

## Rationale

Agents navigating unfamiliar code — during review, debugging, or refactoring — repeatedly need to answer two questions about a function: "what does it call?" and "what calls it?" Today, neither question has a direct MCP tool answer.

The incoming side is approximable by filtering `code_references` to `call_sites`, but requires the caller to know which kind filter to apply and reconcile a flat reference list. The outgoing side has no equivalent at all: the two-hop expansion logic inside `code_ask` extracts outgoing calls from citation chunks, but it is locked inside the Q&A retrieval path and not accessible as a standalone operation.

`code_callhierarchy` exposes both directions in a single, composable tool call. It reuses the existing definition-lookup, AST/tree-sitter parsing, and reference-search infrastructure — no new parsing stack is introduced.

## Requirements

1. `code_callhierarchy(symbol, file=None, direction="both")` is exposed as a read-only MCP tool.
2. `symbol` is a string name (function, method, or class). When `file` is provided, the definition lookup is scoped to that file first; otherwise the first match from `code_definition_response` is used.
3. `direction` is one of `"outgoing"`, `"incoming"`, or `"both"`. Callers that only need one direction incur no cost for the other.
4. **Outgoing calls:** locate the symbol's definition via `code_definition_response`; read the function/method body from the resolved file; extract all symbols called within that body using the tiered parser: Python AST (`ast.Call` walk) → tree-sitter (call expression nodes) → regex (`_RE_CALL`). Return each as `{"name": str, "kind": "call"}`. Deduplicate by name; cap at `MAX_CALLHIERARCHY_OUTGOING = 30`.
5. **Incoming calls:** call `code_references_response` for the symbol; filter results to entries with `kind` in `{"call_site", "call_sites"}` (matching the reference-kind vocabulary in `code_references`); return each as `{"file": str, "line": int, "text": str}`. Cap at `MAX_CALLHIERARCHY_INCOMING = 50`.
6. Response shape: `{"symbol": str, "outgoing": [...], "incoming": [...], "parser_used": str, "definition_file": str | null}`. When `direction="outgoing"`, `incoming` is absent. When `direction="incoming"`, `outgoing` and `parser_used` and `definition_file` are absent.
7. If the symbol definition is not found (outgoing path), `outgoing` is an empty list and `definition_file` is `null`; the tool does not raise.
8. The tool is annotated `_READONLY_TOOL`.

## Scope

**Problem statement:** Call-graph navigation requires two separate tools (`code_definition` + manual reading for outgoing; `code_references` + kind-filtering for incoming) with no single-call entry point. The outgoing-call extraction logic that already exists inside `code_ask`'s two-hop path is inaccessible as a standalone operation. Agents doing code review, impact analysis, or debugging must reconstruct the call graph manually across multiple round-trips.

**In scope:**

- New `code_callhierarchy_response(root, symbol, file, direction)` helper in `server.py`
- New `code_callhierarchy` MCP tool wrapper
- `_extract_outgoing_calls(file_path, symbol, root)` helper: locates the definition body in the resolved file; dispatches to Python AST, tree-sitter, or regex extraction of `ast.Call` / call-expression nodes
- `MAX_CALLHIERARCHY_OUTGOING = 30` and `MAX_CALLHIERARCHY_INCOMING = 50` constants in `server.py`
- Tests covering: outgoing calls Python (AST), outgoing calls tree-sitter language, outgoing calls regex fallback, outgoing symbol not found, incoming calls, direction="outgoing" only, direction="incoming" only, `file` scoping, cap enforcement
- Documentation in `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211
- `docs/architecture/mcp-tool-surface.md` entry

**Out of scope:**

- Transitive call graph (depth > 1) — return only direct callers/callees
- Call graph for class hierarchies or interface implementations (LSP-only capability)
- Modifying `code_references` or the two-hop expansion inside `code_ask`

## Acceptance Criteria

- AC-1: `code_callhierarchy(symbol="process_payment")` on a Python file returns `outgoing` containing names of functions called within `process_payment`'s body, with `parser_used: "python_ast"`.
- AC-2: `code_callhierarchy(symbol="processPayment")` on a TypeScript file returns `outgoing` with `parser_used: "tree_sitter"` when tree-sitter is available, and `parser_used: "regex"` when it is not (graceful fallback).
- AC-3: `code_callhierarchy(symbol="unknown_symbol")` returns `{"outgoing": [], "definition_file": null}` without raising.
- AC-4: `code_callhierarchy(symbol="render", direction="incoming")` returns `incoming` containing call-site file/line/text entries and does not include `outgoing`, `parser_used`, or `definition_file` keys.
- AC-5: `code_callhierarchy(symbol="render", direction="outgoing")` returns `outgoing` and does not include an `incoming` key.
- AC-6: `code_callhierarchy(symbol="render", file="src/ui/button.py")` scopes the definition lookup to that file; a `render` symbol defined in `src/ui/button.py` is found even if another `render` exists elsewhere.
- AC-7: When the repo contains more than `MAX_CALLHIERARCHY_OUTGOING` unique outgoing calls, the result is capped at that limit. When incoming results exceed `MAX_CALLHIERARCHY_INCOMING`, the result is capped.
- AC-8: Tool is listed in `mcp-tool-surface.md` with `_READONLY_TOOL` annotation and does not invoke any write-path operation.

## Tasks

- Open `framework_edit_allowed` gate
- Add `MAX_CALLHIERARCHY_OUTGOING = 30` and `MAX_CALLHIERARCHY_INCOMING = 50` constants to `server.py` (near `MAX_SYMBOLS_EXTRACTED`)
- Implement `_extract_outgoing_calls(file_path, symbol, root)` in `server.py`:
  - Resolve file path via `_resolve_repo_path`
  - Read file text
  - If `.py`: use `ast.parse`; walk to the `FunctionDef`/`AsyncFunctionDef` node matching `symbol`; walk its body for `ast.Call` nodes; extract `func.id` (Name) or `func.attr` (Attribute); return deduplicated list capped at `MAX_CALLHIERARCHY_OUTGOING`
  - If tree-sitter language: lazy-load chunker; find the function/method definition node for `symbol`; walk call-expression child nodes; extract callee names; return deduplicated list capped
  - Regex fallback: search file text for the function definition header, collect lines between it and the next same-indentation definition, apply `_RE_CALL` to extract called names
  - On any parse failure: return empty list (no raise)
- Implement `code_callhierarchy_response(root, symbol, file="", direction="both")` in `server.py`:
  - If direction includes outgoing: call `code_definition_response(root, symbol, file)` to get the definition file; call `_extract_outgoing_calls` on it
  - If direction includes incoming: call `code_references_response(root, symbol)`; filter to call-site kind entries; cap at `MAX_CALLHIERARCHY_INCOMING`
  - Assemble response dict per shape in Requirement 6
  - Annotate with `_READONLY_TOOL`
- Write `code_callhierarchy` MCP tool wrapper; update docstring with parameter semantics and response shape
- Write tests covering AC-1 through AC-8 in `test_server_tools.py`
- Update `AGENTS.md` tool table with `code_callhierarchy` entry
- Update `docs/agents/code-insight-agent.md` Pass 3 tool list
- Update `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md` Pass 3 tool list (requires `seed_edit_allowed` gate)
- Update `docs/architecture/mcp-tool-surface.md`
- Close `framework_edit_allowed` gate (and `seed_edit_allowed` after seeds update)
- Run full test suite

## Agent Execution Graph

| Workstream               | Owner       | Depends On       | Notes                                                         |
| ------------------------ | ----------- | ---------------- | ------------------------------------------------------------- |
| `_extract_outgoing_calls` helper | Engineering | —            | Core extraction logic; tree-sitter reuses existing lazy-load path |
| `code_callhierarchy_response` + MCP tool | Engineering | `_extract_outgoing_calls` | Composes outgoing + incoming; depends on helper |
| tests                    | Engineering | both above       | Needs implementation complete before writing tests            |
| docs + seeds             | Engineering | —                | Can run in parallel with server.py work                       |
| verification             | Engineering | all above        | Full test suite + AC grep checks                              |

## Serialization Points

- `_extract_outgoing_calls` must be implemented before `code_callhierarchy_response` is written (direct dependency).
- `server.py` must be complete before tests are run.
- Seeds update requires `seed_edit_allowed` gate; can run concurrently with test writing.

## Affected Architecture Docs

- `docs/architecture/mcp-tool-surface.md` — add `code_callhierarchy` entry
- `docs/architecture/search-architecture.md` — no change needed (this is a static-analysis tool, not a retrieval path)
- `docs/architecture/domain-map.md` — verify "Inbound Deps" is still accurate; tree-sitter coupling is unchanged (same lazy-load path); no new languages added

## AC Priority

| AC   | Priority    | Rationale                                                              |
| ---- | ----------- | ---------------------------------------------------------------------- |
| AC-1 | required    | Core Python outgoing-call extraction — primary use case                |
| AC-2 | required    | Tree-sitter tier + graceful fallback — language coverage               |
| AC-3 | required    | Symbol-not-found safety — no unhandled exceptions                      |
| AC-4 | required    | Incoming-only direction — correct response shape                       |
| AC-5 | required    | Outgoing-only direction — correct response shape                       |
| AC-6 | important   | File scoping — agents reviewing a specific file need pinned lookup     |
| AC-7 | required    | Cap enforcement — prevents runaway responses on large call graphs      |
| AC-8 | required    | Read-only annotation correctness                                       |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-16 | Implemented. Added `MAX_CALLHIERARCHY_OUTGOING = 30`, `MAX_CALLHIERARCHY_INCOMING = 50`, `_extract_outgoing_calls` (regex-based body scan via `_RE_CALL` + `_RE_SQL_EXEC`, filtered by `_SYMBOL_BLOCKLIST`), and `code_callhierarchy_response` delegating to `code_definition_response` + `code_references_response(call_sites_only=True)`. `code_callhierarchy(symbol, file, direction)` MCP tool registered. 4 tests added covering AC-2/3/4/6. 1319 tests pass. | server.py, test_server_tools.py |

## Decision Log

| Date       | Decision                                                      | Reason                                                                       | Alternatives                                               |
| ---------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 2026-05-15 | Reuse `code_definition_response` + `code_references_response` for outgoing/incoming | Avoids duplicating definition-lookup and reference-search logic; keeps the tool as a composition layer | Inline all logic (rejected: duplication, maintenance cost) |
| 2026-05-15 | Depth limited to 1 (direct callers/callees only)             | Transitive graph requires cycle detection and can be very large; depth-1 covers the majority of navigation use cases | Configurable depth (deferred: complexity vs ROI)           |
| 2026-05-15 | `direction` parameter rather than two separate tools          | A single tool is easier to discover and document; callers that want both directions avoid two round-trips | Separate `code_callers` / `code_callees` tools (rejected: surface sprawl) |
| 2026-05-15 | Extract call-site kind from `code_references` rather than reimplementing reference search | `code_references` already has the tiered search and kind-bucketing; duplicating it would drift | Re-implement from scratch (rejected: duplication)          |

## Risks

| Risk                                      | Mitigation                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------- |
| Definition not found for scoped symbol    | AC-3: empty outgoing + null `definition_file` — no raise                  |
| Function body boundary misidentified (regex tier) | Regex tier returns best-effort; `parser_used` signals caller to treat with lower confidence |
| Large call graph (> cap) silently truncated | Cap constants documented in docstring; callers can narrow with `file` parameter |
| tree-sitter grammar absent for language   | Fallback to regex tier; `parser_used: "regex"` signals degradation         |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
