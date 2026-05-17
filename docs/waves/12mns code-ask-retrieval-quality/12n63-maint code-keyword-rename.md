# Rename code_keyword_search → code_keyword (and code_constants_search → code_constants)

Change ID: `12n63-maint code-keyword-rename`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12mns

## Rationale

The framework naming rule for MCP tools is: **a tool carries the `_search` suffix if and only if it uses the semantic index (vector embeddings + reranker)**. Tools that operate by direct filesystem scan, regex, AST parsing, or exact-key index lookup do not carry `_search`. This rule gives agents an unambiguous signal about retrieval strategy from the tool name alone.

`code_keyword_search` and `code_constants_search` violate this rule — they are exact-match filesystem tools, not semantic tools. Renaming them before broad deployment eliminates the inconsistency at low cost.

## Requirements

1. `code_keyword_search` is renamed to `code_keyword` in `server.py`, all tests, all agent docs, all seed prompts, and `mcp-tool-surface.md`.
2. `code_constants_search` is renamed to `code_constants` in the same surfaces.
3. No behavioral change — signatures, return shapes, and semantics are unchanged.
4. After the rename, `grep -r "code_keyword_search\|code_constants_search" docs/ .wavefoundry/framework/seeds/ AGENTS.md` returns no matches.

## Scope

**Problem statement:** `code_keyword_search` and `code_constants_search` carry the `_search` suffix, implying semantic index involvement. They are exact-match filesystem tools. The canonical rule — `_search` iff semantic index — must be enforced consistently so agents can infer retrieval strategy from the tool name.

**In scope:**

- Rename `code_keyword_search` → `code_keyword` in `server.py` (function name, `@mcp.tool()` decorator, docstring references)
- Rename `code_constants_search` → `code_constants` in `server.py`
- Update all test files that reference the old names
- Update `AGENTS.md` tool table and any inline references
- Update `docs/agents/code-insight-agent.md`
- Update `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md`
- Update `docs/architecture/mcp-tool-surface.md` (or equivalent tool surface doc)
- Update any wave change docs that reference the old names

**Out of scope:**

- Any behavioral or signature changes to the tools themselves
- Renaming `code_search` or `docs_search` (those are correctly named)

## Acceptance Criteria

- AC-1: `code_keyword` is exposed as an MCP tool and responds identically to the old `code_keyword_search`.
- AC-2: `code_constants` is exposed as an MCP tool and responds identically to the old `code_constants_search`.
- AC-3a: `grep -r "code_keyword_search\|code_constants_search" docs/ .wavefoundry/framework/seeds/ AGENTS.md` returns no matches in active docs and seeds (historical closed-wave docs are exempt).
- AC-3b: `grep -r "code_keyword_search\|code_constants_search" .wavefoundry/framework/scripts/` returns no matches (server.py and test files fully renamed).
- AC-4: All existing tests that exercised the old tool names pass under the new names.
- AC-5: Test files do not contain the string `code_keyword_search` or `code_constants_search` (verified by AC-3b grep scope).

## Tasks

- Open `framework_edit_allowed` gate
- In `server.py`: rename `code_keyword_search` function and decorator to `code_keyword`; rename `code_constants_search` function and decorator to `code_constants`; update any internal docstring cross-references
- Update test files: rename all invocations of `code_keyword_search` → `code_keyword` and `code_constants_search` → `code_constants`
- Update `AGENTS.md`: rename in tool table, usage notes, and any inline text
- Update `docs/agents/code-insight-agent.md`: rename in tool references and Pass 3 comments
- Update `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md`: same renames
- Update wave change docs for `12n5x-enh code-keyword-search-multi-query` and `12n5x-enh code-constants-search` to use new names
- Update `docs/architecture/mcp-tool-surface.md` if it exists; update `docs/architecture/search-architecture.md` tool references
- Close `framework_edit_allowed` gate
- Run full test suite; verify AC-3 grep returns empty

## Agent Execution Graph

| Workstream              | Owner       | Depends On | Notes                                      |
| ----------------------- | ----------- | ---------- | ------------------------------------------ |
| server.py rename        | Engineering | —          | Open gate before; close after              |
| test updates            | Engineering | server.py  | Must match new names before running        |
| docs + seeds rename     | Engineering | —          | Can run in parallel with server.py rename  |
| verification (AC-3 grep)| Engineering | all above  | Final gate before wave_add_change complete |

## Serialization Points

- `server.py` must be renamed before tests are run (tests import or invoke tool by name).
- Wave change doc updates can be done in parallel with server.py and docs changes.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — update any tool-name references from `code_keyword_search` → `code_keyword` and `code_constants_search` → `code_constants`
- `docs/architecture/mcp-tool-surface.md` — update tool name entries
- No boundary, layer, or flow changes — this is a pure rename maintenance.

## AC Priority

| AC    | Priority  | Rationale                                                        |
| ----- | --------- | ---------------------------------------------------------------- |
| AC-1  | required  | Core deliverable                                                 |
| AC-2  | required  | Core deliverable                                                 |
| AC-3a | required  | Verifies no stale references in active docs/seeds/AGENTS.md      |
| AC-3b | required  | Verifies no stale references in server.py and test files         |
| AC-4  | required  | No regression                                                    |
| AC-5  | required  | Test files updated — not just server.py                          |

## Progress Log

| Date       | Update                                                               | Evidence                                               |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------------ |
| 2026-05-15 | Implemented: `code_keyword` rename complete in server.py + tests; all active docs, seeds, AGENTS.md swept; 1251 tests pass; AC-3a and AC-3b grep clean | `run_tests.py` → 1251 OK; AC-3 grep → no output |

## Decision Log

| Date       | Decision                                              | Reason                                         | Alternatives                        |
| ---------- | ----------------------------------------------------- | ---------------------------------------------- | ----------------------------------- |
| 2026-05-15 | Canonical rule: `_search` suffix iff tool uses semantic index (vector embeddings + reranker). Direct filesystem, regex, AST, and exact-key index lookup tools do not carry `_search`. | Gives agents an unambiguous signal about retrieval strategy from the tool name alone. Applies to all future tool additions. | Suffix-by-category (rejected: category boundaries drift); no convention (rejected: naming entropy) |
| 2026-05-15 | Rename both tools now; framework pre-broad-deployment | Low cost; eliminates naming drift before it propagates | Keep as-is (rejected: violates the rule established above) |

## Risks

| Risk                                  | Mitigation                                            |
| ------------------------------------- | ----------------------------------------------------- |
| Stale references left in docs/seeds   | AC-3 grep check catches any missed occurrences        |
| Test suite broken by rename           | AC-4: full test run required before closing change    |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
