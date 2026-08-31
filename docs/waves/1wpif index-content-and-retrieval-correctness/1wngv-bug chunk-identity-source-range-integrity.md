# Preserve Chunk Identity and Source Ranges

Change ID: `1wngv-bug chunk-identity-source-range-integrity`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpif index-content-and-retrieval-correctness

## Rationale

The index currently contains distinct CSS, JavaScript, and TOML chunks that share an ID, so the unique-ID registry and FTS layer retain only one of several real source chunks. Oversized Markdown, RST, and AsciiDoc sections also emit section-relative line ranges as though every section began at line 1. Those false coordinates can produce incorrect citations and cause `_agent_candidate_select` to collapse distinct evidence sharing `(path, lines)`. These are supported-path content-loss and citation-integrity defects.

## Requirements

1. Every emitted chunk ID SHALL be stable and unique within its source file for distinct content, including repeated flat tree-sitter selectors and symbols.
2. Every chunk line range SHALL use one-based absolute source-file coordinates and resolve to the chunk's source-derived payload; generated breadcrumbs or headings are verified separately and SHALL NOT be treated as literal source-range text.
3. Candidate deduplication SHALL remove true duplicates without collapsing distinct chunks solely because legacy metadata shares a path and line range.
4. Index health or build verification SHALL detect same-ID/distinct-content collisions before reporting full derived-state coverage.
5. Python code summaries SHALL enumerate module-level classes and functions without allowing nested methods or nested functions to consume the top-level symbol cap.
6. The change SHALL preserve unaffected chunk IDs where possible, bump the appropriate chunker/index compatibility version, and document the required rebuild.
7. For a non-colliding flat-emitter base, the legacy ID SHALL remain unchanged. A collision group SHALL use one deterministic per-file disambiguation rule with an explicit same-line tie-break, and insertion or reordering of an earlier same-slug sibling SHALL not churn unrelated chunk IDs.
8. Retrieval deduplication SHALL key evidence by `(normalized_path, normalized_lines, chunk_hash)`. When `chunk_hash` is absent, it SHALL use a deterministic digest of the canonical returned evidence fields. Only identical keys merge; merged evidence preserves its source provenance.
9. Collision disambiguation SHALL use keyed state with O(chunks-per-file) time and memory. The repository collision census SHALL be O(total emitted chunks), consume already-materialized build rows, perform no second repository chunking or embedding pass, and add no more than 10% wall-clock overhead versus a same-tree chunk/build baseline.

## Scope

**Problem statement:** Chunk identity and source-coordinate defects silently remove searchable content and can miscite the content that remains.

**In scope:**

- Flat tree-sitter chunk ID generation for CSS, JavaScript, TOML, and sibling emitters using the same helper.
- Absolute line-offset propagation for oversized Markdown, RST, and AsciiDoc prose.
- Retrieval-result deduplication identity and collision diagnostics.
- Python module-summary symbol extraction and cap behavior.
- Regression fixtures, corpus census, version bump, and architecture documentation.

**Out of scope:**

- Changing embedding models or reranker policy.
- Rewriting all chunk IDs when an existing unique ID remains valid.
- General prose chunk-size tuning.

## Acceptance Criteria

- [ ] AC-1: A whole-repository census reports zero same-ID/distinct-content chunks and zero registry/FTS losses attributable to chunk-ID collision.
- [ ] AC-2: Markdown, RST, and AsciiDoc oversized-section fixtures report absolute line ranges that select the source-derived payload exactly, with any generated breadcrumb/header asserted separately.
- [ ] AC-3: Selection retains two distinct chunks with the same path and legacy line range while still removing exact duplicate evidence.
- [ ] AC-4: Incremental and full builds produce equivalent chunk sets, and unaffected unique chunks retain stable IDs.
- [ ] AC-5: Health/build diagnostics fail or warn explicitly on an injected same-ID/distinct-content collision.
- [ ] AC-6: In a Python module containing a class with at least twenty methods followed by a module-level function, nested methods do not consume the summary cap and the later module-level function remains in the summary.
- [ ] AC-7: The chunker/index version and chunking/search architecture documentation identify the compatibility boundary and rebuild requirement; focused and full framework tests pass.
- [ ] AC-8: Same-slug insertion/reordering fixtures preserve unrelated IDs, and same-path/same-range rows with different hashes both survive selection while an exact clone collapses once and retains all source provenance.
- [ ] AC-9: On a synthetic growing collision corpus, doubling chunks preserves linear row visits, each file is chunked once, embedding call count is unchanged, the census consumes materialized rows, and same-tree measured overhead is at most 10%.

## Tasks

- [ ] Route flat-emitter ID bases through a stable per-file collision guard.
- [ ] Add absolute base-line support to prose line-window chunking and all section callers.
- [ ] Replace path-and-lines-only result deduplication with content-aware stable identity.
- [ ] Freeze the deterministic collision disambiguator, same-line tie-break, canonical fallback digest, and provenance-preserving merge behavior.
- [ ] Instrument collision/census row visits, chunker invocations, embedding calls, and same-tree wall-clock overhead.
- [ ] Add collision census and health/build diagnostics.
- [ ] Use module-structure-aware Python summary extraction and add nested-symbol fixtures.
- [ ] Add structural, retrieval-selection, incremental-equivalence, and rebuild tests.
- [ ] Update chunking/search architecture documentation and compatibility versions.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Chunk emission | implementer | — | IDs and absolute coordinates |
| Retrieval identity | implementer | Chunk emission | Selection and diagnostics |
| Verification | qa-reviewer | Both | Corpus census and regression fixtures |

## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`, `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/`, `docs/architecture/chunking-and-indexing-pipeline.md`, `docs/architecture/search-architecture.md`

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents silent index content loss. |
| AC-2 | required | Source citations must identify the actual indexed text. |
| AC-3 | required | Fixes the observed retrieval evidence collapse. |
| AC-4 | required | Protects incremental stability and compatibility. |
| AC-5 | important | Makes future collisions observable before healthy publication. |
| AC-6 | important | Preserves top-level orientation in method-heavy Python modules. |
| AC-7 | required | Rebuild/version and verification contracts must remain explicit. |
| AC-8 | required | Makes chunk identity and retrieval deduplication executable rather than relying on ambiguous “content-aware” behavior. |
| AC-9 | required | Prevents collision detection from adding quadratic work or a second indexing pass. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned from the multi-agent index-quality audit. | 8,019 code rows versus 7,741 unique IDs; 150 same-ID/distinct-content groups; absolute-line probes on oversized prose. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Repair emit-time identity and coordinates, use module-structure-aware Python summary extraction, then make selection robust to legacy collisions. | It fixes index metadata at its source and keeps module orientation structurally honest. | **Selection-only repair:** leaves FTS/registry content loss and summary omissions. **Append counters plus regex-only summary extraction:** destabilizes unaffected IDs and keeps nested-symbol misclassification. |

## Risks

| Risk | Mitigation |
| --- | --- |
| ID changes cause a large one-time delta. | Preserve already-unique IDs, bump compatibility explicitly, and compare full versus incremental output. |
| Content-aware deduplication returns redundant evidence. | Retain exact-duplicate suppression and add targeted result-diversity tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
