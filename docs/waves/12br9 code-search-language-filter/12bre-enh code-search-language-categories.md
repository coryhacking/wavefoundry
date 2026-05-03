# Code Search Language Categories

Change ID: `12bre-enh code-search-language-categories`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12br9 code-search-language-filter`

## Rationale

Callers searching a multi-language codebase (e.g. a web frontend with TypeScript and JSX, or a data pipeline mixing SQL and Scala) had no way to filter by language family — they either searched everything or had to repeat the query per language. Adding category filters (`java`, `web`, `systems`, `script`, `data`, `sparksql`, `dotnet`) lets a single query span a related family while excluding noise from unrelated languages. `sparksql` as an alias for `sql` improves discoverability for data engineers who think in Spark terms rather than file extensions.

## Requirements

1. A `_LANG_CATEGORIES` map must define intent-based language groupings. Categories may overlap (a language may appear in more than one category).
2. Passing a category name to `code_search` must fetch results unfiltered then post-filter to chunks whose `language` is in the category set — no changes to `WaveIndex.search_code` signature.
3. Category responses must include `language_resolved` (sorted list of canonical language names in the category) and `language_extensions` (sorted list of all extensions across those languages).
4. Single-language and extension responses must not include `language_resolved` — only `language_extensions`.
5. Category resolution must take priority over extension normalization in the lookup chain.
6. `wave_help(goal='search_code')` must describe categories and when to use each filter form.
7. `docs/specs/mcp-tool-surface.md` Tool Selection Guide must include a "when to use" section covering no-filter, category, and exact-language scenarios with examples.
8. `_EXT_TO_LANG` must include config/data format extensions: `.json`, `.jsonc`, `.toml`, `.yaml`, `.yml`, `.kt`, `.kts`, `.groovy`, `.scala`, `.css`, `.scss`, `.sql`, `.xml`, `.html`, `.htm`, `.swift`.
9. A test must assert that every language in every category has at least one entry in `_LANG_TO_EXTS` — prevents categories referencing languages with no indexed extensions.

## Scope

**Problem statement:** No way to filter code search by language family; discoverability of the language filter was poor.

**In scope:**

- `_LANG_CATEGORIES` map in `server.py`
- `_EXT_TO_LANG` extended with config/data format extensions
- `code_search_response` category resolution and `language_resolved` field
- `code_search` tool docstring with inline routing guidance
- `wave_help(goal='search_code')` rationale updated
- `docs/specs/mcp-tool-surface.md` Tool Selection Guide extended with "when to use" section
- Tests: category expansion, post-filtering, `language_resolved`, `sparksql` alias, guard test

**Out of scope:**

- Fuzzy category matching (e.g. `"jvm"` as an alias for `"java"`) — exact match only
- Categories for `docs_search` — only `code_search` has a language filter
- Changing `WaveIndex.search_code` signature

## Acceptance Criteria

- AC-1: `code_search(language="web")` returns TypeScript, JavaScript, HTML, CSS, and SCSS chunks and includes `language_resolved: ["css", "html", "javascript", "scss", "typescript"]`.
- AC-2: `code_search(language="java")` covers java, kotlin, scala, groovy chunks.
- AC-3: `code_search(language="sparksql")` resolves to `language_resolved: ["sql"]`.
- AC-4: `code_search(language="data")` resolves to `language_resolved: ["sql"]`.
- AC-5: Single-language and extension queries do not include `language_resolved` in the response.
- AC-6: `language_resolved` and `language_extensions` are present in no-results and error response paths for category queries.
- AC-7: A guard test asserts every category language has at least one extension in `_LANG_TO_EXTS`.
- AC-8: `wave_help(goal='search_code')` describes all categories and when to use no-filter vs category vs exact.
- AC-9: Tool Selection Guide in `docs/specs/mcp-tool-surface.md` includes "when to use" guidance with concrete examples for each filter form.
- AC-10: All pre-existing framework tests continue to pass.

## Tasks

- [x] Add `_LANG_CATEGORIES` to `server.py`
- [x] Extend `_EXT_TO_LANG` with config/data format extensions
- [x] Update `code_search_response` for category resolution and `language_resolved`
- [x] Update `code_search` tool docstring with routing guidance
- [x] Update `wave_help(goal='search_code')` rationale
- [x] Update `docs/specs/mcp-tool-surface.md` Tool Selection Guide
- [x] Add `CodeSearchLanguageCategoryTests` (9 tests)

## Agent Execution Graph

| Workstream | Owner       | Depends On            | Notes                                         |
| ---------- | ----------- | --------------------- | --------------------------------------------- |
| server-map | Engineering | 12br9-enh (ext norm)  | `_LANG_CATEGORIES` + `_EXT_TO_LANG` extension |
| response   | Engineering | server-map            | Category resolution in `code_search_response` |
| docs       | Engineering | response              | Docstring + spec + wave_help                  |
| tests      | Engineering | response              | 9 new category tests                          |

## Serialization Points

- Depends on `12br9-enh` — extension normalization must land first so the resolution order (category → extension → canonical) is consistent.

## Affected Architecture Docs

N/A — enhancement confined to server.py query path and MCP spec doc. No boundary or data-flow architecture impact.

## AC Priority

| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | Core behavior — web category is the primary use case |
| AC-2  | required  | Core behavior — java category covers the JVM family |
| AC-3  | required  | sparksql alias is the discoverability hook for data engineers |
| AC-4  | required  | data category correctness |
| AC-5  | required  | Response shape contract — language_resolved must not appear in single-language responses |
| AC-6  | important | Consistency — error/no-results paths should match success path shape |
| AC-7  | required  | Guard test prevents silent category misconfiguration |
| AC-8  | required  | wave_help is the runtime discovery surface for agents |
| AC-9  | required  | Spec is the reference for human reviewers and documentation |
| AC-10 | required  | Non-regression gate |

## Progress Log

| Date       | Update                                                                  | Evidence              |
| ---------- | ----------------------------------------------------------------------- | --------------------- |
| 2026-05-02 | Implemented and tested. 743 tests passing. Spec and docstrings updated. | `run_tests.py` output |

## Decision Log

| Date       | Decision                                                                     | Reason                                                                                      | Alternatives |
| ---------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------ |
| 2026-05-02 | Categories are intent-based, not strict partitions — overlap allowed         | Scala belongs to both `java` (JVM) and could belong to `data` (Spark); intent wins over purity | Strict disjoint sets (rejected: Scala/Spark use case breaks it) |
| 2026-05-02 | `java` chosen over `jvm` as category name                                    | Simpler; developers know what Java means; Kotlin/Scala/Groovy users understand the grouping | `jvm` (rejected: too technical) |
| 2026-05-02 | `sparksql` as alias for `sql` rather than `spark` → `{scala, python, sql}`   | Spark code is in whatever language the repo uses; `sparksql` targets query files specifically | `spark` category covering scala+python+sql (rejected: too broad) |
| 2026-05-02 | Post-filter at response layer, not in `WaveIndex.search_code`                | Keeps the index layer simple; avoids changing a shared interface for a query-path concern   | Add `languages: set` param to `search_code` (rejected: over-engineering the index layer) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Category over-fetches (`n * len(category_langs)`) may return too few results if most chunks are in one language | Acceptable for now; top-n is clamped to 20; revisit if real query patterns show it |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
