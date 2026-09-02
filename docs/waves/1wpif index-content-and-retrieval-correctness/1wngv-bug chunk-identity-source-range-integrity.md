# Preserve Chunk Identity and Source Ranges

Change ID: `1wngv-bug chunk-identity-source-range-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-02
Wave: 1wpif index-content-and-retrieval-correctness

## Rationale

The index currently contains distinct CSS, JavaScript, and TOML chunks that share an ID, so the unique-ID registry and FTS layer retain only one of several real source chunks. Oversized Markdown, RST, and AsciiDoc sections also emit section-relative line ranges as though every section began at line 1. Those false coordinates can produce incorrect citations and cause `_agent_candidate_select` to collapse distinct evidence sharing `(path, lines)`. These are supported-path content-loss and citation-integrity defects.

## Requirements

1. Every emitted chunk ID SHALL be stable and unique within its source file for distinct content, including repeated flat tree-sitter selectors and symbols.
2. Every chunk line range SHALL use one-based absolute source-file coordinates and SHALL contain the chunk's source-derived payload; generated breadcrumbs or headings are verified separately and SHALL NOT be treated as literal source-range text. For windows and table row-group parts the range SHALL be the minimal contiguous span containing that part's own payload.
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

- [x] AC-1: A whole-repository census reports zero same-ID/distinct-content chunks and zero registry/FTS losses attributable to chunk-ID collision.
- [x] AC-2: Markdown, RST, and AsciiDoc chunks report one-based ABSOLUTE line ranges that CONTAIN their source-derived payload, with any generated breadcrumb/header asserted separately. Exactness is scoped by chunk class (delivery-repair clarification, 2026-08-31): a whole section keeps its section span (heading through section end), while an oversized-section window and a table row-group part carry the MINIMAL contiguous span containing their own payload — a window straddling an excised block (fence, rst code directive, adoc listing) carries the minimal span containing its payload, and reproduced context (the injected breadcrumb, the splice artifact, and the prelude plus table header a row-group part after the first repeats for column context) is generated, never counted as source text. Verified by fixtures plus a whole-repository census over every md/rst/adoc file that classifies each prose chunk exact / minimal-superset / wrong and requires zero wrong.
- [x] AC-3: Selection retains two distinct chunks with the same path and legacy line range while still removing exact duplicate evidence.
- [x] AC-4: Incremental and full builds produce equivalent chunk sets, and unaffected unique chunks retain stable IDs.
- [x] AC-5: Health/build diagnostics fail or warn explicitly on an injected same-ID/distinct-content collision.
- [x] AC-6: In a Python module containing a class with at least twenty methods followed by a module-level function, nested methods do not consume the summary cap and the later module-level function remains in the summary.
- [x] AC-7: The chunker/index version and chunking/search architecture documentation identify the compatibility boundary and rebuild requirement; this change's own suites and every test it adds pass, the documents this change edits validate, and no failure elsewhere is attributable to this change. (Locality repair 2026-09-02: the clause formerly read "focused and full framework tests pass", asserting repository-wide state this change does not control. The whole-suite result is a close-time gate recorded in the wave record, not an acceptance criterion; advisory sensor `ac_asserts_repository_state`, wave `1wur7`.)
- [x] AC-8: Same-slug insertion/reordering fixtures preserve unrelated IDs, and same-path/same-range rows with different hashes both survive selection while an exact clone collapses once and retains all source provenance.
- [x] AC-9: On a synthetic growing collision corpus, doubling chunks preserves linear row visits, each file is chunked once, embedding call count is unchanged, the census consumes materialized rows, and same-tree measured overhead is at most 10% under a declared protocol (paired same-process runs, at least three measured repetitions, median or pooled nearest-rank p95 declared before measurement; the countable assertions are the primary oracle and the wall-clock bound is advisory evidence, so the number cannot be tuned to noise; QA-RDY-5/PERF-RDY-5).

## Tasks

- [x] Route flat-emitter ID bases through a stable per-file collision guard.
- [x] Add splice-aware absolute line mapping to prose line-window chunking and all section callers: windows map to original body coordinates across extracted fenced-code spans in `chunk_markdown`, `_emit_prose_sections`, the oversized-body decomposition callers, and the universal oversize guard (`split_large_chunks`/`_line_wrap_chunk`, which line-windows any over-cap chunk with text-relative offsets and the same splice blindness; CODE-RDY-3) — a base offset alone cannot meet AC-2 after a fence (prepare-council A4); fixtures place a fence before the oversized prose, including one routed through the universal guard.
- [x] Replace path-and-lines-only result deduplication with content-aware stable identity.
- [x] Freeze the deterministic collision disambiguator, same-line tie-break, canonical fallback digest, and provenance-preserving merge behavior.
- [x] Instrument collision/census row visits, chunker invocations, embedding calls, and same-tree wall-clock overhead; the census detector consumes real materialized build rows (the store's `chunk_sync_raw`/`unique` counters are the existing O(total chunks) source) and the synthetic growing corpus proves scaling only, never defines the detector (red-team hazard: tests reflect the system); the overhead bound's timing protocol is specified so it cannot be tuned to noise.
- [x] Add collision census and health/build diagnostics.
- [x] Use module-structure-aware Python summary extraction and add nested-symbol fixtures.
- [x] Add structural, retrieval-selection, incremental-equivalence, and rebuild tests.
- [x] Update chunking/search architecture documentation and compatibility versions.

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
- `docs/architecture/performance-budget.md` (the docs-constants lint binds "chunker version `39`" there, so the bump fails the docs gate without it; AC-9's census-overhead budget also lands in its structural-budget table; ARCH-RDY-3)

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
| 2026-09-02 | Delivery reverification cycles 3 and 4, harness scope. **`CODE-RV2-2`:** an independent AST census found three `setUp`-level bare imports of the server module beyond the file already repaired; two genuinely failed standalone and are converted to the shared loader, the third already ran standalone and was left alone. The next lane re-derived the census independently over 42 import sites across the whole tests tree, confirmed exactly one remains at `setUp` scope (the deliberate exclusion), and ran every class holding a bare import in isolation with all green, so nothing was missed. | `test_server_tools.BackgroundBuildReapRegistryTests` and `test_fts_lexical_layer.LexicalFusionWiringTests` now run standalone; reverting both reproduces the import error in every test of both classes. |
| 2026-09-02 | Delivery reverification cycle 2, oracle repairs. The independent qa lane re-derived the coordinate census from a fresh corpus walk (1,743 files, 23,206 prose chunks, zero wrong) and independently covered the table row-group class the original attestation missed (2,016 parts, zero wrong), killing a source-level pre-repair mutant at 1,962 wrong. **QA-RV1-1**: its `_classify` has a fourth verdict, `empty`, and the census test asserted only `wrong == 0`, so a chunk that escaped classification was scored neither right nor wrong; under the pre-repair mutant the bucket absorbed chunks that would otherwise have been flagged. The test now asserts `empty == 0` as well. **CODE-RV1-1**: the independent code lane confirmed `_candidate_merge_key` is applied at all four merge seams but proved only the hybrid fusion seam was pinned, reverting either of the other three individually left the whole 8,051-test suite green. A source pin now fixes the seam count at eight call expressions inside `search_combined` and asserts the legacy `(path, tuple(lines))` key exists nowhere in production. | `ChunkCoordinateContractTests.test_repository_prose_coordinate_census_reports_zero_wrong` (now asserting the `empty` bucket; the lane's pre-repair mutant reports `empty` non-zero); `CandidateMergeIdentityTests.test_every_merge_seam_keys_on_the_candidate_identity`. Landing rule: reverting seam 3 to the legacy key fails the pin with `7 != 8`, a revert the full suite previously missed. |
| 2026-09-02 | Wave reopened for review attribution (`wf_reopen_wave(purpose='review')`) to finish the outstanding attestation. AC-7 locality repair: the criterion asserted "focused and full framework tests pass", which this change does not control; it now asserts this change's own suites, the documents it edits, and the absence of an attributable failure elsewhere. The whole-suite result stays a close-time gate in the wave record. No code changed. | Advisory sensor `ac_asserts_repository_state` (wave `1wur7`) cleared for this document; `wf_validate_docs`. |
| 2026-08-31 | Thought: delivery-repair order for the builder lane, seams read through MCP before any edit. (1) RED-DEL-1 table row groups: the coordinate defect is that `_decompose_oversized_table_chunk` anchors every emitted part at the table head (`table_start_line`) and the `split_large_chunks` remap re-derives the index from that same head, so parts 2..n carry the header's lines; the repair moves the mapping INTO the decomposer, which alone knows each group's row offset, and emits a per-part `line_map` so an over-cap part still line-wraps with absolute coordinates. Reproduced header/separator on parts 2..n becomes generated context (map entry `None`), so a part's range is exactly its own rows. (2) RED-DEL-4 `_dedupe_chunk_ids` seeds its counter from the FULL original id multiset and loops until the resolved id is unused, so a generated `-L{n}` can never equal a natively emitted one. (3) CODE-DEL-3 rst/adoc preambles carry per-line absolute numbers (the doc-title block is excised from the middle of the body, so a single base offset cannot describe it). (4) Version 41 with the corrected version-40 comment scope. Then the coordinate census over the real repository md/rst/adoc corpus as the falsifying oracle for the whole class. | This log row; the repair rows below. |
| 2026-08-31 | Delivery repair landed (RED-DEL-1, RED-DEL-4, CODE-DEL-3, plus the version and comment corrections). chunker.py: `_decompose_oversized_table_chunk` now owns the coordinate mapping (per-group row offsets, a per-part `line_map`, prelude/header reproduced on parts 2..n marked generated) and the broken `split_large_chunks` remap that re-derived every index from the table head is gone; `_dedupe_chunk_ids` checks its generated `-L{n}` base against the FULL original id set and re-tie-breaks until unused; `_rst_process_body` / `_adoc_process_body` / `_emit_prose_sections` accept per-line absolute numbers so the preamble and only-title sections stop numbering their first RETAINED line as 1 (the sections tuple carries `body_numbers`, and the chunk's own `lines` bounds come from it); `_extract_python_module_symbols` degrades to the regex scan on `RecursionError` / `MemoryError` as well; `CHUNKER_VERSION` 41 with a rationale naming both stored-coordinate corrections and the rebuild requirement, and the version-40 comment's "select the payload exactly" overclaim is now scoped per chunk class. Version-bound figures updated: `performance-budget.md` chunker version, the chunking pipeline doc's mismatch and version-table entries, and the `test_chunker` version pin (with the 40 -> 41 transition line). AC-2 and Requirement 2 amended to the scoped contract; Decision Log row added. | test_chunker.py 568 tests OK (10 new in `ChunkCoordinateContractTests`, one superseded tautological test removed). Live example now correct: `docs/architecture/current-state.md#current-risk-areas:L133-L141:rows6-7` reports (140, 141) for rows living at 140-141 (was (133, 136)). |
| 2026-08-31 | Coordinate census over the real repository is the class-level oracle: 1,726 md/rst/adoc files, 22,848 prose chunks, **zero wrong** (7,077 exact, 15,771 minimal-superset), 1.3 s. Wrong means a payload line outside the stored range or a range opening on a non-payload line; minimal-superset means the extras are blanks or excised-block lines a contiguous range cannot exclude. The census is proven non-vacuous by a paired test that restores the pre-repair anchoring on the same fixture and asserts it reports wrong. The golden-corpus id test is no longer tautological: it now asserts the EMITTER output (pre-guard) is already unique on that corpus, that the terminal guard is a proven no-op there, and that the FINAL set — whose oversize-guard window and row-group ids the guard never sees — is unique. | `ChunkCoordinateContractTests.test_repository_prose_coordinate_census_reports_zero_wrong`, `...detects_the_pre_repair_row_group_anchor`, `...test_golden_corpus_ids_are_unique_before_and_after_the_terminal_guard`. |
| 2026-08-31 | Live rebuild (coordinator): the real index was rebuilt under chunker 40 (generation 6, attempt `a4298f9b`); the store-side census reads zero id collisions and full registry/FTS coverage (docs 26,617 rows, code 8,245 rows, previously 7,881 unique of 8,159 raw), so AC-1's live-store clause is met on the production store, not only the in-process census; the standing gate's holdout metrics are unchanged against the `1sear` baseline. | `index_health` after `wf_reload_mcp`; `docs/reports/retrieval-quality-post-1wpif*.json`. |
| 2026-08-30 | Planned from the multi-agent index-quality audit. | 8,019 code rows versus 7,741 unique IDs; 150 same-ID/distinct-content groups; absolute-line probes on oversized prose. |
| 2026-08-31 | Code landed across all four seams. chunker.py: CHUNKER_VERSION 40; flat-emitter per-file guard (bare first occurrence, `{slug}-L{start}` for k>=2, `~k` same-line tie-break); `Chunk.line_map` carrier plus `_spliced_line_numbers`/`_line_bounds_after_strip`/`_map_window_lines`; splice-aware absolute coordinates in `chunk_markdown` (all four branches), `_split_h3_sections`, `_decompose_oversized_markdown_body`, `_emit_prose_sections` with 3-tuple `_rst_process_body`/`_adoc_process_body`; map-aware `_line_wrap_chunk` (suffix `~k` dedupe for char-split pieces of one long line) and table-decomposition remap; ast module-level Python summary; terminal `_dedupe_chunk_ids` guard at the `chunk_file` boundary (covers structured-chunker fallback qnames such as the dashboard.js `ErrorBoundary.method` trio the census exposed). server_impl.py: `_agent_candidate_select._key` re-keyed to (normalized path, normalized lines, chunk_hash or sha256 digest of id/kind/section/text); `_state_store_health_summary` id_collisions passthrough; `index_health_response` chunk_id_collisions diagnostic. index_state_store.py: `chunk_id_collision_census`, `chunk_id_collision_counts`, census meta persisted at `rebuild_chunk_index`, reconcile passthrough plus stderr/store-log warning. indexer.py: `_sync_chunk_derived_state` census surfacing. | Whole-repo in-process census after the fix: 2130 files, 56387 chunks, ZERO same-ID/distinct-content groups and ZERO duplicate-id groups (pre-fix baseline on the same tree: 150 groups / 563 losses; interim rerun caught 77 residual groups from the structured-chunker and char-split classes, both then fixed). Census overhead reference: paired same-process rebuilds, 3 interleaved reps, median 53.6 ms vs 52.0 ms on 8000 synthetic rows (ratio 1.03). |
| 2026-08-31 | FULL framework suite green: 7802 tests across 67 files, OK (3 skipped), 131.5 s wall / 698.4 s worker time via `run_tests.py --no-cache`; `wf_validate_docs` passed with the chunker-version-40 docs-constants binding; no `__pycache__` residue under scripts. AC-7 marked; Change Status set to implemented. | Full-suite runner output in session transcript. |
| 2026-08-31 | Regression suites landed and green on focused runs: test_chunker.py 559 tests OK (new `ChunkIdentitySourceRangeTests`, 16 tests: flat-emitter frozen rule for toml/css, minified same-line `~k` tie-break, insertion stability, terminal `_dedupe_chunk_ids` guard, golden-corpus per-file id-uniqueness census, md/rst/adoc window payload-exactness, universal-guard parts, seed decompose maps, char-split suffix dedupe, determinism, python summary); test_index_state_store.py 47 OK (new `ChunkIdCollisionCensusTests`, 7 tests: detection vs churn duplicates, linear row visits 400/800, hashless skip, injected store-row collision recorded plus reconcile warning and in-sync persistence, materialized-rows spy with chunker/embedder sentinels, paired-median advisory overhead bound); test_indexer.py 315 OK (unchanged-set no-op with zero embeds; single-changed-chunk embeds exactly once); test_server_tools_retrieval.py 933 OK (distinct-hash same-path/lines survival, exact-clone collapse with three-source provenance, hashless digest fallback, index_health chunk_id_collisions diagnostic). All tasks and AC-1..AC-6, AC-8, AC-9 marked; AC-7 awaits the full-suite run. Coordinator-owned residue: the live `.wavefoundry/index/` rebuild under chunker 40 plus the store-side census receipt (zero registry/FTS losses on the LIVE store) after that rebuild; the in-process whole-repository census on this tree is already zero. | Focused runner outputs in session transcript; census and timing numbers in the prior rows. |
| 2026-08-31 | Markdown differential snapshot regenerated as a deliberate versioned step (the 1whup precedent): 24 of 26 rows byte-identical; the 2 changed rows are `docs/oversized.md#deployment/rollback` lines [33,36]->[36,36] and `#deployment/verification` [37,39]->[40,40], both verified payload-exact against the fixture source (the old ranges were heading-anchored spans; the new ranges select exactly the prose payload). | Classification probe output in session transcript; `MarkdownDifferentialTests` and `UniversalOversizedChunkGuardTests` green post-regen. |
| 2026-08-31 | Thought: implementation order for the builder lane: (1) flat-emitter per-file ID guard with the frozen line-anchor disambiguation and `~k` same-line tie-break; (2) splice-aware line maps: shared splice/strip helpers, `Chunk.line_map` carrier, `chunk_markdown` (whole-section, oversized-window, H3-split, preamble), `_emit_prose_sections` plus both `process_body` line-number returns, `_decompose_oversized_markdown_body`, and map-aware `_line_wrap_chunk`/table decomposition in the universal guard; (3) AST-based Python module summary with regex fallback on SyntaxError; (4) `_agent_candidate_select` re-key to (normalized path, normalized lines, chunk_hash-or-digest); (5) collision census in `rebuild_chunk_index` with meta persistence, reconcile pass-through, and `index_health` diagnostic; (6) `CHUNKER_VERSION` 40 bump plus the three architecture docs; (7) tests per AC then focused and full suites. MCP-first retrieval completed across chunker/indexer/index_state_store/server_impl seams before any edit. | This log row; retrieval evidence in session transcript. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-31 | Delivery-repair clarification of the AC-2 coordinate contract: `lines` is a contiguous one-based ABSOLUTE range that CONTAINS the chunk's source-derived payload, and exactness is SCOPED — a whole section keeps its section span, while an oversized-section window and a table row-group part carry the MINIMAL span containing their own payload; a window straddling an excised block carries the minimal span containing its payload; reproduced context (breadcrumb, splice artifact, and the prelude plus table header repeated on row-group parts after the first) is generated and never anchors a range. The census over the real corpus is the oracle for the whole class. | The version-40 comment and the original AC wording said ranges "select the source-derived payload exactly", which is true only for windows and parts: whole sections deliberately span their heading and any content the chunk text does not repeat. The unqualified claim hid a real defect behind an unmeetable standard, and the reviewer's row-group class (1,075 of 1,413 live parts wrong) needed a per-class contract to be checkable at all. | **Keep the unqualified wording:** no census can pass it, so nothing would be measured. **Make whole sections minimal too:** would drop the heading anchor and the section-span contract every consumer already reads, a far larger chunk-shape change with no citation benefit. |
| 2026-08-31 | Prepare-council amendment A4 plus the red-team census hazard: the prose line-window task requires splice-aware mapping to original body coordinates across extracted fence spans (a base offset alone still miscites post-fence windows because `chunk_markdown`/`_emit_prose_sections` character-splice fences out before windowing), with a fence-before-prose fixture; the collision census detector consumes real materialized build rows and the synthetic corpus proves scaling only. | The primer verified the splice by reading the chunker (windows are numbered within a spliced slice, not the section) and reproduced 150 colliding groups / 563 losses in-process on the live tree; the standing rule is that tests reflect the system, never the reverse. | **Base offset only:** meets the task wording while failing AC-2. **Synthetic-corpus detector:** the fixture-shaped-prior class the 1seaw council removed. |
| 2026-08-30 | Repair emit-time identity and coordinates, use module-structure-aware Python summary extraction, then make selection robust to legacy collisions. | It fixes index metadata at its source and keeps module orientation structurally honest. | **Selection-only repair:** leaves FTS/registry content loss and summary omissions. **Append counters plus regex-only summary extraction:** destabilizes unaffected IDs and keeps nested-symbol misclassification. |

## Risks

| Risk | Mitigation |
| --- | --- |
| ID changes cause a large one-time delta. | Preserve already-unique IDs, bump compatibility explicitly, and compare full versus incremental output. |
| Content-aware deduplication returns redundant evidence. | Retain exact-duplicate suppression and add targeted result-diversity tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
