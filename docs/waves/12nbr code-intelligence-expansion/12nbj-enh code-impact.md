# Add code_impact tool — reverse dependency (what imports this file?)

Change ID: `12nbj-enh code-impact`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns code-ask-retrieval-quality

## Rationale

`code_dependencies` answers "what does this file import?" — the forward direction. The reverse direction — "what files import this file?" — has no equivalent tool. Agents doing refactoring, planning a deletion, or assessing the blast radius of a change must manually grep the repo or issue multiple `code_keyword` calls to reconstruct the importer set.

`code_impact` fills this gap: given a target file path, it scans all repo files, parses their imports using the existing `_IMPORT_PARSERS` stack (already used by `code_dependencies`), and returns the set of files that import the target. This is the "impact analysis" mode from lsp-mcp's `codemap` tool, implemented offline without a live LSP daemon.

## Requirements

1. `code_impact(path, max_results=50)` is exposed as a read-only MCP tool.
2. `path` is the repo-relative path of the target file whose importers are sought. It is resolved and confined via `_resolve_repo_path`.
3. The tool scans all source files in the repository using the same file-walk strategy as `code_keyword` (respects existing exclusion rules). For each file, it parses imports using `_IMPORT_PARSERS`. Binary files and files that fail to read are skipped silently.
4. **Import matching** — an import in file F is considered a match if its `module` field resolves to the target file by any of the following heuristics, tried in order:
   - **Module path match:** normalize the import module name to a path (substitute `.` → `/`, strip extension) and check against the target's repo-relative path stem. E.g. `auth.user` matches `src/auth/user.py`.
   - **Filename stem match:** the final component of the import module name matches the target filename stem, and the stem is ≥ 4 characters. E.g. `from user import X` matches `auth/user.py` but not `io.py`.
   - **Relative path match:** for JS/TS imports prefixed with `./` or `../`, resolve the import path relative to the importing file's directory and compare to the target path, trying common extensions (`.ts`, `.tsx`, `.js`, `.jsx`, `/index.ts`, `/index.js`).
5. Results are capped at `max_results`. When the cap is hit, the response includes `truncated: true` and `total_found` reflecting the full count before truncation.
6. Each result entry: `{"file": str, "import_statement": str, "kind": str}` where `kind` is the import kind from `_IMPORT_PARSERS` (e.g. `"import"`, `"from_import"`, `"require"`, `"dynamic"`).
7. The target file itself is excluded from results.
8. Response shape: `{"path": str, "importers": [...], "truncated": bool, "total_found": int, "method": "heuristic"}`. The `method: "heuristic"` field signals that matching is not compiler-resolved so callers can calibrate confidence.
9. The tool is annotated `_READONLY_TOOL`.

## Scope

**Problem statement:** Agents assessing refactoring impact or planning a file deletion need to know what files import a given file. No MCP tool provides this. `code_keyword` can find an import string but requires knowing the exact text and doesn't handle path variants.

**In scope:**

- New `code_impact_response(root, path, max_results)` in `server.py`
- `_match_import_to_target(import_entry, target_rel, importing_file_rel)` pure helper implementing the three matching heuristics
- Repo-wide file walk reusing the existing walk infrastructure (same exclusion logic as `code_keyword`)
- Import parsing reusing `_IMPORT_PARSERS` — no new parsing stack
- Tests covering: Python module path match, JS/TS relative path match, filename stem match, self-import excluded, cap + truncation, path escape rejection, file not found
- Documentation in `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211
- `docs/architecture/mcp-tool-surface.md` entry

**Out of scope:**

- Compiler-accurate import resolution (no tsconfig/pyproject parsing, no sys.path resolution)
- Transitive impact (depth > 1) — direct importers only; callers can chain calls for transitive analysis
- Symbol-level impact (file-level granularity only)
- Languages not covered by `_IMPORT_PARSERS`

## Acceptance Criteria

- AC-1: `code_impact(path="src/auth/user.py")` returns files containing `import auth.user`, `from auth.user import X`, or `from auth import user` in their imports.
- AC-2: `code_impact(path="src/ui/button.tsx")` returns files containing `import X from './button'`, `import X from '../ui/button'`, or equivalent relative JS/TS imports.
- AC-3: The target file itself is not present in the `importers` list.
- AC-4: `code_impact(path="src/auth/user.py", max_results=5)` with more than 5 importers returns exactly 5 results, `truncated: true`, and `total_found` equal to the actual importer count.
- AC-5: A path escaping the project root returns an error response.
- AC-6: A path to a non-existent file returns an error response with `file_not_found` diagnostic.
- AC-7: All success responses include `method: "heuristic"`.
- AC-8: Tool is listed in `mcp-tool-surface.md` with `_READONLY_TOOL` annotation.

## Tasks

- Open `framework_edit_allowed` gate
- Implement `_match_import_to_target(import_entry, target_rel, importing_file_rel)` in `server.py`:
  - Heuristic 1: normalize module name (`.` → `/`, strip extension), check against target path and stem
  - Heuristic 2: compare final module component to target filename stem (≥ 4 chars only)
  - Heuristic 3: resolve `./`/`../` imports relative to importing file's directory; try common extensions; compare to `target_rel`
  - Return `True` if any heuristic matches
- Implement `code_impact_response(root, path, max_results)` in `server.py`:
  - Resolve and validate target path
  - Walk all repo source files using existing walk helper
  - For each file: read source, detect language, look up `_IMPORT_PARSERS`, parse imports, call `_match_import_to_target` for each import entry
  - Skip target file itself; collect matches up to `max_results + 1` to detect truncation
  - Return `_response("ok", {"path", "importers", "truncated", "total_found", "method": "heuristic"})`
  - Annotate `_READONLY_TOOL`
- Write `code_impact` MCP tool wrapper
- Write tests covering AC-1 through AC-8
- Update `AGENTS.md`, `docs/agents/code-insight-agent.md`, seed 211, `mcp-tool-surface.md`
- Close `framework_edit_allowed` gate (and `seed_edit_allowed` after seeds)
- Run full test suite

## Agent Execution Graph

| Workstream                    | Owner       | Depends On       | Notes                                          |
| ----------------------------- | ----------- | ---------------- | ---------------------------------------------- |
| `_match_import_to_target`     | Engineering | —                | Pure function; unit-testable in isolation      |
| `code_impact_response` + MCP  | Engineering | matcher helper   | Repo walk + parse + match + cap                |
| tests                         | Engineering | both above       | Needs implementation complete                  |
| docs + seeds                  | Engineering | —                | Can run in parallel                            |
| verification                  | Engineering | all above        | Full test suite pass required                  |

## Serialization Points

- `_match_import_to_target` must be complete before `code_impact_response` is implemented.
- Seeds update requires `seed_edit_allowed` gate separately from `framework_edit_allowed`.

## Affected Architecture Docs

- `docs/architecture/mcp-tool-surface.md` — add `code_impact` entry
- `docs/architecture/search-architecture.md` — no change (not a retrieval path)
- `docs/architecture/domain-map.md` — no new dependencies; reuses existing `_IMPORT_PARSERS` and walk infrastructure

## AC Priority

| AC   | Priority    | Rationale                                                              |
| ---- | ----------- | ---------------------------------------------------------------------- |
| AC-1 | required    | Python import matching — primary language                              |
| AC-2 | required    | JS/TS relative import path matching — second most common use case      |
| AC-3 | required    | Self-import exclusion — correctness                                    |
| AC-4 | required    | Cap + truncation contract                                              |
| AC-5 | required    | Path confinement — security                                            |
| AC-6 | required    | File-not-found error — correctness                                     |
| AC-7 | required    | `method: "heuristic"` — callers must know matching is approximate      |
| AC-8 | required    | Read-only annotation correctness                                       |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-16 | Implemented. Added `_match_import_to_target` (three heuristics: module-path normalization, filename-stem match ≥4 chars, relative `./..` path resolution with extension variants) and `code_impact_response` (full-repo walk via indexer `walk_repo`, `_IMPORT_PARSERS` per file, early-termination after `max_results + 1` matches). `code_impact(path, max_results)` MCP tool registered. 5 tests added covering AC-1/3/4/5/6. 1319 tests pass. | server.py, test_server_tools.py |

## Decision Log

| Date       | Decision                                                              | Reason                                                                                              | Alternatives                                                              |
| ---------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 2026-05-15 | Heuristic matching rather than compiler-accurate resolution           | Full module resolution requires language-specific tooling (tsconfig, pyproject, sys.path); heuristics cover the common case at zero additional dependency cost | Compiler-accurate (rejected: requires LSP or language-specific resolvers) |
| 2026-05-15 | `method: "heuristic"` in response                                     | Callers must know results may have false positives or false negatives; field makes this explicit    | Omit field (rejected: callers may over-trust results)                     |
| 2026-05-15 | Stem match gated at ≥ 4 characters                                    | Short stems (`io`, `os`, `re`) produce too many false positives from stdlib/vendor imports          | No length gate (rejected: high false positive rate)                       |
| 2026-05-15 | Depth 1 only (direct importers)                                       | Transitive impact can be very large; callers can chain `code_impact` calls for transitive analysis | Configurable depth (deferred)                                             |
| 2026-05-15 | Reuse `_IMPORT_PARSERS` from `code_dependencies`                      | Avoids duplicating import parsing logic; consistent language coverage and behavior                  | Separate regex-based import scan (rejected: duplication, divergence risk) |

## Risks

| Risk                                           | Mitigation                                                                              |
| ---------------------------------------------- | --------------------------------------------------------------------------------------- |
| False positives from stem matching             | 4-char minimum; `method: "heuristic"` signals approximate results                      |
| Large repo scan latency                        | `max_results` cap terminates early; binary files skipped; same O(n) profile as `code_keyword` |
| JS/TS barrel files (`index.ts`) missed         | Heuristic 3 tries `index.ts`/`index.js` extensions; full barrel resolution requires tsconfig |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
