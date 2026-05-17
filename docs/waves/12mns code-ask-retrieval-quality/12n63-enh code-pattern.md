# Add code_pattern tool — regex pattern search across repository files

Change ID: `12n63-enh code-pattern`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns

## Rationale

`code_keyword` covers exact substring matching; `code_search` covers semantic similarity. There is no tool for structured pattern matching (regex). Agents reaching for grep-style pattern searches have no MCP-native option and fall back to raw `Bash` grep, which is path-unsafe and bypasses the allowed-roots confinement boundary. `code_pattern` fills this gap: regex search, glob-scoped, result-capped, read-only, confined to the project root.

## Requirements

1. `code_pattern(pattern, glob="**/*", max_results=50, ignore_case=False)` is exposed as a read-only MCP tool.
2. `pattern` is a Python `re`-compatible regex string. Invalid patterns return a structured error (not an exception trace).
3. The tool searches line-by-line across files matching `glob` within the project root. Each match returns the file path (relative to project root), line number, and the matched line text.
4. Results are capped at `max_results`. When the cap is hit, the response includes `truncated: true` and `total_matches_found` reflecting the full count found before truncation.
5. `ignore_case=True` applies `re.IGNORECASE`.
6. `pattern` is compiled via `re.compile()` — no shell interpolation at any stage.
7. All file access uses `_resolve_repo_path` (or equivalent confinement check) — no path escapes the project root.
8. The tool is annotated `_READONLY_TOOL`.

## Scope

**Problem statement:** Agents need regex-based pattern search confined to the project root. No such MCP tool exists; agents fall back to `Bash` grep, which is unconfined and path-unsafe.

**In scope:**

- New `code_pattern` function in `server.py`
- Registration as an MCP tool with `_READONLY_TOOL` annotation
- Input validation: invalid regex returns `{"error": "invalid_pattern", "detail": "<re error message>"}` rather than raising
- Result structure: `{"matches": [{"file": str, "line": int, "text": str}], "truncated": bool, "total_matches_found": int}`
- Tests covering: basic match, `ignore_case`, glob scoping, cap + truncation, invalid pattern error, path-escape rejection
- Documentation in `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211

**Out of scope:**

- Multi-line pattern matching (single-line per match only)
- Match highlighting or capture group extraction (return the full matched line)
- Replacing or editing matched content (read-only)

## Acceptance Criteria

- AC-1: `code_pattern(pattern="def .*search", glob="**/*.py")` returns matches with correct file, line, and text fields.
- AC-2: `code_pattern(pattern="[invalid", ...)` returns `{"error": "invalid_pattern", ...}` without raising.
- AC-3: `code_pattern(pattern="x", max_results=5)` with more than 5 matches returns exactly 5 results, `truncated: true`, and `total_matches_found` equal to the actual number of matches in the scanned files (not clamped to `max_results`).
- AC-4: `code_pattern(pattern="TODO", ignore_case=True)` matches `todo`, `TODO`, and `Todo`.
- AC-5: A path argument constructed to escape the project root (e.g., `glob="../../../etc/**"`) is rejected or returns no results outside root.
- AC-6: Tool is listed in MCP tool surface with `_READONLY_TOOL` annotation and does not invoke any write-path operation.
- AC-7: `code_pattern(pattern="x")` with no `glob` argument returns matches from files across multiple directories (default `glob="**/*"` is applied, not an empty/no-op glob).

## Tasks

- Open `framework_edit_allowed` gate
- Implement `code_pattern` in `server.py`:
  - Accept `pattern: str`, `glob: str = "**/*"`, `max_results: int = 50`, `ignore_case: bool = False`
  - Compile with `re.compile(pattern, re.IGNORECASE if ignore_case else 0)` inside try/except `re.error`
  - Walk files matching glob within confined root using `pathlib.Path.glob` or equivalent
  - Apply `_resolve_repo_path` confinement check per file before reading
  - Line-by-line search; collect matches up to `max_results + 1` to detect truncation
  - Return `{"matches": [...], "truncated": bool, "total_matches_found": int}`
  - Annotate with `_READONLY_TOOL`
- Write tests covering AC-1 through AC-6
- Update `AGENTS.md` tool table with `code_pattern` entry
- Update `docs/agents/code-insight-agent.md` Pass 3 tool list
- Update `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md` Pass 3 tool list
- Update `docs/architecture/mcp-tool-surface.md`
- Close `framework_edit_allowed` gate
- Run full test suite

## Agent Execution Graph

| Workstream              | Owner       | Depends On   | Notes                               |
| ----------------------- | ----------- | ------------ | ----------------------------------- |
| server.py implementation| Engineering | —            | Open gate before; close after       |
| tests                   | Engineering | server.py    | After implementation is in place    |
| docs + seeds updates    | Engineering | —            | Can run in parallel with server.py  |
| verification            | Engineering | all above    | Full test suite + AC grep check     |

## Serialization Points

- `server.py` implementation must be complete before tests are written and run.
- Docs updates are independent and can run in parallel.

## Affected Architecture Docs

- `docs/architecture/mcp-tool-surface.md` — add `code_pattern` entry
- `docs/architecture/search-architecture.md` — mention regex search tool in the tool-surface overview if present
- Security note: `re.escape()` is NOT required here because the user controls the pattern intentionally; the security requirement is that the pattern is never interpolated into shell commands (it is compiled via `re.compile` only).

## AC Priority

| AC   | Priority    | Rationale                                            |
| ---- | ----------- | ---------------------------------------------------- |
| AC-1 | required    | Core functionality                                   |
| AC-2 | required    | Error safety — no unhandled exceptions to callers    |
| AC-3 | required    | Cap + truncation contract                            |
| AC-4 | required    | `ignore_case` correctness                            |
| AC-5 | required    | Security — path confinement                          |
| AC-6 | required    | Read-only annotation correctness                     |
| AC-7 | required    | Default glob correctness — `**/*` must not silently become a no-op |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-15 | Implemented: `code_pattern_response` + MCP tool; 1 MB file size guard (ReDoS mitigation); 8 tests added covering AC-1 through AC-7; 1299 tests pass | `run_tests.py` → 1299 OK |

## Decision Log

| Date       | Decision                                             | Reason                                                       | Alternatives                              |
| ---------- | ---------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| 2026-05-15 | Single-line match only; no capture group extraction  | Keeps interface simple; full line text is sufficient context | Return capture groups (deferred to later) |
| 2026-05-15 | `re`-based (not ripgrep/subprocess)                 | Keeps tool pure-Python and confinement-safe; no shell paths  | subprocess ripgrep (rejected: unsafe)     |
| 2026-05-15 | `max_results=50` default cap                         | Matches `code_keyword` convention; prevents runaway responses | Higher cap (medium DoS risk)              |

## Risks

| Risk                               | Mitigation                                                          |
| ---------------------------------- | ------------------------------------------------------------------- |
| Catastrophic regex (ReDoS)         | `max_results + 1` cap terminates the scan loop; `re.search()` per-line is unbounded within a single line. Implementation must choose one of: (a) per-line timeout via `signal.alarm`, (b) `max_file_size_bytes` guard (skip files > 1 MB), or (c) explicit documentation that pathological patterns are caller-controlled risk with no server protection. One of these three must appear in the implementation before ship. |
| Path escape via crafted glob       | `_resolve_repo_path` confinement check on each file before read    |
| Large repo scan latency            | `max_results` hard cap; document that broad globs are slow         |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
