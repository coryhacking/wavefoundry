# Codebase Knowledge Extraction

Change ID: `12d4h-feat codebase-knowledge-extraction`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12d4b codebase-qa`

## Rationale

The Codebase Ask Agent (12d4b-feat) relies on the semantic index for retrieval, but the index currently has structural gaps that reduce answer quality:

1. **No file-level summary chunks** — the agent must scan dozens of line-window chunks just to determine what a file does, burning context and missing files that aren't directly queried. This applies to both code files (no module overview) and doc files (no table of contents).
2. **`code_references` / `code_definition` are Python-only** — projects using JS/TS/Go/Rust get no structural symbol lookup, forcing the agent to fall back to broad semantic search for questions it should be able to answer precisely. Both tools need cross-language fallback.
3. **No dependency traversal** — "what does this file import" and "what depends on X" are unanswerable without a full file scan, blocking architectural questions.
4. **`docs/repo-index.md` orientation knowledge is not surfaced in the retrieval loop** — agents don't know to read it first, so well-maintained module inventory is often ignored.
5. **Module docstrings are inconsistent** — the chunker can extract them for `kind="code-summary"` chunks, but only if implementation agents write them consistently.

These gaps affect any agent that reasons about unfamiliar code, and are the primary bottleneck for quality answers on non-Python projects.

## Requirements

1. The chunker must produce one `kind="code-summary"` chunk per source file containing: the module-level docstring (or leading comment block), all top-level exported symbol names (functions, classes, constants), and the file path. This enables a fast orientation pass before targeted retrieval.
2. The chunker must produce one `kind="doc-summary"` chunk per doc/seed/prompt markdown file containing: the first paragraph (purpose statement) and all H1/H2/H3 headings extracted and concatenated. This gives the CIA a table-of-contents anchor for each doc file without retrieving individual sections. Routed to the docs index.
3. `code_references(symbol_name)` must fall back to `code_keyword_search(symbol_name)` when AST-based lookup is unavailable (non-Python files). Results must be tagged with `"method": "keyword_fallback"` so callers can distinguish from structural results.
4. A new `code_dependencies(path)` MCP tool must accept a repo-relative file path and return the list of imported modules/files extracted from that file's import statements. Computed on demand (not pre-indexed). Must support Python, JavaScript/TypeScript, Go, and Rust at minimum.
5. Seed-030 (inventory agent) must include a structured `## Module: <name>` format for entries in `docs/repo-index.md`, covering: one-sentence purpose, public entry points, and key dependencies. This makes repo-index.md machine-readable for orientation passes.
6. Seed-100 (project prompt surface bootstrap) must include guidance that implementation agents write module-level docstrings in a consistent one-sentence-purpose format so `kind="code-summary"` chunks are meaningfully populated. Seed-100 was chosen because it owns the repo's coding conventions and standards documentation surface.
7. `CHUNKER_VERSION` must be bumped after the `kind="code-summary"` and `kind="doc-summary"` changes to force a full index rebuild.

## Scope

**Problem statement:** The index captures line-window code and markdown sections but lacks file-level summaries for both code and docs, cross-language structural navigation, and dependency traversal. This limits the Ask Agent to broad semantic search for questions that should have precise structural answers.

**In scope:**

- `chunker.py` — new `kind="code-summary"` chunk type (code files: module docstring + symbol names) and `kind="doc-summary"` chunk type (doc/seed/prompt files: first paragraph + heading list); `CHUNKER_VERSION` bump
- `indexer.py` — emit `code-summary` chunks in code index dispatch; emit `doc-summary` chunks in docs index dispatch
- `server.py` — `code_references` and `code_definition` cross-language fallback to `code_keyword_search`; new `code_dependencies(path)` MCP tool; `docs_search` `kind="doc-summary"` filter support
- `.wavefoundry/framework/seeds/030-repo-inventory.prompt.md` — structured `## Module:` format for `docs/repo-index.md` entries (requires `seed_edit_allowed` gate)
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` — module docstring convention guidance (requires `seed_edit_allowed` gate)
- `docs/architecture/search-architecture.md` — document `kind="code-summary"`, `kind="doc-summary"`, `code_dependencies`, and cross-language reference fallback
- Tests: `test_chunker.py` for `kind="code-summary"` and `kind="doc-summary"` extraction; `test_server_tools.py` for `code_references`/`code_definition` fallback, `code_dependencies`, and `docs_search(kind="doc-summary")`

**Out of scope:**

- Full call graph or cross-file call analysis (major complexity, deferred)
- Class hierarchy indexing (limited incremental value)
- Automated docstring generation (agents write them; this change establishes the convention)
- Runtime type information
- Streaming or incremental `code_dependencies` for very large files

## Acceptance Criteria

- AC-1: `chunk_file(source, "src/foo.py")` returns a chunk with `kind="code-summary"` containing the module docstring and top-level symbol names (capped at 20 symbols per file to bound chunk size)
- AC-2: `code_search(query, kind="code-summary")` returns only summary chunks; unfiltered `code_search` includes summary chunks alongside line-window chunks ranked by relevance
- AC-3: `chunk_file(source, "docs/architecture/search-architecture.md")` returns a chunk with `kind="doc-summary"` containing the first paragraph and a concatenated heading list
- AC-4: `docs_search(query, kind="doc-summary")` returns only doc-summary chunks; unfiltered `docs_search` includes doc-summary chunks alongside section chunks
- AC-5: `code_references("MyComponent")` on a TypeScript file returns results tagged `"method": "keyword_fallback"` with the same shape as structural results — same keys, consistent field names — rather than an error
- AC-6: `code_definition("MyComponent")` on a TypeScript file returns results tagged `"method": "keyword_fallback"` rather than an error
- AC-7: `code_dependencies("src/billing.py")` returns `{path, imports: [{module, resolved_path?, resolved: bool}], method}` for a Python file
- AC-8: `code_dependencies("src/App.tsx")` returns imported paths for a TypeScript file
- AC-9: `code_dependencies` returns `{path, imports: [], method: "unsupported"}` (not an error) for files with no imports or unsupported languages
- AC-10: Seed-030 `docs/repo-index.md` guidance includes `## Module: <name>` format with purpose, entry points, and dependencies fields
- AC-11: Seed-100 includes module docstring convention guidance
- AC-12: `CHUNKER_VERSION` is bumped
- AC-13: All pre-existing framework tests pass

## Tasks

**Preflight:** seed edits require `seed_edit_allowed` gate — open before seed tasks, close immediately after.

- [ ] `chunker.py`: add `kind="code-summary"` chunk type; extract module docstring (first docstring or leading `#` comment block) and top-level exported symbol names (`def`, `class`, `export function`, `export class`, `export const`, `func`, `type`, `struct` by language); cap symbol list at 20 entries; emit one summary chunk per file; bump `CHUNKER_VERSION`
- [ ] `chunker.py`: add `kind="doc-summary"` chunk type for markdown files routed to the docs index (doc/seed/prompt kinds); extract first paragraph + all H1/H2/H3 headings concatenated; emit one doc-summary chunk per file; no additional `CHUNKER_VERSION` bump needed (same bump as code-summary)
- [ ] `indexer.py` `_is_docs_kind()`: add `"doc-summary"` to the set — `kind in ("doc", "seed", "prompt", "doc-summary")`; without this, doc-summary chunks route to the code index silently
- [ ] `indexer.py`: emit `code-summary` chunks in the code index dispatch path; emit `doc-summary` chunks in the docs index dispatch path
- [ ] `server.py` `_doc_matches_kind()`: add `"doc-summary"` branch — matches chunks with `kind="doc-summary"`
- [ ] `server.py` `search_code()`: add optional `kind` parameter; filter results to `r.get("kind") == kind` when provided; no change to default behavior
- [ ] `server.py` `code_references`: detect non-Python file and fall back to `code_keyword_search`; tag results with `"method": "keyword_fallback"`
- [ ] `server.py` `code_definition`: detect non-Python file and fall back to `code_keyword_search`; tag results with `"method": "keyword_fallback"`
- [ ] `server.py` `code_dependencies`: new MCP tool; parse import statements on demand; support Python (`import`/`from … import`), JS/TS (`import`/`require`), Go (`import`), Rust (`use`); return `{path, imports: [{module, resolved_path?, resolved: bool}], method: "ast"|"regex"|"unsupported"}`; unsupported language returns `method: "unsupported"` with empty `imports`
- [ ] Seed-030: add `## Module: <name>` format guidance with purpose, entry points, dependencies fields (gate: `seed_edit_allowed`)
- [ ] Seed-100: add module docstring convention guidance (gate: `seed_edit_allowed`)
- [ ] `docs/architecture/search-architecture.md`: add `kind="code-summary"` orientation layer, `code_dependencies` tool, cross-language reference fallback sections
- [ ] Tests: `test_chunker.py` — `kind="code-summary"` extraction for Python, JS/TS, Go; no summary for empty files; symbol cap at 20; `kind="doc-summary"` extraction for markdown with headings; doc-summary contains first paragraph + heading list; `test_server_tools.py` — `code_search(kind="code-summary")` filter; `docs_search(kind="doc-summary")` filter; `code_references` fallback tagged `method: "keyword_fallback"`; `code_definition` fallback tagged `method: "keyword_fallback"`; `code_dependencies` for Python and TS; `method: "unsupported"` and empty `imports` for unsupported language

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| `kind="code-summary"` chunker | Engineering | — | chunker.py + CHUNKER_VERSION bump |
| `kind="doc-summary"` chunker | Engineering | — | chunker.py — same bump; first paragraph + heading list |
| indexer dispatch | Engineering | code-summary + doc-summary chunker | emit summary chunks in both code and docs dispatch paths |
| `code_search` kind filter | Engineering | — | server.py — one-line addition to `search_code()`; required for CIA orientation pass |
| `_is_docs_kind` + `_doc_matches_kind` | Engineering | doc-summary chunker | indexer.py + server.py — must land before indexer dispatch or doc-summary routes to wrong index |
| `docs_search` doc-summary filter | Engineering | `_is_docs_kind` update | server.py — `_doc_matches_kind` new branch |
| `code_references` fallback | Engineering | — | server.py — independent of chunker |
| `code_definition` fallback | Engineering | — | server.py — same pattern as `code_references` fallback |
| `code_dependencies` tool | Engineering | — | server.py — independent of chunker |
| seed edits | Engineering | — | seed-030, seed-100; requires gate; independent of code |
| architecture doc | Engineering | code-summary + code_dependencies | after tool shapes are settled |
| tests | Engineering | all workstreams | test_chunker.py + test_server_tools.py |

## Serialization Points

- `chunker.py` and `indexer.py` share the chunk dispatch path — coordinate summary chunk emission with existing code chunk path; do not parallelize these two workstreams.
- Seed edits require `seed_edit_allowed` gate — open before, close immediately after; do not run concurrently with other seed edits.
- `server.py` is a single-author surface — `code_references` fallback and `code_dependencies` can be implemented in one pass.
- **Sequencing with CIA (12d4b-feat):** `kind="code-summary"` chunks improve CIA orientation pass quality but are not a prerequisite. `code_references` fallback and `code_dependencies` can land in parallel with CIA implementation. Recommended order: implement 12d4h workstreams first or in parallel, then CIA integration testing with the enriched index.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — `kind="code-summary"` and `kind="doc-summary"` orientation layers, `code_dependencies` tool, cross-language reference/definition fallback

## AC Priority

| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | Core chunk type — Ask Agent code orientation pass depends on it |
| AC-2  | required  | `kind` filter on `code_search` enables CIA orientation pass; without it summary chunks are present but not isolatable |
| AC-3  | required  | Core doc-summary chunk — CIA docs orientation pass depends on it |
| AC-4  | required  | `kind` filter on `docs_search` enables CIA to isolate doc-summary chunks for orientation |
| AC-5  | required  | Cross-language projects need usable reference lookup |
| AC-6  | required  | `code_definition` and `code_references` are symmetric tools — both need the same cross-language fallback |
| AC-7  | required  | Python dependency traversal is the most common case |
| AC-8  | important | TS/JS is the second most common; error degrades answer quality |
| AC-9  | required  | Empty result is safe; error is not |
| AC-10 | required  | Machine-readable repo-index.md enables orientation pass |
| AC-11 | important | Docstring convention improves summary chunk quality over time |
| AC-12 | required  | Forces rebuild after kind change |
| AC-13 | required  | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-04 | Change doc created from design session | Research: existing chunk kinds, structural gaps, MCP tool surface audit |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-04 | `code_dependencies` computed on demand, not pre-indexed | Import graphs change frequently; on-demand computation avoids stale index; single file parse is fast | Pre-index dependency graph (deferred: high complexity, stale risk) |
| 2026-05-04 | `code_references` fallback to `code_keyword_search` rather than a new tool | Preserves existing tool surface; callers get results instead of errors; `method` tag preserves transparency | New `code_references_any_language` tool (rejected: unnecessary surface growth) |
| 2026-05-04 | `code_definition` fallback uses same keyword pattern as `code_references` | Symmetric tools should have symmetric fallback behavior; one implementation pattern for both | Different fallback strategy per tool (rejected: inconsistent caller experience) |
| 2026-05-04 | One summary chunk per file (not per class/module section) | Orientation pass needs a single retrievable anchor per file; multiple summary chunks per file would dilute relevance | Per-class summaries (deferred: over-indexing at v1) |
| 2026-05-04 | `kind="doc-summary"` routed to docs index (not a new separate index) | Doc summaries are documentation about docs — same embedding model, same search surface, filterable via `docs_search(kind="doc-summary")`; adding a third index would complicate merging and health checks | Separate summary index (rejected: complexity); no kind filter, just mix with doc chunks (rejected: not isolatable for orientation pass) |
| 2026-05-04 | Doc-summary content: first paragraph + heading list (not full section text) | First paragraph is the purpose statement; headings are a table of contents — together they answer "does this doc cover what I need?" without duplicating section content already in the index | Full doc re-chunk as single summary (rejected: too large, dilutes embedding signal); headings only (rejected: loses purpose statement) |
| 2026-05-04 | Seed changes in same wave as code changes | Docstring convention and repo-index.md format are prerequisites for summary chunk quality; shipping without the convention guidance leaves the feature half-baked | Separate wave for seed changes (rejected: incomplete without convention) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Summary chunk quality poor for files without docstrings | Chunk still emits symbol list even without docstring; seed guidance improves adoption over time |
| `code_dependencies` regex misses complex import patterns | Tag results with `"method": "regex"` vs `"method": "ast"`; Ask Agent treats regex results with lower confidence |
| `CHUNKER_VERSION` bump forces ~6 min full rebuild for all users | `wave_index_health` `chunker_version_mismatch` advisory surfaces this automatically; documented in upgrade notes |
| Summary chunks increase index size | One chunk per file is bounded; typical project has hundreds of source files, not millions |
| Doc-summary heading extraction misses non-standard heading formats | ATX headings (`#`, `##`, `###`) cover the vast majority of markdown docs; setext headings are rare and can be added later |
| First paragraph absent in docs with no preamble (starts directly with a heading) | Heading list alone is still useful; chunk emits headings-only when no first paragraph exists |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
