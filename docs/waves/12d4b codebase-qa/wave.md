# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-04

wave-id: `12d4b codebase-qa`
Title: Code Insight Agent (CIA)

## Objective

Establish the Code Insight Agent (CIA): codebase QA agent, knowledge extraction, code search result diversity, CIA seed distribution, and agent guidance.

## Changes

Change ID: `12d4b-feat codebase-qa-agent`
Change Status: `implemented`

Change ID: `12d4h-feat codebase-knowledge-extraction`
Change Status: `implemented`

Change ID: `12d5s-enh code-search-result-diversity`
Change Status: `implemented`

Change ID: `12d82-feat cia-seed-distribution`
Change Status: `implemented`

Change ID: `12d8a-enh cia-agent-guidance`
Change Status: `implemented`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| architecture-reviewer | review | All three changes — MCP tool contracts, index routing (`_is_docs_kind`, `DOCS_SEARCH_KINDS`), module boundaries |
| code-reviewer | review | All three changes + 12d82 — `chunker.py`, `indexer.py`, `server.py` script correctness, pattern compliance, test coverage; seed-010/160/100 edits |
| qa-reviewer | review | All three changes + 12d82 + 12d8a — AC priority tables for all changes |
| performance-reviewer | review | 12d4h — new per-file extraction (`_chunk_code_summary`, `_chunk_doc_summary`, `_extract_code_symbols`); `_keyword_fallback_definitions` file walk |
| security-reviewer | review | 12d4h — `code_dependencies_response` path handling, `_keyword_fallback_definitions` `re.escape` usage; 12d4b — write-path constraint on `code_ask` |
| docs-contract-reviewer | review | 12d82 — seed-010/160/100 content accuracy and completeness; seed-211/212/213 fidelity to source prompt bodies; 12d8a — CIA prompt extended role coverage, seed-050 role-doc rules |

Completed At: 2026-05-04

## Wave Summary

Introduces the Code Insight Agent (CIA) — a read-only, retrieval-grounded agent with a `code_ask` MCP tool that accepts natural-language questions about the codebase and returns grounded, cited answers using the semantic code and docs indexes. Paired with knowledge extraction improvements: `kind="code-summary"` chunks, cross-language `code_references` fallback, `code_dependencies` tool, and seed guidance for consistent module documentation.

## Journal Watchpoints

- **Watchpoint — read-only constraint**: `code_ask` and the CIA must never call write-path MCP tools. Block any implementation that proposes edits or creates files.
- **Watchpoint — citation discipline**: every claim in a `code_ask` response must trace to a specific indexed chunk (file + line range). Block synthesis that asserts facts without citation.
- **Watchpoint — `server.py` single-author surface**: `code_ask` and `code_dependencies` registrations must not run concurrently with other server.py MCP tool changes.

## Review Signoff Evidence

- architecture-reviewer: approved — all 9 checklist items pass: `_is_docs_kind` routing correct, `DOCS_SEARCH_KINDS` includes `"doc-summary"`, `_doc_matches_kind` guard order correct, `docs_search` Literal schema updated, `search_code` filter order correct, `code_ask` write-path clean, keyword error guard present, CIA prompt sections present, `search-architecture.md` updated.
- code-reviewer: approved with notes — `kw_resp` error guard confirmed, `re.escape` in fallback confirmed, seeds generic-only, 902 tests pass. Notes (fixed): `_SYMBOL_PATTERNS` raw strings promoted to compiled patterns; `heading_pattern` moved to module-level `_DOC_HEADING_RE`; import regex patterns in `_parse_js_ts_imports`/`_parse_go_imports`/`_parse_rust_imports` moved to module-level constants. 12d82: seed-010/160/100 edits correct format and placement; 902 tests pass.
- qa-reviewer: approved — all required and important ACs covered across all three change docs; 5 named new tests confirmed present and passing; 902 tests pass. 12d82: all 7 required ACs verified (seeds 211–213 exist, seed-010/160/100 updated, 902 tests pass). 12d8a: all 4 required ACs verified (CIA prompt extended with planning/impl/persona guidance + fallback section + availability note, seed-211 matches, seed-050 MCP condition removed and unconditional, 902 tests pass).
- performance-reviewer: approved with notes — O(n) per-file model intact throughout. Notes (fixed): `_SYMBOL_PATTERNS` patterns pre-compiled; `_chunk_doc_summary` heading pattern moved to module level; import regex constants hoisted; `_keyword_fallback_definitions` result capped at 50.
- security-reviewer: approved after fix — `re.escape` confirmed in `_keyword_fallback_definitions`; write-path constraint clean; both tools `_READONLY_TOOL` annotated; excerpt capped. Fix applied: `code_dependencies_response` now uses `_resolve_repo_path` with escape check; traversal and absolute path rejection tests added.
- docs-contract-reviewer: approved (12d82) — seeds 211–213 content matches source prompt bodies exactly; seed-010 output list additions correctly formatted with file paths and seed references; seed-160 backfill sub-bullets correctly nested and named; seed-100 `Ask codebase` rule correctly scoped, MCP-conditional, and path-accurate. 12d8a: CIA prompt planning/implementation/persona guidance and fallback section complete, seed-211 matches exactly, seed-050 MCP condition removed and unconditional with correct forward-looking framing, references point to project-local path.

## Dependencies

- No external wave dependencies.
