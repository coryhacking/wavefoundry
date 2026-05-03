# Code Search Language Extension Normalization

Change ID: `12br9-enh code-search-language-extension-normalization`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12br9 code-search-language-filter`

## Rationale

After fixing the language tag mismatch, `code_search(language="typescript")` works correctly — but passing `language="tsx"` or `language=".tsx"` still returns nothing. Callers shouldn't need to know the canonical name; passing a file extension should be equivalent. Additionally, the response gives no feedback about which extensions are covered by a given language filter, making it hard to diagnose empty results.

## Requirements

1. `code_search` must normalize a raw extension (e.g. `"tsx"`, `".tsx"`) to its canonical language name before filtering.
2. The response must include a `language_extensions` field listing the file extensions covered by the resolved language filter, or `null` when no filter is applied.
3. The normalized canonical language name must be echoed back in the response `language` field regardless of what the caller passed.
4. Normalization and `language_extensions` must be present in all response paths: success, no-results, index-not-ready, and model-unavailable.
5. An unknown value (not a recognized extension or canonical name) must be passed through unchanged with `language_extensions: null` — no error.

## Scope

**Problem statement:** `code_search` only accepted canonical language names; raw extensions silently returned zero results. Responses gave no visibility into which extensions were being filtered.

**In scope:**

- `code_search_response` in `server.py`: normalization logic, `language_extensions` field in all response paths
- `_LANG_TO_EXTS` reverse map derived from `_EXT_TO_LANG`
- `code_search` tool docstring updated to document both forms and list canonical names with their extensions
- `docs/specs/mcp-tool-surface.md` updated with canonical name list and extension equivalence
- Tests covering: canonical passthrough, extension without dot, extension with dot, specific normalizations, `language_extensions` in all response paths, unknown extension passthrough

**Out of scope:**

- Fuzzy matching or partial language name matching (e.g. `"type"` → `"typescript"`) — exact match only
- Normalization in `code_keyword_search` or other tools — only `code_search` uses the language filter

## Acceptance Criteria

- AC-1: `code_search(language="tsx")` and `code_search(language=".tsx")` both filter to TypeScript chunks (same as `language="typescript"`).
- AC-2: Response `language` field always contains the canonical name, never the raw extension passed by the caller.
- AC-3: Response `language_extensions` lists extensions for the resolved language (e.g. `["ts", "tsx"]` for typescript), sorted alphabetically.
- AC-4: `language_extensions` is `null` when no language filter is applied.
- AC-5: `language_extensions` is present in no-results and error response paths (not only success).
- AC-6: An unrecognized value (e.g. `"lua"`) is passed through with `language_extensions: null` — no error.
- AC-7: `docs/specs/mcp-tool-surface.md` documents both canonical names and raw extensions as accepted input, with the full canonical name → extensions mapping.
- AC-8: All 709 pre-existing framework tests continue to pass.

## Tasks

- [x] Add `_LANG_TO_EXTS` reverse map to `server.py`
- [x] Add extension normalization in `code_search_response` before search and response construction
- [x] Add `language_extensions` to all four response paths in `code_search_response`
- [x] Update `code_search` tool docstring
- [x] Update `docs/specs/mcp-tool-surface.md`
- [x] Add `CodeSearchLanguageNormalizationTests` covering all ACs

## Agent Execution Graph

| Workstream      | Owner       | Depends On    | Notes                                    |
| --------------- | ----------- | ------------- | ---------------------------------------- |
| server-response | Engineering | bug fix (12br9-bug) | Normalization + language_extensions |
| spec-docs       | Engineering | server-response | MCP spec update                        |
| tests           | Engineering | server-response | 12 new test cases                      |

## Serialization Points

- Depends on `12br9-bug` — normalization is only meaningful once canonical names are stored correctly in chunks.

## Affected Architecture Docs

N/A — enhancement confined to `code_search_response` in server.py and MCP spec doc. No boundary or flow architecture impact.

## AC Priority

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | Core behavior — the primary UX improvement |
| AC-2 | required      | Callers must be able to trust the echoed value |
| AC-3 | important     | Useful for debugging; not blocking for search correctness |
| AC-4 | important     | Consistency — null is the correct sentinel |
| AC-5 | important     | Error paths should be consistent with success path |
| AC-6 | required      | Unknown values must not error |
| AC-7 | important     | Agents need accurate docs to use the filter correctly |
| AC-8 | required      | Non-regression gate |

## Progress Log

| Date       | Update                                                                     | Evidence              |
| ---------- | -------------------------------------------------------------------------- | --------------------- |
| 2026-05-02 | Implemented and tested. 734 tests passing. Spec updated.                   | `run_tests.py` output |

## Decision Log

| Date       | Decision                                                                 | Reason                                                        | Alternatives |
| ---------- | ------------------------------------------------------------------------ | ------------------------------------------------------------- | ------------ |
| 2026-05-02 | Derive `_LANG_TO_EXTS` from `_EXT_TO_LANG` at module load rather than hardcoding | Single source of truth; stays in sync automatically | Hardcoded reverse map (rejected: would drift) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| None identified. | — |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
